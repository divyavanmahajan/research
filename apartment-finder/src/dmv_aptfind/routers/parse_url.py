"""Parse URL router — POST /api/parse-url."""

import httpx
from fastapi import APIRouter, HTTPException

from ..models.requests import ParseUrlRequest
from ..services.kr_client import fetch_kr_listing
from ..services.qasa_client import fetch_listing
from ..services.url_parser import extract_home_id, extract_kr_id

router = APIRouter()


@router.post("/parse-url")
async def post_parse_url(body: ParseUrlRequest):
    """Parse a listing URL (Qasa or KEY Relocation) and return its listing data."""
    home_id = extract_home_id(body.url)
    if home_id is not None:
        try:
            data = await fetch_listing(home_id)
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=502, detail="Upstream API error")
        if data is None:
            raise HTTPException(status_code=404, detail="Listing not found or unavailable")
        return data

    kr_id = extract_kr_id(body.url)
    if kr_id is not None:
        data = await fetch_kr_listing(body.url, kr_id)
        if data is None:
            raise HTTPException(status_code=404, detail="KR listing not found")
        return data

    raise HTTPException(status_code=400, detail="Cannot parse home ID from URL")
