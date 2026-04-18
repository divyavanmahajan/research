"""Listing router — GET /api/listing/{home_id}."""

import httpx
from fastapi import APIRouter, HTTPException

from services.qasa_client import fetch_listing

router = APIRouter()


@router.get("/listing/{home_id}")
async def get_listing(home_id: str):
    """Fetch a single Qasa listing by home ID."""
    if not home_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid home_id")

    try:
        data = await fetch_listing(home_id)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Upstream API error")

    if data is None:
        raise HTTPException(
            status_code=404, detail="Listing not found or unavailable"
        )

    return data
