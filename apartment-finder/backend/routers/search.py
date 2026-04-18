"""Search router — POST /api/search."""

import httpx
from fastapi import APIRouter, HTTPException

from models.requests import SearchRequest
from services.qasa_client import search_listings

router = APIRouter()


@router.post("/search")
async def post_search(body: SearchRequest):
    """Search Qasa listings with filters. Fetches all pages server-side."""
    try:
        result = await search_listings(
            area_identifier=body.areaIdentifier,
            min_room_count=body.minRoomCount,
            max_room_count=body.maxRoomCount,
            min_rent=body.minRent,
            max_rent=body.maxRent,
            min_square_meters=body.minSquareMeters,
            max_square_meters=body.maxSquareMeters,
            currency=body.currency,
            markets=body.markets,
            furnished=body.furnished,
            pets_allowed=body.petsAllowed,
            home_type=body.homeType,
            first_hand=body.firstHand,
            student_home=body.studentHome,
            senior_home=body.seniorHome,
            corporate_home=body.corporateHome,
            sort_by=body.sortBy,
            sort_direction=body.sortDirection,
        )
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Upstream API error")

    return result
