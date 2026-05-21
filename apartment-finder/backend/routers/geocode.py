"""Geocode router — POST /api/geocode."""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from services.geocoder import geocode

router = APIRouter()


class GeocodeRequest(BaseModel):
    address: str


@router.post("/geocode")
async def post_geocode(body: GeocodeRequest):
    """Geocode a free-text address via Nominatim.

    Returns latitude/longitude, or nulls if the address cannot be found.
    """
    async with httpx.AsyncClient() as client:
        result = await geocode(body.address, client)
    if result:
        return {"latitude": result[0], "longitude": result[1]}
    return {"latitude": None, "longitude": None}
