"""Tests for POST /api/travel-times."""

import httpx
import pytest
import respx
from unittest.mock import AsyncMock, patch

VALID_REQUEST = {
    "from_lat": 57.706,
    "from_lon": 11.940,
    "destinations": [
        {"label": "Office", "lat": 57.697, "lon": 11.979},
        {"label": "Park",   "lat": 57.710, "lon": 11.960},
    ],
}


def _patch(side_effect):
    return patch(
        "routers.travel_times.get_route_duration_minutes",
        new=AsyncMock(side_effect=side_effect),
    )


@pytest.mark.asyncio
async def test_travel_times_returns_durations(async_client):
    # foot→12, cycling→5 repeated for both destinations
    with _patch([12, 5, 12, 5]):
        response = await async_client.post("/api/travel-times", json=VALID_REQUEST)

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["label"] == "Office"
    assert data["results"][0]["walk_minutes"] == 12
    assert data["results"][0]["bike_minutes"] == 5


@pytest.mark.asyncio
async def test_travel_times_maps_urls(async_client):
    with _patch([10, 4]):
        response = await async_client.post("/api/travel-times", json={
            "from_lat": 57.706,
            "from_lon": 11.940,
            "destinations": [{"label": "X", "lat": 57.697, "lon": 11.979}],
        })

    result = response.json()["results"][0]
    assert "travelmode=walking"   in result["maps_url_walk"]
    assert "travelmode=bicycling" in result["maps_url_bike"]
    assert "travelmode=transit"   in result["maps_url_transit"]
    assert "57.706" in result["maps_url_walk"]
    assert "57.697" in result["maps_url_walk"]


@pytest.mark.asyncio
async def test_travel_times_osrm_failure_returns_none(async_client):
    with _patch([None, None]):
        response = await async_client.post("/api/travel-times", json={
            "from_lat": 57.706,
            "from_lon": 11.940,
            "destinations": [{"label": "X", "lat": 57.697, "lon": 11.979}],
        })

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["walk_minutes"] is None
    assert result["bike_minutes"] is None
    assert "maps_url_transit" in result


@pytest.mark.asyncio
async def test_travel_times_empty_destinations(async_client):
    response = await async_client.post("/api/travel-times", json={
        "from_lat": 57.706,
        "from_lon": 11.940,
        "destinations": [],
    })
    assert response.status_code == 200
    assert response.json()["results"] == []


# --- Unit tests for osrm_client service directly ---

@pytest.mark.asyncio
async def test_osrm_client_parses_duration():
    from services.osrm_client import get_route_duration_minutes
    from unittest.mock import AsyncMock, MagicMock

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": "Ok", "routes": [{"duration": 780.0, "distance": 900.0}]}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_route_duration_minutes("foot", 57.706, 11.940, 57.697, 11.979, mock_client)
    assert result == 13  # round(780 / 60)


@pytest.mark.asyncio
async def test_osrm_client_returns_none_on_non_ok_code():
    from services.osrm_client import get_route_duration_minutes
    from unittest.mock import AsyncMock, MagicMock

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": "NoRoute", "routes": []}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_route_duration_minutes("foot", 57.706, 11.940, 57.697, 11.979, mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_osrm_client_returns_none_on_exception():
    from services.osrm_client import get_route_duration_minutes
    from unittest.mock import AsyncMock, MagicMock

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))

    result = await get_route_duration_minutes("foot", 57.706, 11.940, 57.697, 11.979, mock_client)
    assert result is None
