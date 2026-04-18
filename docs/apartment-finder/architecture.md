# Apartment Finder — Architecture

**Version:** 1.0
**Date:** 2026-04-18

---

## System Overview

```
Browser (React + Vite)
  │
  ├── IndexedDB  ←── all apartment data lives here
  │
  └── HTTP ──► Express backend (port 3001)
                  │
                  └── HTTPS ──► qasa.se  (scraping)
```

Single-user, single-machine. No auth, no cloud, no database server.

---

## Repository Layout

```
research/
└── apartment-finder/
    ├── package.json          # root — scripts: dev, build, start
    ├── CLAUDE.md             # project-level AI guidance
    ├── backend/
    │   ├── package.json
    │   ├── server.js         # Express entry point
    │   └── scrapers/
    │       └── qasa.js       # cheerio-based scraper
    └── frontend/
        ├── package.json
        ├── vite.config.js    # proxy /api → localhost:3001
        ├── index.html
        └── src/
            ├── main.jsx
            ├── App.jsx
            ├── db.js             # idb wrapper (IndexedDB)
            ├── views/
            │   ├── ListView.jsx
            │   ├── DetailView.jsx
            │   ├── InvestigateView.jsx
            │   └── MapView.jsx
            └── components/
                ├── ApartmentCard.jsx
                ├── PriorityPicker.jsx
                ├── StatusStepper.jsx
                ├── PhotoGallery.jsx
                └── ExportImport.jsx
```

---

## Frontend

| Concern | Choice | Reason |
|---|---|---|
| Framework | React 18 | Ecosystem, familiarity |
| Build tool | Vite | Fast HMR, simple proxy config |
| Routing | React Router v6 | Declarative, lightweight |
| Styling | Tailwind CSS | Utility-first, no build overhead |
| Map | Leaflet + react-leaflet | Free, OSM tiles, no API key |
| Geocoding | Nominatim (OSM) | Free, no key, adequate for SE cities |
| Storage | idb (IndexedDB wrapper) | Persistent, fast, no backend needed |
| State | React Context + useReducer | No extra dependency for this scope |

### Routing

| Path | View |
|---|---|
| `/` | My List |
| `/apartment/:id` | Apartment Detail |
| `/investigate` | Investigate Mode |
| `/map` | Map View |

### API Proxy

Vite dev server proxies `/api/*` → `http://localhost:3001` so the frontend never makes cross-origin requests. In production (`npm run build`), Express serves the static build and handles `/api` routes itself.

---

## Backend

| Concern | Choice |
|---|---|
| Runtime | Node.js 20 |
| Framework | Express 4 |
| HTML parsing | cheerio |
| HTTP client | axios |
| Process manager (dev) | nodemon |

### Endpoints

#### `GET /api/scrape`

Query params: `url` (required) — a qasa.se listing URL.

Response:
```json
{
  "title": "...",
  "address": "...",
  "city": "...",
  "price": 12000,
  "deposit": 24000,
  "size": 45,
  "rooms": 2,
  "floor": "3",
  "availableFrom": "2026-05-01",
  "photos": ["https://..."],
  "description": "...",
  "sourceUrl": "https://qasa.se/..."
}
```

Error: `{ "error": "message" }` with appropriate HTTP status.

#### `GET /api/search`

Query params: `city`, `minPrice`, `maxPrice`, `minSize`, `maxSize`, `rooms` (all optional).

Response:
```json
{
  "results": [
    { "title": "...", "address": "...", "price": 12000, "size": 45, "rooms": 2, "photo": "...", "sourceUrl": "..." },
    ...
  ]
}
```

---

## Storage

All apartment data is stored in IndexedDB via the `idb` library.

| Store | Key | Indexes |
|---|---|---|
| `apartments` | `id` (UUID) | `addedAt`, `priority`, `status` |

Operations are wrapped in `src/db.js` exposing:
- `getAll()` → `Apartment[]`
- `get(id)` → `Apartment`
- `put(apartment)` → saves or updates
- `remove(id)`
- `exportAll()` → JSON string
- `importAll(json, mode)` → merge or replace

---

## Dev Startup

Root `package.json` uses `concurrently` to start both processes with one command:

```bash
npm run dev
# → backend:  nodemon backend/server.js    (port 3001)
# → frontend: vite --port 5173             (port 5173)
```

Production build:
```bash
npm run build   # vite build → dist/
npm start       # Express serves dist/ + /api routes
```

---

## Scraping Notes

- qasa.se is a React SPA; most listing data is embedded in a `__NEXT_DATA__` or `window.__STATE__` JSON blob in the HTML — prefer parsing that over DOM scraping.
- Search results may require parsing the initial JSON state from the search page.
- Respect `robots.txt`; add reasonable request delays if batching.
- Photo URLs from qasa.se may have CORS restrictions — store them as-is and load via `<img>` tags (browsers allow cross-origin image loads).
- If qasa.se changes their markup, update `backend/scrapers/qasa.js` — the data model is stable.

---

## Geocoding

- On apartment save, call Nominatim: `https://nominatim.openstreetmap.org/search?q=<address>&format=json&limit=1`
- Store `lat`/`lng` in the record.
- Cache: if `lat`/`lng` already populated, skip geocoding.
- Rate limit: Nominatim allows 1 req/s; geocode on save (not on list render).
