"""
KI Enterprise Department System (Phase 4).

Build order'daki 9 departman: development, research, marketing, finance,
security, support, design, video, operations. Worker katmani (Phase 5) henuz
kurulmadigi icin Department Manager su an:
  1. Event Bus'taki task.> subject'ini (Workflow Engine'in yayinladigi, Executive
     Board tarafindan degerlendirilmis planlar) dinler
  2. Her gorevi ilgili departmana yonlendirir (WORKFLOW_TO_DEPARTMENT), Memory'ye
     kaydeder (departmanin "backlog"u - Phase 5'te worker'lar buradan cekecek)
  3. CEO'nun zaten dinledigi report.<departman> subject'ine bir alindi raporu
     yayinlar - CEO'nun rapor toplama mekanizmasi (Phase 2) boylece Phase 4'u de
     otomatik olarak kapsar, ek entegrasyon gerekmez.

Bu servis kasitli olarak Workflow Engine'in bir activity'si DEGIL, ayri bir
servistir (Executive Board ile ayni gerekce - birim bazli yonetim).

Guvenilirlik notlari (Fable 5 + Opus denetimi sonrasi, bkz. proje hafizasi):
  - Backlog kaydi + rapor yayini artik IDEMPOTENT: kaynak mesajin stream+sequence
    numarasindan turetilen deterministik bir idempotency_key kullanilir, hem
    Memory store'da (ON CONFLICT DO NOTHING) hem NATS publish'te (Nats-Msg-Id).
    Redelivery (ack_wait asimi, gecici hata sonrasi retry) artik duplicate
    backlog/rapor kaydi yaratmaz.
  - max_deliver tukenmesi artik SESSIZ DEGIL: bir mesaj son deneme hakkinda
    basarisiz olursa DLQ'ya (Memory, mem_type=global scope_key=dlq:department-manager)
    yazilir ve CRITICAL loglanir, JetStream'in sessizce vazgecmesine birakilmaz.
  - fetch batch'i kucultuldu (10->3) ve ack_wait uzatildi (30->90) - bir batch
    icindeki yavas bir HTTP cagrisi digerlerinin ack suresini asirtip gereksiz
    redelivery/duplicate riskini tetiklemesin diye.
"""
import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
import nats
from fastapi import Depends, FastAPI, Header, HTTPException
from nats.js.api import ConsumerConfig

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("departments")

HERE = Path(__file__).parent

DEPARTMENTS = [
    # Eski 9 (Phase 4'ten) - degismedi.
    "development", "research", "marketing", "finance",
    "security", "support", "design", "video", "operations",
    # 2026-07-15 eklendi - 9-Chief org genislemesi (bkz. ORG_CHART.md,
    # AGENTIC_ARCHITECTURE_PLAN.md SS14). Chief->departman eslemesi icin
    # core.env:DEPARTMENT_TO_CHIEF tek dogruluk kaynagidir.
    "tester",  # CTO/QA - onceden worker persona'si vardi ama bu listede yoktu, tutarlilik icin eklendi
    # COO
    "customer_success", "procurement", "administration",
    # CTO
    "platform", "ai_engineering", "architecture",
    # CFO
    "accounting", "treasury", "tax", "fp_a",
    # CPO
    "product_management", "product_operations", "product_analytics",
    # CMO
    "brand", "digital_marketing", "communications_pr",
    # CRO
    "sales", "partnerships", "revops", "customer_expansion",
    # CISO
    "soc", "governance", "privacy",
    # CDO
    "data_engineering", "data_science", "bi", "ai_data", "data_governance",
]

# Mevcut workflow'lar (Phase 1) ile departmanlar arasindaki eslesme. Eslesmeyen
# bir workflow gelirse "operations" departmanina duser (fallback) VE WARNING
# loglanir - eskiden bu sessizdi, yeni workflow eklenip harita guncellenmezse
# fark edilmiyordu.
#
# NOT (bilinen tutarsizlik): finance/security/design/video departmanlarina
# eslesen HICBIR workflow yok (mevcut 6 workflow bunlari kapsamiyor) - bu
# departmanlar Phase 1'deki workflow kumesi genisleyene kadar hicbir zaman
# gorev almayacak. Build order'in 9 departman listesiyle Phase 1'in 6
# workflow'u arasindaki bu ayrisma bilinen bir sinirlamadir.
#
# Kaynak: core.env:WORKFLOW_TO_DEPARTMENT (core/workers ve core/projects ile
# PAYLASILAN tek dogruluk kaynagi - Phase 4/5 denetimlerinde 3 kez bulunan
# "her serviste ayri kopya" sorunu Phase 6'da boyle cozuldu).
WORKFLOW_TO_DEPARTMENT = settings.WORKFLOW_TO_DEPARTMENT

TASK_MAX_DELIVER = 5
DLQ_SCOPE_KEY = "dlq:department-manager"
DLQ_FALLBACK_FILE = HERE / "dlq_fallback.jsonl"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


async def _remember(http: httpx.AsyncClient, mem_type: str, scope_key: str, content: dict, idempotency_key: str | None = None) -> bool:
    try:
        payload = {"mem_type": mem_type, "scope_key": scope_key, "content": content}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        resp = await http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning(f"Memory'e yazilamadi ({mem_type}/{scope_key}): {e}")
        return False


async def _report(nc: nats.NATS, department: str, payload: dict, msg_id: str):
    js = nc.jetstream()
    # Nats-Msg-Id: ayni kaynak mesaj yuzunden redelivery olursa CEO tarafinda
    # (JetStream dedup penceresi icinde) duplicate "received" raporu olusmaz.
    await js.publish(f"report.{department}", json.dumps(payload).encode(), headers={"Nats-Msg-Id": msg_id})


async def _send_to_dlq(http: httpx.AsyncClient, subject: str, num_delivered: int, reason: str, raw_data: str) -> bool:
    logger.critical(f"DLQ: mesaj {num_delivered} denemede kalici olarak basarisiz oldu ({subject}): {reason}")
    entry = {
        "subject": subject,
        "num_delivered": num_delivered,
        "reason": reason,
        "raw_data": raw_data[:2000],
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    ok = await _remember(http, "global", DLQ_SCOPE_KEY, entry)
    if ok:
        return True
    # Memory Layer'a da yazilamadi (dongusel bagimlilik: DLQ'nun kendisi Memory'e
    # bagimliydi) - yerel dosyaya (append-only JSONL) fallback yaz ki mesaj izsiz
    # kaybolmasin. Ayri bir tuketici (Faz B) bu dosyayi okuyup Memory geri gelince
    # tekrar deneyebilir.
    try:
        with open(DLQ_FALLBACK_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.warning(f"DLQ Memory'e yazilamadi, yerel dosyaya fallback yapildi: {DLQ_FALLBACK_FILE}")
        return True
    except OSError as e:
        logger.critical(f"DLQ hem Memory'e hem yerel dosyaya yazilamadi, mesaj KAYBOLABILIR: {e}")
        return False


async def _task_supervisor(nc: nats.NATS, http: httpx.AsyncClient, heartbeat: dict):
    while True:
        try:
            await _handle_task_loop_with_heartbeat(nc, http, heartbeat)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Department Manager coktu, 5sn sonra yeniden baslatiliyor: {e}")
            await asyncio.sleep(5)


async def _handle_task_loop_with_heartbeat(nc: nats.NATS, http: httpx.AsyncClient, heartbeat: dict):
    """_handle_task_loop'u sarar ve her fetch dongusunde heartbeat zaman damgasi
    gunceller - /health bu sayede supervisor'in "calisiyor gorunup aslinda
    ilerlemedigi" (crash-restart dongusu) durumu ayirt edebilir."""
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        "task.>",
        durable=settings.TASK_CONSUMER_DURABLE,
        stream="TASK",
        config=ConsumerConfig(max_deliver=TASK_MAX_DELIVER, ack_wait=90),
    )
    logger.info("Department Manager basladi (task.> dinleniyor).")
    while True:
        heartbeat["last_loop"] = datetime.now(timezone.utc)
        try:
            msgs = await sub.fetch(3, timeout=5)
        except TimeoutError:
            continue

        for msg in msgs:
            await _process_one(nc, http, msg)


async def _process_one(nc: nats.NATS, http: httpx.AsyncClient, msg):
    is_last_attempt = msg.metadata.num_delivered >= TASK_MAX_DELIVER
    source_id = f"{msg.metadata.stream}:{msg.metadata.sequence.stream}"

    try:
        workflow_name = msg.subject.split(".", 1)[1] if "." in msg.subject else "unknown"
        raw = msg.data.decode()
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Bozuk task mesaji, dusuruluyor ({msg.subject}): {e}")
        await msg.term()
        return

    department = WORKFLOW_TO_DEPARTMENT.get(workflow_name)
    if department is None:
        logger.warning(f"'{workflow_name}' workflow'u icin departman eslesmesi yok, 'operations'a yonlendiriliyor.")
        department = "operations"

    # project="" ise "unassigned" havuzuna duser - Project Manager'da HICBIR
    # projede gorunmeyen (sessiz kor nokta) is kategorisi olusmasin diye.
    effective_project = payload.get("project") or "unassigned"

    backlog_content = {
        "workflow": workflow_name,
        "project": payload.get("project", ""),
        "prompt": payload.get("prompt"),
        "plan_summary": (payload.get("plan") or "")[:500],
        "requires_user_approval": payload.get("requires_user_approval", False),
        "status": "queued_for_workers",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    ok = await _remember(http, "department", f"{department}-backlog", backlog_content, idempotency_key=f"backlog:{source_id}")

    if not ok:
        if is_last_attempt:
            dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, "Memory'e yazilamadi (son deneme)", raw)
            if dlq_ok:
                await msg.ack()
            else:
                await msg.nak(delay=30)
        else:
            await msg.nak(delay=5)
        return

    # PROJE-BAZLI ayrica kaydedilir (core/projects, Phase 6) - {department}-backlog
    # TUM projelerin ortak havuzu oldugu icin (limit=N ile sabit sayida kayit
    # cekilip client-side filtrelenirse havuz buyudukce eski kayitlar sessizce
    # kaybolur, bkz. Fable 5 Phase 6 denetimi K1) Project Manager bu ayri,
    # kucuk/izole scope_key'den okur. Basarisiz olsa bile ana akisi durdurmaz -
    # department gorunumu (yukaridaki) zaten kalici kaydedildi, bu ikincil bir
    # indeks/gorunumdur.
    await _remember(http, "project", f"{effective_project}-backlog", {**backlog_content, "department": department},
                     idempotency_key=f"project-backlog:{source_id}")

    try:
        await _report(nc, department, {
            "status": "received",
            "workflow": workflow_name,
            "note": "Worker sistemi (Phase 5) henuz kurulmadigi icin gorev backlog'a alindi.",
        }, msg_id=f"report:{source_id}")
    except Exception as e:
        if is_last_attempt:
            dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, f"Rapor yayinlanamadi (son deneme): {e}", raw)
            if dlq_ok:
                await msg.ack()
            else:
                await msg.nak(delay=30)
        else:
            logger.warning(f"Rapor yayinlanamadi ({department}): {e}")
            await msg.nak(delay=5)
        return

    await msg.ack()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nc = await nats.connect(settings.NATS_URL)
    app.state.http = httpx.AsyncClient(timeout=30.0)
    app.state.background_tasks: set[asyncio.Task] = set()
    app.state.heartbeat = {"last_loop": None}

    task = asyncio.create_task(_task_supervisor(app.state.nc, app.state.http, app.state.heartbeat))
    app.state.task_consumer = task
    app.state.background_tasks.add(task)
    task.add_done_callback(app.state.background_tasks.discard)

    logger.info("Department System NATS'a baglandi.")
    yield

    for t in list(app.state.background_tasks):
        t.cancel()
    await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
    await app.state.nc.close()
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Department System", lifespan=lifespan)


@app.get("/api/v1/departments", dependencies=[Depends(verify_api_key)])
async def list_departments():
    return {"departments": DEPARTMENTS, "workflow_mapping": WORKFLOW_TO_DEPARTMENT}


@app.get("/api/v1/departments/{name}/backlog", dependencies=[Depends(verify_api_key)])
async def get_backlog(name: str, limit: int = 20):
    if name not in DEPARTMENTS:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen departman: {name}. Gecerli: {DEPARTMENTS}")
    try:
        resp = await app.state.http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": "department", "scope_key": f"{name}-backlog", "limit": limit},
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Memory servisi zaman asimina ugradi")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory servisine erisilemedi: {e}")
    if resp.status_code == 404:
        return {"department": name, "items": []}
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail=f"Memory servisi hata dondurdu: {resp.status_code}")
    resp.raise_for_status()
    return resp.json()


@app.get("/health")
async def health():
    checks = {}
    try:
        checks["nats"] = app.state.nc.is_connected
    except Exception:
        checks["nats"] = False
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False

    task_consumer = getattr(app.state, "task_consumer", None)
    task_alive = task_consumer is not None and not task_consumer.done()
    # Sadece task.done()==False yeterli degil: supervisor sonsuz crash-restart
    # dongusundeyken de task hep "alive" gorunur ama ilerleme olmaz. Son fetch
    # dongusunun 60s icinde calistigini da kontrol et (fetch timeout=5s, normal
    # calismada heartbeat cok sik guncellenir).
    heartbeat = getattr(app.state, "heartbeat", {})
    last_loop = heartbeat.get("last_loop")
    heartbeat_ok = last_loop is not None and (datetime.now(timezone.utc) - last_loop).total_seconds() < 60
    checks["task_consumer"] = task_alive and heartbeat_ok

    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
