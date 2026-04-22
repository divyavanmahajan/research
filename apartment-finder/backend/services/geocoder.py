"""Nominatim geocoding helper."""

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "dmv-aptfind/1.0 (personal tool)"}


async def geocode(address: str, client: httpx.AsyncClient) -> tuple[float, float] | None:
    """Geocode an address string via Nominatim.

    Returns (latitude, longitude) or None if no result found.
    """
    response = await client.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1, "countrycodes": "se,no,fi"},
        headers=_HEADERS,
        timeout=10.0,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])
