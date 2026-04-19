# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python 3.12 + FastAPI)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn main:app --reload --port 8000   # run server
PYTHONPATH=. pytest -v                  # run all tests
PYTHONPATH=. pytest tests/test_listing.py::test_name -v  # run one test
```

### Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install

npm run dev        # Vite dev server → http://localhost:5173
npm run test       # Vitest (watch mode)
npm run test:ui    # Vitest with browser UI
npm run build      # tsc + vite build
npm run lint       # ESLint
```

Both processes must run simultaneously in development; Vite proxies `/api/*` to `localhost:8000`.

## Architecture

Two independent processes, no shared database:

| Layer | Tech | Port |
|-------|------|------|
| Frontend | React 19 + Vite + TypeScript + Zustand | 5173 |
| Backend | Python 3.12 + FastAPI + httpx | 8000 |

**Data lives exclusively in the browser** — `localStorage` key `apartment-finder-db` (JSON). The backend is a stateless proxy that forwards requests to `https://api.qasa.se/graphql` and returns data; it never stores anything.

### Backend layout

```
backend/
├── main.py                # FastAPI app, CORS, router registration
├── routers/               # One file per endpoint
├── services/qasa_client.py  # All GraphQL calls to api.qasa.se
├── models/                # Pydantic request/response schemas
└── tests/                 # respx mocks — no real Qasa calls in tests
```

New endpoint checklist: router → register in `main.py` → Pydantic models → tests first → service logic.

### Frontend layout

```
frontend/src/
├── types/index.ts         # All shared TypeScript interfaces
├── store/useAppStore.ts   # Zustand store + localStorage persist middleware
├── api/qasaApi.ts         # Typed fetch wrappers (calls /api/*)
├── utils/db.ts            # localStorage read/write/migrate — only place that touches storage
├── components/
│   ├── layout/            # LeftPanel, MapPanel (MapPanel stays mounted across tab switches)
│   ├── mylist/            # ApartmentCard, ApartmentDetail
│   ├── search/            # SearchPanel, SearchResults, SearchResultCard
│   ├── savedSearches/
│   ├── tags/
│   ├── comments/
│   └── common/            # Toast, ConfirmDialog, ImportExport
└── tests/                 # Vitest + RTL, mirrors src/
```

### Key constraints

- **All localStorage access goes through `utils/db.ts`** — never directly from components or the store.
- **All fetch calls go through `api/qasaApi.ts`** — never `fetch` directly from components.
- **Geocoding happens in the backend**, not the frontend (Nominatim CORS restriction).
- Backend `POST /api/search` fetches **all pages** from Qasa before returning — can be slow for large result sets.

### State management

Zustand store (`useAppStore`) holds: `apartments`, `savedSearches`, `searchResults`, `selectedApartmentId`, `activeTab`. The `persist` middleware automatically syncs to localStorage. Schema migrations run in `db.ts` when `version` in stored JSON is behind `CURRENT_VERSION`.

### Testing patterns

**Backend** — mock httpx with `respx`:
```python
with respx.mock(base_url="https://api.qasa.se") as rx:
    rx.post("/graphql").mock(return_value=httpx.Response(200, json=MOCK_DATA))
```

**Frontend** — mock the API module, not fetch:
```typescript
vi.mock('../../../src/api/qasaApi', () => ({
  fetchListing: vi.fn().mockResolvedValue({ id: '123', ... }),
}));
```

Vitest requires `environment: 'jsdom'` in `vitest.config.ts` — tests will fail with "window is not defined" otherwise.

## Docs

| File | Content |
|------|---------|
| `docs/spec.md` | Product spec — views and user goals |
| `docs/architecture.md` | Detailed architecture and API contracts |
| `docs/plan.md` | Milestone status — update as work progresses |
| `docs/developer.md` | Full developer setup guide |
| `protocol/qasa-protocol.md` | Reverse-engineered Qasa GraphQL reference |

## Conventions

- Tailwind for all styling — no inline styles, no CSS modules.
- Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `test(scope): ...`
- TDD: write a failing test before production code.
- No comments unless the WHY is non-obvious.
