#!/usr/bin/env python3
"""
skills-mcp: MCP server for role-based skill access.

Filters skills from core/skills/skills_registry.py by OWNER_ROLE environment variable
and exposes them as MCP tools. Each tool proxies to http://localhost:5007/api/v1/skills/{name}/execute.
"""

import json
import os
import sys
import traceback

import httpx
from mcp.server import FastMCP

def log_error(msg: str):
    """Log errors to stderr for debugging"""
    print(f"[skills-mcp] {msg}", file=sys.stderr, flush=True)

try:
    # Read OWNER_ROLE from environment (required)
    OWNER_ROLE = os.environ.get("OWNER_ROLE", "").strip()
    if not OWNER_ROLE:
        raise RuntimeError("OWNER_ROLE environment variable not set or empty")

    # Read INTERNAL_API_KEY from environment (required)
    INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "").strip()
    if not INTERNAL_API_KEY:
        raise RuntimeError("INTERNAL_API_KEY environment variable not set")

    log_error(f"Starting skills-mcp for OWNER_ROLE={OWNER_ROLE}")

    SKILLS_BASE_URL = "http://localhost:5007"

    # Import skills registry
    sys.path.insert(0, "/opt/ki-enterprise/core/skills")
    from skills_registry import SKILLS
    log_error(f"Loaded {len(SKILLS)} total skills from registry")

except Exception as e:
    log_error(f"ERROR during initialization: {e}")
    log_error(traceback.format_exc())
    raise

# Create FastMCP instance
mcp = FastMCP(f"skills-mcp-{OWNER_ROLE}")

# HTTP client for making requests to skills service
http = httpx.Client(timeout=30.0)


def _headers() -> dict:
    """Return headers with INTERNAL_API_KEY authorization."""
    return {"Authorization": f"Bearer {INTERNAL_API_KEY}"}


def _make_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make an HTTP request to the skills service."""
    url = f"{SKILLS_BASE_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    headers.update(_headers())

    try:
        resp = http.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Request to {endpoint} failed: {e}")


def _python_type_to_json_type(python_type: str) -> dict:
    """
    Convert Python type hint string to JSON schema type.

    Examples:
      "str" → {"type": "string"}
      "int" → {"type": "integer"}
      "list[str]" → {"type": "array", "items": {"type": "string"}}
    """
    python_type = python_type.strip()

    if python_type == "str":
        return {"type": "string"}
    elif python_type == "int":
        return {"type": "integer"}
    elif python_type == "float":
        return {"type": "number"}
    elif python_type == "bool":
        return {"type": "boolean"}
    elif python_type.startswith("list[") and python_type.endswith("]"):
        inner_type = python_type[5:-1].strip()
        inner_json = _python_type_to_json_type(inner_type)
        return {"type": "array", "items": inner_json}
    else:
        # Fallback for unknown types
        return {"type": "string"}


def _build_tool_input_schema(inputs_dict: dict) -> dict:
    """
    Build MCP tool input schema from skill's inputs dict.

    Skill input format:
      "field_name": {"type": "str/int/...", "required": bool, "description": "..."}

    MCP input schema format:
      {
        "type": "object",
        "properties": {...},
        "required": [...]
      }
    """
    properties = {}
    required_fields = []

    for field_name, field_spec in inputs_dict.items():
        field_type = field_spec.get("type", "str")
        field_desc = field_spec.get("description", "")
        is_required = field_spec.get("required", False)

        # Build JSON schema for this field
        json_type = _python_type_to_json_type(field_type)
        properties[field_name] = {
            **json_type,
            "description": field_desc
        }

        if is_required:
            required_fields.append(field_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required_fields
    }


# Filter skills by OWNER_ROLE and create MCP tools
filtered_skills = {
    name: spec for name, spec in SKILLS.items()
    if spec.get("owner_role") == OWNER_ROLE
}


try:
    # Register each skill as an MCP tool
    for skill_name, skill_spec in filtered_skills.items():
        skill_description = skill_spec.get("description", "")
        skill_inputs = skill_spec.get("inputs", {})

        # Build input schema
        input_schema = _build_tool_input_schema(skill_inputs)

        # Create a tool function for this skill
        def create_skill_tool(name: str, schema: dict):
            def skill_tool(**kwargs) -> str:
                """Execute a skill by proxying to the skills service."""
                try:
                    data = _make_request("POST", f"/api/v1/skills/{name}/execute", json={"inputs": kwargs})
                    return json.dumps(data, indent=2, ensure_ascii=False)
                except Exception as e:
                    return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)

            return skill_tool

        tool_func = create_skill_tool(skill_name, input_schema)
        tool_func.__name__ = skill_name
        tool_func.__doc__ = skill_description

        # Register with MCP
        mcp.tool(name=skill_name, description=skill_description)(tool_func)

    log_error(f"Registered {len(filtered_skills)} skills as MCP tools")

except Exception as e:
    log_error(f"ERROR during tool registration: {e}")
    log_error(traceback.format_exc())
    raise


if __name__ == "__main__":
    try:
        log_error(f"Starting MCP server: mcp_name={mcp.name}")
        mcp.run()
    except Exception as e:
        log_error(f"ERROR during mcp.run(): {e}")
        log_error(traceback.format_exc())
        raise
