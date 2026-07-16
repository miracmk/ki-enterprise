#!/usr/bin/env python3
"""
Twenty CRM MCP Server — GraphQL API adapter for KI Enterprise CEO/Board
Provides MCP tools for CRM operations: list/search people, companies, opportunities, notes.
"""

import os
import sys
import json
import logging
from typing import Optional, Any
import traceback
import httpx
from mcp.server import FastMCP

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twenty-mcp")

# Environment variables
TWENTY_API_URL = os.getenv("TWENTY_API_URL", "http://localhost:3020/graphql")
TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")

if not TWENTY_API_KEY:
    logger.error("TWENTY_API_KEY not set in environment")
    sys.exit(1)

# MCP Server setup
mcp = FastMCP("twenty-crm")

# HTTP client
http_client = httpx.Client(timeout=30.0)


def graphql_query(query: str, variables: Optional[dict] = None) -> dict:
    """
    Execute a GraphQL query against Twenty CRM API.

    Args:
        query: GraphQL query or mutation string
        variables: Optional variables dict

    Returns:
        Response data dict, or {"error": str} on failure
    """
    try:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = http_client.post(
            TWENTY_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {TWENTY_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result and result["errors"]:
            return {"error": str(result["errors"][0])}

        return result.get("data", {})
    except Exception as e:
        logger.error(f"GraphQL query failed: {e}")
        return {"error": str(e)}


@mcp.tool()
def list_people(limit: int = 10) -> str:
    """
    List people (contacts/leads) from Twenty CRM.

    Args:
        limit: Number of results to return (default: 10)

    Returns:
        Formatted list of people with names and contact info
    """
    query = f"""
    query {{
      people(first: {limit}) {{
        edges {{
          node {{
            id
            firstName
            lastName
            email
            phone
            linkedinUrl
            createdAt
          }}
        }}
      }}
    }}
    """
    result = graphql_query(query)
    if "error" in result:
        return json.dumps({"error": result["error"]})

    people = result.get("people", {}).get("edges", [])
    output = f"Found {len(people)} people:\n"
    for edge in people:
        node = edge.get("node", {})
        output += f"  - {node.get('firstName', '')} {node.get('lastName', '')} ({node.get('id', 'N/A')})\n"
        if node.get('email'):
            output += f"    Email: {node.get('email')}\n"

    return output


@mcp.tool()
def list_companies(limit: int = 10) -> str:
    """
    List companies from Twenty CRM.

    Args:
        limit: Number of results to return (default: 10)

    Returns:
        Formatted list of companies
    """
    query = f"""
    query {{
      companies(first: {limit}) {{
        edges {{
          node {{
            id
            name
            domainName
            address
            createdAt
          }}
        }}
      }}
    }}
    """
    result = graphql_query(query)
    if "error" in result:
        return json.dumps({"error": result["error"]})

    companies = result.get("companies", {}).get("edges", [])
    output = f"Found {len(companies)} companies:\n"
    for edge in companies:
        node = edge.get("node", {})
        output += f"  - {node.get('name', 'N/A')} ({node.get('id', 'N/A')})\n"
        if node.get('domainName'):
            output += f"    Domain: {node.get('domainName')}\n"

    return output


@mcp.tool()
def list_opportunities(limit: int = 10) -> str:
    """
    List opportunities (deals/leads) from Twenty CRM.

    Args:
        limit: Number of results to return (default: 10)

    Returns:
        Formatted list of opportunities
    """
    query = f"""
    query {{
      opportunities(first: {limit}) {{
        edges {{
          node {{
            id
            name
            stage
            amount
            expectedCloseDate
            createdAt
          }}
        }}
      }}
    }}
    """
    result = graphql_query(query)
    if "error" in result:
        return json.dumps({"error": result["error"]})

    opps = result.get("opportunities", {}).get("edges", [])
    output = f"Found {len(opps)} opportunities:\n"
    for edge in opps:
        node = edge.get("node", {})
        output += f"  - {node.get('name', 'N/A')} (Stage: {node.get('stage', 'N/A')}, ${node.get('amount', 0)})\n"

    return output


@mcp.tool()
def search_person(query_str: str) -> str:
    """
    Search for a person by name or email.

    Args:
        query_str: Name or email to search for

    Returns:
        Matching person(s) or error message
    """
    if not query_str:
        return json.dumps({"error": "query_str parameter required"})

    # Twenty search might use filters; for now, list all and filter client-side
    graphql_query_str = """
    query {
      people(first: 50) {
        edges {
          node {
            id
            firstName
            lastName
            email
            phone
          }
        }
      }
    }
    """
    result = graphql_query(graphql_query_str)
    if "error" in result:
        return json.dumps({"error": result["error"]})

    people = result.get("people", {}).get("edges", [])
    matches = []
    for edge in people:
        node = edge.get("node", {})
        name = f"{node.get('firstName', '')} {node.get('lastName', '')}".lower()
        email = (node.get('email', '') or "").lower()
        if query_str.lower() in name or query_str.lower() in email:
            matches.append(node)

    output = f"Found {len(matches)} matching person(s):\n"
    for person in matches:
        output += f"  - {person.get('firstName', '')} {person.get('lastName', '')} ({person.get('id', 'N/A')})\n"
        if person.get('email'):
            output += f"    Email: {person.get('email')}\n"

    return output


@mcp.tool()
def create_note(recordId: str, title: str, body: str) -> str:
    """
    Create a note/activity attached to a CRM record.

    Args:
        recordId: UUID of the record (person, company, opportunity, etc.)
        title: Note title
        body: Note body/content

    Returns:
        Success/error message with note details
    """
    if not recordId or not title or not body:
        return json.dumps({"error": "recordId, title, and body are required"})

    # Twenty's create note/activity mutation
    mutation = """
    mutation CreateNote($input: CreateNoteInput!) {
      createNote(input: $input) {
        id
        title
        body
      }
    }
    """
    variables = {
        "input": {
            "recordId": recordId,
            "title": title,
            "body": body
        }
    }

    result = graphql_query(mutation, variables)
    if "error" in result:
        return json.dumps({"error": f"Error creating note: {result['error']}"})

    note = result.get("createNote", {})
    output = f"Note created successfully:\n"
    output += f"  ID: {note.get('id', 'N/A')}\n"
    output += f"  Title: {note.get('title', 'N/A')}"
    return output


if __name__ == "__main__":
    mcp.run()
