# Apartment Finder — Developer Guide

> **Version:** 1.0 · 2026-04-19

---

## 1. Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Python | 3.12 | `pyenv install 3.12` or system package |
| Node.js | 20 LTS | `nvm install 20` |
| npm | 10+ | bundled with Node 20 |
| git | any | system |

---

## 2. Repository Layout

```
apartment-finder/
├── backend/          # Python FastAPI app
├── frontend/         # React + Vite app
├── docs/             # All documentation
│   ├── spec.md
│   ├── architecture.md
│   ├── developer.md  ← you are here
│   ├── user.md
│   └── plan.md
└── protocol/
    └── qasa-protocol.md   # Reverse-engineered Qasa API reference
```

---

## 3. Backend Setup

### 3.1 Create virtual environment

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3.2 Install dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt`** (initial):
```
fastapi>=0.111
uvicorn[standard]>=0.29
httpx>=0.27
pydantic>=2.7
```

**`requirements-dev.txt`** (for testing):
```
pytest>=8
pytest-asyncio>=0.23
respx>=0.21       # mock httpx requests
httpx>=0.27       # async test client
```

### 3.3 Run the backend

```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3.4 Run backend tests

```bash
pytest -v
```

Tests are in `backend/tests/`. All tests mock external HTTP calls — no real Qasa requests are made.

---

## 4. Frontend Setup

### 4.1 Install dependencies

```bash
cd frontend
npm install
```

### 4.2 Key dependencies

```json
{
  "react": "^18",
  "react-dom": "^18",
  "typescript": "^5",
  "vite": "^5",
  "zustand": "^4",
  "leaflet": "^1.9",
  "react-leaflet": "^4",
  "uuid": "^9"
}
```

```json
{
  "devDependencies": {
    "vitest": "^1",
    "@testing-library/react": "^14",
    "@testing-library/user-event": "^14",
    "jsdom": "^24"
  }
}
```

### 4.3 Run the frontend

```bash
npm run dev
```

Opens at: http://localhost:5173

The Vite dev server proxies `/api/*` to `http://localhost:8000` — make sure the backend is running.

### 4.4 Run frontend tests

```bash
npm run test
```

Or with UI:

```bash
npm run test:ui
```

---

## 5. Development Workflow

### 5.1 TDD Approach

For **every feature**, follow this order:

1. **Write a failing test** (pytest for backend, Vitest for frontend).
2. **Write the minimum code** to make the test pass.
3. **Refactor** without breaking tests.
4. Repeat.

Never write production code before a test exists for it.

### 5.2 Git Conventions

Use **Conventional Commits**:

```
feat(search): add city selector to search panel
fix(backend): handle null home in HomeView response
test(listing): add test for upstream 502 error
docs(spec): update search filter parameters
```

Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`

Branch naming: `feat/us-01-add-by-url`, `fix/null-home-id`, etc.

---

## 6. Adding a New Backend Endpoint

1. Create (or update) a router file in `backend/routers/`.
2. Register the router in `main.py` with `app.include_router(router, prefix="/api")`.
3. Add a Pydantic request model in `models/requests.py`.
4. Add a Pydantic response model in `models/responses.py`.
5. Write tests in `backend/tests/test_{feature}.py` **first**.
6. Implement the service logic in `services/`.

### Example skeleton

```python
# backend/routers/listing.py
from fastapi import APIRouter, HTTPException
from services.qasa_client import fetch_listing

router = APIRouter()

@router.get("/listing/{home_id}")
async def get_listing(home_id: str):
    if not home_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid home_id")
    data = await fetch_listing(home_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return data
```

---

## 7. Adding a New Frontend Component

1. Create component in `src/components/{category}/ComponentName.tsx`.
2. Write tests in `tests/components/{category}/ComponentName.test.tsx` **first**.
3. Export from the component file; import where needed.
4. Add to the Zustand store if new state is required.

### Testing pattern

```typescript
// tests/components/tags/TagInput.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagInput } from '../../../src/components/tags/TagInput';

describe('TagInput', () => {
  it('adds a tag on Enter', async () => {
    const onChange = vi.fn();
    render(<TagInput tags={[]} onChange={onChange} />);
    await userEvent.type(screen.getByRole('textbox'), 'interested{Enter}');
    expect(onChange).toHaveBeenCalledWith(['interested']);
  });
});
```

---

## 8. localStorage Database

The `db.ts` utility handles all persistence:

```typescript
// src/utils/db.ts
const DB_KEY = 'apartment-finder-db';
const CURRENT_VERSION = 1;

export function readDb(): AppDatabase { ... }
export function writeDb(db: AppDatabase): void { ... }
export function migrateDb(raw: unknown): AppDatabase { ... }
```

The Zustand store uses the `persist` middleware pointed at these functions. Never write directly to `localStorage` from components — always go through the store.

---

## 9. Mocking the Qasa API in Tests

### Backend (respx)

```python
# backend/tests/conftest.py
import pytest
import respx

MOCK_HOME_RESPONSE = {
    "data": {
        "home": {
            "id": "1348599",
            "rent": 11250,
            # ... minimal valid fixture
        }
    }
}

@pytest.fixture
def mock_qasa():
    with respx.mock(base_url="https://api.qasa.se") as rx:
        rx.post("/graphql").mock(return_value=httpx.Response(200, json=MOCK_HOME_RESPONSE))
        yield rx
```

### Frontend (MSW or vi.fn)

Use `vi.fn()` to mock the `qasaApi.ts` module:

```typescript
vi.mock('../../../src/api/qasaApi', () => ({
  fetchListing: vi.fn().mockResolvedValue({ id: '1348599', rent: 11250, ... }),
}));
```

---

## 10. Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `QASA_GRAPHQL_URL` | `https://api.qasa.se/graphql` | Override for testing |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowed origin |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `` (empty — uses proxy) | Backend base URL for production |

Set in `.env.local` (not committed to git).

---

## 11. Common Issues

### Map tiles not loading
Make sure you have internet access. OpenStreetMap tiles are fetched at runtime — there is no offline mode.

### CORS error from frontend
Ensure the backend is running on port 8000 and the Vite proxy is configured in `vite.config.ts`.

### localStorage quota exceeded
The browser typically allows 5–10 MB per origin. With ~500 saved apartments and full Qasa data, you may approach this limit. The `db.ts` module warns at 4 MB.

### Qasa returns `null` for `home`
Some listings are deleted or hidden. The backend returns 404 in this case; the frontend shows an error toast.

### Tests failing with "window is not defined"
Ensure `vitest.config.ts` sets `environment: 'jsdom'`.
