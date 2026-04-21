"""Travel times router — POST /api/travel-times."""

import asyncio

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from services.gmaps_client import get_all_travel_times

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
    drive_minutes: int | None
    transit_minutes: int | None
    walk_minutes: int | None
    bike_minutes: int | None
    maps_url_drive: str
    maps_url_transit: str
    maps_url_walk: str
    maps_url_bike: str


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
        tasks = [
            get_all_travel_times(
                request.from_lat, request.from_lon, dest.lat, dest.lon, client
            )
            for dest in request.destinations
        ]
        all_times = await asyncio.gather(*tasks)

    results = []
    for dest, times in zip(request.destinations, all_times):
        results.append(DestinationResult(
            label=dest.label,
            drive_minutes=times["drive"],
            transit_minutes=times["transit"],
            walk_minutes=times["walk"],
            bike_minutes=times["bike"],
            maps_url_drive=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "driving"),
            maps_url_transit=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "transit"),
            maps_url_walk=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "walking"),
            maps_url_bike=_maps_url(request.from_lat, request.from_lon, dest.lat, dest.lon, "bicycling"),
        ))
    return TravelTimesResponse(results=results)
