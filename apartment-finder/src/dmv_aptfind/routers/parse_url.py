"""Parse URL router — POST /api/parse-url."""

import httpx
from fastapi import APIRouter, HTTPException

from ..models.requests import ParseUrlRequest
from ..services.qasa_client import fetch_listing
from ..services.url_parser import extract_home_id

router = APIRouter()


@router.post("/parse-url")
async def post_parse_url(body: ParseUrlRequest):
    """Parse a Qasa listing URL and return its listing data."""
    home_id = extract_home_id(body.url)
    if home_id is None:
        raise HTTPException(
            status_code=400, detail="Cannot parse home ID from URL"
        )

    try:
        data = await fetch_listing(home_id)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Upstream API error")

    if data is None:
        raise HTTPException(
            status_code=404, detail="Listing not found or unavailable"
        )

    return data
