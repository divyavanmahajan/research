"""Travel times router — POST /api/travel-times."""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from services.osrm_client import get_route_duration_minutes

router = APIRouter()


class TravelDestination(BaseModel):
    label: str
    lat: float
    lon: float


class TravelTimesRequest(BaseModel):
    from_lat: float
    from_lon: float
    destinations: list[TravelDestination]


class DestinationResult(BaseModel):
    label: str
    walk_minutes: int | None
    bike_minutes: int | None
    maps_url_walk: str
    maps_url_bike: str
    maps_url_transit: str


class TravelTimesResponse(BaseModel):
    results: list[DestinationResult]


def _maps_url(from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str) -> str:
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={from_lat},{from_lon}"
        f"&destination={to_lat},{to_lon}"
        f"&travelmode={mode}"
    )


@router.post("/travel-times", response_model=TravelTimesResponse)
async def travel_times(request: TravelTimesRequest) -> TravelTimesResponse:
    async with httpx.AsyncClient() as client:
        results = []
        for dest in request.destinations:
            walk, bike = await _fetch_both(
                request.from_lat, request.from_lon, dest.lat, dest.lon, client
            )
            results.append(DestinationResult(
                label=dest.label,
                walk_minutes=walk,
                bike_minutes=bike,
                maps_url_walk=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "walking"),
                maps_url_bike=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "bicycling"),
                maps_url_transit=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "transit"),
            ))
    return TravelTimesResponse(results=results)


async def _fetch_both(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float, client: httpx.AsyncClient
) -> tuple[int | None, int | None]:
    import asyncio
    walk, bike = await asyncio.gather(
        get_route_duration_minutes("foot", from_lat, from_lon, to_lat, to_lon, client),
        get_route_duration_minutes("cycling", from_lat, from_lon, to_lat, to_lon, client),
    )
    return walk, bike
