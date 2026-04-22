"""Tests for KEY Relocation scraper and url_parser KR support."""

import httpx
import respx

from services.kr_client import fetch_kr_listing, _parse_swedish_date, _extract_th_value
from services.url_parser import extract_kr_id

GUID = "FEA64C9F-F2B2-4CA4-AB40-5A755038247C"
KR_URL = f"https://kr-backoffice-web-production.azurewebsites.net/{GUID}"

# Matches real page structure: <th>/<td> rows, card-header/card-body divs, Azure Blob hrefs
MOCK_KR_HTML = """<!DOCTYPE html>
<html><body>
<table>
  <tr><th>Hyra</th><td>10&#xA0;000 kr</td></tr>
  <tr><th>Storlek</th><td>75 kvm</td></tr>
  <tr><th>RoK</th><td>3 rok (1 sov, 1 bad)</td></tr>
  <tr><th>Gata</th><td><a href="#">Hackspettsgatan</a> <span>(v\u00e5n 3)</span></td></tr>
  <tr><th>Post</th><td>41270 G\u00f6teborg</td></tr>
  <tr><th>Tid</th><td><span>ons 1 apr 2026</span> - <span>Tillsvidare</span></td></tr>
</table>
<div class="card-header">Beskrivning</div>
<div class="card-body">L\u00e4genheten utg\u00f6r renoverad vind.</div>
<div class="card-header">Description in English</div>
<div class="card-body">The flat is located in the attic.</div>
<a href="https://krbackofficeprod.blob.core.windows.net/photos/abc.jpg"><img src="thumb.jpg"></a>
<a href="https://krbackofficeprod.blob.core.windows.net/photos/def.jpg"><img src="thumb2.jpg"></a>
</body></html>"""

NOMINATIM_RESPONSE = [{"lat": "57.6832", "lon": "11.9688", "display_name": "Göteborg"}]


# --- url_parser unit tests ---


def test_extract_kr_id_valid():
    assert extract_kr_id(KR_URL) == GUID


def test_extract_kr_id_case_insensitive():
    url = f"https://kr-backoffice-web-production.azurewebsites.net/{GUID.lower()}"
    assert extract_kr_id(url).lower() == GUID.lower()


def test_extract_kr_id_invalid():
    assert extract_kr_id("https://qasa.com/se/en/home/1234") is None


def test_extract_kr_id_random_string():
    assert extract_kr_id("not a url at all") is None


# --- Helper unit tests ---


def test_parse_swedish_date_with_weekday_prefix():
    assert _parse_swedish_date("ons 1 apr 2026") == "2026-04-01T00:00:00Z"


def test_parse_swedish_date_without_prefix():
    assert _parse_swedish_date("1 apr 2026") == "2026-04-01T00:00:00Z"


def test_parse_swedish_date_unknown_month():
    assert _parse_swedish_date("1 xyz 2026") is None


def test_extract_th_value_found():
    html = "<table><tr><th>Hyra</th><td>10 000 kr</td></tr></table>"
    assert _extract_th_value(html, "Hyra") == "10 000 kr"


def test_extract_th_value_not_found():
    html = "<table><tr><th>Hyra</th><td>10 000 kr</td></tr></table>"
    assert _extract_th_value(html, "Storlek") is None


def test_extract_th_value_decodes_entities():
    html = "<table><tr><th>Post</th><td>41270 G&#xF6;teborg</td></tr></table>"
    assert _extract_th_value(html, "Post") == "41270 Göteborg"


# --- fetch_kr_listing tests ---


@respx.mock
async def test_fetch_kr_listing_success():
    respx.get(KR_URL).mock(return_value=httpx.Response(200, text=MOCK_KR_HTML))
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_RESPONSE)
    )

    result = await fetch_kr_listing(KR_URL, GUID)

    assert result is not None
    assert result["id"] == f"kr-{GUID}"
    assert result["rent"] == 10000
    assert result["squareMeters"] == 75
    assert result["roomCount"] == 3.0
    assert result["floor"] == 3
    assert result["currency"] == "SEK"
    assert result["location"]["route"] == "Hackspettsgatan"
    assert result["location"]["postalCode"] == "41270"
    assert result["location"]["locality"] == "Göteborg"
    assert result["location"]["latitude"] == 57.6832
    assert result["location"]["longitude"] == 11.9688
    assert result["duration"]["startOptimal"] == "2026-04-01T00:00:00Z"
    assert result["duration"]["endUfn"] is True
    assert "Lägenheten" in result["description"]
    assert "The flat" in result["description"]
    assert len(result["uploads"]) == 2
    assert result["uploads"][0]["url"] == "https://krbackofficeprod.blob.core.windows.net/photos/abc.jpg"
    assert result["uploads"][0]["metadata"]["primary"] is True
    assert result["uploads"][1]["metadata"]["primary"] is False
    assert result["landlord"]["firstName"] == "KEY Relocation"


@respx.mock
async def test_fetch_kr_listing_not_found():
    respx.get(KR_URL).mock(
        return_value=httpx.Response(302, headers={"location": "https://kr-backoffice-web-production.azurewebsites.net/"})
    )

    result = await fetch_kr_listing(KR_URL, GUID)
    assert result is None


# --- Integration test: POST /api/parse-url with KR URL ---


@respx.mock
async def test_parse_url_kr(async_client):
    respx.get(KR_URL).mock(return_value=httpx.Response(200, text=MOCK_KR_HTML))
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_RESPONSE)
    )

    response = await async_client.post("/api/parse-url", json={"url": KR_URL})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == f"kr-{GUID}"
    assert data["rent"] == 10000


@respx.mock
async def test_parse_url_kr_not_found(async_client):
    respx.get(KR_URL).mock(
        return_value=httpx.Response(302, headers={"location": "https://kr-backoffice-web-production.azurewebsites.net/"})
    )

    response = await async_client.post("/api/parse-url", json={"url": KR_URL})
    assert response.status_code == 404
