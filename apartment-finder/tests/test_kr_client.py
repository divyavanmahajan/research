"""Tests for KEY Relocation scraper and url_parser KR support (dmv_aptfind package)."""

import httpx
import respx

from dmv_aptfind.services.kr_client import fetch_kr_listing, _parse_swedish_date, _extract_th_value
from dmv_aptfind.services.url_parser import extract_kr_id

GUID = "FEA64C9F-F2B2-4CA4-AB40-5A755038247C"
KR_URL = f"https://kr-backoffice-web-production.azurewebsites.net/{GUID}"

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


def test_extract_kr_id_valid():
    assert extract_kr_id(KR_URL) == GUID


def test_extract_kr_id_invalid():
    assert extract_kr_id("https://qasa.com/se/en/home/1234") is None


def test_parse_swedish_date_with_weekday_prefix():
    assert _parse_swedish_date("ons 1 apr 2026") == "2026-04-01T00:00:00Z"


def test_extract_th_value_decodes_entities():
    html = "<table><tr><th>Post</th><td>41270 G&#xF6;teborg</td></tr></table>"
    assert _extract_th_value(html, "Post") == "41270 Göteborg"


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
    assert result["location"]["locality"] == "Göteborg"
    assert "Lägenheten" in result["description"]


@respx.mock
async def test_fetch_kr_listing_not_found():
    respx.get(KR_URL).mock(
        return_value=httpx.Response(302, headers={"location": "https://kr-backoffice-web-production.azurewebsites.net/"})
    )
    assert await fetch_kr_listing(KR_URL, GUID) is None


@respx.mock
async def test_parse_url_kr(async_client):
    respx.get(KR_URL).mock(return_value=httpx.Response(200, text=MOCK_KR_HTML))
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_RESPONSE)
    )

    response = await async_client.post("/api/parse-url", json={"url": KR_URL})
    assert response.status_code == 200
    assert response.json()["rent"] == 10000
