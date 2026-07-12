#!/usr/bin/env python3
"""
ceo-mcp: MCP server for KI Enterprise CEO dispatch & ecosystem operations.

Uses FastMCP (simpler SDK) to proxy to http://127.0.0.1:5000.
"""

import json
import os
import uuid

import httpx
from mcp.server import FastMCP

# Read INTERNAL_API_KEY from environment
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY environment variable not set")

CEO_BASE_URL = "http://127.0.0.1:5000"

# Create FastMCP instance
mcp = FastMCP("ceo-mcp")

# HTTP client for making requests to CEO service
http = httpx.Client(timeout=30.0)


def _headers() -> dict:
    """Return headers with INTERNAL_API_KEY authorization."""
    return {"Authorization": f"Bearer {INTERNAL_API_KEY}"}


def _make_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make an HTTP request to the CEO service."""
    url = f"{CEO_BASE_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    headers.update(_headers())

    try:
        resp = http.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Request to {endpoint} failed: {e}")


@mcp.tool()
def ecosystem_scan() -> str:
    """Scan the KI Ecosystem (apps/ and websites/) to see active projects and their status."""
    data = _make_request("GET", "/api/v1/ceo/ecosystem-scan")
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def list_workflows(status: str = None) -> str:
    """List workflows from Temporal, optionally filtered by status (RUNNING, COMPLETED, FAILED, etc.)."""
    params = {}
    if status:
        params["status"] = status
    data = _make_request("GET", "/api/v1/ceo/workflows", params=params)
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def get_dispatch_status(workflow_id: str) -> str:
    """Get the status of a specific workflow by its ID."""
    if not workflow_id:
        return "Error: workflow_id required"
    data = _make_request("GET", f"/api/v1/ceo/dispatch/{workflow_id}")
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def dispatch_project(prompt: str, workflow: str = "new_project", project: str = "") -> str:
    """Dispatch a new project workflow. Initiates work in the CEO dispatch system."""
    if not prompt:
        return "Error: prompt required"
    
    body = {
        "prompt": prompt,
        "workflow": workflow,
        "project": project,
        "initiated_by": "openclaw-john"
    }
    idempotency_key = str(uuid.uuid4())
    headers = _headers()
    headers["Idempotency-Key"] = idempotency_key

    data = _make_request("POST", "/api/v1/ceo/dispatch", json=body, headers=headers)
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def cancel_workflow(workflow_id: str) -> str:
    """Cancel a running workflow."""
    if not workflow_id:
        return "Error: workflow_id required"
    data = _make_request("POST", f"/api/v1/ceo/dispatch/{workflow_id}/cancel")
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def approve_cost(workflow_id: str) -> str:
    """DANGEROUS: This tool approves REAL MONEY spending. Only call when the user (Miraç) explicitly and unambiguously approves in their message with clear affirmative words like 'onaylıyorum' (I approve), 'evet harca' (yes spend), 'onayla' (approve). Never call this proactively, never guess, never use 'probably would approve' logic. Double-check the user's exact message before calling."""
    if not workflow_id:
        return "Error: workflow_id required"
    data = _make_request("POST", f"/api/v1/ceo/dispatch/{workflow_id}/approve")
    return json.dumps(data, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
