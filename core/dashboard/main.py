"""
KI Enterprise Dashboard (Phase 9).

Build order'daki panel setine karsilik gelir: CEO/Department/Project/Finance/
Marketing/System Dashboard. Bu servis bir ARKA UC (backend API) - frontend/UI
katmani yok, her panel icin JSON konsolide gorunum doner.

Onceki fazlardan (6/8) ogrenilen dersler BASTAN uygulanir:
  - Tum coklu-kaynak sorgular PARALEL (asyncio.gather) - sirali N+1 anti-pattern'i
    Project Manager (Phase 6) ve Aethris'te (Phase 8) bulunup duzeltilmisti.
  - Tek bir alt-servisin hatasi/beklenmedik semasi TUM paneli dusurmez -
    her yardimci fonksiyon hata durumunda None/bos doner, dogrudan dict
    indekslemesi (Aethris Phase 8 K2) kullanilmaz.
"""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from config import settings
from static_ui import render_dashboard_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

ALL_SERVICES = {
    "ceo": settings.CEO_API_URL,
    "memory": settings.MEMORY_API_URL,
    "ai_gateway": settings.AI_GATEWAY_URL,
    "executives": settings.EXECUTIVES_API_URL,
    "departments": settings.DEPARTMENTS_API_URL,
    "workers": settings.WORKERS_API_URL,
    "projects": settings.PROJECTS_API_URL,
    "skills": settings.SKILLS_API_URL,
    "aethris": settings.AETHRIS_API_URL,
}


async def verify_api_key(authorization: str = Header(default="")):
    """Ya ana INTERNAL_API_KEY (sunucu-sunucu cagrilari) YA DA kapsami
    daraltilmis DASHBOARD_UI_TOKEN (SADECE /ui sayfasindan gelen tarayici
    istekleri) kabul edilir. UI token sizarsa (herkese acik sayfa) saldirgan
    sadece Dashboard'un salt-okunur verisini okuyabilir - CEO dispatch/Memory
    yazma gibi TUM sistemi acan ana anahtara ERISEMEZ."""
    valid = (
        secrets.compare_digest(authorization, f"Bearer {settings.INTERNAL_API_KEY}") or
        secrets.compare_digest(authorization, f"Bearer {settings.DASHBOARD_UI_TOKEN}")
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


async def _safe_get(http: httpx.AsyncClient, url: str, timeout: float = 15.0) -> tuple[dict | None, str | None]:
    """Basarisiz olursa (herhangi bir sebeple) (None, hata_metni) doner - TEK
    bir alt-servis cagrisi tum dashboard panelini dusurmesin diye genis except
    kullanilir. ONEMLI (Fable 5 Phase 9 denetiminde bulunan regresyon):
    eskiden basitce None donuyordu, "servis gercekten 0 veri dondu" ile
    "servise erisilemedi/coktu" AYIRT EDILEMIYORDU - Project Manager'in Phase 6'da
    ozenle korudugu degraded/errors ayrimi burada kaybolmustu, artik geri
    getirildi."""
    try:
        resp = await http.get(url, headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"}, timeout=timeout)
        if resp.status_code != 200:
            err = f"{url}: HTTP {resp.status_code}"
            logger.warning(err)
            return None, err
        return resp.json(), None
    except Exception as e:
        err = f"{url}: {e}"
        logger.warning(err)
        return None, err


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Dashboard", lifespan=lifespan)


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Basit web arayuzu - HTML/JS sayfasinin kendisi auth GEREKTIRMEZ (bir
    tarayicinin sayfayi indirebilmesi icin), ama sayfa icindeki fetch()
    cagrilari INTERNAL_API_KEY'i (sayfaya gomulu) kullanarak API uclarini
    cagirir - API uclarinin kendisi auth gerektirmeye devam eder."""
    return render_dashboard_html(settings.DASHBOARD_UI_TOKEN)


@app.get("/api/v1/dashboard/ceo", dependencies=[Depends(verify_api_key)])
async def ceo_dashboard():
    decisions_resp, err = await _safe_get(
        app.state.http, f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve?mem_type=global&scope_key=ceo:decisions&limit=50"
    )
    items = [i["content"] for i in (decisions_resp or {}).get("items", []) if isinstance(i.get("content"), dict)]
    by_status = {}
    for d in items:
        status = d.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total_decisions": len(items),
        "by_status": by_status,
        "recent": items[:10],
        "degraded": err is not None,
        "errors": [err] if err else [],
    }


@app.get("/api/v1/dashboard/departments", dependencies=[Depends(verify_api_key)])
async def departments_dashboard():
    async def _dept_view(dept: str) -> dict:
        (backlog, backlog_err), (deliverables, deliverables_err) = await asyncio.gather(
            _safe_get(app.state.http, f"{settings.DEPARTMENTS_API_URL}/api/v1/departments/{dept}/backlog?limit=50"),
            _safe_get(app.state.http, f"{settings.WORKERS_API_URL}/api/v1/workers/{dept}/deliverables?limit=50"),
        )
        errors = [e for e in (backlog_err, deliverables_err) if e]
        return {
            "department": dept,
            "backlog_count": len((backlog or {}).get("items", [])),
            "deliverables_count": len((deliverables or {}).get("items", [])),
            "degraded": bool(errors),
            "errors": errors,
        }

    views = await asyncio.gather(*[_dept_view(d) for d in settings.ACTIVE_DEPARTMENTS])
    return {"departments": list(views)}


@app.get("/api/v1/dashboard/projects", dependencies=[Depends(verify_api_key)])
async def projects_dashboard():
    results = await asyncio.gather(*[
        _safe_get(app.state.http, f"{settings.PROJECTS_API_URL}/api/v1/projects/{p}/report") for p in settings.PROJECTS
    ])
    summaries = []
    for project, (report, err) in zip(settings.PROJECTS, results):
        if report is None:
            summaries.append({"project": project, "status": "unavailable", "degraded": True, "errors": [err] if err else []})
        else:
            summaries.append({
                "project": project,
                "roadmap_items": report.get("roadmap_items", 0),
                "backlog_count": report.get("backlog_count", 0),
                "deliverables_count": report.get("deliverables_count", 0),
                "cost_flagged_count": report.get("cost_flagged_count", 0),
                "degraded": report.get("degraded", False),
            })
    return {"projects": summaries}


@app.get("/api/v1/dashboard/finance", dependencies=[Depends(verify_api_key)])
async def finance_dashboard():
    """NOT: bu panel GERCEK bir para toplami DEGILDIR - Project Manager'in
    /budget ucu (bkz. core/projects/main.py, Phase 6) sadece CFO'nun
    cost_flag=true isaretledigi is sayisini/serbest-metin notunu listeler.
    Yapilandirilmis maliyet alani (orn. tahmini $ tutari) Executive Board'un
    ciktisinda henuz yok."""
    results = await asyncio.gather(*[
        _safe_get(app.state.http, f"{settings.PROJECTS_API_URL}/api/v1/projects/{p}/budget") for p in settings.PROJECTS
    ])
    all_cost_items, errors = [], []
    for project, (budget, err) in zip(settings.PROJECTS, results):
        if err:
            errors.append(err)
            continue
        for item in (budget or {}).get("cost_flagged_items", []):
            all_cost_items.append({"project": project, **item})
    # approval_status yalnizca "published" veya "approval_timeout" olabilir
    # (core/workflow/workflows.py) - yani bu sayac gercekte SU AN bekleyen
    # onaylari DEGIL, SURESI DOLMUS (artik onaylanamayacak) isleri sayar.
    # Gercekten hala RUNNING/onay bekleyen workflow'lar ceo:decisions'da HIC
    # KAYIT uretmiyor (Aethris Phase 8'de bulunan AYNI kok neden) - bu yuzden
    # "su an kac onay bekliyor" burada guvenilir sekilde hesaplanamiyor.
    expired = [i for i in all_cost_items if i.get("approval_status") == "approval_timeout"]
    return {
        "disclaimer": "Bu panel gercek bir para toplami degildir - sadece CFO'nun maliyet-isaretledigi is sayisini/notlarini listeler.",
        "total_cost_flagged_items": len(all_cost_items),
        "expired_approval_count": len(expired),
        "pending_approval_count": None,
        "pending_approval_note": "Su an bekleyen onaylar guvenilir sekilde raporlanamiyor - bilinen kisit, bkz. proje hafizasi (Aethris Phase 8 K1 ile ayni kok neden).",
        "items": all_cost_items,
        "degraded": bool(errors),
        "errors": errors,
    }


@app.get("/api/v1/dashboard/marketing", dependencies=[Depends(verify_api_key)])
async def marketing_dashboard():
    if "marketing" not in settings.ACTIVE_DEPARTMENTS:
        raise HTTPException(status_code=404, detail="Marketing departmani aktif degil")
    (backlog, backlog_err), (deliverables, deliverables_err) = await asyncio.gather(
        _safe_get(app.state.http, f"{settings.DEPARTMENTS_API_URL}/api/v1/departments/marketing/backlog?limit=50"),
        _safe_get(app.state.http, f"{settings.WORKERS_API_URL}/api/v1/workers/marketing/deliverables?limit=50"),
    )
    errors = [e for e in (backlog_err, deliverables_err) if e]
    return {
        "backlog": (backlog or {}).get("items", []),
        "deliverables": (deliverables or {}).get("items", []),
        "degraded": bool(errors),
        "errors": errors,
    }


@app.get("/api/v1/dashboard/system", dependencies=[Depends(verify_api_key)])
async def system_dashboard():
    async def _check(name: str, url: str) -> dict:
        health, err = await _safe_get(app.state.http, f"{url}/health", timeout=5.0)
        status = (health or {}).get("status", "unreachable") if err is None else "unreachable"
        return {"service": name, "status": status, "detail": health}

    results = await asyncio.gather(*[_check(name, url) for name, url in ALL_SERVICES.items()])
    healthy_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "services": list(results),
        "healthy_count": healthy_count,
        "total_count": len(ALL_SERVICES),
        "overall_status": "ok" if healthy_count == len(ALL_SERVICES) else "degraded",
    }


@app.get("/health")
async def health():
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        memory_ok = resp.status_code == 200
    except Exception:
        memory_ok = False
    return {"status": "ok" if memory_ok else "degraded", "checks": {"memory": memory_ok}}
