# Google Maps Directions Protocol

## Overview

Google Maps displays travel times for four transport modes (driving, transit, walking, cycling) using a single undocumented internal API endpoint: `https://www.google.com/maps/preview/directions`. This endpoint accepts a compact protobuf-like query parameter (`pb`) and returns a large JSON array containing route data for all modes simultaneously. No API key, session cookie, or login is required.

All findings were captured via Chrome DevTools Protocol (CDP) on 2026-04-19 from the following URL:

```
https://www.google.com/maps/dir/57.7211054,11.9216104/57.70675,11.9401/@57.7115724,11.8998268,13z/data=!3m1!4b1!4m2!4m1!3e3?entry=ttu
```

Route: Oterdahlsgatan 14, Göteborg → Lindholmspiren 5, Göteborg
Observed times: Car 9 min, Transit 30 min, Walking 38 min, Cycling 13 min

## Prerequisites

- No account or API key required
- No cookies required
- No authentication tokens required
- A `User-Agent` header that looks like a browser is required (bare `curl` UA returns an empty response)
- The `Referer` header should point to a `maps.google.com` URL

## Page Load Sequence

| # | Request | Purpose |
|---|---------|---------|
| 1 | `GET /maps/dir/...` | Main page HTML (no route data embedded here) |
| 2 | `GET /maps/preview/directions?pb=...` | **Primary data fetch** — all route data and travel times for all modes |
| 3 | `POST /maps/_/MapsWizUi/data/batchexecute?rpcids=sv1Drc` | "Suggestions along route" panel (POIs en route) |
| 4 | `POST /maps/_/MapsWizUi/data/batchexecute?rpcids=r4skrb` | Merchant status check (irrelevant for travel times) |
| 5 | `POST /maps/_/MapsWizUi/data/batchexecute?rpcids=T4jwAf` | Viewport metadata (irrelevant for travel times) |
| 6 | `GET /maps/vt/pb=...` | Map tiles (images, irrelevant for travel times) |

The travel times for all four modes are returned in a single response to request #2.

## Request Reference

### All-Mode Travel Time Query

This is the only request needed to obtain travel times for all transport modes.

- **URL:** `https://www.google.com/maps/preview/directions`
- **Method:** GET
- **Required Headers:**
  ```
  User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  Referer: https://www.google.com/maps/
  Origin: https://www.google.com
  ```

- **Query Parameters:**

  | Parameter | Value | Notes |
  |-----------|-------|-------|
  | `authuser` | `0` | Always 0 (anonymous) |
  | `hl` | `sv` | UI language (affects string labels like "min", "km") |
  | `gl` | `se` | Country for transit data and locale |
  | `pb` | _(see below)_ | Route specification in protobuf-string format |

- **pb Parameter Structure (decoded):**

  The `pb` parameter uses Google's internal protobuf-as-query-string notation. Fields are prefixed with `!{index}{type}` where type is `m` (message/sub-object), `d` (double), `i` (int), `b` (bool), `e` (enum), `s` (string), `f` (float).

  ```
  !1m4!3m2!3d{ORIGIN_LAT}!4d{ORIGIN_LNG}!6e2
  !1m4!3m2!3d{DEST_LAT}!4d{DEST_LNG}!6e2
  !3m8!1m3!1d{MAP_RADIUS}!2d{MAP_CENTER_LNG}!3d{MAP_CENTER_LAT}!3m2!1i1024!2i768!4f13.1
  !6m56!1m5!18b1!30b1!31m1!1b1!34e1
  !2m4!5m1!6e2!20e3!39b1
  !6m27!49b1!63m0!66b1!74i150000!85b1!91b1!114b1!149b1!206b1!209b1!212b1!216b1!222b1!223b1!232b1!234b1!235b1!241b1!244b1!246b1!250b1!253b1!260b1!266b1!268b1!269b1!272b1
  !10b1!12b1!13b1!14b1!16b1
  !17m1!3e1
  !20m5!1e3!2e3!5e2!6b1!14b1
  !46m1!1b0!96b1!99b1
  !15m3!1s{ANY_32_CHAR_STRING}!7e81!15i10142
  ```

  **Key fields to substitute:**

  | Field | Description | Example |
  |-------|-------------|---------|
  | `!3d{ORIGIN_LAT}` | Origin latitude | `!3d57.7211054` |
  | `!4d{ORIGIN_LNG}` | Origin longitude | `!4d11.9216104` |
  | `!3d{DEST_LAT}` | Destination latitude | `!3d57.70675` |
  | `!4d{DEST_LNG}` | Destination longitude | `!4d11.9401` |
  | `!1d{MAP_RADIUS}` | Map viewport radius in meters | `!1d34100.601` |
  | `!2d{MAP_CENTER_LNG}` | Map center longitude | `!2d11.8998268` |
  | `!3d{MAP_CENTER_LAT}` | Map center latitude | `!3d57.7115724` |
  | `!1i1024!2i768` | Viewport width × height in pixels | (can use any reasonable values) |
  | `!17m1!3e{N}` | Active mode display (does NOT filter returned modes) | `!3e1` = transit |
  | `!15m3!1s{TOKEN}` | Session token (required for transit time; value is arbitrary) | `!1sRANDOMSTRING` |

  **Mode codes** (for `!3e{N}` in `!17m1`):
  - `0` = Driving
  - `1` = Transit (in the pb, though data[0][19]=3 means transit)
  - `2` = Walking
  - `3` = Cycling/Biking
  - `4` = Two-wheeler (some regions)

  **Critical discovery:** The `!15m3!1s{TOKEN}!7e81!15i10142` segment is required for the transit time to appear in the response. The token value itself is arbitrary — any alphanumeric string works. Without this segment, the transit entry in `data[0][20]` returns `[[3], 1]` (no duration) instead of `[[3], 0, [1800, "30 min"]]`.

- **Response Structure:**

  The response starts with `)]}'\n` (XSSI protection prefix) followed by a deeply nested JSON array.

  ```
  Response: )]}'\n[[...large array...]]
  ```

  After stripping the prefix and parsing as JSON, the key fields are:

  ```
  data[0][20]  →  Multi-mode travel time summary (4 entries, one per mode)
  data[0][1]   →  Detailed route alternatives with step-by-step instructions
  data[0][0]   →  Origin and destination geocoding info
  data[0][19]  →  Selected mode code (integer)
  data[0][11]  →  Canonical URL path for this route
  ```

  **Multi-mode summary at `data[0][20]`:**

  ```json
  [
    [[0], 0, [507, "8 min"]],
    [[3], 0, [1800, "30 min"], [[0]]],
    [[2], 0, [2286, "38 min"]],
    [[1], 0, [782, "13 min"]]
  ]
  ```

  Each entry: `[[mode_code], status_int, [duration_seconds, "N min"], [optional_data]]`

  | Mode code | Transport | `duration_seconds` path | `"N min"` path |
  |-----------|-----------|------------------------|----------------|
  | `[0]` | Driving | `data[0][20][0][2][0]` | `data[0][20][0][2][1]` |
  | `[3]` | Transit | `data[0][20][1][2][0]` | `data[0][20][1][2][1]` |
  | `[2]` | Walking | `data[0][20][2][2][0]` | `data[0][20][2][2][1]` |
  | `[1]` | Cycling | `data[0][20][3][2][0]` | `data[0][20][3][2][1]` |

  Note: The order of entries in `data[0][20]` is fixed (drive, transit, walk, bike) regardless of which mode is selected in `!17m1`.

  **Transit-specific timing at `data[0][1][N][0][5]`** (for each transit route alternative):

  ```json
  [
    [1776634545, "Europe/Stockholm", "23:35", 7200, 1776634500],
    [1776636301, "Europe/Stockholm", "00:05", 7200, 1776636300],
    ...
  ]
  ```

  Format: `[unix_timestamp, "timezone_name", "HH:MM", utc_offset_seconds, rounded_timestamp]`
  - Index 0: Departure time
  - Index 1: Arrival time

  **Route alternatives at `data[0][1]`:**

  Each entry is a route alternative. `data[0][1][N][0]` contains:
  - `[0]`: Mode code (3=transit, 2=walking)
  - `[2]`: `[distance_meters, "N.N km", 0]`
  - `[3]`: `[duration_seconds, "N min", rounded_seconds]`
  - `[5]`: Departure/arrival timestamps (transit only)
  - `[14]`: Transit line icons and walk segments summary

## How to Replicate Without a Browser

### Step 1 — Build the pb parameter

Replace the coordinate placeholders with your origin and destination coordinates. The map center should be roughly the midpoint between origin and destination, and the radius should cover the full route distance.

```python
import urllib.parse

origin_lat = 57.7211054
origin_lng = 11.9216104
dest_lat   = 57.70675
dest_lng   = 11.9401

# Approximate map center (midpoint)
center_lat = (origin_lat + dest_lat) / 2
center_lng = (origin_lng + dest_lng) / 2
# Approximate radius in meters (rough straight-line distance × 3)
import math
dlat = abs(origin_lat - dest_lat) * 111000
dlng = abs(origin_lng - dest_lng) * 111000 * math.cos(math.radians(center_lat))
radius = math.sqrt(dlat**2 + dlng**2) * 3

pb = (
    f"!1m4!3m2!3d{origin_lat}!4d{origin_lng}!6e2"
    f"!1m4!3m2!3d{dest_lat}!4d{dest_lng}!6e2"
    f"!3m8!1m3!1d{radius:.1f}!2d{center_lng}!3d{center_lat}!3m2!1i1024!2i768!4f13.1"
    "!6m56!1m5!18b1!30b1!31m1!1b1!34e1"
    "!2m4!5m1!6e2!20e3!39b1"
    "!6m27!49b1!63m0!66b1!74i150000!85b1!91b1!114b1!149b1!206b1!209b1!212b1"
    "!216b1!222b1!223b1!232b1!234b1!235b1!241b1!244b1!246b1!250b1!253b1"
    "!260b1!266b1!268b1!269b1!272b1"
    "!10b1!12b1!13b1!14b1!16b1"
    "!17m1!3e1"
    "!20m5!1e3!2e3!5e2!6b1!14b1"
    "!46m1!1b0!96b1!99b1"
    "!15m3!1sRANDOMTOKEN12345678901234!7e81!15i10142"
)
```

### Step 2 — Make the request

```python
import urllib.request, json, urllib.parse

url = (
    "https://www.google.com/maps/preview/directions"
    "?authuser=0&hl=en&gl=se"
    "&pb=" + urllib.parse.quote(pb)
)

req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/maps/",
    "Origin": "https://www.google.com",
})

with urllib.request.urlopen(req) as r:
    body = r.read().decode("utf-8")

# Strip XSSI prefix
if body.startswith(")]}'\n"):
    body = body[5:]

data = json.loads(body)

# Extract all-mode travel times
mode_names = {0: "Driving", 1: "Cycling", 2: "Walking", 3: "Transit"}
for entry in data[0][20]:
    mode_code = entry[0][0]
    if len(entry) >= 3 and isinstance(entry[2], list):
        seconds = entry[2][0]
        label   = entry[2][1]
        print(f"{mode_names.get(mode_code, mode_code)}: {label} ({seconds}s)")
```

Expected output:
```
Driving: 8 min (507s)
Transit: 30 min (1800s)
Walking: 38 min (2286s)
Cycling: 13 min (782s)
```

### Working curl Example

```bash
curl 'https://www.google.com/maps/preview/directions?authuser=0&hl=en&gl=se&pb=%211m4%213m2%213d57.7211054%214d11.9216104%216e2%211m4%213m2%213d57.70675%214d11.9401%216e2%213m8%211m3%211d34100.6%212d11.8998268%213d57.7115724%213m2%211i1024%212i768%214f13.1%216m56%211m5%2118b1%2130b1%2131m1%211b1%2134e1%212m4%215m1%216e2%2120e3%2139b1%216m27%2149b1%2163m0%2166b1%2174i150000%2185b1%2191b1%21114b1%21149b1%21206b1%21209b1%21212b1%21216b1%21222b1%21223b1%21232b1%21234b1%21235b1%21241b1%21244b1%21246b1%21250b1%21253b1%21260b1%21266b1%21268b1%21269b1%21272b1%2110b1%2112b1%2113b1%2114b1%2116b1%2117m1%213e1%2120m5%211e3%212e3%215e2%216b1%2114b1%2146m1%211b0%2196b1%2199b1%2115m3%211sRANDOMTOKEN12345678901234%217e81%2115i10142' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -H 'Referer: https://www.google.com/maps/' \
  -H 'Origin: https://www.google.com' \
  | sed 's/^)]}.//' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
modes = {0:'Driving', 1:'Cycling', 2:'Walking', 3:'Transit'}
for e in data[0][20]:
    mc = e[0][0]
    if len(e) >= 3 and isinstance(e[2], list):
        print(f'{modes.get(mc, mc)}: {e[2][1]} ({e[2][0]}s)')
"
```

## Dynamic Values

| Value | Where to get it | Required? |
|-------|-----------------|-----------|
| Origin lat/lng | Known (geocode your address if needed) | Yes |
| Destination lat/lng | Known | Yes |
| Map center lat/lng | Midpoint between origin and destination | Approximate — server accepts any reasonable value |
| Map radius | Rough distance in meters | Approximate |
| Session token (`!15m3!1s{TOKEN}`) | Any alphanumeric string ≥ 10 chars | Required for transit time; value is ignored by the server |
| `hl` (language) | ISO 639-1 code | Affects label strings ("min" vs "min" etc.) |
| `gl` (country) | ISO 3166-1 code | Affects transit data (local operators) |

## Feasibility Assessment

**Feasible to replicate server-side without a browser.** Verified working with a plain `urllib` request.

Summary of constraints:

| Factor | Status |
|--------|--------|
| Authentication | Not required |
| API key | Not required |
| Session cookie | Not required |
| Login | Not required |
| Browser JS execution | Not required |
| Session token in `pb` | Required (but any value works) |
| Browser-like User-Agent | Required |
| CORS | Not an issue server-side |

**Rate limiting:** No rate limiting signals (429, `x-ratelimit-*`) were observed during testing. However, since this is an undocumented internal API, Google may apply IP-level rate limits or bot detection at scale. Aggressive polling from a single IP could trigger CAPTCHAs or blocks.

**Stability warning:** This is an undocumented internal API. Google can change the `pb` parameter format, the response array structure, or the endpoint path without notice. The `data[0][20]` field position is not guaranteed to be stable across Google Maps JS builds.

## Additional Endpoints Observed

### `GET /maps/preview/place`
Returns detailed place information (address, photos, reviews) for origin and destination place IDs. Not needed for travel times.

### `POST /maps/_/MapsWizUi/data/batchexecute?rpcids=sv1Drc`
Calls `/MapsTravelLocationsService.SuggestAlongRoute` to return points of interest along the route. Uses the Google RPC-over-HTTP (`f.req` form-encoded) format. Requires `X-Same-Domain: 1` and `Content-Type: application/x-www-form-urlencoded` headers.

### `GET /maps/preview/log204`
Analytics pings. No data returned (204 response). Safely ignored.

### `GET /maps/vt/pb=...`
Map tile images (PNG/JPEG). Not needed for travel time data.
