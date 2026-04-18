# Apartment Finder — Developer Specification

> **Status:** Draft v1.0 · 2026-04-19  
> **Audience:** Junior Developer  
> **Stack:** Python 3.12 + FastAPI (backend) · React 18 + Vite + TypeScript (frontend)  
> **Test frameworks:** pytest + httpx (backend) · Vitest + React Testing Library (frontend)

---

## 1. Product Overview

A single-page **apartment research tool** that lets a user:

1. Search Qasa.com listings using filters, or paste a direct Qasa listing URL.
2. Browse search results on a map and in a list.
3. Save interesting apartments to a personal list with **freeform tags** and **timestamped comments**.
4. View all saved apartments on a persistent map (Leaflet + OpenStreetMap).
5. Export and import the entire database as a JSON file.

All user data is stored in **browser localStorage** — no backend database. The Python backend is a **stateless proxy** that only wraps the Qasa GraphQL API.

---

## 2. User Stories

### US-01 — Fetch listing by URL
> As a user, I can paste a Qasa listing URL (e.g. `https://qasa.com/se/en/home/1348599`) into a field and press "Add". The app fetches the listing from the backend and adds it to my saved list.

**Acceptance criteria:**
- Valid URL containing a numeric home ID is parsed and sent to `GET /api/listing/{id}`.
- Listing data is stored in localStorage.
- A success toast is shown; the apartment appears on the map immediately.
- If the same listing is added again, show a warning toast "Already in your list".
- If the URL is invalid or the API errors, show an error toast.

---

### US-02 — Search with filters
> As a user, I can set search filters (city, rooms, rent, size, furnished, etc.) and run a search. Results appear in both a list and on the map.

**Acceptance criteria:**
- City selector defaults to Gothenburg; supports: Gothenburg, Stockholm, Malmö, Oslo, Helsinki.
- Filter panel exposes all parameters listed in §5.4.
- Clicking "Search" calls `POST /api/search`; a loading spinner is shown.
- All result pages are fetched server-side; the full result set is returned.
- Results appear in a scrollable list with thumbnail, address, rent, size, rooms.
- Map pins are shown for all results (distinct colour from saved apartments).
- Clicking a result pin or list row opens a preview panel.
- Each result has an "Add to my list" button.

---

### US-03 — Save a search preset
> As a user, I can save the current filter state as a named preset and re-run it later.

**Acceptance criteria:**
- "Save search" button prompts for a name.
- Saved searches are listed in a "Saved Searches" tab.
- Clicking a saved search loads its filters and runs the search automatically.
- Searches can be deleted.

---

### US-04 — View saved apartments
> As a user, I see all my saved apartments in a list and on the map simultaneously.

**Acceptance criteria:**
- Left panel has tabs: **My List** / **Search** / **Saved Searches**.
- My List shows all saved apartments with: primary image, address, rent, tags, comment count.
- Map always shows saved apartments as coloured pins.
- Clicking a pin highlights the corresponding list row and vice versa.
- Map auto-fits to the bounding box of all saved apartments on load.

---

### US-05 — Tag an apartment
> As a user, I can add/remove freeform tags on any saved apartment. Tags can be anything; the app pre-populates common suggestions.

**Acceptance criteria:**
- Tag input is a freeform chip input that accepts any text.
- Pre-suggested tags: `interested`, `applied`, `rejected`, `visited`, `not interested`, `favourite`.
- Tags appear as coloured chips on list and detail views.
- Tags are saved immediately to localStorage.
- Map pin colour reflects the first tag (see §8 for colour mapping). Custom tags use grey.

---

### US-06 — Comment on an apartment
> As a user, I can add timestamped comments to any saved apartment.

**Acceptance criteria:**
- Comment is a textarea in the apartment detail panel.
- Each saved comment shows: timestamp (local time) + text.
- Comments are prepended (newest first).
- Comments can be deleted individually.
- Comments are saved immediately to localStorage.

---

### US-07 — Remove an apartment
> As a user, I can remove a saved apartment from my list.

**Acceptance criteria:**
- Confirmation dialog shown before deletion.
- Apartment removed from localStorage and from the map.

---

### US-08 — Export / Import database
> As a user, I can export all my data to a JSON file and import it back.

**Acceptance criteria:**
- Export button downloads `apartment-finder-export-{YYYY-MM-DD}.json`.
- Import button accepts a `.json` file; validates schema version; merges or replaces (user choice).
- Import shows a summary: "X apartments imported, Y already existed".

---

## 3. Data Models

### 3.1 Apartment (stored in localStorage)

```typescript
interface SavedApartment {
  id: string;                  // Qasa home ID (numeric string, e.g. "1348599")
  qasaData: QasaListingData;   // Full HomeView response, cached
  qasaUrl: string;             // Canonical Qasa URL
  addedAt: string;             // ISO 8601 timestamp
  tags: string[];              // freeform, ordered by insertion
  comments: ApartmentComment[];
}

interface ApartmentComment {
  id: string;       // uuid v4
  text: string;
  createdAt: string; // ISO 8601
}
```

### 3.2 Qasa Listing Data (from backend)

```typescript
interface QasaListingData {
  id: string;
  rent: number;
  currency: string;
  squareMeters: number;
  roomCount: number;
  floor: number | null;
  buildingFloors: number | null;
  tenureType: string;         // "condominium" | "rental"
  rentalType: string;         // "long_term" | "short_term" | "vacation"
  shared: boolean;
  description: string;
  publishedAt: string;
  status: string;
  location: QasaLocation;
  uploads: QasaUpload[];
  duration: QasaDuration;
  traits: QasaTrait[];
  landlord: QasaLandlord;
  homeTemplates: QasaHomeTemplate[];
}

interface QasaLocation {
  id: string;
  latitude: number;
  longitude: number;
  locality: string;
  route: string;
  streetNumber: string | null;
  postalCode: string;
  countryCode: string;
  country: string;
}

interface QasaUpload {
  id: string;
  url: string;
  type: string;
  metadata: { primary: boolean; order: number };
}

interface QasaDuration {
  startOptimal: string | null;
  endOptimal: string | null;
  startAsap: boolean;
  endUfn: boolean;
  possibilityOfExtension: boolean;
}

interface QasaTrait {
  type: string;
  detail: string | null;
}

interface QasaLandlord {
  uid: string;
  firstName: string;
  professional: boolean;
  premium: boolean;
}

interface QasaHomeTemplate {
  id: string;
  squareMeters: number;
  roomCount: number;
  rent: number;
  type: string;
  description: string;
}
```

### 3.3 Saved Search Preset

```typescript
interface SavedSearch {
  id: string;        // uuid v4
  name: string;
  filters: SearchFilters;
  createdAt: string;
}

interface SearchFilters {
  areaIdentifier: string;       // e.g. "se/gothenburg"
  minRoomCount?: number;
  maxRoomCount?: number;
  minRent?: number;
  maxRent?: number;
  minSquareMeters?: number;
  maxSquareMeters?: number;
  currency: string;             // default "SEK"
  markets: string[];            // default ["sweden", "norway", "finland"]
  furnished?: boolean;
  petsAllowed?: boolean;
  homeType?: string;            // "apartment" | "house" | "room"
  firstHand?: boolean;
  studentHome?: boolean;
  seniorHome?: boolean;
  corporateHome?: boolean;
  sortBy: "published_or_bumped_at" | "rent";
  sortDirection: "ascending" | "descending";
}
```

### 3.4 App Database (exported JSON schema)

```typescript
interface AppDatabase {
  version: 1;
  exportedAt: string;           // ISO 8601
  apartments: SavedApartment[];
  savedSearches: SavedSearch[];
}
```

---

## 4. System Architecture

```
┌──────────────────────────────────────┐     ┌──────────────────────────────┐
│   Browser (React + Vite + TS)        │     │  Python FastAPI Backend       │
│                                      │     │  http://localhost:8000        │
│  ┌─────────────┐  ┌────────────────┐ │     │                              │
│  │  Left Panel  │  │   Map Panel   │ │     │  GET /api/listing/{id}        │
│  │  (tabs)      │  │  (Leaflet +   │◄├────►│  POST /api/search            │
│  │              │  │   OSM tiles)  │ │     │  POST /api/parse-url         │
│  └─────────────┘  └────────────────┘ │     │  GET /api/health             │
│                                      │     │                              │
│  ┌──────────────────────────────┐    │     └──────────┬───────────────────┘
│  │  localStorage (AppDatabase)  │    │                │
│  └──────────────────────────────┘    │                ▼
└──────────────────────────────────────┘     https://api.qasa.se/graphql
```

See `docs/architecture.md` for full detail.

---

## 5. Backend API Specification

### 5.1 Base URL

`http://localhost:8000`

All responses use `Content-Type: application/json`.

### 5.2 `GET /api/health`

**Response 200:**
```json
{ "status": "ok" }
```

### 5.3 `GET /api/listing/{home_id}`

Fetch a single Qasa listing using the `HomeView` GraphQL query.

**Path param:** `home_id` — numeric string (e.g. `"1348599"`)

**Response 200:** `QasaListingData` (see §3.2)

**Response 400:** `{ "detail": "Invalid home_id" }` — if non-numeric  
**Response 404:** `{ "detail": "Listing not found or unavailable" }` — if Qasa returns null  
**Response 502:** `{ "detail": "Upstream API error" }` — if Qasa returns HTTP error

### 5.4 `POST /api/search`

Run a paginated search, fetching **all pages**, and return all listing nodes.

**Request body:**
```json
{
  "areaIdentifier": "se/gothenburg",
  "minRoomCount": 2,
  "maxRoomCount": null,
  "minRent": null,
  "maxRent": 15000,
  "minSquareMeters": null,
  "maxSquareMeters": null,
  "currency": "SEK",
  "markets": ["sweden", "norway", "finland"],
  "furnished": null,
  "petsAllowed": null,
  "homeType": null,
  "firstHand": null,
  "studentHome": null,
  "seniorHome": null,
  "corporateHome": null,
  "sortBy": "published_or_bumped_at",
  "sortDirection": "descending"
}
```

All fields except `areaIdentifier`, `currency`, `markets`, `sortBy`, `sortDirection` are optional.

**Response 200:**
```json
{
  "totalCount": 647,
  "pagesCount": 11,
  "results": []
}
```

**Response 400:** `{ "detail": "areaIdentifier is required" }`  
**Response 502:** `{ "detail": "Upstream API error" }`

### 5.5 `POST /api/parse-url`

Parse a Qasa listing URL and return its listing data.

**Request body:**
```json
{ "url": "https://qasa.com/se/en/home/1348599" }
```

**Response 200:** Same as `GET /api/listing/{home_id}`  
**Response 400:** `{ "detail": "Cannot parse home ID from URL" }`

### 5.6 CORS

Backend must allow CORS from `http://localhost:5173` (Vite dev server).

---

## 6. Frontend Component Structure

```
src/
├── main.tsx
├── App.tsx                    # Root: layout split (left panel + map)
├── store/
│   └── useAppStore.ts         # Zustand store wrapping localStorage
├── types/
│   └── index.ts               # All TypeScript types (§3)
├── api/
│   └── qasaApi.ts             # fetch wrappers for backend calls
├── components/
│   ├── layout/
│   │   ├── LeftPanel.tsx      # Tabbed panel container
│   │   └── MapPanel.tsx       # Leaflet map, always rendered
│   ├── mylist/
│   │   ├── MyList.tsx         # Saved apartments list
│   │   ├── ApartmentCard.tsx  # Row in My List
│   │   └── ApartmentDetail.tsx # Drawer with full info + tags + comments
│   ├── search/
│   │   ├── SearchPanel.tsx    # Filters form
│   │   ├── SearchResults.tsx  # Results list
│   │   └── SearchResultCard.tsx
│   ├── savedSearches/
│   │   └── SavedSearches.tsx
│   ├── tags/
│   │   └── TagInput.tsx       # Freeform chip tag input
│   ├── comments/
│   │   └── CommentThread.tsx  # Add + display timestamped comments
│   └── common/
│       ├── Toast.tsx
│       ├── ConfirmDialog.tsx
│       └── ImportExport.tsx   # Export/import buttons
└── utils/
    ├── urlParser.ts           # Extract home ID from Qasa URL
    ├── pinColor.ts            # Map pin colour logic
    └── db.ts                  # localStorage read/write, schema versioning
```

---

## 7. State Management

Use **Zustand** for global state, backed by localStorage persistence.

```typescript
interface AppState {
  apartments: SavedApartment[];
  savedSearches: SavedSearch[];
  searchResults: SearchResultNode[];
  searchLoading: boolean;
  selectedApartmentId: string | null;
  activeTab: 'mylist' | 'search' | 'savedSearches';

  // Actions
  addApartment: (listing: QasaListingData, url: string) => void;
  removeApartment: (id: string) => void;
  updateTags: (id: string, tags: string[]) => void;
  addComment: (id: string, text: string) => void;
  deleteComment: (apartmentId: string, commentId: string) => void;
  saveSearch: (name: string, filters: SearchFilters) => void;
  deleteSearch: (id: string) => void;
  setSearchResults: (results: SearchResultNode[], total: number) => void;
  setSelectedApartment: (id: string | null) => void;
  exportDb: () => void;
  importDb: (data: AppDatabase, mode: 'merge' | 'replace') => ImportSummary;
}
```

---

## 8. Map Behaviour

- Tiles: OpenStreetMap via `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- Library: `react-leaflet` + `leaflet`
- Default centre: Gothenburg (`57.7089, 11.9746`), zoom 12
- On "Search": map pans/zooms to fit all result pins
- On "My List" tab: map pans/zooms to fit all saved apartment pins
- Pin colours by first tag:
  - `interested` → green `#22c55e`
  - `favourite` → amber `#f59e0b`
  - `applied` → blue `#3b82f6`
  - `visited` → purple `#a855f7`
  - `rejected` / `not interested` → red `#ef4444`
  - no tag / custom tag → grey `#6b7280`
- Search results (not yet saved): hollow orange circle `#f97316`
- Click any pin → opens apartment detail drawer

---

## 9. TDD Requirements

### 9.1 Backend (pytest)

All external HTTP calls to Qasa are **mocked** (use `respx` or `pytest-httpx`).

| Test | Description |
|------|-------------|
| `test_health` | Returns 200 + `{"status": "ok"}` |
| `test_fetch_listing_valid_id` | Mocked Qasa response → correct shape |
| `test_fetch_listing_invalid_id` | Non-numeric → 400 |
| `test_fetch_listing_not_found` | Qasa returns null → 404 |
| `test_fetch_listing_upstream_error` | Qasa 500 → 502 |
| `test_search_basic` | Valid params → returns results |
| `test_search_missing_area` | Missing `areaIdentifier` → 400 |
| `test_search_pagination` | Multi-page: all pages fetched |
| `test_parse_url_valid` | Valid URL → extracts ID, returns listing |
| `test_parse_url_invalid` | Malformed URL → 400 |
| `test_cors_header` | CORS header present |

### 9.2 Frontend (Vitest + RTL)

| Test | Description |
|------|-------------|
| `urlParser` | Valid/invalid URL extraction |
| `db.ts` | read/write/merge/replace localStorage |
| `pinColor` | Correct colour for each tag value |
| `TagInput` | Adds/removes chips; shows suggestions |
| `CommentThread` | Adds, orders, deletes comments |
| `ImportExport` | Export triggers download; import triggers dialog |
| `SearchPanel` | All filter inputs render; submit fires API |
| `ApartmentCard` | Correct rent, tags, comment count |

---

## 10. Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Search response time | < 10 s for 600+ results (all pages) |
| Backend startup | < 2 s |
| Frontend initial load | < 2 s (Vite dev) |
| localStorage usage | Warn user if > 4 MB |
| CORS | Backend allows `localhost:5173` |
| Browser support | Chrome / Firefox / Safari latest |

---

## 11. Out of Scope (v1)

- User accounts / cloud sync
- Mobile / responsive layout
- Viewing calendar slot booking
- Email / push notifications
- Browser extension
- Real-time updates
