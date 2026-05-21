from __future__ import annotations

import json
from typing import Any

import httpx


async def mcp_call(server_url: str, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
    """Call a tool on an MCP server using the JSON-RPC protocol."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments or {}},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            server_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise RuntimeError(f"MCP error: {data['error']}")

    result = data.get("result", {})
    content = result.get("content", [])
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(parts)
    return json.dumps(result, indent=2)
