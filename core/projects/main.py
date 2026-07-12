"""
KI Enterprise Project Manager Layer (Phase 6).

Build order'daki 6 proje: ki-business, ki-social, ki-wallet, ki-form,
ki-management, aethris (+ "unassigned": project etiketi olmadan dispatch edilen
isler icin - hicbir zaman gorunmez kalmasin diye, bkz. asagida).

Bu servis kendi NATS consumer'ini KURMAZ; CEO/Department Manager/Worker Pool
zaten bir workflow'un "project" etiketiyle PROJE-BAZLI Memory kayitlari YAZAR
(core/ceo:{project}-decisions, core/departments:{project}-backlog,
core/workers:{project}-deliverables - hepsi mem_type="project"). Bu servis
sadece bu ONCEDEN-IZOLE EDILMIS kayitlari OKUR ve birlestirir (read-time
aggregation) - departman/global havuzlarini TARAYIP client-side FILTRELEMEZ.

Onceki tasarim (Fable 5 Phase 6 denetiminde bulundu, K1): {department}-backlog
gibi TUM projelerin ortak oldugu bir havuzdan sabit limit(50) ile kayit cekip
sonra project alanina gore filtreliyordu - havuz limiti asinca eski kayitlar
sessizce sorgu disi kaliyor, HATA VERMEDEN eksik/yanlis rapor uretiyordu. Artik
her yazan servis (CEO/Departments/Workers) departman/global kaydinin YANI SIRA
proje-bazli KUCUK/IZOLE bir kopya da yaziyor - Project Manager bu izole
kayitlardan okudugu icin capraz-proje kirlenmesi/limit asimi riski yok.

Roadmap: TEK yazma-yetkili veri (bu servis tarafindan POST ile eklenir).

Hata yonetimi: _memory_get artik SESSIZCE [] DONMUYOR - Memory'e erisilemezse
exception firlatir, cagiran (get_tasks/get_budget/get_report) bunu yakalayip
yanitta "degraded": true + "errors": [...] olarak ISARETLER (eskiden hata ile
"gercekten bos" ayirt edilemiyordu).
"""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("projects")

# "unassigned": project etiketi olmadan dispatch edilen isler icin ozel bir
# sozde-proje - PROJECTS listesinde DEGIL ama tum sorgu uclarinda gecerli bir
# isim olarak kabul edilir (bkz. _require_project).
UNASSIGNED = "unassigned"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


def _require_project(name: str):
    if name not in settings.PROJECTS and name != UNASSIGNED:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen proje: {name}. Gecerli: {settings.PROJECTS + [UNASSIGNED]}")


class MemoryUnavailable(Exception):
    pass


async def _memory_get(http: httpx.AsyncClient, mem_type: str, scope_key: str, limit: int = 50) -> list[dict]:
    """Basarisiz olursa SESSIZCE [] DONMEZ - MemoryUnavailable firlatir, cagiran
    bunu "gercekten bos" ile "veri alinamadi" ayrimini korumak icin yakalar."""
    try:
        resp = await http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": mem_type, "scope_key": scope_key, "limit": limit},
        )
    except httpx.HTTPError as e:
        raise MemoryUnavailable(f"{mem_type}/{scope_key}: {e}")
    if resp.status_code == 404:
        return []
    if resp.status_code >= 400:
        raise MemoryUnavailable(f"{mem_type}/{scope_key}: HTTP {resp.status_code}")
    items = resp.json().get("items", [])
    # Bozuk/eski kayitlar (content dict degilse) atlanir, 500'e yol acmaz.
    return [i for i in items if isinstance(i.get("content"), dict)]


class RoadmapItem(BaseModel):
    title: str
    description: str = ""
    status: str = "planned"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Project Manager Layer", lifespan=lifespan)


@app.get("/api/v1/projects", dependencies=[Depends(verify_api_key)])
async def list_projects():
    return {"projects": settings.PROJECTS, "unassigned_pseudo_project": UNASSIGNED}


@app.post("/api/v1/projects/{name}/roadmap", dependencies=[Depends(verify_api_key)])
async def add_roadmap_item(name: str, item: RoadmapItem):
    _require_project(name)
    try:
        resp = await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "mem_type": "project", "scope_key": f"{name}-roadmap",
                "content": {
                    "title": item.title, "description": item.description, "status": item.status,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory'e yazilamadi: {e}")
    return resp.json()


async def _get_roadmap(name: str) -> list[dict]:
    return await _memory_get(app.state.http, "project", f"{name}-roadmap")


@app.get("/api/v1/projects/{name}/roadmap", dependencies=[Depends(verify_api_key)])
async def get_roadmap(name: str):
    _require_project(name)
    try:
        items = await _get_roadmap(name)
    except MemoryUnavailable as e:
        raise HTTPException(status_code=502, detail=f"Memory'e erisilemedi: {e}")
    return {"project": name, "roadmap": items}


async def _get_tasks(name: str) -> dict:
    try:
        backlog, deliverables = await asyncio.gather(
            _memory_get(app.state.http, "project", f"{name}-backlog", limit=200),
            _memory_get(app.state.http, "project", f"{name}-deliverables", limit=200),
        )
    except MemoryUnavailable as e:
        return {"backlog": [], "deliverables": [], "degraded": True, "errors": [str(e)]}
    return {
        "backlog": [i["content"] for i in backlog],
        "deliverables": [i["content"] for i in deliverables],
        "degraded": False, "errors": [],
    }


@app.get("/api/v1/projects/{name}/tasks", dependencies=[Depends(verify_api_key)])
async def get_tasks(name: str):
    _require_project(name)
    result = await _get_tasks(name)
    return {"project": name, **result}


async def _get_budget(name: str) -> dict:
    try:
        decisions = await _memory_get(app.state.http, "project", f"{name}-decisions", limit=200)
    except MemoryUnavailable as e:
        return {"cost_flagged_items": [], "count": 0, "degraded": True, "errors": [str(e)]}

    cost_items = []
    for item in decisions:
        content = item["content"]
        result = content.get("result") or {}
        if result.get("requires_user_approval"):
            cfo = (result.get("executive_review") or {}).get("cfo", {})
            cost_items.append({
                "workflow_id": content.get("workflow_id"), "workflow": content.get("workflow"),
                "prompt": content.get("prompt"), "cfo_notes": cfo.get("notes"),
                "approval_status": result.get("status"),
            })
    return {"cost_flagged_items": cost_items, "count": len(cost_items), "degraded": False, "errors": []}


@app.get("/api/v1/projects/{name}/budget", dependencies=[Depends(verify_api_key)])
async def get_budget(name: str):
    """NOT: gercek bir para toplami DEGILDIR - CFO'nun serbest-metin
    degerlendirmesinde cost_flag=true isaretledigi is sayisini/notlarini
    listeler. Yapilandirilmis maliyet alani (orn. tahmini aylik $ tutari)
    Executive Board'un ciktisinda henuz yok - sonraki bir iyilestirme."""
    _require_project(name)
    result = await _get_budget(name)
    return {"project": name, **result}


@app.get("/api/v1/projects/{name}/report", dependencies=[Depends(verify_api_key)])
async def get_report(name: str):
    _require_project(name)
    # Uc bagimsiz sorgu grubu (roadmap/tasks/budget) PARALEL calisir - eskiden
    # 10 sirali Memory cagrisi 1-2s+ suruyordu.
    roadmap_task, tasks_result, budget_result = await asyncio.gather(
        _get_roadmap(name), _get_tasks(name), _get_budget(name),
        return_exceptions=True,
    )
    errors = []
    if isinstance(roadmap_task, MemoryUnavailable):
        errors.append(str(roadmap_task))
        roadmap_task = []
    if tasks_result.get("errors"):
        errors.extend(tasks_result["errors"])
    if budget_result.get("errors"):
        errors.extend(budget_result["errors"])

    return {
        "project": name,
        "degraded": bool(errors),
        "errors": errors,
        "roadmap_items": len(roadmap_task),
        "backlog_count": len(tasks_result["backlog"]),
        "deliverables_count": len(tasks_result["deliverables"]),
        "cost_flagged_count": budget_result["count"],
        "roadmap": roadmap_task,
        "recent_deliverables": tasks_result["deliverables"][:5],
        "cost_flagged_items": budget_result["cost_flagged_items"],
    }


@app.get("/health")
async def health():
    checks = {}
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
