#!/usr/bin/env python3
"""
Ki-Social Publishing MCP Server — REST API adapter for content generation and publishing
Provides MCP tools for social media operations via ki-social-backend.
"""

import os
import sys
import logging
from typing import Optional
import traceback
import httpx
from mcp.server import FastMCP

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("social-mcp")

# Environment variables
KI_SOCIAL_API_URL = os.getenv("KI_SOCIAL_API_URL", "http://127.0.0.1:8021/api/v1")

# MCP Server setup
mcp = FastMCP("ki-social-publishing")

# HTTP client
http_client = httpx.Client(timeout=60.0)


def api_request(method: str, path: str, json_data: Optional[dict] = None) -> dict:
    """
    Make an HTTP request to ki-social-backend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., "/accounts/", "/generate/content")
        json_data: JSON payload for POST/PUT requests

    Returns:
        Response data dict, or {"error": str} on failure
    """
    url = f"{KI_SOCIAL_API_URL}{path}"
    try:
        if method.upper() == "GET":
            response = http_client.get(url)
        elif method.upper() == "POST":
            response = http_client.post(url, json=json_data)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}

        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API request failed: {method} {path} — {e}")
        return {"error": str(e)}


@mcp.tool()
def generate_content(topic: str, platform: str = "instagram", tone: str = "professional") -> str:
    """
    Generate a social media content draft (caption, image, etc.) using ki-social.

    Args:
        topic: Topic or subject for the content
        platform: Social media platform (instagram, twitter, linkedin, etc.) - default: instagram
        tone: Tone of the content (professional, casual, humorous, etc.) - default: professional

    Returns:
        Generated content details or error message
    """
    if not topic:
        return '{"error": "topic is required"}'

    payload = {
        "topic": topic,
        "platforms": [platform],
        "content_type": "post",
        "generate_image": True,
    }

    # Call POST /api/v1/generate/content
    result = api_request("POST", "/generate/content", payload)
    if "error" in result:
        return f'{{"error": "Error generating content: {result["error"]}"}}'

    content = result
    output = f"Content draft created successfully:\n"
    output += f"  ID: {content.get('id', 'N/A')}\n"
    output += f"  Platform: {platform}\n"
    output += f"  Caption: {str(content.get('caption', 'N/A'))[:100]}...\n"
    output += f"  Status: {content.get('status', 'N/A')}\n"
    if content.get('image_url'):
        output += f"  Image: {content.get('image_url')}\n"

    return output


@mcp.tool()
def publish_content(content_id: str) -> str:
    """
    Publish a content draft to social media immediately.

    Args:
        content_id: UUID of the content item to publish

    Returns:
        Publication status and report
    """
    if not content_id:
        return '{"error": "content_id is required"}'

    # Call POST /api/v1/content/{content_id}/publish
    result = api_request("POST", f"/content/{content_id}/publish", {})
    if "error" in result:
        return f'{{"error": "Error publishing content: {result["error"]}"}}'

    publish_result = result
    output = f"Content published:\n"
    output += f"  Content ID: {publish_result.get('content', {}).get('id', 'N/A')}\n"
    output += f"  Success: {publish_result.get('success', False)}\n"
    if publish_result.get('error'):
        output += f"  Error: {publish_result.get('error')}\n"

    report = publish_result.get('report', {})
    if report:
        output += f"  Report:\n"
        for key, value in report.items():
            output += f"    - {key}: {value}\n"

    return output


@mcp.tool()
def list_accounts() -> str:
    """
    List all connected social media accounts.

    Returns:
        List of connected accounts with platform and status
    """
    result = api_request("GET", "/accounts/", None)
    if "error" in result:
        return f'{{"error": "Error listing accounts: {result["error"]}"}}'

    accounts = result if isinstance(result, list) else result.get("accounts", [])
    output = f"Found {len(accounts)} connected social media account(s):\n"
    for account in accounts:
        output += f"  - {account.get('platform', 'N/A').upper()}: {account.get('username', 'N/A')} (ID: {account.get('id', 'N/A')})\n"
        if account.get('status'):
            output += f"    Status: {account.get('status')}\n"

    return output


if __name__ == "__main__":
    mcp.run()
