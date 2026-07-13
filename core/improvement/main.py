"""
KI Enterprise Self Improvement (Phase 10 - SON FAZ).

Build order kisitlamasi (KESINLIKLE UYULMALI): CEO (ve bu servis) su dortunu
YAPAMAZ, Mirac'in ONAYI OLMADAN:
  - Kod merge edemez
  - Para harcayamaz
  - Deploy edemez
  - Silme islemi yapamaz

Bu yuzden core/improvement KASITLI OLARAK SADECE OKUMA yapar. Hicbir POST/PUT/
DELETE uc YOKTUR ki bir "aksiyon" alamasin - tek yazma islemi, ANALIZ
SONUCLARINI Memory'e KAYDETMEKTIR (bir oneri listesi, uygulama DEGIL).

Yapabildikleri (build order): eksik skill tespiti, yeni workflow/worker/proje
onerisi, verimsizlik raporu. Bu servis analiz eder + Memory'e ONERI olarak
yazar - Mirac/Aethris bunlari GORUR, servis KENDI BASINA HICBIR SEYI
UYGULAMAZ.
"""
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("improvement")

# Build order'daki TAM 9 departman listesi (core.env:ACTIVE_DEPARTMENTS sadece
# su an GERCEKTEN is alan 4'unu tutar - buradaki analiz "hangi departmanlar
# hicbir zaman is almadi" farkini tespit etmek icin TUM 9'u bilmeli).
ALL_BUILD_ORDER_DEPARTMENTS = [
    "development", "research", "marketing", "finance",
    "security", "support", "design", "video", "operations",
]

PROPOSALS_SCOPE_KEY = "improvement-proposals"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


async def _memory_get(http: httpx.AsyncClient, mem_type: str, scope_key: str, limit: int = 50) -> tuple[list[dict], str | None]:
    """(kayitlar, hata) doner - "gercekten 0 kayit var" ile "Memory'e
    erisilemedi" ARTIK AYIRT EDILEBILIR (Fable 5 Phase 10 denetiminde
    bulundu: analiz fonksiyonlari sessizce [] donuyordu, "0 sorun" ile
    "olcemedim" karisiyordu)."""
    try:
        resp = await http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": mem_type, "scope_key": scope_key, "limit": limit},
        )
    except httpx.HTTPError as e:
        err = f"Memory'e erisilemedi ({mem_type}/{scope_key}): {e}"
        logger.warning(err)
        return [], err
    if resp.status_code >= 400:
        return [], None  # 404 = gercekten kayit yok, hata degil
    return [i["content"] for i in resp.json().get("items", []) if isinstance(i.get("content"), dict)], None


async def _analyze_dlq(http: httpx.AsyncClient) -> tuple[list[dict], list[str]]:
    """DLQ'lardaki (Phase 4/5'te kurulan safe-consumer deseni) kalici basarisiz
    mesajlari tarar - bunlar somut, KANITLANMIS guvenilirlik sorunlaridir."""
    proposals, errors = [], []
    for dlq_service in ["dlq:department-manager", "dlq:worker-pool", "dlq:ceo-report-collector"]:
        entries, err = await _memory_get(http, "global", dlq_service)
        if err:
            errors.append(err)
        if entries:
            proposals.append({
                "type": "reliability_issue",
                # reason kirpilir: exception mesajlari bazen istek/URL detayi
                # tasiyabilir, evidence'a kopyalamadan once sinirlanir.
                "evidence": [str(e.get("reason", "?"))[:200] for e in entries[:5]],
                "title": f"{dlq_service} icinde {len(entries)} kalici basarisiz mesaj var",
                "severity": "high" if len(entries) > 3 else "medium",
            })
    return proposals, errors


def _analyze_department_coverage() -> list[dict]:
    """Build order'in 9 departmanindan kacinin GERCEKTEN is aldigini (mevcut
    workflow kumesiyle eslesip eslesmedigini) tespit eder - KANIT: core.env'deki
    WORKFLOW_TO_DEPARTMENT haritasi + ACTIVE_DEPARTMENTS listesi (Phase 4/5
    denetimlerinde belgelenen bilinen sinirlama)."""
    mapped_departments = set(settings.WORKFLOW_TO_DEPARTMENT.values())
    uncovered = [d for d in ALL_BUILD_ORDER_DEPARTMENTS if d not in mapped_departments]
    if not uncovered:
        return []
    return [{
        "type": "missing_workflow",
        "title": f"{len(uncovered)} departman hicbir workflow'a eslenmemis, hic gorev almiyor: {uncovered}",
        "evidence": [f"WORKFLOW_TO_DEPARTMENT: {settings.WORKFLOW_TO_DEPARTMENT}"],
        "recommendation": f"Bu departmanlar icin yeni workflow tipleri (Workflow Engine, core/workflow) ve worker persona'lari (core/workers) tanimlanmasi onerilir: {uncovered}",
        "severity": "low",
    }]


async def _analyze_skill_usage(http: httpx.AsyncClient) -> tuple[list[dict], list[str]]:
    """Hangi skill'lerin (Phase 7) HIC calistirilmadigini tespit eder - kullanilmayan
    skill = ya kesif edilemiyor ya da gereksiz, her ikisi de verimsizlik isareti."""
    errors = []
    try:
        resp = await http.get(
            f"{settings.SKILLS_API_URL}/api/v1/skills",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return [], [f"Skills servisi HTTP {resp.status_code} dondurdu"]
        skill_names = [s["name"] for s in resp.json().get("skills", [])]
    except httpx.HTTPError as e:
        return [], [f"Skills servisine erisilemedi: {e}"]

    unused = []
    for name in skill_names:
        executions, err = await _memory_get(http, "global", f"skill:{name}:executions", limit=1)
        if err:
            errors.append(err)
        if not executions:
            unused.append(name)
    if not unused:
        return [], errors
    return [{
        "type": "unused_skill",
        "title": f"{len(unused)} skill hic calistirilmamis: {unused}",
        "evidence": unused,
        "recommendation": "Bu skill'lerin Worker Pool'a entegre edilip edilmeyecegi (otomatik tetikleme) veya kaldirilip kaldirilmayacagi degerlendirilmeli.",
        "severity": "low",
    }], errors


async def _analyze_cost_patterns(http: httpx.AsyncClient) -> tuple[list[dict], list[str]]:
    """Sik maliyet-isaretli proje tespit eder - butce gozden gecirme onerisi."""
    proposals, errors = [], []
    for project in settings.PROJECTS:
        try:
            resp = await http.get(
                f"{settings.PROJECTS_API_URL}/api/v1/projects/{project}/budget",
                headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                errors.append(f"'{project}' butce sorgusu HTTP {resp.status_code} dondurdu")
                continue
            data = resp.json()
            if data.get("count", 0) >= 2:
                proposals.append({
                    "type": "budget_review",
                    "title": f"'{project}' projesinde {data['count']} maliyet-isaretli is var",
                    "evidence": [i.get("cfo_notes", "") for i in data.get("cost_flagged_items", [])],
                    "recommendation": f"'{project}' icin toplu bir butce onayi/self-hosted alternatif degerlendirmesi dusunulebilir.",
                    "severity": "medium",
                })
        except httpx.HTTPError as e:
            errors.append(f"'{project}' butce sorgusu basarisiz: {e}")
    return proposals, errors


def _known_architectural_gaps() -> list[dict]:
    """Bu oturumda GERCEKTEN 3 KEZ (CEO->Aethris->Dashboard) ayni kok nedenden
    bulunan bilinen bir mimari eksiklik - somut, kanitlanmis bir 'verimsizlik
    raporu' ornegi (build order Phase 10'un istedigi tam olarak bu):
    tekrarlanan kalip TEK bir kok neden duzeltmesiyle cozulebilir.

    2026-07-13 guncellemesi: core/aethris servisi SILINDI (kisisel asistan
    artik KI Enterprise disinda, Ki-Life-OS/OpenClaw uzerinde bagimsiz
    calisiyor - bkz. core/organization/AGENTIC_ARCHITECTURE_PLAN.md). Asagidaki
    "Aethris" evidence satiri artik TARIHSEL bir kanit (kok nedenin 3 kez
    tekrarlandigini gosteriyor) - aktif bir tuketici DEGIL. CEO tarafi da
    kismen duzeldi: core/ceo artik GET /api/v1/ceo/workflows (Temporal'dan
    canli RUNNING sorgusu) sunuyor - Dashboard bunu HENUZ benimsemedi,
    asil kalan is bu."""
    return [{
        "type": "inefficiency_report",
        "title": "Onay bekleyen workflow'lar hicbir yerde guvenilir sekilde gorunmuyor (3 farkli tuketicide bulundu, kismen duzeltildi)",
        "evidence": [
            "CEO (core/ceo) Phase 2: _wait_and_remember SADECE workflow tamamlandiktan sonra yazardi - 2026-07-13'te GET /api/v1/ceo/workflows (Temporal canli sorgu) eklenerek COZULDU",
            "Aethris (core/aethris) Phase 8: pending_approvals_count metrigi bu yuzden her zaman 0/yanlisti - servis 2026-07-13'te SILINDI (artik KI Enterprise kapsami disinda, bkz. Ki-Life-OS), bu madde artik TARIHSEL",
            "Dashboard (core/dashboard) Phase 9: pending_approval_count AYNI kok nedenle yanlis (adi expired_approval_count olarak duzeltildi, ama gercek sayim hala yok) - HALA COZULMEDI",
        ],
        "recommendation": (
            "Dashboard, core/ceo'nun zaten var olan GET /api/v1/ceo/workflows?status=RUNNING "
            "ucunu kullanacak sekilde guncellenirse kalan tek tuketici de duzelir."
        ),
        "severity": "medium",
    }]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Self Improvement (analiz-yalnizca, hicbir aksiyon almaz)", lifespan=lifespan)


@app.get("/api/v1/improvement/analyze", dependencies=[Depends(verify_api_key)])
async def analyze():
    """Sistemi analiz eder, onerileri Memory'e KAYDEDER (uygulamaz) ve doner.
    Bu servisin YAPTIGI TEK 'yazma' islemi budur - bir oneri LISTESI kaydetmek,
    onerilerin HICBIRINI kendisi UYGULAMAZ (kod merge/harcama/deploy/silme
    icin hicbir uc/yetenek bu serviste YOKTUR)."""
    dlq_proposals, dlq_errors = await _analyze_dlq(app.state.http)
    coverage_proposals = _analyze_department_coverage()
    skill_proposals, skill_errors = await _analyze_skill_usage(app.state.http)
    cost_proposals, cost_errors = await _analyze_cost_patterns(app.state.http)
    architectural_proposals = _known_architectural_gaps()

    all_proposals = dlq_proposals + coverage_proposals + skill_proposals + cost_proposals + architectural_proposals
    # "0 sorun bulundu" ile "bazi kaynaklara erisilemedigi icin olcemedim"
    # ARTIK AYIRT EDILEBILIR (Fable 5 Phase 10 denetiminde bulundu).
    analysis_errors = dlq_errors + skill_errors + cost_errors
    generated_at = datetime.now(timezone.utc).isoformat()

    record = {
        # producer+schema_version: bu kaydin core/improvement tarafindan,
        # bilinen bir semayla uretildigini isaretler - ayni scope_key'e
        # INTERNAL_API_KEY'i bilen baska biri sahte veri yazarsa (paylasilan
        # sir modelinin dogal siniri) en azindan bunun BU servisten gelip
        # gelmedigi izlenebilir. Kriptografik dogrulama DEGILDIR.
        "producer": "core/improvement", "schema_version": 1,
        "proposals": all_proposals, "analysis_errors": analysis_errors, "generated_at": generated_at,
    }
    try:
        await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"mem_type": "global", "scope_key": PROPOSALS_SCOPE_KEY, "content": record},
        )
    except httpx.HTTPError as e:
        logger.warning(f"Oneriler Memory'e kaydedilemedi (yine de donuluyor): {e}")

    return {
        "proposal_count": len(all_proposals),
        "proposals": all_proposals,
        "analysis_errors": analysis_errors,
        "generated_at": generated_at,
        "note": "Bu bir ANALIZ raporudur - hicbir oneri otomatik UYGULANMAZ. Mirac/Aethris onayi gerektirir.",
    }


@app.get("/api/v1/improvement/proposals", dependencies=[Depends(verify_api_key)])
async def get_proposals():
    """En son kaydedilen analiz sonuclarini (yeniden analiz calistirmadan) doner."""
    items, _err = await _memory_get(app.state.http, "global", PROPOSALS_SCOPE_KEY, limit=1)
    if not items:
        return {"proposals": [], "note": "Henuz analiz calistirilmadi - once GET /analyze cagirin."}
    return items[0]


@app.get("/health")
async def health():
    checks = {}
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    try:
        resp = await app.state.http.get(f"{settings.PROJECTS_API_URL}/health", timeout=5.0)
        checks["projects"] = resp.status_code == 200
    except Exception:
        checks["projects"] = False
    try:
        resp = await app.state.http.get(f"{settings.SKILLS_API_URL}/health", timeout=5.0)
        checks["skills"] = resp.status_code == 200
    except Exception:
        checks["skills"] = False
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
