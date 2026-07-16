"""
John (ki-enterprise/CEO) Telegram koprusu.

Miracin CEO'ya dogrudan komut verebilmesi + "Mirac Ki AI Cell" grubunda John'un
ayri bir katilimci olarak bulunmasi icin ince bir koprü. Karar/is mantigi
core/ceo (Temporal dispatch + exec board + approve_cost) tarafinda kalir; bu
servis SADECE Telegram <-> CEO API arasinda cevirmen.

Guvenlik: sadece Mirac'in kisisel DM'i (OWNER_CHAT_ID) ve tek bir onayli grup
(GROUP_CHAT_ID) dinlenir - baska hicbir chat'ten gelen komut isleme alinmaz.
"""
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [john-bridge] %(message)s")
logger = logging.getLogger("john-bridge")

HERE = Path(__file__).parent
STATE_FILE = HERE / "offset.json"

# core.env (paylasilan) + kendi .env'i (bot token) birlikte okunur.
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
local_env = _load_env(HERE / ".env")

JOHN_BOT_TOKEN = local_env["JOHN_BOT_TOKEN"]
INTERNAL_API_KEY = core_env["INTERNAL_API_KEY"]
CEO_API_URL = "http://127.0.0.1:5000"
AI_GATEWAY_URL = "http://127.0.0.1:5002"

OWNER_CHAT_ID = 5895622522        # Mirac'in kisisel Telegram DM'i
GROUP_CHAT_ID = -1004399310343    # "Mirac Ki AI Cell"
ALLOWED_CHATS = {OWNER_CHAT_ID, GROUP_CHAT_ID}

VALID_WORKFLOWS = list(json.loads(core_env["WORKFLOW_TO_DEPARTMENT"]).keys())

TG_API = f"https://api.telegram.org/bot{JOHN_BOT_TOKEN}"

# Chat basina en son dispatch edilen workflow_id - "bu workflowu durdur" gibi
# ID belirtmeyen dogal-dil iptal isteklerini cozebilmek icin (bkz. handle_cancel).
# Surec ici, kalici degil - bridge restart olursa unutulur (bilinen, kabul
# edilebilir kisit: restart nadir, kullanici /status ile ID'yi tekrar sorabilir).
LAST_DISPATCH_BY_CHAT: dict[int, str] = {}


def _load_offset() -> int:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()).get("offset", 0)
        except Exception:
            return 0
    return 0


def _save_offset(offset: int):
    STATE_FILE.write_text(json.dumps({"offset": offset}))


def send_message(client: httpx.Client, chat_id: int, text: str, reply_to: int | None = None):
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        resp = client.post(f"{TG_API}/sendMessage", json=payload, timeout=15.0)
        if resp.status_code != 200:
            logger.error(f"sendMessage basarisiz: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"sendMessage istisnasi: {e}")


def ceo_headers():
    return {"Authorization": f"Bearer {INTERNAL_API_KEY}"}


def handle_dispatch(client: httpx.Client, workflow: str, project: str, prompt: str, chat_id: int | None = None) -> str:
    if workflow not in VALID_WORKFLOWS:
        return f"'{workflow}' diye bir is turumuz yok. Elimizdekiler: {', '.join(VALID_WORKFLOWS)}."
    key = str(uuid.uuid4())
    try:
        resp = client.post(
            f"{CEO_API_URL}/api/v1/ceo/dispatch",
            headers={**ceo_headers(), "Idempotency-Key": key, "Content-Type": "application/json"},
            json={"prompt": prompt, "workflow": workflow, "project": project, "initiated_by": "mirac"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if chat_id is not None:
            LAST_DISPATCH_BY_CHAT[chat_id] = data["workflow_id"]
        return f"Dispatch edildi.\nworkflow_id: {data['workflow_id']}\nstatus: {data['status']}"
    except httpx.HTTPStatusError as e:
        # Ham JSON hata govdesini KULLANICIYA DOKME - John karakterinde,
        # anlasilir bir cumleye cevir (canli testte bulunan sorun: "CEO
        # reddetti (422): {\"detail\":\"Gecersiz proje...\"}" gibi teknik bir
        # dump, bir CEO'nun konusma tarzi degil).
        detail = "bilinmeyen bir hata"
        try:
            detail = e.response.json().get("detail", detail)
        except (ValueError, AttributeError):
            pass
        if e.response.status_code == 422 and "proje" in detail.lower():
            return f"'{project}' diye tanimli bir projemiz yok su an. {detail}\nHangisini kastettigini soylersen hemen baslatirim."
        return f"Bunu su haliyle baslatamam: {detail}"
    except Exception as e:
        return f"Su an sana ulasamiyorum, teknik bir sorun var: {e}"


def handle_approve(client: httpx.Client, workflow_id: str) -> str:
    try:
        resp = client.post(
            f"{CEO_API_URL}/api/v1/ceo/dispatch/{workflow_id}/approve",
            headers=ceo_headers(), timeout=15.0,
        )
        resp.raise_for_status()
        return f"Onaylandi: {workflow_id}"
    except httpx.HTTPStatusError as e:
        return f"Onay basarisiz ({e.response.status_code}): {e.response.text[:500]}"
    except Exception as e:
        return f"CEO'ya erisilemedi: {e}"


def handle_cancel(client: httpx.Client, workflow_id: str | None) -> str:
    """Canli testte bulunan ciddi hata icin eklendi: eskiden 'bu workflowu
    durdur' gibi bir istek, gercek bir iptal mekanizmasi OLMADIGI icin YENI
    bir workflow dispatch'ine donusuyordu. workflow_id verilmezse bu chat'te
    en son dispatch edilen ise (LAST_DISPATCH_BY_CHAT) bakilir."""
    if not workflow_id:
        return "Hangi isi durdurmami istedigini bilmiyorum - once bir is dispatch edilmis olmali, ya da /cancel <workflow_id> ile belirt."
    try:
        resp = client.post(
            f"{CEO_API_URL}/api/v1/ceo/dispatch/{workflow_id}/cancel",
            headers=ceo_headers(), timeout=15.0,
        )
        resp.raise_for_status()
        return f"Durdurma istegi gonderildi: {workflow_id}"
    except httpx.HTTPStatusError as e:
        return f"Durduramadim ({e.response.status_code}): {e.response.text[:300]}"
    except Exception as e:
        return f"CEO'ya erisilemedi: {e}"


def handle_status(client: httpx.Client, workflow_id: str | None) -> str:
    if workflow_id:
        try:
            resp = client.get(
                f"{CEO_API_URL}/api/v1/ceo/dispatch/{workflow_id}",
                headers=ceo_headers(), timeout=15.0,
            )
            resp.raise_for_status()
            return json.dumps(resp.json(), ensure_ascii=False, indent=2)[:3500]
        except httpx.HTTPStatusError as e:
            return f"Bulunamadi ({e.response.status_code}): {e.response.text[:300]}"
        except Exception as e:
            return f"CEO'ya erisilemedi: {e}"
    try:
        resp = client.get(f"{CEO_API_URL}/health", timeout=10.0)
        return f"CEO durumu: {json.dumps(resp.json(), ensure_ascii=False)}"
    except Exception as e:
        return f"CEO'ya erisilemedi: {e}"


GROUP_SPEAK_GUIDANCE = (
    "Grup ortami: Mirac, Aetheris (kisisel asistan) ve sen (John/CEO) ayni Telegram "
    "grubundasiniz - herkes birbirinin mesajini gorur. Dogrudan hitap edilmedigin her "
    "mesaja cevap verme (Aetheris'in kendi kurali da boyle - 'her mesaja cevap verme, "
    "gercek deger katmiyorsan sessiz kal'). respond=true SADECE su durumlarda: "
    "sana/CEO'ya dogrudan soru soruldu, adin gecti, sirket/proje/karar hakkinda gercek "
    "bilgi katkin var, ya da onay/karar bekleyen bir sey var. respond=false: sıradan "
    "sohbet, Aetheris'e yonelik bir sey, ya da senin katkinin gerek olmadigi mesajlarda."
)


def classify_message(client: httpx.Client, text: str, is_group: bool, addressed: bool) -> dict:
    """Serbest metni {cancel, workflow, project, prompt, respond} JSON'una cevirir.

    workflow != "none" -> is talebi, HER ZAMAN dispatch edilir (dogrudan komut,
    mention/adres sartina bakilmaz). workflow == "none" -> respond alanina gore
    (grupta) ya da her zaman (DM'de) sohbet cevabi verilir/verilmez.

    Canli testte bulunan hata: 'tum Ki Ecosystemi tara ve projeleri listele' gibi
    SALT BILGI sorgulari yanlislikla workflow=research_request + project='Ki
    Ecosystem' (gecersiz proje adi) olarak siniflandirilip CEO'dan 422 aliyordu.
    Asagidaki ek kural bunu onler - mevcut bilgiyi soran/ozetleyen istekler is
    talebi SAYILMAZ, dogrudan sohbete (chat_as_ceo) duser, orada John artik
    /opt/ki-ecosystem'i CANLI tarayip cevaplayabiliyor.

    IKINCI, DAHA CIDDI hata: 'bu workflowu durdur' gibi bir iptal istegi, ozel
    bir 'cancel' alani OLMADIGI icin YENI bir workflow (feature_request) olarak
    dispatch ediliyordu - is durdurulmuyor, ustune bir tane daha basliyordu.
    'cancel' alani bunu ayri, ONCELIKLI bir dal olarak isler (bkz. process_message)."""
    system = (
        "Sen bir siniflandirma aracisin. Kullanicinin mesajini asagidaki JSON semasina "
        "cevir, BASKA HICBIR SEY yazma (sadece JSON):\n"
        '{"cancel": <true|false>, "workflow": "<' + "|".join(VALID_WORKFLOWS) + '>", '
        '"project": "<proje-adi-veya-bos>", "prompt": "<islenecek talep, oz ve net>", '
        '"respond": <true|false>}\n'
        "Mesaj bir is talebi degilse (sohbet/soru/durum sorma ise) workflow alanina "
        '"none" yaz ve prompt alanini bos birak.\n'
        "ONEMLI: MEVCUT bilgiyi soran/ozetleyen istekler (orn. 'projelerimizi listele', "
        "'Ki Ecosystem'i tara', 'ne durumdayiz', 'hangi isler calisiyor') YENI BIR IS "
        "TALEBI DEGILDIR - bunlar icin de workflow='none' yaz, bunlari dispatch etme; "
        "CEO zaten canli veriye erisip dogrudan cevap verebiliyor.\n"
        "COK ONEMLI: Kullanici ACIKCA calisan/az once baslatilan bir isi durdurmak/"
        "iptal etmek istiyorsa (orn. 'bu workflowu durdur', 'iptal et', 'durdur', "
        "'dur', 'stop it', 'vazgec bundan') cancel=true yap ve workflow='none' yap - "
        "bunu ASLA yeni bir is olarak siniflandirma, iptal bir is TALEBI degildir.\n"
        + (GROUP_SPEAK_GUIDANCE if is_group else "Bu bir DM, Mirac dogrudan sana yaziyor - respond her zaman true olsun.")
    )
    default = {"cancel": False, "workflow": "none", "project": "", "prompt": "", "respond": not is_group or addressed}
    try:
        resp = client.post(
            f"{AI_GATEWAY_URL}/api/chat",
            headers={**ceo_headers(), "Content-Type": "application/json"},
            json={"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ]},
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return default
        parsed = json.loads(match.group(0))
        if addressed:
            parsed["respond"] = True  # dogrudan mention/reply/komut ise cevap sarti tartismasiz
        return parsed
    except Exception as e:
        logger.warning(f"Mesaj siniflandirilamadi: {e}")
        return default


# John'un sohbet karakteri artik burada DEGIL - tek merkezi kaynak core/ceo/main.py
# (POST /api/v1/ceo/chat, CEO_PERSONA + ceo:decisions baglami orada uretilir).
# Bu koprü sadece Telegram <-> CEO API cevirmeni (bkz. dosya basi aciklamasi).
def chat_as_ceo(client: httpx.Client, text: str) -> str:
    try:
        resp = client.post(
            f"{CEO_API_URL}/api/v1/ceo/chat",
            headers={**ceo_headers(), "Content-Type": "application/json"},
            json={"message": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["answer"]
    except Exception as e:
        return f"Su an sana ulasamiyorum, teknik bir sorun var: {e}"


def process_message(client: httpx.Client, msg: dict):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    if chat_id not in ALLOWED_CHATS:
        return  # izinsiz chat - sessizce yoksay

    if msg.get("from", {}).get("is_bot"):
        return  # baska bir bot (Aetheris dahil) - sonsuz bot-bot dongusunu engelle

    text = (msg.get("text") or "").strip()
    if not text:
        return

    message_id = msg.get("message_id")
    is_group = chat_id == GROUP_CHAT_ID
    mentioned = "@KiJohn_bot" in text
    is_reply_to_bot = (msg.get("reply_to_message", {}).get("from", {}).get("username") == "KiJohn_bot")
    addressed = mentioned or is_reply_to_bot or text.startswith("/")

    clean = text.replace("@KiJohn_bot", "").strip()

    if clean.startswith("/dispatch"):
        parts = clean.split(maxsplit=3)
        if len(parts) < 4:
            reply = "Kullanim: /dispatch <workflow> <project|-> <prompt>\nworkflow: " + ", ".join(VALID_WORKFLOWS)
        else:
            _, workflow, project, prompt = parts
            project = "" if project == "-" else project
            reply = handle_dispatch(client, workflow, project, prompt, chat_id=chat_id)
    elif clean.startswith("/approve"):
        parts = clean.split(maxsplit=1)
        if len(parts) < 2:
            reply = "Kullanim: /approve <workflow_id>"
        else:
            reply = handle_approve(client, parts[1].strip())
    elif clean.startswith("/cancel"):
        parts = clean.split(maxsplit=1)
        wf_id = parts[1].strip() if len(parts) > 1 else LAST_DISPATCH_BY_CHAT.get(chat_id)
        reply = handle_cancel(client, wf_id)
    elif clean.startswith("/status"):
        parts = clean.split(maxsplit=1)
        wf_id = parts[1].strip() if len(parts) > 1 else None
        reply = handle_status(client, wf_id)
    elif clean.startswith("/help") or clean.startswith("/start"):
        reply = (
            "Ben John (CEO). Komutlar:\n"
            "/dispatch <workflow> <project|-> <prompt>\n"
            "/approve <workflow_id>\n"
            "/cancel [workflow_id]\n"
            "/status [workflow_id]\n"
            f"workflow degerleri: {', '.join(VALID_WORKFLOWS)}\n"
            "Ya da düz yaz, ne istediğini anlamaya çalışırım - grupta her mesajı görürüm, gerekince katılırım."
        )
    else:
        # Iş talebi mi, iptal mi, sohbet mi, grupta cevap vermeye deger mi - hepsi tek siniflandirmada.
        parsed = classify_message(client, clean, is_group, addressed)
        workflow = parsed.get("workflow", "none")
        if parsed.get("cancel"):
            reply = handle_cancel(client, LAST_DISPATCH_BY_CHAT.get(chat_id))
        elif workflow != "none":
            reply = (
                f"Şöyle anladım -> workflow: {workflow}, proje: {parsed.get('project') or '(genel)'}\n"
                f"Talep: {parsed.get('prompt') or clean}\n\n"
                + handle_dispatch(client, workflow, parsed.get("project", ""), parsed.get("prompt") or clean, chat_id=chat_id)
            )
        elif parsed.get("respond"):
            reply = chat_as_ceo(client, clean)
        else:
            return  # grupta katkı gerekmiyor - Aetheris'in "ne zaman konuş" ilkesiyle aynı, sessiz kal

    send_message(client, chat_id, reply, reply_to=message_id if is_group else None)


def main():
    offset = _load_offset()
    logger.info(f"John bridge basladi, offset={offset}")
    with httpx.Client() as client:
        while True:
            try:
                resp = client.get(
                    f"{TG_API}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=40.0,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"getUpdates basarisiz: {e}")
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if msg:
                    try:
                        process_message(client, msg)
                    except Exception as e:
                        logger.error(f"Mesaj isleme hatasi: {e}")
                _save_offset(offset)


if __name__ == "__main__":
    main()
