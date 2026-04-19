"""OSRM routing client for walking and cycling travel times."""

import httpx

OSRM_BASE_URL = "http://router.project-osrm.org/route/v1"


async def get_route_duration_minutes(
    profile: str,
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    client: httpx.AsyncClient,
) -> int | None:
    """Return travel duration in whole minutes, or None on failure.

    profile: "foot" | "cycling"
    """
    url = f"{OSRM_BASE_URL}/{profile}/{from_lon},{from_lat};{to_lon},{to_lat}"
    try:
        response = await client.get(url, params={"overview": "false"}, timeout=10.0)
        data = response.json()
        if data.get("code") == "Ok" and data.get("routes"):
            seconds = data["routes"][0]["duration"]
            return max(1, round(seconds / 60))
    except Exception:
        pass
    return None
