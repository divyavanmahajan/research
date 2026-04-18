"""Tests for POST /api/parse-url and services/url_parser.py."""

import httpx
import respx

from conftest import MOCK_HOME_RESPONSE
from services.url_parser import extract_home_id


# --- Unit tests for url_parser ---


def test_extract_home_id_valid():
    """extract_home_id returns correct ID from valid Qasa URL."""
    assert extract_home_id("https://qasa.com/se/en/home/1348599") == "1348599"


def test_extract_home_id_with_www():
    """extract_home_id works with www prefix."""
    assert extract_home_id("https://www.qasa.com/se/en/home/1348599") == "1348599"


def test_extract_home_id_qasa_se_domain():
    """extract_home_id works with qasa.se domain."""
    assert extract_home_id("https://qasa.se/se/home/1348599") == "1348599"


def test_extract_home_id_with_trailing_path():
    """extract_home_id works when URL has trailing path segments."""
    url = "https://qasa.com/se/en/home/1348599/some-slug"
    assert extract_home_id(url) == "1348599"


def test_extract_home_id_invalid_no_id():
    """extract_home_id returns None for URL without numeric ID."""
    assert extract_home_id("https://qasa.com/se/en/home/") is None


def test_extract_home_id_invalid_domain():
    """extract_home_id returns None for non-Qasa URL."""
    assert extract_home_id("https://example.com/home/123") is None


def test_extract_home_id_invalid_garbage():
    """extract_home_id returns None for random string."""
    assert extract_home_id("not a url at all") is None


def test_extract_home_id_empty():
    """extract_home_id returns None for empty string."""
    assert extract_home_id("") is None


# --- Integration tests for POST /api/parse-url ---


@respx.mock
async def test_parse_url_valid(async_client):
    """POST /api/parse-url with valid Qasa URL returns listing data."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(200, json=MOCK_HOME_RESPONSE)
    )

    response = await async_client.post(
        "/api/parse-url",
        json={"url": "https://qasa.com/se/en/home/1348599"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "1348599"
    assert data["rent"] == 11250


@respx.mock
async def test_parse_url_invalid(async_client):
    """POST /api/parse-url with invalid URL returns 400."""
    response = await async_client.post(
        "/api/parse-url",
        json={"url": "https://example.com/not-a-listing"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot parse home ID from URL"


@respx.mock
async def test_parse_url_upstream_error(async_client):
    """POST /api/parse-url returns 502 when Qasa returns HTTP error."""
    respx.post("https://api.qasa.se/graphql").mock(
        return_value=httpx.Response(500, text="Server Error")
    )

    response = await async_client.post(
        "/api/parse-url",
        json={"url": "https://qasa.com/se/en/home/1348599"},
    )
    assert response.status_code == 502
