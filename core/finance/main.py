"""
KI Enterprise Finance Data Layer (core/finance).

CFO'nun (Vera) gercek veriyle calisabilmesi icin uc kaynak saglar:
  1. Banka ekstresi/CSV - MANUEL yukleme (henuz gercek bir banka API'sine
     baglanti YOK - bu bilincli bir kapsam siniri, kullanici acikca "banka
     API'si yok, CSV yeter" dedi). Ayristirma deterministik (Python csv
     modulu) yapilir, LLM'e GITMEZ - FinRobot'un "deterministic compute,
     LLM narration" ilkesiyle ayni gerekce: rakamlar kod tarafinda kesin
     hesaplanir, yorumlama/analiz core/skills'teki CFO skill'lerine (LLM)
     birakilir.
  2. Gercek piyasa verisi - crypto (CoinGecko), hisse (Stooq), doviz
     (exchangerate.host) - ucuncu, ANAHTARSIZ/UCRETSIZ API'lerden CANLI
     cekilir (sirket politikasi: once ucretsiz).
  3. Islem gecmisi - yuklenen ekstreler Memory Layer'a (mem_type=global,
     scope_key="finance:transactions") kaydedilir, GET ile geri okunabilir.

Bilinen kapsam sinirlari (bilerek ertelendi):
  - Rakip/urun fiyatlandirma verisi CANLI CEKILMEZ (hedef-spesifik scraping
    ayri, cok daha buyuk bir muhendislik/yetkilendirme karari) - CFO/CMO
    hala core/skills:competitor-analysis (LLM akil yurutmesi) kullanir.
  - LiteLLM'in kendi /spend uclari mevcut master key ile 403 donuyor
    (proxy_admin scope kisiti) - sirketin GERCEK AI/bulut maliyeti bu
    servise henuz baglanmadi, infrastructure/litellm config degisikligi
    gerektirir (ayri onay/karar konusu).
"""
import csv
import hashlib
import io
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance")

REQUIRED_COLUMNS = {"date", "description", "amount"}
MAX_ROWS_PER_UPLOAD = 2000
MAX_CSV_CHARS = 500_000


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=15.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Finance Data Layer", lifespan=lifespan)


class StatementUpload(BaseModel):
    csv_text: str
    source_label: str = "unlabeled"


def _parse_statement(csv_text: str) -> tuple[list[dict], list[str]]:
    """CSV'yi deterministik olarak (LLM'siz) ayristirir - date/description/amount
    zorunlu kolonlardir, category opsiyoneldir. Basarisiz/eksik satirlar
    dusurulmez, ayri bir 'errors' listesinde raporlanir (sessiz veri kaybi olmasin)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="CSV bos veya basliksiz")

    normalized_fields = {f.strip().lower() for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - normalized_fields
    if missing:
        raise HTTPException(status_code=422, detail=f"CSV'de eksik zorunlu kolon(lar): {missing}. Gerekli: {REQUIRED_COLUMNS}")

    rows, errors = [], []
    for i, raw_row in enumerate(reader):
        if i >= MAX_ROWS_PER_UPLOAD:
            errors.append(f"satir {i}: MAX_ROWS_PER_UPLOAD ({MAX_ROWS_PER_UPLOAD}) asildi, geri kalan satirlar atlandi")
            break
        row = {k.strip().lower(): (v.strip() if v else v) for k, v in raw_row.items()}
        try:
            amount = float(row["amount"])
        except (TypeError, ValueError, KeyError):
            errors.append(f"satir {i}: gecersiz/eksik 'amount': {row.get('amount')!r}")
            continue
        if not row.get("date") or not row.get("description"):
            errors.append(f"satir {i}: 'date' veya 'description' eksik")
            continue
        rows.append({
            "date": row["date"],
            "description": row["description"],
            "amount": amount,
            "category": row.get("category") or None,
        })
    return rows, errors


@app.post("/api/v1/finance/statements/upload", dependencies=[Depends(verify_api_key)])
async def upload_statement(request: StatementUpload):
    if len(request.csv_text) > MAX_CSV_CHARS:
        raise HTTPException(status_code=422, detail=f"CSV {MAX_CSV_CHARS} karakteri asamaz")

    rows, errors = _parse_statement(request.csv_text)

    stored, store_failures = 0, 0
    for row in rows:
        # Idempotency: ayni (kaynak, tarih, aciklama, tutar) tekrar yuklenirse
        # duplicate satir OLUSTURMAZ - ayni ekstrenin yanlislikla iki kez
        # yuklenmesi (kullanici hatasi) sessizce cift sayilmasin diye.
        fingerprint = f"{request.source_label}:{row['date']}:{row['description']}:{row['amount']}"
        idempotency_key = hashlib.sha256(fingerprint.encode()).hexdigest()
        content = {**row, "source_label": request.source_label, "uploaded_at": datetime.now(timezone.utc).isoformat()}
        try:
            resp = await app.state.http.post(
                f"{settings.MEMORY_API_URL}/api/v1/memory/store",
                headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
                json={
                    "mem_type": "global", "scope_key": "finance:transactions",
                    "content": content, "idempotency_key": idempotency_key,
                },
            )
            resp.raise_for_status()
            stored += 1
        except httpx.HTTPError as e:
            logger.warning(f"Islem Memory'e yazilamadi: {e}")
            store_failures += 1

    return {
        "parsed_rows": len(rows), "stored": stored, "store_failures": store_failures,
        "parse_errors": errors,
    }


@app.get("/api/v1/finance/transactions", dependencies=[Depends(verify_api_key)])
async def get_transactions(limit: int = 50):
    if not (1 <= limit <= 500):
        raise HTTPException(status_code=422, detail="limit 1-500 araliginda olmali")
    try:
        resp = await app.state.http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": "global", "scope_key": "finance:transactions", "limit": limit},
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory'den okunamadi: {e}")
    items = resp.json().get("items", [])
    return {"transactions": [i["content"] for i in items]}


@app.get("/api/v1/finance/market/crypto/{coin_id}", dependencies=[Depends(verify_api_key)])
async def get_crypto_price(coin_id: str):
    """CANLI fiyat - CoinGecko'nun ucretsiz/anahtarsiz ucundan. coin_id
    CoinGecko'nun kendi id'sidir (orn. 'bitcoin', 'ethereum')."""
    try:
        resp = await app.state.http.get(
            f"{settings.COINGECKO_URL}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"CoinGecko'ya erisilemedi: {e}")
    if coin_id not in data:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen coin_id: {coin_id} (CoinGecko id formatinda olmali)")
    return {"coin_id": coin_id, "usd": data[coin_id].get("usd"), "usd_24h_change": data[coin_id].get("usd_24h_change"), "fetched_at": datetime.now(timezone.utc).isoformat()}


YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


@app.get("/api/v1/finance/market/stock/{ticker}", dependencies=[Depends(verify_api_key)])
async def get_stock_price(ticker: str):
    """CANLI fiyat - Yahoo Finance'in ucretsiz/anahtarsiz chart ucundan.
    ticker orn. 'AAPL', 'THYAO.IS' (Yahoo'nun kendi sembol/borsa-soneki kurallari gecerli)."""
    try:
        resp = await app.state.http.get(
            f"{settings.YAHOO_FINANCE_URL}/{ticker}",
            params={"interval": "1d", "range": "1d"},
            headers=YAHOO_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Yahoo Finance'e erisilemedi: {e}")
    results = data.get("chart", {}).get("result")
    if not results:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen ticker veya veri yok: {ticker}")
    meta = results[0]["meta"]
    return {
        "ticker": ticker, "currency": meta.get("currency"),
        "price": meta.get("regularMarketPrice"), "previous_close": meta.get("previousClose") or meta.get("chartPreviousClose"),
        "exchange": meta.get("fullExchangeName"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/finance/market/fx/{base}/{quote}", dependencies=[Depends(verify_api_key)])
async def get_fx_rate(base: str, quote: str):
    """CANLI doviz kuru - open.er-api.com'un ucretsiz/anahtarsiz ucundan."""
    try:
        resp = await app.state.http.get(f"{settings.EXCHANGERATE_URL}/latest/{base.upper()}")
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"open.er-api.com'a erisilemedi: {e}")
    rate = data.get("rates", {}).get(quote.upper())
    if data.get("result") != "success" or rate is None:
        raise HTTPException(status_code=404, detail=f"Kur bulunamadi: {base}/{quote}")
    return {"base": base.upper(), "quote": quote.upper(), "rate": rate, "fetched_at": datetime.now(timezone.utc).isoformat()}


@app.get("/health")
async def health():
    checks = {}
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    try:
        resp = await app.state.http.get(f"{settings.COINGECKO_URL}/ping", timeout=5.0)
        checks["market_data"] = resp.status_code == 200
    except Exception:
        checks["market_data"] = False
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
