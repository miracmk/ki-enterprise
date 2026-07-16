#!/usr/bin/env python3
"""
image-mcp: Cloudflare Workers AI ile gercek gorsel URETIMI.

2026-07-15/16 bulgusu (bkz. AGENTIC_ARCHITECTURE_PLAN.md SS13/SS14): LiteLLM'in
`/v1/images/generations` ucu, Cloudflare Workers AI'in stable-diffusion modeli
icin HTTP 200 donuyor ama bos `data:[]` - Cloudflare'in binary PNG yanitini
LiteLLM'in OpenAI-uyumlu JSON semasina CEVIREMEDIGI dogrulandi (gercek curl
testiyle: Cloudflare'i DOGRUDAN cagirinca gercek, gecerli bir 1024x1024 PNG
donuyor). Cozum: LiteLLM'i TAMAMEN BYPASS edip Cloudflare Workers AI'i
DOGRUDAN cagiran bu kucuk MCP sunucusu - core/skills-mcp/server.py ile AYNI
FastMCP deseni, tek bir tool.
"""

import os
import sys
import traceback

import httpx
from mcp.server.fastmcp import FastMCP, Image


def log_error(msg: str):
    print(f"[image-mcp] {msg}", file=sys.stderr, flush=True)


try:
    CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not CLOUDFLARE_API_TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN environment variable not set")

    CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not CLOUDFLARE_ACCOUNT_ID:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID environment variable not set")

    MODEL = os.environ.get("CLOUDFLARE_IMAGE_MODEL", "@cf/stabilityai/stable-diffusion-xl-base-1.0").strip()

    log_error(f"Starting image-mcp (model={MODEL})")
except Exception as e:
    log_error(f"ERROR during initialization: {e}")
    log_error(traceback.format_exc())
    raise

mcp = FastMCP("image-mcp")
http = httpx.Client(timeout=60.0)


@mcp.tool(
    name="generate_image",
    description=(
        "Bir metin aciklamasindan gercek bir gorsel (PNG) uretir - Cloudflare "
        "Workers AI'in ucretsiz katmani uzerinden (stable-diffusion-xl). "
        "'free as possible' prensibiyle secildi, kredi karti/ekstra maliyet "
        "gerektirmez."
    ),
)
def generate_image(prompt: str) -> Image:
    """Cloudflare Workers AI'a dogrudan istek atar, PNG bytes'i doner."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"
    resp = http.post(
        url,
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
        json={"prompt": prompt},
    )
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "image" not in content_type:
        # Cloudflare bazen hata JSON'u donebilir (gecerli PNG degil) - acikca yakala.
        raise RuntimeError(f"Cloudflare beklenmeyen yanit dondu (content-type={content_type}): {resp.text[:500]}")
    return Image(data=resp.content, format="png")


if __name__ == "__main__":
    try:
        log_error(f"Starting MCP server: mcp_name={mcp.name}")
        mcp.run()
    except Exception as e:
        log_error(f"ERROR during mcp.run(): {e}")
        log_error(traceback.format_exc())
        raise
