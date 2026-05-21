from __future__ import annotations

import json
import os

import httpx


async def web_search(query: str) -> str:
    """Search the web using Bing Search API or Tavily."""
    provider = os.getenv("SEARCH_PROVIDER", "tavily").lower()
    if provider == "bing":
        return await _bing_search(query)
    return await _tavily_search(query)


async def _tavily_search(query: str) -> str:
    api_key = os.getenv("TAVILY_API_KEY", "")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": 5},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        return json.dumps(
            [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]} for r in results],
            indent=2,
        )


async def _bing_search(query: str) -> str:
    api_key = os.getenv("BING_SEARCH_API_KEY", "")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            headers={"Ocp-Apim-Subscription-Key": api_key},
            params={"q": query, "count": 5},
        )
        response.raise_for_status()
        data = response.json()
        pages = data.get("webPages", {}).get("value", [])
        return json.dumps(
            [{"title": p.get("name"), "url": p.get("url"), "snippet": p.get("snippet", "")} for p in pages],
            indent=2,
        )
