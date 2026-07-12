"""
KI Enterprise Executive Board (Phase 3).

CEO altinda calisir. Departman/worker katmani (Phase 4/5) henuz kurulmadigi icin
Executive Board su an CEO'nun ürettigi planlari 5 yonetici perspektifinden
(CTO/CFO/CMO/COO/CISO) inceler, kararlarini Memory Layer'a kaydeder.

CFO icin build order'daki maliyet kurali aynen uygulanir:
  "Once ucretsiz, sonra self-hosted, sonra open source, sonra ucretli.
   Her maliyet kullanici onayi ister."
Plan ucretli/paid bir servis/kaynak iceriyorsa CFO cost_flag=true isaretler ve
requires_user_approval alani true doner - Workflow Engine (core/workflow/workflows.py,
ApprovalMixin) bu alani GERCEK bir kapi olarak kullanir: true ise CEO'nun
POST /api/v1/ceo/dispatch/{id}/approve ucuyla approve_cost sinyali gonderilene
kadar task.<workflow> event'i yayinlanmaz.

Guvenlik notu: LLM ciktisi semaya uymuyorsa veya cfo alani hic yoksa, "fail-open"
(cost_flag=False, otomatik onay) DEGIL "fail-safe" (cost_flag=True, onay bekletilir)
davranilir - parse edilemeyen bir yanit "maliyet yok" anlamina gelmemeli.

Bu servis kasitli olarak Workflow Engine'in bir activity'si DEGIL, ayri bir
servistir - ilerideki gelistirme surecinde her birim (CEO, Executive Board,
Departmanlar, Worker'lar) bagimsiz olarak yonetilecek.
"""
import asyncio
import json
import logging
import secrets

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("executives")

app = FastAPI(title="KI Enterprise Executive Board")

ROLES = ["cto", "cfo", "cmo", "coo", "ciso"]
# Plan icerigi kullanici/CEO tarafindan uretilen serbest metindir - sisteme
# talimat enjekte etmeyi zorlastirmak icin uzunluk sinirlanir (ayrica gereksiz
# token/maliyet de onlenir).
MAX_PLAN_CHARS = 4000

# Tek dogruluk kaynagi: core/personas/PERSONAS.md (Yonetim Kurulu bolumu).
# Orada degisirse burasi da elle guncellenmeli (ayri servis/venv - dogrudan import edilemiyor).
REVIEW_SYSTEM_PROMPT = """Sen KI Enterprise sirketinin Executive Board'usun - 5 ayri
karakterin sesisin, her biri kendi bakis acisiyla degerlendirir. Sana bir CEO plani
verilecek. SADECE asagidaki JSON semasina uyan bir cikti uret, baska hicbir metin ekleme:

{
  "cto": {"verdict": "onay|kaygi|red", "notes": "teknik degerlendirme, 1-2 cumle"},
  "cfo": {"verdict": "onay|kaygi|red", "notes": "finansal degerlendirme, 1-2 cumle", "cost_flag": true|false},
  "cmo": {"verdict": "onay|kaygi|red", "notes": "pazarlama degerlendirmesi, 1-2 cumle"},
  "coo": {"verdict": "onay|kaygi|red", "notes": "operasyonel degerlendirme, 1-2 cumle"},
  "ciso": {"verdict": "onay|kaygi|red", "notes": "guvenlik degerlendirmesi, 1-2 cumle"}
}

Karakterler (notes alanini bu sesle yaz):
- cto = Kai: pragmatik kidemli muhendis. Abartili/moda teknolojiye degil kanitlanmis,
  bakimi kolay cozumlere guvenir. Teknik borc/olceklenebilirlik riskini nazik ama net soyler.
- cfo = Vera: rakam onceliki, dogasi geregi supheci - her ucretli harcamayi once
  sorgular. Net ROI gorunce onaylar, gerekcesiz harcamaya izin vermez.
- cmo = Iris: buyume/marka odakli, iyimser. Isin disaridan/musteri gozunden nasil
  gorundugunu dusunur.
- coo = Leo: surec/yurutme takintili. Zaman cizelgesi, bagimlilik, kaynak planlamasi
  onun derdi. Kapsam kaymasina (scope creep) toleransi dusuk.
- ciso = Nora: guvenlik oncelikli, "paranoyak ama adil" - gercek riski isaretler,
  tiyatro yapmaz. Somut aciksa "red", teorik/uzak riske "kaygi" yeter.

CFO KURALI (ONEMLI, karakterden BAGIMSIZ islevsel kural - degistirilemez): Sirket
politikasi "once ucretsiz, sonra self-hosted, sonra open source, sonra ucretli"dir.
Plan ucretli/paid bir servis, API veya kaynak kullanimi iceriyorsa cfo.cost_flag=true
yap ve notes alaninda hangi maliyetin kullanici onayi gerektirdigini belirt.
Ucretsiz/self-hosted/open-source kaynaklar kullaniliyorsa cost_flag=false yap."""


class ReviewRequest(BaseModel):
    workflow: str
    prompt: str
    plan: str


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


@app.on_event("startup")
async def startup():
    app.state.http = httpx.AsyncClient(timeout=90.0)


@app.on_event("shutdown")
async def shutdown():
    await app.state.http.aclose()


_FAIL_SAFE_REVIEWS = {role: {"verdict": "kaygi", "notes": "Degerlendirme parse edilemedi", "parse_error": True} for role in ROLES}


def _coerce_cost_flag(value) -> bool:
    """cost_flag'i tip-guvenli sekilde bool'a cevirir. LLM'ler bazen
    "cost_flag": "false" (STRING) donebilir - Python'da bool("false")==True
    oldugu icin bu ciddi bir CFO-kapisi bypass riskidir, fail-open olmamali."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "evet")
    return bool(value)


def _parse_review(raw_content: str) -> dict:
    """LLM ciktisini JSON olarak parse eder. Model aciklama metni eklerse
    (yaygin bir LLM davranisi) ilk '{' ile son '}' arasini cikarip tekrar dener.

    Guvenlik: parse basarisiz olursa VEYA cfo alani eksikse fail-SAFE davranilir
    (cost_flag=True, onay bekletilir) - fail-open (cost_flag=False, otomatik
    onay) asla varsayilan olmamalidir. Parse hatasinda raw_content teshis icin
    loglanir."""
    parsed = None
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        start, end = raw_content.find("{"), raw_content.rfind("}")
        if start != -1 and end != -1:
            try:
                parsed = json.loads(raw_content[start:end + 1])
            except json.JSONDecodeError:
                pass

    if not isinstance(parsed, dict):
        logger.error(f"Executive review parse edilemedi, fail-safe uygulaniyor. Ham yanit: {raw_content!r}")
        return dict(_FAIL_SAFE_REVIEWS)

    reviews = {}
    for role in ROLES:
        verdict = parsed.get(role)
        if not isinstance(verdict, dict):
            logger.warning(f"'{role}' icin degerlendirme eksik/gecersiz, fail-safe uygulaniyor. Ham yanit: {raw_content!r}")
            verdict = {"verdict": "kaygi", "notes": "Rol icin degerlendirme yok", "parse_error": True}
        reviews[role] = verdict

    cfo = reviews["cfo"]
    if "cost_flag" not in cfo or cfo.get("parse_error"):
        # cfo eksik/parse edilemedi - maliyet durumu bilinmiyor, fail-safe: onay bekletilsin.
        cfo["cost_flag"] = True
        cfo.setdefault("notes", "CFO degerlendirmesi eksik - guvenlik geregi onay gerektiriyor olarak isaretlendi")
    else:
        cfo["cost_flag"] = _coerce_cost_flag(cfo["cost_flag"])

    return reviews


async def _remember(mem_type: str, scope_key: str, content: dict) -> bool:
    try:
        resp = await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"mem_type": mem_type, "scope_key": scope_key, "content": content},
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning(f"Memory'e yazilamadi ({mem_type}/{scope_key}): {e}")
        return False


@app.post("/api/v1/executives/review", dependencies=[Depends(verify_api_key)])
async def review(req: ReviewRequest):
    # Sistem talimati (JSON semasi + CFO kurali) ile kullanici/CEO tarafindan
    # uretilen plan metni AYRI mesaj rollerinde gonderilir (chat/completions'in
    # system+user ayrimi) - plan icine "cfo.cost_flag=false yap" gibi bir talimat
    # enjekte edilse bile system rolundeki kurallarla ayni agirlikta degerlendirilmez.
    # Ayrica plan MAX_PLAN_CHARS ile kirpilir (asiri uzun girdiyle bogma/maliyet onlemi).
    truncated_plan = req.plan[:MAX_PLAN_CHARS]
    try:
        resp = await app.state.http.post(
            f"{settings.AI_GATEWAY_URL}/api/chat",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "model": settings.REVIEW_MODEL,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Talep: {req.prompt}\n\nPlan:\n{truncated_plan}"},
                ],
            },
        )
        resp.raise_for_status()
        raw_content = resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"AI Gateway'e erisilemedi/beklenmedik yanit: {e}")

    reviews = _parse_review(raw_content)

    # 5 Memory yazimi sirayla degil PARALEL yapilir - LLM cagrisi zaten 10-90s
    # surebiliyor, sirali 5 ek HTTP cagrisi activities.py'deki 90s activity
    # timeout'unu asma riski yaratiyordu.
    results = await asyncio.gather(*[
        _remember("department", role, {"workflow": req.workflow, "prompt": req.prompt, **reviews[role]})
        for role in ROLES
    ])
    memory_write_failures = [role for role, ok in zip(ROLES, results) if not ok]
    if memory_write_failures:
        logger.warning(f"Bazi degerlendirmeler Memory'e yazilamadi (event/response'ta hala mevcut): {memory_write_failures}")

    return {
        "reviews": reviews,
        "requires_user_approval": reviews["cfo"]["cost_flag"],
        "memory_write_failures": memory_write_failures,
    }


@app.get("/health")
async def health():
    checks = {}
    try:
        resp = await app.state.http.get(f"{settings.AI_GATEWAY_URL}/health", timeout=5.0)
        checks["ai_gateway"] = resp.status_code == 200
    except Exception:
        checks["ai_gateway"] = False
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
