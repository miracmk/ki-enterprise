"""
KI Enterprise Memory Layer.

Memory tipleri: short, long, project, department, global, personal.
  - short  -> Redis (TTL'li, hizli erisim)
  - digerleri -> PostgreSQL (kalici) + istege bagli Qdrant (semantik arama icin embedding)

Atomiklik: embed=True ise once embedding hesaplanir (PG'ye hic dokunulmadan), sonra
PG insert + Qdrant upsert AYNI PG transaction'i icinde yapilir; Qdrant basarisiz olursa
PG insert rollback edilir (yari-yazilmis / vektorsuz "hayalet" kayit birakmaz).
"""
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import httpx
import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from config import settings
from db import get_pool

app = FastAPI(title="KI Enterprise Memory Layer")

MemType = Literal["short", "long", "project", "department", "global", "personal"]
QDRANT_COLLECTION = "ki_memory"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


class StoreRequest(BaseModel):
    mem_type: MemType
    scope_key: str
    content: dict[str, Any]
    metadata: dict[str, Any] = {}
    embed: bool = False
    # Verilirse, ayni idempotency_key ile tekrar store cagrisi (orn. NATS
    # consumer redelivery'si sonrasi) YENI bir satir eklemez, mevcut kaydi
    # aynen dondurur. NATS mesaj kaynakli yazan servisler (CEO, Executive
    # Board, Department Manager) source mesajin stream+sequence'ini kullanir.
    idempotency_key: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    mem_type: Optional[MemType] = None
    top_k: int = 5


@app.on_event("startup")
async def startup():
    app.state.redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    app.state.pg = await get_pool(settings.POSTGRES_URL)
    app.state.qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    app.state.http = httpx.AsyncClient(timeout=30.0)
    collections = await app.state.qdrant.get_collections()
    if QDRANT_COLLECTION not in [c.name for c in collections.collections]:
        await app.state.qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=settings.EMBEDDING_DIM, distance=Distance.COSINE),
        )


@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.aclose()
    await app.state.pg.close()
    await app.state.http.aclose()


async def _embed(text: str) -> list[float]:
    resp = await app.state.http.post(
        f"{settings.LITELLM_API_BASE}/embeddings",
        headers={"Authorization": f"Bearer {settings.LITELLM_API_KEY}"},
        json={"model": settings.EMBEDDING_MODEL, "input": text},
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


@app.post("/api/v1/memory/store", dependencies=[Depends(verify_api_key)])
async def store_memory(req: StoreRequest):
    if req.mem_type == "short":
        key = f"short:{req.scope_key}"
        await app.state.redis.set(key, json.dumps(req.content), ex=settings.SHORT_MEMORY_TTL_SECONDS)
        return {"status": "stored", "backend": "redis", "key": key}

    vector = None
    text = None
    if req.embed:
        text = json.dumps(req.content)
        try:
            vector = await _embed(text)
        except (httpx.HTTPError, KeyError, IndexError) as e:
            raise HTTPException(status_code=502, detail=f"Embedding basarisiz, hicbir sey kaydedilmedi: {e}")

    try:
        async with app.state.pg.acquire() as conn:
            async with conn.transaction():
                if req.idempotency_key:
                    # Deterministik UUID (uuid5): ayni idempotency_key -> ayni id.
                    # ON CONFLICT DO UPDATE (no-op) RETURNING her zaman bir satir
                    # dondurur - ister yeni eklensin ister zaten var olsun.
                    row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, req.idempotency_key))
                    row = await conn.fetchrow(
                        """INSERT INTO memories (id, mem_type, scope_key, content, metadata)
                           VALUES ($1, $2, $3, $4, $5)
                           ON CONFLICT (id) DO UPDATE SET id = memories.id
                           RETURNING id, created_at, (xmax = 0) AS inserted""",
                        row_id, req.mem_type, req.scope_key, json.dumps(req.content), json.dumps(req.metadata),
                    )
                else:
                    row = await conn.fetchrow(
                        "INSERT INTO memories (mem_type, scope_key, content, metadata) VALUES ($1, $2, $3, $4) RETURNING id, created_at",
                        req.mem_type, req.scope_key, json.dumps(req.content), json.dumps(req.metadata),
                    )
                if req.embed and (not req.idempotency_key or row["inserted"]):
                    await app.state.qdrant.upsert(
                        collection_name=QDRANT_COLLECTION,
                        points=[PointStruct(id=str(row["id"]), vector=vector, payload={
                            "mem_type": req.mem_type, "scope_key": req.scope_key, "text": text,
                        })],
                    )
    except Exception as e:
        # transaction icinde exception -> PG insert rollback edildi, Qdrant'a hic yazilmadi.
        raise HTTPException(status_code=500, detail=f"Kayit basarisiz (rollback edildi): {e}")

    return {
        "status": "stored", "backend": "postgres", "id": str(row["id"]),
        "qdrant_point_id": str(row["id"]) if req.embed else None,
    }


@app.get("/api/v1/memory/exists", dependencies=[Depends(verify_api_key)])
async def check_exists(idempotency_key: str):
    """Bir idempotency_key ile daha once kayit yapilmis mi kontrol eder -
    PAHALI islemlerden (orn. LLM cagrisi) ONCE cagrilarak, redelivery/restart
    durumunda islemin GEREKSIZ YERE TEKRAR YAPILMASINI onlemek icin kullanilir.
    (idempotency_key sadece Memory'e DUPLICATE KAYIT yazilmasini onler, ondan
    ONCEKI pahali islemi engellemez - bu uc, cagirana "zaten yapilmis" bilgisini
    onceden vererek pahali islemi bastan atlatir.)"""
    row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key))
    async with app.state.pg.acquire() as conn:
        row = await conn.fetchrow("SELECT id, content, created_at FROM memories WHERE id=$1", row_id)
    if row is None:
        return {"exists": False}
    return {"exists": True, "id": str(row["id"]), "content": json.loads(row["content"]), "created_at": row["created_at"].isoformat()}


@app.get("/api/v1/memory/retrieve", dependencies=[Depends(verify_api_key)])
async def retrieve_memory(mem_type: MemType, scope_key: str, limit: int = 20):
    if mem_type == "short":
        val = await app.state.redis.get(f"short:{scope_key}")
        if val is None:
            raise HTTPException(status_code=404, detail="not found or expired")
        return {"mem_type": "short", "scope_key": scope_key, "content": json.loads(val)}

    async with app.state.pg.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, content, metadata, created_at FROM memories WHERE mem_type=$1 AND scope_key=$2 ORDER BY created_at DESC LIMIT $3",
            mem_type, scope_key, limit,
        )
    return {
        "mem_type": mem_type,
        "scope_key": scope_key,
        "items": [
            {"id": str(r["id"]), "content": json.loads(r["content"]), "metadata": json.loads(r["metadata"]),
             "created_at": r["created_at"].isoformat()}
            for r in rows
        ],
    }


@app.post("/api/v1/memory/search", dependencies=[Depends(verify_api_key)])
async def search_memory(req: SearchRequest):
    """Qdrant'ta semantik arama (embed=True ile kaydedilenler) + Postgres'te
    metin araması (embed=False ile kaydedilenler dahil TÜM kayıtlar) birleştirilir.
    Onceki surum sadece Qdrant'i tariyordu; embed=False (varsayilan) kayitlar hic
    goruntulenmiyordu."""
    vector = await _embed(req.query)
    query_filter = None
    if req.mem_type:
        query_filter = Filter(must=[FieldCondition(key="mem_type", match=MatchValue(value=req.mem_type))])

    semantic = await app.state.qdrant.query_points(
        collection_name=QDRANT_COLLECTION, query=vector, limit=req.top_k, query_filter=query_filter,
    )
    semantic_results = [
        {"id": str(p.id), "score": p.score, "source": "qdrant", "payload": p.payload} for p in semantic.points
    ]

    async with app.state.pg.acquire() as conn:
        if req.mem_type:
            rows = await conn.fetch(
                "SELECT id, mem_type, scope_key, content FROM memories WHERE mem_type=$1 AND content::text ILIKE $2 ORDER BY created_at DESC LIMIT $3",
                req.mem_type, f"%{req.query}%", req.top_k,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, mem_type, scope_key, content FROM memories WHERE content::text ILIKE $1 ORDER BY created_at DESC LIMIT $2",
                f"%{req.query}%", req.top_k,
            )
    seen_ids = {r["id"] for r in semantic_results}
    text_results = [
        {"id": str(r["id"]), "score": None, "source": "postgres_text",
         "payload": {"mem_type": r["mem_type"], "scope_key": r["scope_key"], "text": r["content"]}}
        for r in rows if str(r["id"]) not in seen_ids
    ]

    return {"results": semantic_results + text_results}


@app.get("/health")
async def health():
    checks = {}
    try:
        checks["redis"] = await app.state.redis.ping()
    except Exception:
        checks["redis"] = False
    try:
        async with app.state.pg.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False
    try:
        await app.state.qdrant.get_collections()
        checks["qdrant"] = True
    except Exception:
        checks["qdrant"] = False
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks, "time": datetime.now(timezone.utc).isoformat()}
