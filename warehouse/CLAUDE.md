# Warehouse Management System — Claude Code Guide

## Project Overview

FastAPI + SQLAlchemy + Jinja2 + HTMX warehouse management system. Single-file SQLite DB. No frontend build step.

## Run

```bash
pip install -r requirements.txt

# Dev server with auto-reload
uvicorn main:app --reload --port 8000

# Open http://localhost:8000
# Default login: admin / admin123
```

## Key Files

| File | Purpose |
|---|---|
| `main.py` | App entry, router registration, dashboard endpoint, startup hook |
| `database.py` | SQLAlchemy engine/session factory, `init_db()` |
| `models.py` | ORM models: User, Aisle, Rack, Level, Bin, Item, Inventory, PickSession, PickStop |
| `schemas.py` | Pydantic request/response schemas |
| `auth.py` | `require_user()`, `require_admin()`, JWT decode, `NotAuthenticated` / `NotAuthorized` exceptions |
| `picking.py` | Pick route optimisation |
| `routers/` | One file per resource, each with its own `APIRouter` |

## Auth Pattern

- JWT stored as HTTP-only `access_token` cookie
- `require_user(request)` — raises `NotAuthenticated` if missing/invalid
- `require_admin(request)` — raises `NotAuthorized` if role != admin
- Both exceptions are caught by global handlers in `main.py` and redirected

## HTMX Partials

The `templates/partials/` folder contains HTML fragments returned by HTMX requests (e.g. expanding a rack row inline). These are returned as `HTMLResponse`, not full page renders.

## Database

SQLite file: `warehouse.db` (auto-created on first run via `init_db()`).
Schema is defined in `models.py` via SQLAlchemy declarative models.

## Roles

- `admin` — full access to all pages including user management and structure edits
- `picker` — can only access search, inventory view, and pick sessions

## Demo / Seeding

```bash
cd demo
python seed.py     # populate with sample aisles, racks, bins, items
bash demo.sh       # run Showboat browser automation to capture screenshots
```
