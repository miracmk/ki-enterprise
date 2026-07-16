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


def sync_connections() -> dict:
    """Composio'dan bagli tum hesaplari ceker, ozetleyip cache dosyasina yazar."""
    accounts = []
    cursor = None
    while True:
        page = composio_client.connected_accounts.list(cursor=cursor, limit=100)
        accounts.extend(_sanitize_account(item) for item in page.items)
        cursor = page.next_cursor
        if not cursor:
            break

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
