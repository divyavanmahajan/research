"""Tests for POST /api/search."""

import httpx
import respx

from conftest import make_search_node, make_search_response


@respx.mock
async def test_search_basic(async_client):
    """POST /api/search with valid params returns results (single page)."""
    nodes = [make_search_node(f"{i}") for i in range(3)]
    mock_response = make_search_response(
        nodes=nodes, total_count=3, pages_count=1, has_next_page=False
    )
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = await async_client.post(
        "/api/search",
        json={"areaIdentifier": "se/gothenburg"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["totalCount"] == 3
    assert data["pagesCount"] == 1
    assert len(data["results"]) == 3
    assert data["results"][0]["id"] == "0"


@respx.mock
async def test_search_pagination(async_client):
    """POST /api/search fetches multiple pages and merges all results."""
    page1_nodes = [make_search_node(f"p1-{i}") for i in range(59)]
    page2_nodes = [make_search_node(f"p2-{i}") for i in range(10)]

    page1_response = make_search_response(
        nodes=page1_nodes, total_count=69, pages_count=2, has_next_page=True
    )
    page2_response = make_search_response(
        nodes=page2_nodes, total_count=69, pages_count=2, has_next_page=False
    )

    route = respx.post("https://api.qasa.se/graphql").mock(
        side_effect=[
            httpx.Response(200, json=page1_response),
            httpx.Response(200, json=page2_response),
        ]
    )

    response = await async_client.post(
        "/api/search",
        json={"areaIdentifier": "se/gothenburg", "minRoomCount": 2},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["totalCount"] == 69
    assert data["pagesCount"] == 2
    assert len(data["results"]) == 69

    # Verify both pages were fetched
    assert route.call_count == 2

    # Verify first result from page 1 and last from page 2
    assert data["results"][0]["id"] == "p1-0"
    assert data["results"][-1]["id"] == "p2-9"


@respx.mock
async def test_search_missing_area(async_client):
    """POST /api/search without areaIdentifier returns 422 (validation error)."""
    response = await async_client.post(
        "/api/search",
        json={"minRoomCount": 2},
    )
    # Pydantic validation catches missing required field
    assert response.status_code == 422


@respx.mock
async def test_search_upstream_error(async_client):
    """POST /api/search returns 502 when Qasa returns HTTP error."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    response = await async_client.post(
        "/api/search",
        json={"areaIdentifier": "se/gothenburg"},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Upstream API error"


@respx.mock
async def test_search_with_all_filters(async_client):
    """POST /api/search passes all filters correctly."""
    nodes = [make_search_node("1", rent=8000)]
    mock_response = make_search_response(
        nodes=nodes, total_count=1, pages_count=1, has_next_page=False
    )
    route = respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = await async_client.post(
        "/api/search",
        json={
            "areaIdentifier": "se/gothenburg",
            "minRoomCount": 2,
            "maxRoomCount": 4,
            "minRent": 5000,
            "maxRent": 15000,
            "minSquareMeters": 40,
            "maxSquareMeters": 100,
            "currency": "SEK",
            "markets": ["sweden"],
            "furnished": True,
            "petsAllowed": True,
            "homeType": "apartment",
            "firstHand": False,
            "studentHome": False,
            "seniorHome": False,
            "corporateHome": False,
            "sortBy": "rent",
            "sortDirection": "ascending",
        },
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert route.call_count == 1
