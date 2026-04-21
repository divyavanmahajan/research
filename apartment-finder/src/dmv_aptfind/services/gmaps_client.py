"""Google Maps internal directions client — all 4 transport modes in one request."""

import json
import math
import uuid
import urllib.parse

import httpx

_ENDPOINT = "https://www.google.com/maps/preview/directions"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.google.com/maps/",
    "Origin": "https://www.google.com",
}

# Maps mode_code (from data[0][20][N][0][0]) to key name
_MODE_NAMES = {0: "drive", 1: "bike", 2: "walk", 3: "transit"}


def _build_pb(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    token: str,
) -> str:
    center_lat = (from_lat + to_lat) / 2
    center_lon = (from_lon + to_lon) / 2
    dlat = abs(from_lat - to_lat) * 111_000
    dlon = abs(from_lon - to_lon) * 111_000 * math.cos(math.radians(center_lat))
    radius = math.sqrt(dlat**2 + dlon**2) * 3 or 5000.0

    return (
        f"!1m4!3m2!3d{from_lat}!4d{from_lon}!6e2"
        f"!1m4!3m2!3d{to_lat}!4d{to_lon}!6e2"
        f"!3m8!1m3!1d{radius:.1f}!2d{center_lon}!3d{center_lat}!3m2!1i1024!2i768!4f13.1"
        "!6m56!1m5!18b1!30b1!31m1!1b1!34e1"
        "!2m4!5m1!6e2!20e3!39b1"
        "!6m27!49b1!63m0!66b1!74i150000!85b1!91b1!114b1!149b1!206b1!209b1!212b1"
        "!216b1!222b1!223b1!232b1!234b1!235b1!241b1!244b1!246b1!250b1!253b1"
        "!260b1!266b1!268b1!269b1!272b1"
        "!10b1!12b1!13b1!14b1!16b1"
        "!17m1!3e1"
        "!20m5!1e3!2e3!5e2!6b1!14b1"
        "!46m1!1b0!96b1!99b1"
        f"!15m3!1s{token}!7e81!15i10142"
    )


async def get_all_travel_times(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    client: httpx.AsyncClient,
) -> dict[str, int | None]:
    """Return drive/transit/walk/bike minutes (or None) for a single origin→destination pair."""
    token = uuid.uuid4().hex[:24]
    pb = _build_pb(from_lat, from_lon, to_lat, to_lon, token)
    url = f"{_ENDPOINT}?authuser=0&hl=en&gl=se&pb={urllib.parse.quote(pb)}"

    try:
        response = await client.get(url, headers=_HEADERS, timeout=15.0)
        response.raise_for_status()
        body = response.text
        if body.startswith(")]}'\n"):
            body = body[5:]
        data = json.loads(body)
        modes_raw = data[0][20]
    except Exception:
        return {"drive": None, "transit": None, "walk": None, "bike": None}

    result: dict[str, int | None] = {"drive": None, "transit": None, "walk": None, "bike": None}
    for entry in modes_raw:
        try:
            mode_code = entry[0][0]
            key = _MODE_NAMES.get(mode_code)
            if key and len(entry) >= 3 and isinstance(entry[2], list):
                seconds = entry[2][0]
                result[key] = max(1, round(seconds / 60))
        except (IndexError, TypeError, KeyError):
            pass
    return result
