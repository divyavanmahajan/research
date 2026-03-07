# Warehouse Management System

A web-based warehouse management system built with FastAPI, SQLAlchemy, Jinja2, and HTMX. Manages warehouse structure (aisles → racks → levels → bins), item inventory, and guided pick sessions.

## Features

- **Warehouse structure** — hierarchical aisle/rack/level/bin management with volume capacity tracking
- **Items & inventory** — item catalogue and per-bin stock levels
- **Search** — full-text search across items and bins
- **Pick sessions** — create a basket of items, generate an optimised pick route, mark stops complete
- **Pick history** — log of completed pick sessions
- **User management** — admin-only user creation (admin and picker roles)
- **Auth** — JWT cookie-based authentication with role-based access control
- **HTMX** — dynamic content (e.g. expanding rack structure) without page reloads

## Quick Start

```bash
pip install -r requirements.txt

# Run the server (creates warehouse.db automatically)
uvicorn main:app --reload

# Open http://localhost:8000
# Default credentials: admin / admin123
```

## Project Structure

```
warehouse/
├── main.py          FastAPI app, dashboard, startup
├── auth.py          JWT auth, cookie helpers, role checks
├── database.py      SQLAlchemy engine, session, init_db
├── models.py        ORM models: User, Aisle, Rack, Level, Bin, Item, Inventory, PickSession
├── schemas.py       Pydantic request/response schemas
├── picking.py       Pick route optimisation logic
├── routers/         One router per resource
│   ├── auth.py      Login / logout
│   ├── structure.py Aisle tree (HTMX partials)
│   ├── aisles.py    Aisle CRUD
│   ├── racks.py     Rack CRUD
│   ├── levels.py    Level CRUD
│   ├── bins.py      Bin CRUD + capacity
│   ├── items.py     Item catalogue
│   ├── inventory.py Stock level management
│   ├── pick.py      Pick session workflows
│   ├── search.py    Full-text search
│   └── users.py     User management (admin only)
├── templates/       Jinja2 HTML templates
├── static/          CSS
└── demo/            Automated demo with screenshots
    ├── demo.sh      Shell script to run the full demo
    ├── seed.py      Seed script for demo data
    └── warehouse_demo.md  Verified demo walkthrough with screenshots
```

## Demo

```bash
cd demo
python seed.py        # seed demo data
bash demo.sh          # run automated browser demo
```

See [`demo/warehouse_demo.md`](demo/warehouse_demo.md) for a full walkthrough with screenshots.

## Technology Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Templates**: Jinja2 + HTMX (dynamic partials, no JS framework)
- **Auth**: JWT (PyJWT) + bcrypt password hashing, HTTP-only cookies
- **Roles**: `admin` (full access) and `picker` (pick sessions only)
