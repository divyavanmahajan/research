# Apartment Finder

A personal web app for tracking Swedish apartment listings from [qasa.se](https://qasa.se).

## Features

- **My List** — Card grid of saved apartments with tags and personal comments.
- **Search** — Filter listings by city, rent, size, etc., and browse results.
- **Add by URL** — Paste a Qasa listing URL to add it directly to your list.
- **Map View** — See all saved apartments and search results on an interactive map (Leaflet + OSM).
- **Export/Import** — Backup your data as a JSON file and restore it later.

## Technology Stack

- **Backend**: Python 3.12 + FastAPI (stateless proxy for Qasa GraphQL API).
- **Frontend**: React 18 + TypeScript + Vite.
- **State Management**: Zustand with persistence to `localStorage`.
- **Mapping**: Leaflet + OpenStreetMap.
- **Testing**: `pytest` (backend), `Vitest` (frontend).

## Quick Start

### 1. Backend

Requires Python 3.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest tests/  # Run tests
uvicorn main:app --reload --port 8000
```

### 2. Frontend

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run test    # Run tests
npm run dev     # Starts at http://localhost:5173
```

## Documentation

Detailed guides are available in the [docs/](./docs/) directory:
- [Technical Specification](./docs/spec.md)
- [Architecture Overview](./docs/architecture.md)
- [Developer Guide](./docs/developer.md)
- [User Manual](./docs/user.md)
- [Implementation Plan](./docs/plan.md)
