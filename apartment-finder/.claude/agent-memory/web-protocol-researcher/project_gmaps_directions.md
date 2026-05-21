---
name: Google Maps Directions API Protocol
description: Reverse-engineered internal Google Maps directions endpoint that returns travel times for all modes without auth
type: project
---

The Google Maps directions page fetches all transport mode travel times from a single internal endpoint:
`GET https://www.google.com/maps/preview/directions?pb=...`

**Why:** Documented on 2026-04-19 to support the apartment-finder project's commute time feature.

**How to apply:** Use the Python code in `docs/google-maps-directions-protocol.md` to fetch travel times for all 4 modes (drive, transit, walk, bike) without a browser.

Key findings:
- No auth, no cookies, no API key required
- Must include a `User-Agent` that looks like a browser
- `data[0][20]` in the response contains the 4-mode summary: `[[mode_code], status, [seconds, "N min"]]`
- Mode codes: 0=drive, 1=bike, 2=walk, 3=transit
- Transit time requires `!15m3!1s{ANY_STRING}!7e81!15i10142` in the pb param (the token value is ignored by the server)
- The `!6m56!...!6m27!...` block of feature flags in pb is required (returns HTTP 400 without it)
- Times are live/traffic-dependent; vary by time of day
- Response starts with `)]}'\n` XSSI prefix — strip before JSON parsing
