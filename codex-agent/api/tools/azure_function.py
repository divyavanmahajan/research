from __future__ import annotations

import json
import os
from typing import Any

import httpx


async def call_azure_function(url: str, payload: dict[str, Any] | None = None, method: str = "POST") -> str:
    """Call an Azure Function endpoint and return the response body."""
    api_key = os.getenv("AZURE_FUNCTION_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-functions-key"] = api_key

    async with httpx.AsyncClient(timeout=30) as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=headers, params=payload or {})
        else:
            response = await client.post(url, headers=headers, json=payload or {})
        response.raise_for_status()

    try:
        return json.dumps(response.json(), indent=2)
    except Exception:
        return response.text
