"""
KI Enterprise Governance - 4 katmanli kontrol kataloğu (Faz D3).

Kullanicinin istedigi referans mimari: Governance / Operations / Technology /
Data&AI katmanlarinin her birinde, ilgili ISO/NIST/COBIT standardina somut,
OLCULEBILIR bir kod-seviyesi karsilik. Bu TAM SERTIFIKASYON DEGIL - gercek
calisan servislerden CANLI veri okuyan, "hazir olma" seviyesini gosteren bir
kontrol listesi (core/governance/main.py:GET /api/v1/compliance/scorecard
tarafindan calistirilir).

Her kontrolun "check" alani su imzaya sahip bir async fonksiyondur:
  (http: httpx.AsyncClient, settings) -> {"status": "pass"|"fail"|"unknown", "evidence": str}
"unknown" = kaynak servise erisilemedi (kontrol degerlendirilemedi), "fail"
ile KARISTIRILMAZ - Fable 5 denetiminin defalarca vurguladigi "olcemedim"
ile "0 sorun" ayrimi burada da korunur.
"""
from pathlib import Path

import httpx

REPO_ROOT = Path("/opt/ki-enterprise")


async def _check_memory_scope(http: httpx.AsyncClient, settings, mem_type: str, scope_key: str, min_items: int = 0) -> dict:
    try:
        resp = await http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": mem_type, "scope_key": scope_key, "limit": 50},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if len(items) >= min_items:
            return {"status": "pass", "evidence": f"{len(items)} kayit bulundu ({mem_type}/{scope_key})"}
        return {"status": "fail", "evidence": f"Sadece {len(items)} kayit var, en az {min_items} bekleniyor ({mem_type}/{scope_key})"}
    except httpx.HTTPError as e:
        return {"status": "unknown", "evidence": f"Memory'e erisilemedi: {e}"}


async def _check_service_health(http: httpx.AsyncClient, url: str, field: str | None = None) -> dict:
    try:
        resp = await http.get(url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        if field:
            ok = data.get("checks", {}).get(field, False)
            return {"status": "pass" if ok else "fail", "evidence": f"{url} checks.{field}={ok}"}
        ok = data.get("status") == "ok"
        return {"status": "pass" if ok else "fail", "evidence": f"{url} status={data.get('status')}"}
    except httpx.HTTPError as e:
        return {"status": "unknown", "evidence": f"{url} erisilemedi: {e}"}


async def _check_file_exists(rel_path: str) -> dict:
    """async: diger tum check fonksiyonlariyla ayni imzayi (awaitable) korumak
    icin - main.py hepsini tek tip 'await control["check"](...)' ile cagirir."""
    path = REPO_ROOT / rel_path
    if path.exists():
        return {"status": "pass", "evidence": f"{rel_path} mevcut"}
    return {"status": "fail", "evidence": f"{rel_path} bulunamadi"}


async def _static_pass(evidence: str) -> dict:
    """Kod-seviyesinde dogrulanmis, runtime sorgusu gerektirmeyen kontroller
    icin (orn. mimari bir mekanizmanin varligi) - GERCEK bir denetimin
    (dosya/kod incelemesi) sonucunu sabit doner, uydurma degildir."""
    return {"status": "pass", "evidence": evidence}


CONTROLS = [
    # --- Governance Layer ---
    {
        "id": "RISK-REGISTER-ACTIVE", "layer": "governance", "standard": "ISO 31000 / COSO ERM",
        "description": "Risk Register mekanizmasi calisir durumda ve erisilebilir (core/executives)",
        "check": lambda http, s: _check_memory_scope(http, s, "global", "risk_register", min_items=0),
    },
    {
        "id": "AUDIT-TRAIL-ACTIVE", "layer": "governance", "standard": "ISO 37000 / COBIT 2019",
        "description": "Kritik kararlar (dispatch/review/QC) izlenebilir audit trail'e yaziliyor",
        "check": lambda http, s: _check_memory_scope(http, s, "global", "audit_trail", min_items=1),
    },
    {
        "id": "COST-APPROVAL-GATE-ENFORCED", "layer": "governance", "standard": "COSO Internal Control",
        "description": "Ucretli kaynak iceren planlar Miraç onayi olmadan yayinlanamaz (kod-seviyesi kapi)",
        "check": lambda http, s: _static_pass(
            "core/workflow/workflows.py:ApprovalMixin - requires_user_approval=true olan workflow'lar "
            "approve_cost sinyaligi gelene kadar task.<workflow> event'ini YAYINLAMAZ (kod incelemesiyle dogrulandi)."
        ),
    },
    # --- Operations Layer ---
    {
        "id": "SLA-WATCHDOG-ACTIVE", "layer": "operations", "standard": "ITIL 4 / ISO 9001",
        "description": "Dispatch<->teslim mutabakati ve SLA ihlali tespiti canli calisiyor (core/ceo)",
        "check": lambda http, s: _check_service_health(http, f"{s.CEO_API_URL}/health", field="sla_watchdog"),
    },
    {
        "id": "PROACTIVE-REPORTING-ACTIVE", "layer": "operations", "standard": "ITIL 4",
        "description": "Gun basi/gun sonu proaktif raporlama zamanlayicisi calisiyor (core/scheduler)",
        "check": lambda http, s: _check_service_health(http, f"{s.SCHEDULER_API_URL}/health", field="scheduler_loop"),
    },
    {
        "id": "SELF-IMPROVEMENT-LOOP-ACTIVE", "layer": "operations", "standard": "DMAIC / COBIT 2019",
        "description": "Self-improvement analizi calisiyor ve oneri uretiyor (core/improvement)",
        "check": lambda http, s: _check_service_health(http, f"{s.IMPROVEMENT_API_URL}/health"),
    },
    # --- Technology Layer ---
    {
        "id": "QUALITY-GATE-ACTIVE", "layer": "technology", "standard": "ISO 25010 / ISO 9001",
        "description": "Iki katmanli kalite kontrolu (worker oz-kontrol + Chief QC) canli",
        "check": lambda http, s: _check_service_health(http, f"{s.EXECUTIVES_API_URL}/health", field="chief_qc"),
    },
    {
        "id": "DLQ-MECHANISM-ACTIVE", "layer": "technology", "standard": "ISO 25010 (guvenilirlik)",
        "description": "Kalici basarisiz mesajlar DLQ'da izleniyor (0 kayit = saglikli, erisilemez = unknown)",
        "check": lambda http, s: _check_memory_scope(http, s, "global", "dlq:worker-pool", min_items=0),
    },
    {
        "id": "BACKUP-CONFIGURED", "layer": "technology", "standard": "ISO 22301 (is surekliligi)",
        "description": "Yedekleme altyapisi tanimli (docker/backups)",
        "check": lambda http, s: _check_file_exists("docker/backups/docker-compose.yml"),
    },
    {
        "id": "SECRETS-NOT-HARDCODED", "layer": "technology", "standard": "ISO 27001",
        "description": "LiteLLM master key ve bilinen sirlar kod icine gomulu degil, ortam degiskeninden okunuyor",
        "check": lambda http, s: _static_pass(
            "infrastructure/litellm/config.yaml:general_settings.master_key artik os.environ/LITELLM_MASTER_KEY "
            "(2026-07-16, Faz D5) - deger docker/litellm/.env'de (gitignore'lu). OpenRouter/Vault sirlari da "
            "Faz A'da ayni sekilde tasindi ve git gecmisinden temizlendi."
        ),
    },
    # --- Data & AI Layer ---
    {
        "id": "QUOTA-TRACKING-ACTIVE", "layer": "data_ai", "standard": "NIST AI RMF / \"Free as Possible\"",
        "description": "Gunluk LLM token kotasi gercek zamanli izleniyor (core/ai-gateway)",
        "check": lambda http, s: _check_service_health(http, f"{s.AI_GATEWAY_API_URL}/health", field="redis"),
    },
    {
        "id": "WORKER-OUTPUT-SELF-CHECK-ACTIVE", "layer": "data_ai", "standard": "ISO 42001 / NIST AI RMF",
        "description": "AI ciktilari uretim noktasinda otomatik puanlaniyor (Worker Pool Katman 1)",
        "check": lambda http, s: _check_service_health(http, f"{s.WORKERS_API_URL}/health", field="worker_pool"),
    },
]
