# Apartment Finder — Architecture

> **Version:** 1.0 · 2026-04-19

---

## 1. Overview

The application is split into two independently runnable processes:

| Layer | Tech | Port | Role |
|-------|------|------|------|
| **Frontend** | React 18 + Vite + TypeScript | 5173 | UI, state, localStorage |
| **Backend** | Python 3.12 + FastAPI | 8000 | Stateless Qasa API proxy |

There is **no shared database**. All user data lives in the browser's `localStorage`. The backend exists solely to avoid CORS issues and to handle multi-page pagination server-side.

---

## 2. High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                                                                 │
│  ┌──────────────────────┐       ┌──────────────────────────┐   │
│  │     LEFT PANEL       │       │       MAP PANEL          │   │
│  │                      │       │   react-leaflet          │   │
│  │  Tab: My List        │       │   OpenStreetMap tiles    │   │
│  │  Tab: Search         │       │                          │   │
│  │  Tab: Saved Searches │       │   ● saved apartments     │   │
│  │                      │       │   ○ search results       │   │
│  └──────────┬───────────┘       └──────────────────────────┘   │
│             │                                                   │
│  ┌──────────▼───────────────────────────────────────────────┐  │
│  │               Zustand Store (in-memory)                   │  │
│  │  apartments · savedSearches · searchResults · selection   │  │
│  └──────────┬───────────────────────────────────────────────┘  │
│             │                  ▲                               │
│  ┌──────────▼──────────┐       │ persist / hydrate             │
│  │     localStorage    │───────┘                               │
│  │  AppDatabase (JSON) │                                       │
│  └─────────────────────┘                                       │
│                                                                 │
│             │  HTTP (fetch)                                     │
└─────────────┼───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│         FastAPI Backend  (localhost:8000)                        │
│                                                                 │
│   GET  /api/health                                              │
│   GET  /api/listing/{home_id}  ──────────────────────────────┐  │
│   POST /api/search             ─────────────────────────────┐│  │
│   POST /api/parse-url          ──────────────────────────┐  ││  │
│                                                          │  ││  │
└──────────────────────────────────────────────────────────┼──┼┼──┘
                                                           │  ││
                                          POST (GraphQL)   │  ││
                                                           ▼  ▼▼
                                    https://api.qasa.se/graphql
```

---

## 3. Backend Architecture

### 3.1 Module Layout

```
backend/
├── main.py                  # FastAPI app, CORS, router registration
├── routers/
│   ├── listing.py           # GET /api/listing/{home_id}
│   ├── search.py            # POST /api/search
│   └── parse_url.py         # POST /api/parse-url
├── services/
│   ├── qasa_client.py       # All GraphQL calls to api.qasa.se
│   └── url_parser.py        # Extract home_id from Qasa URL
├── models/
│   ├── requests.py          # Pydantic request schemas
│   └── responses.py         # Pydantic response schemas
├── tests/
│   ├── conftest.py          # pytest fixtures, mock HTTP client
│   ├── test_listing.py
│   ├── test_search.py
│   └── test_parse_url.py
├── pyproject.toml
└── requirements.txt
```

### 3.2 Key Design Decisions

**Stateless by design:** The backend holds no state between requests. Every call to `/api/search` re-fetches Qasa. This keeps the backend simple and avoids caching stale data.

**All-pages fetch in `POST /api/search`:** The backend loops over Qasa's paginated `HomeSearch` query until `hasNextPage === false`, merges all nodes, and returns them in one response. This means a search with 600+ results may take several seconds — acceptable for a personal research tool.

**Pydantic validation:** All request bodies and responses are typed via Pydantic models. Invalid inputs are rejected before hitting Qasa.

**httpx for async HTTP:** The backend uses `httpx.AsyncClient` so requests to Qasa are non-blocking. The FastAPI endpoint handlers are `async def`.

### 3.3 GraphQL Queries Used

| Operation | Used By | Purpose |
|-----------|---------|---------|
| `HomeView` | `GET /api/listing/{id}` | Full listing detail |
| `HomeSearch` | `POST /api/search` | Paginated search (all pages) |

`HomeSearchCoordsQuery` (map-pin data) is **not used** — coordinates are already included in `HomeSearch` results via `location.point`.

---

## 4. Frontend Architecture

### 4.1 Module Layout

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx
│   ├── App.tsx              # Root layout
│   ├── types/
│   │   └── index.ts         # All shared TS interfaces
│   ├── store/
│   │   └── useAppStore.ts   # Zustand + localStorage middleware
│   ├── api/
│   │   └── qasaApi.ts       # Typed fetch wrappers
│   ├── components/
│   │   ├── layout/
│   │   │   ├── LeftPanel.tsx
│   │   │   └── MapPanel.tsx
│   │   ├── mylist/
│   │   │   ├── MyList.tsx
│   │   │   ├── ApartmentCard.tsx
│   │   │   └── ApartmentDetail.tsx
│   │   ├── search/
│   │   │   ├── SearchPanel.tsx
│   │   │   ├── SearchResults.tsx
│   │   │   └── SearchResultCard.tsx
│   │   ├── savedSearches/
│   │   │   └── SavedSearches.tsx
│   │   ├── tags/
│   │   │   └── TagInput.tsx
│   │   ├── comments/
│   │   │   └── CommentThread.tsx
│   │   └── common/
│   │       ├── Toast.tsx
│   │       ├── ConfirmDialog.tsx
│   │       └── ImportExport.tsx
│   └── utils/
│       ├── urlParser.ts
│       ├── pinColor.ts
│       └── db.ts
├── tests/                   # Vitest + RTL tests mirror src/
└── public/
```

### 4.2 State Flow

```
User action
    │
    ▼
React Component
    │  dispatch action
    ▼
Zustand Store (useAppStore)
    │  selector
    ├──────────────────► Component re-renders
    │
    │  side-effect (persist middleware)
    ▼
localStorage.setItem('apartment-finder-db', JSON.stringify(state))
```

The Zustand store uses the `persist` middleware to automatically serialise/deserialise state to/from localStorage under the key `apartment-finder-db`.

### 4.3 API Communication

The frontend communicates **only** with the local FastAPI backend (`http://localhost:8000`). It never calls `api.qasa.se` directly (CORS would block it anyway).

Configured via Vite proxy in development:
```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

In production (if ever deployed), set `VITE_API_BASE_URL` env variable.

### 4.4 Map Implementation

- `react-leaflet` wraps Leaflet.js.
- Tiles: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (no API key required).
- The `<MapPanel>` component is always mounted — it never unmounts when tabs switch. This preserves the user's map zoom/pan state.
- Pins are `L.circleMarker` instances coloured per §8 of the spec.
- Click on a pin dispatches `setSelectedApartment(id)` to the store, which causes the left panel to scroll to and highlight that apartment.

---

## 5. Data Flow: Adding a Listing by URL

```
User pastes URL → LeftPanel URL input
        │
        ▼
urlParser.ts: extractHomeId(url) → "1348599"
        │
        ▼
qasaApi.ts: GET /api/listing/1348599
        │
        ▼  (backend)
qasa_client.py: POST api.qasa.se/graphql (HomeView)
        │
        ▼
FastAPI returns QasaListingData JSON
        │
        ▼
Frontend: store.addApartment(listing, url)
        │  ├── Adds to apartments[] in Zustand
        │  └── Persists to localStorage
        ▼
Map pin appears · Toast shown · Detail drawer opens
```

---

## 6. Data Flow: Search

```
User sets filters → SearchPanel
        │
        ▼
store.setSearchLoading(true)
        │
        ▼
qasaApi.ts: POST /api/search { filters }
        │
        ▼  (backend)
search.py: loop HomeSearch until hasNextPage === false
        │  accumulate all nodes
        ▼
FastAPI returns { totalCount, pagesCount, results[] }
        │
        ▼
store.setSearchResults(results, total)
        │  ├── SearchResults list renders
        │  └── MapPanel renders orange pins for all results
        ▼
User clicks "Add" on a result card
        │
        ▼
store.addApartment(result, qasaUrl)
```

---

## 7. localStorage Schema

Key: `apartment-finder-db`

```json
{
  "version": 1,
  "apartments": [...],
  "savedSearches": [...],
  "exportedAt": null
}
```

Schema migrations: if `version` < current, run migration functions in `db.ts` before hydrating the store. Start at version 1; increment for any breaking change.

---

## 8. Security Considerations

- The backend is intended for **local use only**. Do not expose port 8000 on a public network.
- No API keys or secrets are stored.
- Qasa's GraphQL API is public and unauthenticated for read operations.
- localStorage is accessible to any JS on the page; since no external scripts are loaded (Vite build only), this is acceptable.

---

## 9. Development Ports

| Service | URL |
|---------|-----|
| Frontend (Vite) | `http://localhost:5173` |
| Backend (FastAPI) | `http://localhost:8000` |
| API docs (Swagger) | `http://localhost:8000/docs` |
| Qasa GraphQL | `https://api.qasa.se/graphql` |
