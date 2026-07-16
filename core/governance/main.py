"""
KI Enterprise Governance (Faz D2+D3).

Iki gorevi var:
  1. Audit Trail (D2) - kritik olaylarin (dispatch/approve/review/QC duzeltici
     faaliyet) degistirilemez, append-only bir izini tutar. ISO 27001/COBIT'in
     "izlenebilirlik" kontrolunun somut karsiligi.
  2. Uyum Skorkarti (D3) - core/governance/controls.py'deki 4-katmanli
     (Governance/Operations/Technology/Data&AI) kontrol kataloğunu CANLI
     servislerden veri okuyarak degerlendirir, pass/fail/unknown + kanit doner.

Bu servis KASITLI OLARAK pasif/gozlemci - hicbir is akisini degistirmez,
hicbir POST/PUT/DELETE ucu baska bir servisi TETIKLEMEZ (core/improvement'la
ayni build-order ruhu: sadece kaydeder/raporlar, aksiyon almaz).
"""
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings
from controls import CONTROLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("governance")

AUDIT_SCOPE_KEY = "audit_trail"
SCORECARD_SCOPE_KEY = "compliance:scorecard"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


class AuditEntry(BaseModel):
    actor: str  # orn. "ceo", "executive_board", "cfo", "ciso"
    action: str  # orn. "dispatch", "approve_cost", "review", "qc_corrective_action"
    target: str  # orn. workflow_id veya workflow adi
    decision: str  # orn. "dispatched", "approved", "requires_approval", "revizyon_gonderildi"
    detail: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=15.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Governance", lifespan=lifespan)


async def _remember(mem_type: str, scope_key: str, content: dict, idempotency_key: Optional[str] = None) -> bool:
    try:
        body = {"mem_type": mem_type, "scope_key": scope_key, "content": content}
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        resp = await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json=body,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning(f"Memory'e yazilamadi ({mem_type}/{scope_key}): {e}")
        return False


@app.post("/api/v1/audit", dependencies=[Depends(verify_api_key)])
async def create_audit_entry(entry: AuditEntry):
    """Append-only audit kaydi. Idempotency_key KASITLI OLARAK verilmez - ayni
    olayin iki kez loglanmasi (orn. retry) zararsizdir, audit trail'de fazladan
    bir satir olarak kalir (kaybolmaktan cok daha iyi)."""
    content = {**entry.model_dump(), "recorded_at": datetime.now(timezone.utc).isoformat()}
    ok = await _remember("global", AUDIT_SCOPE_KEY, content)
    if not ok:
        raise HTTPException(status_code=502, detail="Audit kaydi Memory'e yazilamadi")
    return content


@app.get("/api/v1/audit", dependencies=[Depends(verify_api_key)])
async def list_audit_entries(actor: Optional[str] = None, action: Optional[str] = None, limit: int = 50):
    try:
        resp = await app.state.http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": "global", "scope_key": AUDIT_SCOPE_KEY, "limit": max(limit, 200)},
        )
        resp.raise_for_status()
        entries = [i["content"] for i in resp.json().get("items", []) if isinstance(i.get("content"), dict)]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory'e erisilemedi: {e}")

    if actor:
        entries = [e for e in entries if e.get("actor") == actor]
    if action:
        entries = [e for e in entries if e.get("action") == action]
    return {"entries": entries[:limit], "count": len(entries)}


@app.get("/api/v1/compliance/scorecard", dependencies=[Depends(verify_api_key)])
async def compliance_scorecard():
    """4 katmanli kontrol kataloğunu CANLI servislerden degerlendirir, sonucu
    Memory'e kaydeder (Faz B gunluk raporu/dashboard bunu KPI olarak okuyabilir)
    ve doner. Tam ISO sertifikasyonu DEGIL - "hazir olma" gostergesidir."""
    results = []
    for control in CONTROLS:
        try:
            outcome = await control["check"](app.state.http, settings)
        except Exception as e:
            outcome = {"status": "unknown", "evidence": f"Kontrol calistirilamadi: {e}"}
        results.append({
            "id": control["id"], "layer": control["layer"], "standard": control["standard"],
            "description": control["description"], **outcome,
        })

    by_status = {"pass": 0, "fail": 0, "unknown": 0}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    record = {
        "controls": results, "summary": by_status, "total": len(results),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await _remember("global", SCORECARD_SCOPE_KEY, record)
    return record


@app.get("/health")
async def health():
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        memory_ok = resp.status_code == 200
    except Exception:
        memory_ok = False
    return {"status": "ok" if memory_ok else "degraded", "checks": {"memory": memory_ok}}
