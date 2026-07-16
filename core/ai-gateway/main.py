"""
KI Enterprise AI Gateway.

Tum modeller (GPT, Claude, Gemini, DeepSeek, Qwen, Ollama, Hermes...) LiteLLM uzerinden
buradan gecer. Bu servis, LiteLLM'in onune ince ve amaca-ozel bir katman koyar:

  POST /api/chat       - genel sohbet tamamlama
  POST /api/reason     - adim adim akil yurutme (sistem prompt'u ile guclendirilmis)
  POST /api/embedding  - metin embedding
  POST /api/agent      - tool-calling destekli ajan tamamlama

Tum uclar Authorization: Bearer <INTERNAL_API_KEY> ister - ucretli model proxy'sinin
kimliksiz acikta durmasi onlenir.
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-gateway")

app = FastAPI(title="KI Enterprise AI Gateway")

# Faz C - kota-farkinda ekonomi. Redis TTL 48 saat (172800s) - eski gunlerin
# sayaclari otomatik silinir, elle temizlik gerekmez.
QUOTA_KEY_TTL_SECONDS = 172800


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        # Aciklanamayan/gecici 401'lerin teshisi icin: header hic yok mu, yanlis mi?
        reason = "header eksik" if not authorization else "key eslesmiyor"
        logger.warning(f"401 - yetkisiz istek ({reason})")
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


# priority: "low" (self-improvement analizi gibi kritik-olmayan arka plan isleri),
# "normal" (worker deliverable uretimi gibi standart is), "high" (CEO plan uretimi/
# chat gibi kritik yol - kota kontrolunden HER ZAMAN muaf). Varsayilan "normal" -
# priority belirtmeyen eski cagiranlar davranissal olarak DEGISMEZ (ne engellenir
# ne otomatik ucuzlatilir) ta ki kota gercekten dolana kadar.
class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: Optional[str] = None
    temperature: float = 0.7
    priority: str = "normal"


class ReasonRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    priority: str = "normal"


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: Optional[str] = None


class AgentRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: Optional[list[dict[str, Any]]] = None
    model: Optional[str] = None
    priority: str = "normal"


@app.on_event("startup")
async def startup():
    app.state.http = httpx.AsyncClient(
        base_url=settings.LITELLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LITELLM_API_KEY}"},
        timeout=90.0,
    )
    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, decode_responses=True
    )


@app.on_event("shutdown")
async def shutdown():
    await app.state.http.aclose()
    await app.state.redis.aclose()


def _today_key(model: str | None = None) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"quota:tokens:{date}:{model}" if model else f"quota:tokens:{date}"


async def _get_today_total() -> int:
    try:
        val = await app.state.redis.get(_today_key())
        return int(val) if val else 0
    except Exception as e:
        # Redis kesintisinde FAIL-OPEN: kota kontrolu devre disi kalir ama
        # servis durmaz - LLM erisimi kota-izlemeye bagimli hale getirilmez.
        logger.warning(f"Redis'ten kota okunamadi, kota kontrolu bu istek icin atlaniyor: {e}")
        return -1


async def _track_usage(model: str, usage: dict | None):
    if not isinstance(usage, dict):
        return
    total_tokens = usage.get("total_tokens")
    if not isinstance(total_tokens, int):
        return
    try:
        pipe = app.state.redis.pipeline()
        pipe.incrby(_today_key(), total_tokens)
        pipe.expire(_today_key(), QUOTA_KEY_TTL_SECONDS)
        pipe.incrby(_today_key(model), total_tokens)
        pipe.expire(_today_key(model), QUOTA_KEY_TTL_SECONDS)
        await pipe.execute()
    except Exception as e:
        logger.warning(f"Kota sayaci guncellenemedi (istek yine de basariyla tamamlandi): {e}")


async def _check_quota(priority: str) -> tuple[bool, str | None, bool]:
    """(izin_verildi, ret_nedeni, ucuz_modele_zorla) doner.

    - priority="high": kota kontrolunden HER ZAMAN muaf (CEO plan/chat gibi kritik yol).
    - Kota kapaliysa (DAILY_TOKEN_BUDGET<=0) veya Redis'e erisilemiyorsa: fail-open.
    - >=%100 (HARD): sadece high gecer, low/normal REDDEDILIR.
    - >=SOFT (varsayilan %80): low REDDEDILIR, normal en ucuz modele ZORLANIR, high dokunulmaz.
    """
    if priority == "high":
        return True, None, False
    budget = settings.DAILY_TOKEN_BUDGET
    if budget <= 0:
        return True, None, False
    used = await _get_today_total()
    if used < 0:
        return True, None, False  # Redis'e erisilemedi - fail-open
    ratio = used / budget
    if ratio >= 1.0:
        if priority == "low":
            return False, f"Gunluk token kotasi doldu ({used}/{budget}), dusuk oncelikli istekler durduruldu.", False
        return False, f"Gunluk token kotasi doldu ({used}/{budget}), sadece kritik (priority=high) istekler kabul ediliyor.", False
    if ratio >= settings.QUOTA_SOFT_THRESHOLD_RATIO:
        if priority == "low":
            pct = int(settings.QUOTA_SOFT_THRESHOLD_RATIO * 100)
            return False, f"Gunluk token kotasinin %{pct}'i doldu ({used}/{budget}), dusuk oncelikli istekler ertelendi.", False
        return True, None, True  # normal -> en ucuz modele zorla, high zaten yukarida gecti
    return True, None, False


async def _post(path: str, payload: dict) -> dict:
    try:
        resp = await app.state.http.post(path, json=payload)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"LiteLLM erisilemedi: {e}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    await _track_usage(payload.get("model", "unknown"), data.get("usage"))
    return data


async def _resolve_model_with_quota(requested_model: Optional[str], default_model: str, priority: str) -> str:
    """Kota kontrolunu uygular, gerekirse HTTPException(429) firlatir, aksi
    halde kullanilacak nihai model adini doner (kota esigini gectiyse cagiranin
    istegini GORMEZDEN GELIP en ucuz modele zorlar - kota korumasi tercih onceligine
    ustundur)."""
    allowed, reason, force_cheap = await _check_quota(priority)
    if not allowed:
        raise HTTPException(status_code=429, detail={"status": "quota_saver", "reason": reason})
    if force_cheap:
        logger.info(f"Kota esigi asildi, istek {settings.CHEAP_FALLBACK_MODEL}'e zorlaniyor (priority={priority}).")
        return settings.CHEAP_FALLBACK_MODEL
    return requested_model or default_model


@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest):
    model = await _resolve_model_with_quota(req.model, settings.DEFAULT_CHAT_MODEL, req.priority)
    payload = {
        "model": model,
        "messages": req.messages,
        "temperature": req.temperature,
    }
    return await _post("/chat/completions", payload)


@app.post("/api/reason", dependencies=[Depends(verify_api_key)])
async def reason(req: ReasonRequest):
    model = await _resolve_model_with_quota(req.model, settings.DEFAULT_REASON_MODEL, req.priority)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Adim adim, mantikli bir sekilde dusun ve gerekcelendirilmis bir sonuca var."},
            {"role": "user", "content": req.prompt},
        ],
        "temperature": 0.3,
    }
    return await _post("/chat/completions", payload)


@app.post("/api/embedding", dependencies=[Depends(verify_api_key)])
async def embedding(req: EmbeddingRequest):
    # Embedding cagirilari kota-gate'ine TABI DEGIL (kucuk/ucuz, Memory Layer'in
    # temel islevi bunlara bagli - kota dolsa bile engellenmemeli); yine de
    # tuketimi tally'e YAZILIR (_post icinde), sadece reddedilmez/dusurulmez.
    payload = {"model": req.model or settings.DEFAULT_EMBEDDING_MODEL, "input": req.input}
    return await _post("/embeddings", payload)


@app.post("/api/agent", dependencies=[Depends(verify_api_key)])
async def agent(req: AgentRequest):
    model = await _resolve_model_with_quota(req.model, settings.DEFAULT_AGENT_MODEL, req.priority)
    payload = {
        "model": model,
        "messages": req.messages,
    }
    if req.tools:
        payload["tools"] = req.tools
    return await _post("/chat/completions", payload)


@app.get("/api/quota", dependencies=[Depends(verify_api_key)])
async def quota():
    """Bugunku toplam + model-bazli token tuketimini ve kalan kotayi doner -
    Faz B gunluk raporu ve dashboard bunu okuyabilir."""
    used = await _get_today_total()
    used = max(used, 0)
    budget = settings.DAILY_TOKEN_BUDGET
    per_model = {}
    try:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prefix = f"quota:tokens:{date}:"
        async for key in app.state.redis.scan_iter(match=f"{prefix}*"):
            val = await app.state.redis.get(key)
            per_model[key[len(prefix):]] = int(val) if val else 0
    except Exception as e:
        logger.warning(f"Model-bazli kota kirilimi alinamadi: {e}")
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "used_tokens": used,
        "daily_budget": budget,
        "remaining_tokens": max(0, budget - used) if budget > 0 else None,
        "usage_ratio": round(used / budget, 4) if budget > 0 else None,
        "soft_threshold_ratio": settings.QUOTA_SOFT_THRESHOLD_RATIO,
        "per_model": per_model,
    }


@app.get("/health")
async def health():
    try:
        # base_url ".../v1" iceriyor, liveliness ucu /v1 altinda degil - mutlak URL kullan.
        resp = await app.state.http.get(
            settings.LITELLM_API_BASE.removesuffix("/v1") + "/health/liveliness", timeout=5.0
        )
        litellm_ok = resp.status_code == 200
    except Exception:
        litellm_ok = False
    try:
        redis_ok = await app.state.redis.ping()
    except Exception:
        redis_ok = False
    return {"status": "ok" if (litellm_ok and redis_ok) else "degraded", "checks": {"litellm": litellm_ok, "redis": redis_ok}}
