"""Tests for GET /api/listing/{home_id} and GET /api/health."""

import httpx
import respx

from conftest import MOCK_HOME_RESPONSE


@respx.mock
async def test_health(async_client):
    """GET /api/health returns 200 with status ok."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@respx.mock
async def test_fetch_listing_valid_id(async_client):
    """GET /api/listing/{id} with valid numeric ID returns listing data."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(200, json=MOCK_HOME_RESPONSE)
    )

    response = await async_client.get("/api/listing/1348599")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "1348599"
    assert data["rent"] == 11250
    assert data["squareMeters"] == 48
    assert data["roomCount"] == 2.0
    assert data["location"]["locality"] == "Göteborg"
    assert len(data["uploads"]) == 1


@respx.mock
async def test_fetch_listing_invalid_id(async_client):
    """GET /api/listing/{id} with non-numeric ID returns 400."""
    response = await async_client.get("/api/listing/abc")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid home_id"


@respx.mock
async def test_fetch_listing_not_found(async_client):
    """GET /api/listing/{id} returns 404 when Qasa returns null home."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(200, json={"data": {"home": None}})
    )

    response = await async_client.get("/api/listing/9999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Listing not found or unavailable"


@respx.mock
async def test_fetch_listing_upstream_error(async_client):
    """GET /api/listing/{id} returns 502 when Qasa returns HTTP error."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    response = await async_client.get("/api/listing/1348599")
    assert response.status_code == 502
    assert response.json()["detail"] == "Upstream API error"


@respx.mock
async def test_cors_header(async_client):
    """No CORS headers by default — frontend is served from the same process."""
    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None
