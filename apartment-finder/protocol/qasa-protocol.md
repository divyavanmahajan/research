# Qasa.com Individual Listing Data Request Protocol

Captured: 2026-04-18
Target URL: `https://qasa.com/se/en/home/1348599`
Method: Chrome DevTools Protocol (CDP) network capture, 140 total requests observed

---

## Overview

Qasa is a Next.js 14 app (App Router, not Pages Router). Individual listing pages do **not** use `__NEXT_DATA__` bootstrapping — no JSON blob is embedded in the HTML. All listing data is fetched client-side via **GraphQL POST requests** to `https://api.qasa.se/graphql` after the React shell hydrates. The GraphQL API requires no authentication for reading public listings.

The page fires four GraphQL operations in sequence after load:
1. `HomeView` — the primary listing data query (unauthenticated, returns everything)
2. `ViewingCalendarForHome` — viewing slots (unauthenticated)
3. `ExclusiveInsight` — analytics/market insights (returns partial data without auth)
4. `SuperApplicationQuota` — requires auth, returns `unauthorized` error for anonymous users

---

## Prerequisites

**None required** for reading public listing data. No login, no API key, no cookies needed.

The GraphQL endpoint at `https://api.qasa.se/graphql` accepts unauthenticated POST requests and returns full listing data for any public home ID.

---

## Page Load Sequence

| # | Request | Type | Auth Required | Purpose |
|---|---------|------|---------------|---------|
| 1 | `GET https://qasa.com/se/en/home/1348599` | Document | No | HTML shell (no embedded data) |
| 2–60 | `/_next/static/chunks/*.js`, fonts, CSS | Static assets | No | Next.js JS bundle |
| 3 | `POST https://api.qasa.se/graphql` (HomeView) | GraphQL | No | **All listing data** |
| 4 | `POST https://api.qasa.se/graphql` (ViewingCalendarForHome) | GraphQL | No | Viewing slots |
| 5 | `POST https://api.qasa.se/tracking/v1/homes/1348599/view` | REST POST | No | Page view tracking (fire-and-forget, 204) |
| 6 | `POST https://api.qasa.se/graphql` (ExclusiveInsight) | GraphQL | No | Market analytics |
| 7 | `POST https://api.qasa.se/graphql` (SuperApplicationQuota) | GraphQL | Yes | Tenant subscription info (irrelevant for scraping) |

---

## Request Reference

### 1. HomeView — Primary Listing Data Query

This is the only request needed to replicate listing data server-side.

- **URL:** `https://api.qasa.se/graphql`
- **Method:** POST
- **Required Headers:**
  ```
  Content-Type: application/json
  Origin: https://qasa.com
  Referer: https://qasa.com/
  ```
- **Optional Headers (sent by browser, not required by server):**
  ```
  User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...
  accept: */*
  sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"
  sec-ch-ua-mobile: ?0
  sec-ch-ua-platform: "macOS"
  ```
- **No cookies required** — confirmed by successful unauthenticated curl test.
- **Request Body:**
  ```json
  {
    "operationName": "HomeView",
    "variables": {
      "id": "1348599"
    },
    "query": "query HomeView($id: ID!) {\n  home(id: $id) {\n    id\n    title\n    rent\n    squareMeters\n    roomCount\n    status\n    rentalType\n    shared\n    description\n    descriptionBuilding\n    descriptionContract\n    descriptionFeatures\n    descriptionLayout\n    descriptionTransportation\n    floor\n    buildingFloors\n    buildYear\n    bathroomRenovationYear\n    kitchenRenovationYear\n    energyClass\n    tenureType\n    firsthand\n    seniorHome\n    studentHome\n    corporateHome\n    publishedAt\n    currency\n    insurance\n    insuranceCost\n    qasaGuarantee\n    qasaGuaranteeCost\n    tenantBaseFee\n    tenantCount\n    minTenantCount\n    maxTenantCount\n    location {\n      id\n      latitude\n      longitude\n      locality\n      route\n      streetNumber\n      postalCode\n      countryCode\n      country\n      __typename\n    }\n    uploads {\n      id\n      url\n      type\n      metadata {\n        primary\n        order\n        __typename\n      }\n      __typename\n    }\n    duration {\n      id\n      startOptimal\n      endOptimal\n      startAsap\n      endUfn\n      possibilityOfExtension\n      __typename\n    }\n    traits {\n      id\n      type\n      detail\n      __typename\n    }\n    landlord {\n      uid\n      firstName\n      companyName\n      professional\n      premium\n      proAgent\n      seenAt\n      createdAt\n      __typename\n    }\n    homeTemplates {\n      id\n      apartmentNumber\n      squareMeters\n      roomCount\n      floor\n      rent\n      type\n      description\n      traits {\n        id\n        type\n        detail\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
  }
  ```

- **Response Structure:**
  ```json
  {
    "data": {
      "home": {
        "id": "1348599",
        "title": null,
        "rent": 11250,
        "squareMeters": 48,
        "roomCount": 2.0,
        "status": "normal",
        "rentalType": "long_term",
        "shared": false,
        "description": "...(Swedish text)...",
        "floor": null,
        "buildingFloors": null,
        "tenureType": "condominium",
        "publishedAt": "...",
        "currency": "SEK",
        "location": {
          "id": "3382853",
          "latitude": 57.6957305,
          "longitude": 11.9658474,
          "locality": "Göteborg",
          "route": "Föreningsgatan",
          "streetNumber": null,
          "postalCode": "411 27",
          "countryCode": "SE",
          "country": "Sverige",
          "__typename": "Location"
        },
        "uploads": [
          {
            "id": "19675281",
            "url": "https://qasa-static-prod.s3-eu-west-1.amazonaws.com/img/a6e13...jpg",
            "type": "home_picture",
            "metadata": {
              "primary": true,
              "order": 0
            }
          }
        ],
        "duration": {
          "startOptimal": null,
          "endOptimal": null,
          "startAsap": true,
          "endUfn": true,
          "possibilityOfExtension": false
        },
        "traits": [
          { "type": "furniture", "detail": "fully_furnished" },
          { "type": "fridge", "detail": null },
          { "type": "balcony", "detail": null }
        ],
        "landlord": {
          "uid": "x7x7cnmg",
          "firstName": "...",
          "professional": false,
          "premium": false,
          "proAgent": false
        },
        "homeTemplates": [
          {
            "id": "1063155",
            "squareMeters": 48,
            "roomCount": 2.0,
            "rent": 11250,
            "type": "apartment",
            "description": "Charmig och välplanerad 2:a..."
          }
        ],
        "__typename": "Home"
      }
    }
  }
  ```

- **Notes:**
  - `title` is `null` for most listings; the display title shown in the browser tab is constructed from the route name + locality.
  - `homeTemplates` is used when a listing has multiple sub-units (e.g., a building with several apartments). The template description contains the marketing copy. For single-unit listings, `homeTemplates[0]` mirrors the top-level fields.
  - `startAsap: true` means "available immediately", `endUfn: true` means "until further notice" (open-ended).
  - `tenureType` values observed: `"condominium"` (bostadsrätt), `"rental"` (hyresrätt).
  - `rentalType` values: `"long_term"`, `"short_term"`, `"vacation"`.
  - `traits` are amenities — `type` is the category, `detail` is optional sub-type (e.g., `furniture`/`fully_furnished`).
  - Image URLs are in the format `https://qasa-static-prod.s3-eu-west-1.amazonaws.com/img/{sha256hash}.jpg`.
  - Images can be resized via the Qasa image proxy: `https://img.qasa.se/unsafe/{width}x{height}/smart/{original_url}`.

---

### 2. ViewingCalendarForHome

- **URL:** `https://api.qasa.se/graphql`
- **Method:** POST
- **Required Headers:** Same as HomeView
- **Request Body:**
  ```json
  {
    "operationName": "ViewingCalendarForHome",
    "variables": { "home_id": "1348599" },
    "query": "query ViewingCalendarForHome($home_id: ID!) {\n  home(id: $home_id) {\n    id\n    viewingCalendar {\n      id\n      bookings {\n        bookingId\n        endTime\n        startTime\n        __typename\n      }\n      slots {\n        slotId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
  }
  ```
- **Response Structure:**
  ```json
  {
    "data": {
      "home": {
        "id": "1348599",
        "viewingCalendar": null,
        "__typename": "Home"
      }
    }
  }
  ```
- **Notes:** Returns `null` when no viewings are scheduled. Only relevant if you need to check for open-house slots.

---

### 3. ExclusiveInsight — Market Analytics

- **URL:** `https://api.qasa.se/graphql`
- **Method:** POST
- **Notes:** Returns limited data without auth. With auth (premium landlord account), returns applicant counts, market rent estimates, etc. For scraping purposes this call is not needed.

---

### 4. View Tracking Endpoint (fire-and-forget)

- **URL:** `https://api.qasa.se/tracking/v1/homes/{home_id}/view`
- **Method:** POST
- **Body:** empty
- **Response:** 204 No Content
- **Notes:** Increments the listing view counter. You do not need to call this; omitting it has no effect on data access.

---

## How to Replicate Without a Browser

### Minimal curl — fetch all listing data

```bash
curl -s -X POST https://api.qasa.se/graphql \
  -H "Content-Type: application/json" \
  -H "Origin: https://qasa.com" \
  -H "Referer: https://qasa.com/" \
  -d '{
    "operationName": "HomeView",
    "variables": {"id": "1348599"},
    "query": "query HomeView($id: ID!) { home(id: $id) { id rent squareMeters roomCount status rentalType shared description floor tenureType publishedAt currency location { latitude longitude locality route streetNumber postalCode countryCode country __typename } uploads { id url type metadata { primary order __typename } __typename } duration { startOptimal endOptimal startAsap endUfn __typename } traits { type detail __typename } landlord { uid firstName professional premium __typename } homeTemplates { id squareMeters roomCount rent type description traits { type detail __typename } __typename } __typename } }"
  }' | python3 -m json.tool
```

### Python requests equivalent

```python
import requests

def fetch_qasa_listing(home_id: str) -> dict:
    resp = requests.post(
        "https://api.qasa.se/graphql",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://qasa.com",
            "Referer": "https://qasa.com/",
        },
        json={
            "operationName": "HomeView",
            "variables": {"id": home_id},
            "query": """
                query HomeView($id: ID!) {
                  home(id: $id) {
                    id
                    rent
                    squareMeters
                    roomCount
                    status
                    rentalType
                    shared
                    description
                    floor
                    tenureType
                    publishedAt
                    currency
                    location {
                      latitude
                      longitude
                      locality
                      route
                      streetNumber
                      postalCode
                      countryCode
                      country
                      __typename
                    }
                    uploads {
                      id
                      url
                      type
                      metadata { primary order __typename }
                      __typename
                    }
                    duration {
                      startOptimal
                      endOptimal
                      startAsap
                      endUfn
                      __typename
                    }
                    traits {
                      type
                      detail
                      __typename
                    }
                    landlord {
                      uid
                      firstName
                      professional
                      premium
                      __typename
                    }
                    homeTemplates {
                      id
                      squareMeters
                      roomCount
                      rent
                      type
                      description
                      traits { type detail __typename }
                      __typename
                    }
                    __typename
                  }
                }
            """,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["home"]
```

---

## Dynamic Values

| Value | Where to Get It | Notes |
|-------|-----------------|-------|
| `home_id` | From the listing URL: `.../home/{home_id}` | Integer string, e.g. `"1348599"` |
| No tokens needed | — | GraphQL endpoint is fully public for read operations |

---

## Anti-Bot / Rate Limiting Observations

- **No authentication required** for the GraphQL API on public listings.
- **No CSRF token** or session cookie required.
- **No rate-limit headers** observed in responses (`x-ratelimit-*`, `retry-after` absent).
- **CORS is open**: `Access-Control-Allow-Origin` is permissive.
- **No Cloudflare / bot detection** observed during capture (no challenge pages, no JS fingerprinting required for the GraphQL endpoint itself).
- The HTML page does load Hotjar, Amplitude, Sentry, and Stripe for analytics/payments — these are irrelevant to data extraction.
- The `_rails_session` cookie is set by `api.qasa.se` and is `httpOnly` + `secure`. It is only needed for authenticated operations (applying, messaging, etc.). Public listing reads work without it.

---

## Cookies Observed

All cookies are analytics/session only — none required for public data access:

| Cookie | Domain | Purpose |
|--------|--------|---------|
| `_rails_session` | `api.qasa.se` | Rails session (only needed for authenticated API calls) |
| `qcc` | `.qasa.com` | Cookie consent / marketing consent |
| `AMP_*` | `.qasa.com` | Amplitude analytics |
| `_hjSession*` | `.qasa.com` | Hotjar session replay |
| `__stripe_mid`, `__stripe_sid` | `.qasa.com` | Stripe fraud detection |

---

## Architecture Notes

- **Framework:** Next.js 14 with App Router (confirmed by `/_next/static/chunks/turbopack-*.js` and React Server Components streaming responses `_rsc=` URLs).
- **No `__NEXT_DATA__`:** This is App Router, not Pages Router. There is no server-embedded JSON blob. All data fetching is client-side via Apollo Client hitting the GraphQL endpoint.
- **GraphQL endpoint:** `https://api.qasa.se/graphql` — single endpoint for all queries.
- **Image CDN:** `https://img.qasa.se/unsafe/{width}x{height}/smart/{s3_url}` — Thumbor-based proxy over S3.
- **Map tiles:** LocationIQ (not Mapbox/OSM directly). API key `pk.0ee1f858f12eb412e3e3bbd20b0efed5` is embedded in frontend code.
- **The `homeTemplates` pattern:** Used for multi-unit buildings. Each template represents a distinct apartment configuration within the same building listing. Most individual listings have exactly one template.

---

## Existing Scraper Relevance

The current apartment-finder scraper (`developer-notes.md`) reads `__NEXT_DATA__` from the search/listing pages. Based on this capture:

- **Individual listing pages** (`/home/{id}`) do NOT have `__NEXT_DATA__` — they are App Router pages.
- **Search/listing pages** may still use `__NEXT_DATA__` if they are Pages Router routes — this needs separate verification.
- For individual listing detail, the correct approach is the GraphQL `HomeView` query above.
- The GraphQL `id` matches the numeric ID in the URL path exactly.

---

---

# Qasa Search API Protocol

Captured: 2026-04-18
Target URL: `https://qasa.com/se/en/find-home?searchAreas=Gothenburg~~se&minRoomCount=2`
Method: Chrome DevTools Protocol (CDP) network capture, 40 API requests observed

---

## Overview

The search/find-home page fires two parallel GraphQL queries on load:

1. **`HomeSearchCoordsQuery`** — fetches a compact list of all matching listing IDs with lat/lon
   coordinates (used to populate the map view). Returns all results in one shot (no pagination).
2. **`HomeSearch`** — fetches paginated full-detail listing cards (used to populate the list view).
   Supports offset-based pagination.

Both queries are unauthenticated for public search results. A third query (`GetUserFavoriteHomes`)
is also fired but always returns `{"errors":[{"message":"unauthorized"}]}` for anonymous visitors
— it can be ignored entirely.

**No `__NEXT_DATA__` bootstrap JSON** was found in the search page HTML. The page is App Router.
All listing data arrives via GraphQL fetch after hydration.

---

## Prerequisites

None. Both search queries work without any API key, session cookie, or authorization token.

---

## Page Load Sequence

| # | Request | Type | Purpose |
|---|---------|------|---------|
| 1 | `GET https://qasa.com/se/en/find-home?...` | Document | HTML shell |
| 2 | `POST https://api.qasa.se/graphql` (HomeSearchCoordsQuery) | GraphQL | All map pins |
| 3 | `POST https://api.qasa.se/graphql` (HomeSearch) | GraphQL | List view, page 1 |
| 4 | `POST https://api.qasa.se/graphql` (GetUserFavoriteHomes) | GraphQL | Always fails anon |
| 5 | (on hover over block listing) `POST /graphql` (BlockListingDataForHome) | GraphQL | Multi-unit ranges |

Only steps 2 and 3 are needed for scraping.

---

## Request Reference — Search

### Search.1  HomeSearch — Paginated Listing Cards

This is the primary query for getting apartment list data.

- **URL:** `https://api.qasa.se/graphql`
- **Method:** `POST`
- **Required Headers:**
  ```
  Content-Type: application/json
  Referer: https://qasa.com/
  ```
  `User-Agent` is not strictly required but recommended for politeness. No `Authorization`,
  `Cookie`, or `Origin` headers are needed.

- **Request Body:**
  ```json
  {
    "operationName": "HomeSearch",
    "variables": {
      "limit": 59,
      "offset": 0,
      "order": {
        "direction": "descending",
        "orderBy": "published_or_bumped_at"
      },
      "params": {
        "currency": "SEK",
        "minRoomCount": 2,
        "areaIdentifier": ["se/gothenburg"],
        "markets": ["sweden", "norway", "finland"]
      }
    },
    "query": "query HomeSearch($order: HomeIndexSearchOrderInput, $offset: Int, $limit: Int, $params: HomeSearchParamsInput) {\n  homeIndexSearch(order: $order, params: $params) {\n    documents(offset: $offset, limit: $limit) {\n      hasNextPage\n      hasPreviousPage\n      nodes {\n        bedroomCount\n        blockListing\n        rentalLengthSeconds\n        householdSize\n        corporateHome\n        description\n        endDate\n        firstHand\n        furnished\n        homeType\n        id\n        instantSign\n        market\n        lastBumpedAt\n        monthlyCost\n        petsAllowed\n        platform\n        publishedAt\n        publishedOrBumpedAt\n        rent\n        currency\n        roomCount\n        seniorHome\n        shared\n        shortcutHome\n        smokingAllowed\n        sortingScore\n        squareMeters\n        startDate\n        studentHome\n        tenantBaseFee\n        title\n        wheelchairAccessible\n        finnishLandlordAssociation\n        location {\n          id\n          locality\n          countryCode\n          streetNumber\n          point {\n            lat\n            lon\n            __typename\n          }\n          route\n          __typename\n        }\n        displayStreetNumber\n        uploads {\n          id\n          order\n          type\n          url\n          __typename\n        }\n        __typename\n      }\n      pagesCount\n      totalCount\n      __typename\n    }\n    __typename\n  }\n}"
  }
  ```

- **Response Structure:**
  ```json
  {
    "data": {
      "homeIndexSearch": {
        "documents": {
          "hasNextPage": true,
          "hasPreviousPage": false,
          "pagesCount": 11,
          "totalCount": 647,
          "nodes": [
            {
              "id": "1350341",
              "homeType": "apartment",
              "roomCount": 2.0,
              "bedroomCount": 1,
              "squareMeters": 41,
              "rent": 10500,
              "monthlyCost": 11019,
              "tenantBaseFee": 519,
              "currency": "SEK",
              "furnished": true,
              "firstHand": false,
              "shared": false,
              "blockListing": false,
              "petsAllowed": true,
              "smokingAllowed": false,
              "wheelchairAccessible": false,
              "instantSign": false,
              "corporateHome": false,
              "seniorHome": false,
              "studentHome": false,
              "shortcutHome": false,
              "finnishLandlordAssociation": false,
              "displayStreetNumber": false,
              "market": "sweden",
              "platform": "dotcom",
              "householdSize": 2,
              "rentalLengthSeconds": 31536000.0,
              "sortingScore": 6.77,
              "description": "...",
              "title": null,
              "publishedAt": "2026-04-18T17:17:23Z",
              "publishedOrBumpedAt": "2026-04-18T17:17:23Z",
              "lastBumpedAt": null,
              "startDate": "2026-07-01T00:00:00+00:00",
              "endDate": "2027-07-01T00:00:00+00:00",
              "location": {
                "id": 3385831,
                "locality": "Göteborg",
                "countryCode": "SE",
                "route": "Bratteråsgatan",
                "streetNumber": null,
                "point": {
                  "lat": 57.7033367,
                  "lon": 11.9155341
                }
              },
              "uploads": [
                {
                  "id": 19677273,
                  "order": 1,
                  "type": "home_picture",
                  "url": "https://qasa-static-prod.s3-eu-west-1.amazonaws.com/img/<sha256>.png"
                }
              ]
            }
          ]
        }
      }
    }
  }
  ```

---

### Search.2  HomeSearchCoordsQuery — Map Pin Data (All Results, No Pagination)

Returns a compact JSON-encoded string of all matching listings with coordinates.
Useful for getting the full set of IDs and locations without paginating.

- **URL:** `https://api.qasa.se/graphql`
- **Method:** `POST`
- **Required Headers:** same as HomeSearch

- **Request Body:**
  ```json
  {
    "operationName": "HomeSearchCoordsQuery",
    "variables": {
      "filterOnArea": false,
      "markets": ["sweden", "norway", "finland"],
      "searchParams": {
        "currency": "SEK",
        "minRoomCount": 2,
        "areaIdentifier": ["se/gothenburg"]
      }
    },
    "query": "query HomeSearchCoordsQuery($markets: [MarketNameTypeEnum!], $searchParams: HomeSearchParamsInput, $filterOnArea: Boolean) {\n  homeSearchCoords(\n    markets: $markets\n    searchParams: $searchParams\n    filterOnArea: $filterOnArea\n  ) {\n    filterHomesRaw\n    __typename\n  }\n}"
  }
  ```

- **Response Structure:**
  `filterHomesRaw` is a **JSON-encoded string** (not an object). You must `JSON.parse()` it
  a second time to get the array.
  ```json
  {
    "data": {
      "homeSearchCoords": {
        "filterHomesRaw": "[{\"id\":1350153,\"cost\":1197,\"rent\":1197,...}, ...]"
      }
    }
  }
  ```
  Each element of the inner array once parsed:
  ```json
  {
    "id": 1350153,
    "cost": 11019,
    "rent": 10500,
    "tenant_base_fee": 519,
    "latitude": "57.7033367",
    "longitude": "11.9155341",
    "currency": "SEK",
    "firsthand": false,
    "external": false,
    "origin": null,
    "early_access_ends_at": null,
    "professional": false,
    "safeRental": null
  }
  ```
  Note: `cost` = `rent + tenant_base_fee`. Coordinates are strings here (unlike `HomeSearch`
  where `point.lat`/`point.lon` are floats).

---

### Search.3  BlockListingDataForHome — Multi-unit Listing Ranges (Optional)

Only needed when `blockListing: true` on a search result node.

- **Request Body:**
  ```json
  {
    "operationName": "BlockListingDataForHome",
    "variables": { "id": "1282753" },
    "query": "query BlockListingDataForHome($id: ID!) {\n  home(id: $id) {\n    id\n    numberOfHomes\n    minSquareMeters\n    maxSquareMeters\n    minRoomCount\n    maxRoomCount\n    minRent\n    maxRent\n    __typename\n  }\n}"
  }
  ```

- **Response:**
  ```json
  {
    "data": {
      "home": {
        "id": "1282753",
        "numberOfHomes": 2,
        "minSquareMeters": 50,
        "maxSquareMeters": 51,
        "minRoomCount": null,
        "maxRoomCount": null,
        "minRent": null,
        "maxRent": null
      }
    }
  }
  ```

---

## How to Replicate Without a Browser

### Working curl example — Gothenburg, 2+ rooms, newest first

```bash
curl -s -X POST https://api.qasa.se/graphql \
  -H 'Content-Type: application/json' \
  -H 'Referer: https://qasa.com/' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -d '{
    "operationName": "HomeSearch",
    "variables": {
      "limit": 59,
      "offset": 0,
      "order": {"direction": "descending", "orderBy": "published_or_bumped_at"},
      "params": {
        "currency": "SEK",
        "minRoomCount": 2,
        "areaIdentifier": ["se/gothenburg"],
        "markets": ["sweden", "norway", "finland"]
      }
    },
    "query": "query HomeSearch($order: HomeIndexSearchOrderInput, $offset: Int, $limit: Int, $params: HomeSearchParamsInput) {\n  homeIndexSearch(order: $order, params: $params) {\n    documents(offset: $offset, limit: $limit) {\n      hasNextPage\n      hasPreviousPage\n      nodes {\n        bedroomCount blockListing rentalLengthSeconds householdSize corporateHome description\n        endDate firstHand furnished homeType id instantSign market lastBumpedAt monthlyCost\n        petsAllowed platform publishedAt publishedOrBumpedAt rent currency roomCount seniorHome\n        shared shortcutHome smokingAllowed sortingScore squareMeters startDate studentHome\n        tenantBaseFee title wheelchairAccessible finnishLandlordAssociation\n        location { id locality countryCode streetNumber point { lat lon __typename } route __typename }\n        displayStreetNumber\n        uploads { id order type url __typename }\n        __typename\n      }\n      pagesCount totalCount __typename\n    }\n    __typename\n  }\n}"
  }'
```

### Python requests — fetch all pages

```python
import requests
import json

GRAPHQL_URL = "https://api.qasa.se/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://qasa.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
}

SEARCH_QUERY = """
query HomeSearch($order: HomeIndexSearchOrderInput, $offset: Int, $limit: Int, $params: HomeSearchParamsInput) {
  homeIndexSearch(order: $order, params: $params) {
    documents(offset: $offset, limit: $limit) {
      hasNextPage
      hasPreviousPage
      nodes {
        bedroomCount blockListing rentalLengthSeconds householdSize corporateHome
        description endDate firstHand furnished homeType id instantSign market
        lastBumpedAt monthlyCost petsAllowed platform publishedAt publishedOrBumpedAt
        rent currency roomCount seniorHome shared shortcutHome smokingAllowed
        sortingScore squareMeters startDate studentHome tenantBaseFee title
        wheelchairAccessible finnishLandlordAssociation displayStreetNumber
        location {
          id locality countryCode streetNumber
          point { lat lon __typename }
          route __typename
        }
        uploads { id order type url __typename }
        __typename
      }
      pagesCount totalCount __typename
    }
    __typename
  }
}
"""


def fetch_page(area: str, min_rooms: int = 2, limit: int = 59, offset: int = 0,
               max_rent: int = None) -> dict:
    params = {
        "currency": "SEK",
        "minRoomCount": min_rooms,
        "areaIdentifier": [area],
        "markets": ["sweden", "norway", "finland"],
    }
    if max_rent is not None:
        params["maxRent"] = max_rent

    payload = {
        "operationName": "HomeSearch",
        "variables": {
            "limit": limit,
            "offset": offset,
            "order": {"direction": "descending", "orderBy": "published_or_bumped_at"},
            "params": params,
        },
        "query": SEARCH_QUERY,
    }
    resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]["homeIndexSearch"]["documents"]


def fetch_all(area: str, min_rooms: int = 2, max_rent: int = None, page_size: int = 59):
    """Fetch every page and return all listing nodes."""
    offset = 0
    all_nodes = []
    while True:
        docs = fetch_page(area, min_rooms=min_rooms, limit=page_size, offset=offset,
                          max_rent=max_rent)
        all_nodes.extend(docs["nodes"])
        if not docs["hasNextPage"]:
            break
        offset += page_size
    return all_nodes


if __name__ == "__main__":
    listings = fetch_all("se/gothenburg", min_rooms=2)
    print(f"Fetched {len(listings)} listings")
    for l in listings[:5]:
        print(
            f"  #{l['id']}  {l['location']['route']}, {l['location']['locality']}"
            f"  —  {l['rent']} SEK  —  {l['roomCount']} rum  —  {l['squareMeters']} m²"
        )
```

---

## Filter Parameters

All filter params go in `variables.params` (HomeSearch) or `variables.searchParams`
(HomeSearchCoordsQuery).

| Parameter | Type | Example | Notes |
|---|---|---|---|
| `areaIdentifier` | `[string]` | `["se/gothenburg"]` | See area identifiers below |
| `minRoomCount` | `int` | `2` | Minimum rooms |
| `maxRoomCount` | `int` | `4` | Maximum rooms |
| `minRent` | `int` | `5000` | Minimum rent (in `currency` units) |
| `maxRent` | `int` | `15000` | Maximum rent |
| `minSquareMeters` | `int` | `40` | Minimum size m² |
| `maxSquareMeters` | `int` | `120` | Maximum size m² |
| `currency` | `string` | `"SEK"` | `"SEK"`, `"EUR"`, `"NOK"`, `"HUF"` |
| `markets` | `[string]` | `["sweden"]` | `"sweden"`, `"norway"`, `"finland"` |
| `furnished` | `bool` | `true` | Furnished status |
| `petsAllowed` | `bool` | `true` | Pet policy |
| `homeType` | `string` | `"apartment"` | `"apartment"`, `"house"`, `"room"` |
| `firstHand` | `bool` | `false` | First-hand contracts only |
| `studentHome` | `bool` | `false` | Student housing only |
| `seniorHome` | `bool` | `false` | Senior housing only |
| `corporateHome` | `bool` | `false` | Corporate listings only |

### Sorting (`variables.order`)

| `orderBy` | `direction` | Description |
|---|---|---|
| `published_or_bumped_at` | `descending` | Newest first (default) |
| `published_or_bumped_at` | `ascending` | Oldest first |
| `rent` | `ascending` | Cheapest first |
| `rent` | `descending` | Most expensive first |

---

## Pagination

Offset-based. No cursor.

- Increment `offset` by `limit` for each subsequent page.
- Stop when `hasNextPage === false`.
- `totalCount` and `pagesCount` are returned on every page response.
- Default page size used by the site: **59**. Any positive integer works.

Example: page 3 at 59/page → `offset: 118, limit: 59`

---

## Area Identifiers

Format: `{countryCode}/{city-slug}` (lowercase, ASCII, no diacritics).
URL query param `searchAreas=Gothenburg~~se` maps to `areaIdentifier: ["se/gothenburg"]`.

| City | `areaIdentifier` |
|---|---|
| Gothenburg | `se/gothenburg` |
| Stockholm | `se/stockholm` |
| Malmö | `se/malmo` |
| Oslo | `no/oslo` |
| Helsinki | `fi/helsinki` |

---

## Response Field Notes

| Field | Notes |
|---|---|
| `rent` | Landlord-advertised base rent (use this) |
| `monthlyCost` | `rent + tenantBaseFee` — total cost to tenant including Qasa fee |
| `tenantBaseFee` | Qasa's service fee charged to tenant |
| `roomCount` | Float (e.g. `2.0`, `3.5`) — Swedish convention counts half-rooms |
| `title` | Usually `null`; street name + locality is the de-facto title |
| `streetNumber` | Withheld (`displayStreetNumber: false`) for privacy; coordinates are still present |
| `platform` | Source: `"dotcom"` (native), `"blocket"` (Swedish classifieds), `"oikotie"` (Finnish) |
| `blockListing` | `true` for multi-unit building listings; fetch `BlockListingDataForHome` for ranges |
| `filterHomesRaw` | Double-encoded JSON string in `HomeSearchCoordsQuery` — parse twice |

---

## Auth Requirements

- **Search queries:** No auth required.
- **`GetUserFavoriteHomes`:** Requires logged-in session. Returns `unauthorized` for anonymous.
- **Applying, messaging:** Requires account — out of scope for read-only scraping.

No CSRF tokens. No dynamic page values to extract. No JavaScript execution required.
