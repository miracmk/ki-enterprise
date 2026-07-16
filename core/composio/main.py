"""
Composio Integration Service — KI Enterprise'in 500+ dis app'e (Gmail, Slack,
GitHub, Notion, vb.) baglanti katmani. Bagli hesap/toolkit listesini periyodik
senkronlar (cache dosyasina yazar) ve departman/chief ajanlari adina yeni
baglanti (OAuth redirect linki) baslatabilir.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from composio import Composio
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("composio-service")

CACHE_PATH = Path(__file__).parent / "connections_cache.json"

composio_client = Composio(api_key=settings.COMPOSIO_API_KEY)

# Toolkit -> kategori haritasi (Integrations hub'inda gruplama icin, Miracin
# talebiyle eklendi: "CRM, Accounting, Social Media, Bank vb. alanlar
# olmasi lazim"). Composio kendisi CRM/Bank/Accounting sunmuyor (bunlar
# core/dashboard katmaninda core/finance ve Twenty CRM ile ayrica eklenir) -
# burada Composio'nun GERCEKTEN sundugu toolkit turlerini kategorize ederiz.
# Eslesmeyen her toolkit "other"a duser (silinmez/gizlenmez, sadece etiketsiz).
TOOLKIT_CATEGORY_MAP: dict[str, str] = {
    "instagram": "social_media", "facebook": "social_media", "linkedin": "social_media",
    "youtube": "social_media", "telegram": "social_media", "twitter": "social_media", "x": "social_media",
    "gmail": "productivity", "googledrive": "productivity", "googlesheets": "productivity",
    "googletasks": "productivity", "googlecalendar": "productivity", "notion": "productivity",
    "github": "dev_infra", "cloudflare": "dev_infra",
}


def _toolkit_category(toolkit: str | None) -> str:
    if not toolkit:
        return "other"
    return TOOLKIT_CATEGORY_MAP.get(toolkit, "other")


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def _sanitize_account(item) -> dict:
    """Token/secret alanlarini disariya sizdirmadan sadece ozet bilgiyi dondurur."""
    return {
        "id": item.id,
        "toolkit": item.toolkit.slug if item.toolkit else None,
        "status": item.status,
        "auth_scheme": item.auth_config.auth_scheme if item.auth_config else None,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "user_id": item.user_id,
    }


# Kimlik-cozumleme (Miracin talebi: "Instagram bagli ama hangi kullanici adi
# falan gibi" - insan-okunabilir kimlik gostermek). Composio'nun connected_account
# meta verisinde GERCEK kullanici adi/email YOK (canli test edildi) - bu yuzden
# her toolkit'in kendi "profil/whoami" action'ini (varsa) CALISTIRIP yanitindan
# email/username/login/handle/name alanini cikariyoruz. Aksiyon adi HARDCODE
# EDILMEZ - toolkit'in kendi action katalogundan dinamik bulunur (yanlis/
# uydurma action adi riski olmasin diye).
_IDENTITY_ACTION_CACHE: dict[str, str | None] = {}
_IDENTITY_ACTION_KEYWORDS = [
    "GET_PROFILE", "WHOAMI", "GET_ME", "MY_INFO", "MY_PROFILE",
    "USER_INFO", "GET_CURRENT_USER", "GET_ACCOUNT", "GET_PERSON",
]
# Bu ifadeleri iceren action'lar GERCEKTEN parametresiz "ben kimim" sorgusudur
# (orn. LINKEDIN_GET_MY_INFO) - "GET_PERSON" gibi genis eslesen ama aslinda
# bir person_id PARAMETRESI isteyen action'lardan (canli testte bulunan
# gercek hata: kisa oldugu icin yanlislikla seciliyordu) ONCELIKLE ayirt edilir.
_STRONG_IDENTITY_HINTS = [
    "MY_INFO", "MY_PROFILE", "WHOAMI", "GET_ME", "CURRENT_USER",
    "AUTHENTICATED_USER", "GET_PROFILE", "USER_INFO",
]
# Bu ifadeleri iceren adaylar HARIC TUTULUR - "GET_ME" gibi kaba substring
# eslesmesi yuzunden yanlislikla secilebilirler (canli testte bulunan gercek
# hata: FACEBOOK_GET_MESSAGE_DETAILS, "GET_ME" alt-dizesini icerdigi icin
# INSTAGRAM_GET_MESSENGER_PROFILE ise "GET_PROFILE" icerdigi icin yanlis
# secilmisti - ikisi de kimlik degil, mesajlasma ile ilgili).
_IDENTITY_EXCLUDE_HINTS = ["MESSENGER", "MESSAGE"]
_IDENTITY_FIELD_PRIORITY = ["email", "username", "login", "handle", "displayname", "fullname", "name"]


def _find_identity_action(toolkit_slug: str) -> str | None:
    """Toolkit'in action katalogunda kimlik-benzeri bir action arar (orn.
    GMAIL_GET_PROFILE, INSTAGRAM_GET_USER_INFO) - toolkit basina bir kez
    sorgulanir, sonuc surec-ici cache'lenir (17 hesap icin tekrar tekrar
    katalog taramasin diye)."""
    if toolkit_slug in _IDENTITY_ACTION_CACHE:
        return _IDENTITY_ACTION_CACHE[toolkit_slug]
    action = None
    try:
        result = composio_client.client.tools.list(toolkit_slug=toolkit_slug, limit=200)
        candidates = [
            t.slug for t in result.items
            if any(k in t.slug.upper() for k in _IDENTITY_ACTION_KEYWORDS)
            and not any(x in t.slug.upper() for x in _IDENTITY_EXCLUDE_HINTS)
        ]
        if candidates:
            strong = [c for c in candidates if any(h in c.upper() for h in _STRONG_IDENTITY_HINTS)]
            pool = strong or candidates
            action = min(pool, key=len)  # havuz icinde en kisa/en genel olani tercih edilir
    except Exception as e:
        logger.debug("Kimlik action'i aranamadi (%s): %s", toolkit_slug, e)
    _IDENTITY_ACTION_CACHE[toolkit_slug] = action
    return action


def _extract_identity(data, depth: int = 0) -> str | None:
    """Action yanitini gezip ilk anlamli kimlik alanini (email/username/login/
    handle/isim) bulur - alan adlari toolkit'e gore farkli oldugu icin
    (orn. 'emailAddress' vs 'email') normalize edilmis substring eslesmesi
    kullanilir, tam esitlik DEGIL."""
    if depth > 3 or not isinstance(data, dict):
        return None
    for field in _IDENTITY_FIELD_PRIORITY:
        for k, v in data.items():
            normalized = k.lower().replace("_", "").replace("-", "")
            if field in normalized and isinstance(v, str) and v.strip():
                return v.strip()
    for v in data.values():
        if isinstance(v, dict):
            found = _extract_identity(v, depth + 1)
            if found:
                return found
    return None


def _resolve_identity(toolkit_slug: str | None, connected_account_id: str, user_id: str) -> str | None:
    if not toolkit_slug:
        return None
    action = _find_identity_action(toolkit_slug)
    if not action:
        return None
    try:
        result = composio_client.tools.execute(
            action, {}, connected_account_id=connected_account_id, user_id=user_id,
            dangerously_skip_version_check=True,
        )
        data = result.get("data") if isinstance(result, dict) else None
        return _extract_identity(data)
    except Exception as e:
        logger.debug("Kimlik cozumlenemedi (%s/%s): %s", toolkit_slug, connected_account_id, e)
        return None


def sync_connections() -> dict:
    """Composio'dan bagli tum hesaplari ceker, ozetleyip cache dosyasina yazar.
    Her hesap icin kategori + (mumkunse) insan-okunabilir kimlik de eklenir -
    kimlik cozumleme gercek bir API cagrisi gerektirdigi icin SADECE bu
    periyodik sync sirasinda yapilir (saatte bir, agir degil)."""
    accounts = []
    cursor = None
    while True:
        page = composio_client.connected_accounts.list(cursor=cursor, limit=100)
        accounts.extend(_sanitize_account(item) for item in page.items)
        cursor = page.next_cursor
        if not cursor:
            break

    for acc in accounts:
        acc["category"] = _toolkit_category(acc["toolkit"])
        acc["identity"] = _resolve_identity(acc["toolkit"], acc["id"], acc["user_id"]) if acc["status"] == "ACTIVE" else None

    by_toolkit: dict[str, int] = {}
    for acc in accounts:
        by_toolkit[acc["toolkit"]] = by_toolkit.get(acc["toolkit"], 0) + 1

    snapshot = {
        "synced_at": time.time(),
        "total": len(accounts),
        "by_toolkit": by_toolkit,
        "accounts": accounts,
    }
    CACHE_PATH.write_text(json.dumps(snapshot, indent=2))
    logger.info("Composio sync tamamlandi: %d bagli hesap, %d toolkit", len(accounts), len(by_toolkit))
    return snapshot


async def sync_loop():
    while True:
        try:
            await asyncio.to_thread(sync_connections)
        except Exception:
            logger.exception("Composio periyodik sync basarisiz")
        await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sync_loop())
    yield
    task.cancel()


app = FastAPI(title="KI Enterprise - Composio Integration", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/composio/connections", dependencies=[Depends(verify_api_key)])
async def get_connections():
    if not CACHE_PATH.exists():
        return await asyncio.to_thread(sync_connections)
    return json.loads(CACHE_PATH.read_text())


@app.post("/api/v1/composio/sync", dependencies=[Depends(verify_api_key)])
async def force_sync():
    return await asyncio.to_thread(sync_connections)


@app.get("/api/v1/composio/toolkits", dependencies=[Depends(verify_api_key)])
async def list_toolkits(search: str | None = None, limit: int = 20):
    def _list():
        kwargs = {"limit": limit}
        if search:
            kwargs["search"] = search
        result = composio_client.client.toolkits.list(**kwargs)
        return [
            {
                "slug": t.slug,
                "name": t.name,
                "categories": [c.name for c in (t.meta.categories or [])] if t.meta else [],
            }
            for t in result.items
        ]

    return await asyncio.to_thread(_list)


class ConnectRequest(BaseModel):
    toolkit: str
    user_id: str = "ki-enterprise"


@app.post("/api/v1/composio/connect", dependencies=[Depends(verify_api_key)])
async def connect_toolkit(req: ConnectRequest):
    """
    Belirtilen toolkit icin yeni bir baglanti baslatir. OAuth gerektiren
    app'ler icin bir redirect_url doner - kullanici bu linki tarayicida
    acip onaylamalidir (tam otomatik OAuth mumkun degil).
    """
    def _authorize():
        req_obj = composio_client.toolkits.authorize(user_id=req.user_id, toolkit=req.toolkit)
        return {
            "toolkit": req.toolkit,
            "redirect_url": getattr(req_obj, "redirect_url", None),
            "connected_account_id": getattr(req_obj, "id", None) or getattr(req_obj, "connected_account_id", None),
        }

    try:
        return await asyncio.to_thread(_authorize)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5012)
