"""Tests for POST /api/travel-times."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

VALID_REQUEST = {
    "from_lat": 57.706,
    "from_lon": 11.940,
    "destinations": [
        {"label": "Office", "lat": 57.697, "lon": 11.979},
        {"label": "Park",   "lat": 57.710, "lon": 11.960},
    ],
}

# Simulated parsed data[0][20] — drive(0), transit(3), walk(2), bike(1)
_ALL_MODES = [
    [[0], 0, [540,  "9 min"]],
    [[3], 0, [1920, "32 min"]],
    [[2], 0, [2280, "38 min"]],
    [[1], 0, [780,  "13 min"]],
]

def _make_gmaps_body(modes_raw):
    """Build a fake Google Maps response with modes at data[0][20]."""
    inner = [None] * 21
    inner[20] = modes_raw
    return ")]}'\n" + json.dumps([inner])


def _mock_response(text: str, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def _patch(side_effect=None, return_value=None):
    if side_effect is not None:
        return patch(
            "dmv_aptfind.routers.travel_times.get_all_travel_times",
            new=AsyncMock(side_effect=side_effect),
        )
    return patch(
        "dmv_aptfind.routers.travel_times.get_all_travel_times",
        new=AsyncMock(return_value=return_value),
    )


_FULL_TIMES = {"drive": 9, "transit": 32, "walk": 38, "bike": 13}
_NULL_TIMES = {"drive": None, "transit": None, "walk": None, "bike": None}


@pytest.mark.asyncio
async def test_travel_times_returns_all_modes(async_client):
    with _patch(side_effect=[_FULL_TIMES, _FULL_TIMES]):
        response = await async_client.post("/api/travel-times", json=VALID_REQUEST)

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    r = data["results"][0]
    assert r["label"] == "Office"
    assert r["drive_minutes"] == 9
    assert r["transit_minutes"] == 32
    assert r["walk_minutes"] == 38
    assert r["bike_minutes"] == 13


@pytest.mark.asyncio
async def test_travel_times_maps_urls(async_client):
    with _patch(return_value=_FULL_TIMES):
        response = await async_client.post("/api/travel-times", json={
            "from_lat": 57.706,
            "from_lon": 11.940,
            "destinations": [{"label": "X", "lat": 57.697, "lon": 11.979}],
        })

    result = response.json()["results"][0]
    assert "travelmode=driving"   in result["maps_url_drive"]
    assert "travelmode=transit"   in result["maps_url_transit"]
    assert "travelmode=walking"   in result["maps_url_walk"]
    assert "travelmode=bicycling" in result["maps_url_bike"]
    assert "57.706" in result["maps_url_drive"]
    assert "57.697" in result["maps_url_drive"]


@pytest.mark.asyncio
async def test_travel_times_failure_returns_nulls(async_client):
    with _patch(return_value=_NULL_TIMES):
        response = await async_client.post("/api/travel-times", json={
            "from_lat": 57.706,
            "from_lon": 11.940,
            "destinations": [{"label": "X", "lat": 57.697, "lon": 11.979}],
        })

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["drive_minutes"] is None
    assert result["transit_minutes"] is None
    assert result["walk_minutes"] is None
    assert result["bike_minutes"] is None


@pytest.mark.asyncio
async def test_travel_times_empty_destinations(async_client):
    response = await async_client.post("/api/travel-times", json={
        "from_lat": 57.706,
        "from_lon": 11.940,
        "destinations": [],
    })
    assert response.status_code == 200
    assert response.json()["results"] == []


# --- Unit tests for gmaps_client directly ---

@pytest.mark.asyncio
async def test_gmaps_client_parses_all_modes():
    from dmv_aptfind.services.gmaps_client import get_all_travel_times

    body = _make_gmaps_body(_ALL_MODES)
    mock_resp = MagicMock()
    mock_resp.text = body
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_all_travel_times(57.706, 11.940, 57.697, 11.979, mock_client)
    assert result["drive"] == 9
    assert result["transit"] == 32
    assert result["walk"] == 38
    assert result["bike"] == 13


@pytest.mark.asyncio
async def test_gmaps_client_returns_nulls_on_exception():
    from dmv_aptfind.services.gmaps_client import get_all_travel_times

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))

    result = await get_all_travel_times(57.706, 11.940, 57.697, 11.979, mock_client)
    assert result == {"drive": None, "transit": None, "walk": None, "bike": None}


@pytest.mark.asyncio
async def test_gmaps_client_handles_missing_mode_gracefully():
    from dmv_aptfind.services.gmaps_client import get_all_travel_times

    # Only driving returned, others absent
    partial = [[[0], 0, [540, "9 min"]]]
    body = _make_gmaps_body(partial)
    mock_resp = MagicMock()
    mock_resp.text = body
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_all_travel_times(57.706, 11.940, 57.697, 11.979, mock_client)
    assert result["drive"] == 9
    assert result["transit"] is None
    assert result["walk"] is None
    assert result["bike"] is None
