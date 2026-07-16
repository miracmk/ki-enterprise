"""
KI Enterprise Scheduler (Faz B1).

CEO'nun (John) Mirac'a proaktif gun basi/gun sonu raporu gondermesini VE
self-improvement analizinin periyodik olarak tetiklenmesini saglayan, tek
gorevi olan ince bir zamanlayici. Mesai saati kavrami YOK - gunun her
saatinde ayni sekilde calisir, sadece belirlenen saat dilimlerinde tetiklenir.

Rapor URETIMI core/ceo tarafinda kalir (POST /api/v1/ceo/daily-report) -
bu servis SADECE "ne zaman" sorusuna cevap verir + sonucu Telegram'a push
eder. Diger servislerle AYNI mimari (kendi venv'i, kendi systemd unit'i,
core.env'i paylasilan tek dogruluk kaynagi olarak okur - core/telegram-bridge
ile ayni _load_env deseni).
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scheduler] %(message)s")
logger = logging.getLogger("scheduler")

HERE = Path(__file__).parent
STATE_FILE = HERE / "scheduler_state.json"


def _load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


core_env = _load_env(HERE.parent.parent / "core.env")
# telegram-bridge'in kendi .env'i (bot token) - ayri bir servis ama ayni bot
# uzerinden Mirac'a mesaj atmak icin token'i ODUNC alir, kendi token'ini
# TUTMAZ (tek bot kimligi, tek dogruluk kaynagi core/telegram-bridge/.env).
bridge_env = _load_env(HERE.parent / "telegram-bridge" / ".env")

INTERNAL_API_KEY = core_env["INTERNAL_API_KEY"]
CEO_API_URL = "http://127.0.0.1:5000"
IMPROVEMENT_API_URL = "http://127.0.0.1:5010"
JOHN_BOT_TOKEN = bridge_env.get("JOHN_BOT_TOKEN", "")
OWNER_CHAT_ID = 5895622522  # Mirac'in kisisel Telegram DM'i (telegram-bridge ile ayni)
TG_API = f"https://api.telegram.org/bot{JOHN_BOT_TOKEN}"

TIMEZONE = ZoneInfo("Europe/Istanbul")
# core.env'de DAILY_REPORT_SLOTS tanimliysa onu kullanir (JSON: {"HH:MM": "morning"|"evening"}),
# yoksa varsayilan gun basi/gun sonu saatleri kullanilir.
DAILY_REPORT_SLOTS = json.loads(core_env.get("DAILY_REPORT_SLOTS", '{"09:00": "morning", "21:00": "evening"}'))
IMPROVEMENT_CHECK_INTERVAL_HOURS = int(core_env.get("IMPROVEMENT_CHECK_INTERVAL_HOURS", "6"))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state))
    except OSError as e:
        logger.warning(f"Scheduler state kaydedilemedi: {e}")


async def _send_telegram(http: httpx.AsyncClient, text: str):
    if not JOHN_BOT_TOKEN:
        logger.warning("JOHN_BOT_TOKEN bulunamadi (telegram-bridge/.env eksik/bos), Telegram'a gonderilemedi.")
        return
    try:
        resp = await http.post(f"{TG_API}/sendMessage", json={"chat_id": OWNER_CHAT_ID, "text": text})
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Telegram gonderimi basarisiz: {e}")


async def _fetch_daily_report(http: httpx.AsyncClient, report_type: str) -> str | None:
    try:
        resp = await http.post(
            f"{CEO_API_URL}/api/v1/ceo/daily-report",
            headers={"Authorization": f"Bearer {INTERNAL_API_KEY}"},
            json={"report_type": report_type},
            timeout=90.0,
        )
        resp.raise_for_status()
        return resp.json().get("report")
    except httpx.HTTPError as e:
        logger.error(f"Gunluk rapor alinamadi ({report_type}): {e}")
        return None


async def _trigger_improvement_analysis(http: httpx.AsyncClient):
    try:
        resp = await http.get(
            f"{IMPROVEMENT_API_URL}/api/v1/improvement/analyze",
            headers={"Authorization": f"Bearer {INTERNAL_API_KEY}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        logger.info(f"Self-improvement analizi tetiklendi: {resp.json().get('proposal_count')} oneri.")
    except httpx.HTTPError as e:
        logger.warning(f"Self-improvement analizi tetiklenemedi: {e}")


async def _scheduler_loop(http: httpx.AsyncClient, heartbeat: dict):
    state = _load_state()
    while True:
        heartbeat["last_loop"] = datetime.now(TIMEZONE)
        now = datetime.now(TIMEZONE)
        today = now.strftime("%Y-%m-%d")
        current_hm = now.strftime("%H:%M")

        if today != state.get("date"):
            # Yeni gun (veya servisin ilk hic calismasi) - gonderilen slotlar
            # sifirlanir, improvement kontrol zamanlamasi (gunler-arasi surekli)
            # KORUNUR. ONEMLI: gunun ilk kez gozlemlendigi anda ZATEN GECMIS
            # olan slotlar geriye-donuk GONDERILMEZ, dogrudan "gonderilmis"
            # sayilir - aksi halde servis gun ortasinda (ilk kurulum veya
            # restart sonrasi) baslatildiginda gecmis saatlerin hepsini
            # ani-ani Telegram'a "catch-up" olarak basardi (canli testte
            # bulunan gercek hata: 13:04'te baslatilinca "09:00" slotu hemen
            # tetiklendi, onaysiz bir mesaj gitti).
            already_past = [slot for slot in DAILY_REPORT_SLOTS if current_hm >= slot]
            state = {"date": today, "sent_slots": already_past, "last_improvement_check": state.get("last_improvement_check")}
            if already_past:
                logger.info(f"Gun ilk kez gozlemlendi, zaten gecmis slotlar geriye-donuk GONDERILMEDEN atlandi: {already_past}")

        for slot, report_type in DAILY_REPORT_SLOTS.items():
            if current_hm >= slot and slot not in state["sent_slots"]:
                logger.info(f"Gunluk rapor tetikleniyor (turu={report_type}, slot={slot}).")
                text = await _fetch_daily_report(http, report_type)
                if text:
                    await _send_telegram(http, text)
                    state["sent_slots"].append(slot)
                    _save_state(state)
                else:
                    logger.warning(f"Rapor uretilemedi (slot={slot}), bir sonraki dongude tekrar denenecek.")

        last_check = state.get("last_improvement_check")
        needs_check = last_check is None or (
            (now - datetime.fromisoformat(last_check)).total_seconds() > IMPROVEMENT_CHECK_INTERVAL_HOURS * 3600
        )
        if needs_check:
            await _trigger_improvement_analysis(http)
            state["last_improvement_check"] = now.isoformat()
            _save_state(state)

        await asyncio.sleep(60)


async def _scheduler_supervisor(http: httpx.AsyncClient, heartbeat: dict):
    """_scheduler_loop coker/baslangicta patlarsa sessizce olmesin diye
    loglayip backoff ile yeniden baslatir (diger servislerdeki ayni desen)."""
    while True:
        try:
            await _scheduler_loop(http, heartbeat)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Scheduler coktu, 5sn sonra yeniden baslatiliyor: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    app.state.heartbeat = {"last_loop": None}
    task = asyncio.create_task(_scheduler_supervisor(app.state.http, app.state.heartbeat))
    app.state.task = task
    logger.info(f"Scheduler basladi. Rapor slotlari: {DAILY_REPORT_SLOTS}")
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Scheduler", lifespan=lifespan)


@app.get("/health")
async def health():
    task = getattr(app.state, "task", None)
    task_alive = task is not None and not task.done()
    heartbeat = getattr(app.state, "heartbeat", {})
    last_loop = heartbeat.get("last_loop")
    heartbeat_ok = last_loop is not None and (datetime.now(TIMEZONE) - last_loop).total_seconds() < 120
    ok = task_alive and heartbeat_ok
    return {"status": "ok" if ok else "degraded", "checks": {"scheduler_loop": ok, "telegram_configured": bool(JOHN_BOT_TOKEN)}}
