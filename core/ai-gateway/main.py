"""
KI Enterprise AI Gateway.

Tum modeller (GPT, Claude, Gemini, DeepSeek, Qwen, Ollama, Hermes...) LiteLLM uzerinden
buradan gecer. Bu servis, LiteLLM'in onune ince ve amaca-ozel bir katman koyar:

  POST /api/chat       - genel sohbet tamamlama
  POST /api/reason     - adim adim akil yurutme (sistem prompt'u ile guclendirilmis)
  POST /api/embedding  - metin embedding
  POST /api/agent      - tool-calling destekli ajan tamamlama

Tum uclar Authorization: Bearer <INTERNAL_API_KEY> ister - ucretli model proxy'sinin
kimliksiz acikta durmasi onlenir.
"""
import logging
import secrets
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-gateway")

app = FastAPI(title="KI Enterprise AI Gateway")


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        # Aciklanamayan/gecici 401'lerin teshisi icin: header hic yok mu, yanlis mi?
        reason = "header eksik" if not authorization else "key eslesmiyor"
        logger.warning(f"401 - yetkisiz istek ({reason})")
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: Optional[str] = None
    temperature: float = 0.7


class ReasonRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: Optional[str] = None


class AgentRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: Optional[list[dict[str, Any]]] = None
    model: Optional[str] = None


@app.on_event("startup")
async def startup():
    app.state.http = httpx.AsyncClient(
        base_url=settings.LITELLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LITELLM_API_KEY}"},
        timeout=90.0,
    )


@app.on_event("shutdown")
async def shutdown():
    await app.state.http.aclose()


async def _post(path: str, payload: dict) -> dict:
    try:
        resp = await app.state.http.post(path, json=payload)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"LiteLLM erisilemedi: {e}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest):
    payload = {
        "model": req.model or settings.DEFAULT_CHAT_MODEL,
        "messages": req.messages,
        "temperature": req.temperature,
    }
    return await _post("/chat/completions", payload)


@app.post("/api/reason", dependencies=[Depends(verify_api_key)])
async def reason(req: ReasonRequest):
    payload = {
        "model": req.model or settings.DEFAULT_REASON_MODEL,
        "messages": [
            {"role": "system", "content": "Adim adim, mantikli bir sekilde dusun ve gerekcelendirilmis bir sonuca var."},
            {"role": "user", "content": req.prompt},
        ],
        "temperature": 0.3,
    }
    return await _post("/chat/completions", payload)


@app.post("/api/embedding", dependencies=[Depends(verify_api_key)])
async def embedding(req: EmbeddingRequest):
    payload = {"model": req.model or settings.DEFAULT_EMBEDDING_MODEL, "input": req.input}
    return await _post("/embeddings", payload)


@app.post("/api/agent", dependencies=[Depends(verify_api_key)])
async def agent(req: AgentRequest):
    payload = {
        "model": req.model or settings.DEFAULT_AGENT_MODEL,
        "messages": req.messages,
    }
    if req.tools:
        payload["tools"] = req.tools
    return await _post("/chat/completions", payload)


@app.get("/health")
async def health():
    try:
        # base_url ".../v1" iceriyor, liveliness ucu /v1 altinda degil - mutlak URL kullan.
        resp = await app.state.http.get(
            settings.LITELLM_API_BASE.removesuffix("/v1") + "/health/liveliness", timeout=5.0
        )
        litellm_ok = resp.status_code == 200
    except Exception:
        litellm_ok = False
    return {"status": "ok" if litellm_ok else "degraded", "checks": {"litellm": litellm_ok}}
