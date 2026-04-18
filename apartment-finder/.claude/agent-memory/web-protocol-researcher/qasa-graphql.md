---
name: Qasa GraphQL API
description: Qasa.com uses a public unauthenticated GraphQL API at api.qasa.se/graphql for all listing data — no auth, no cookies, no CSRF
type: project
---

## Qasa API Summary (captured 2026-04-18)

**GraphQL endpoint:** `https://api.qasa.se/graphql`
- No authentication required for public listing reads
- No cookies, no API key, no CSRF token needed
- Only required headers: `Content-Type: application/json`, `Origin: https://qasa.com`, `Referer: https://qasa.com/`

**Primary query:** `HomeView` with variable `{ "id": "<listing_id_string>" }`
- listing_id is the numeric string from the URL: `.../home/{id}`
- Returns: rent, squareMeters, roomCount, status, rentalType, location (lat/lng/address), uploads (images), duration, traits (amenities), landlord profile, homeTemplates

**Framework:** Next.js 14 App Router — individual listing pages (/home/{id}) have NO `__NEXT_DATA__` embedded JSON. Data is fetched client-side via Apollo GraphQL after hydration.

**Why this matters for apartment-finder:** The existing scraper reads `__NEXT_DATA__` but that only works for search/listing pages (may be Pages Router). Individual listing detail pages require the GraphQL API.

**Image proxy:** `https://img.qasa.se/unsafe/{w}x{h}/smart/{original_s3_url}` (Thumbor)

**Protocol document:** `/Users/divya/projects/research/apartment-finder/protocol/qasa-protocol.md`

**How to apply:** When scraping individual Qasa listing pages, skip HTML parsing and call the GraphQL API directly. The listing ID from the URL is all that's needed.
