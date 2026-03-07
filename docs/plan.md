# Warehouse Management System — Plan & Progress

**Version:** 1.0
**Date:** 2026-03-07
**Branch:** `claude/warehouse-management-system-jN8Dc`

---

## Decisions Made

| Topic | Decision |
|---|---|
| Stack | Python + FastAPI |
| Frontend | HTMX + Jinja2 templates |
| UI Style | Dashboard-style (sidebar, cards, Tailwind CSS) |
| Storage | SQLite via SQLAlchemy |
| Auth | JWT in HTTP-only cookies, Admin + Operator roles |
| Bin capacity | Volume-based (W × H × D cm³) |
| Addressing | Aisle-Rack-Level-Bin (A1-R2-L3-B4) |
| Picking algorithm | S-shape traversal |
| Pick list UI | Interactive checklist with live progress bar (HTMX) |
| Search | Live search by name/SKU, 300 ms debounce (HTMX) |
| Demo tooling | `showboat` (demo documents) + `rodney` (browser automation) |

---

## Milestones

### M1 — Project Setup
- [x] Git branch created: `claude/warehouse-management-system-jN8Dc`
- [x] Directory structure created
- [x] docs/product_spec.md written
- [x] docs/architecture.md written
- [x] docs/plan.md written (this file)

### M2 — Backend Core
- [x] warehouse/requirements.txt
- [x] warehouse/database.py
- [x] warehouse/models.py
- [x] warehouse/schemas.py
- [x] warehouse/auth.py
- [x] warehouse/picking.py

### M3 — Routers
- [x] warehouse/routers/auth.py
- [x] warehouse/routers/aisles.py
- [x] warehouse/routers/racks.py
- [x] warehouse/routers/levels.py
- [x] warehouse/routers/bins.py
- [x] warehouse/routers/items.py
- [x] warehouse/routers/inventory.py
- [x] warehouse/routers/pick.py
- [x] warehouse/routers/users.py

### M4 — Application Entry Point
- [x] warehouse/main.py

### M5 — Templates
- [x] warehouse/templates/base.html
- [x] warehouse/templates/login.html
- [x] warehouse/templates/dashboard.html
- [x] warehouse/templates/structure.html
- [x] warehouse/templates/bins.html
- [x] warehouse/templates/items.html
- [x] warehouse/templates/inventory.html
- [x] warehouse/templates/search.html
- [x] warehouse/templates/pick_new.html
- [x] warehouse/templates/pick_session.html
- [x] warehouse/templates/pick_history.html
- [x] warehouse/templates/users.html
- [x] warehouse/templates/partials/rack_row.html
- [x] warehouse/templates/partials/bin_row.html
- [x] warehouse/templates/partials/capacity_bar.html
- [x] warehouse/templates/partials/search_results.html
- [x] warehouse/templates/partials/item_row.html
- [x] warehouse/templates/partials/pick_stop.html
- [x] warehouse/templates/partials/pick_progress.html

### M6 — Static Assets
- [x] warehouse/static/style.css

### M7 — Demo
- [x] warehouse/demo/seed.py
- [x] warehouse/demo/demo.sh

### M8 — Version Control
- [x] Commit all files
- [x] Push to branch

---

## File Inventory

```
warehouse/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── auth.py
├── picking.py
├── requirements.txt
├── routers/
│   ├── __init__.py
│   ├── auth.py
│   ├── aisles.py
│   ├── racks.py
│   ├── levels.py
│   ├── bins.py
│   ├── items.py
│   ├── inventory.py
│   ├── pick.py
│   └── users.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── structure.html
│   ├── bins.html
│   ├── items.html
│   ├── inventory.html
│   ├── search.html
│   ├── pick_new.html
│   ├── pick_session.html
│   ├── pick_history.html
│   ├── users.html
│   └── partials/
│       ├── rack_row.html
│       ├── bin_row.html
│       ├── capacity_bar.html
│       ├── search_results.html
│       ├── item_row.html
│       ├── pick_stop.html
│       └── pick_progress.html
├── static/
│   └── style.css
└── demo/
    ├── seed.py
    └── demo.sh

docs/
├── product_spec.md
├── architecture.md
└── plan.md (this file)
```

---

## Known Constraints & Design Choices

- **Level cap:** Enforced at router level (HTTP 400 if rack already has 3 levels)
- **Volume check:** Enforced at inventory add time; partial fills allowed
- **Basket storage:** Pick baskets are server-side draft sessions in `pick_sessions` table
- **Inventory decrement:** Happens per-stop check-off (not at session completion)
- **Multi-bin items:** Resolved by nearest-aisle greedy selection before S-shape sort
- **Auth:** JWT expiry is 8 hours; no refresh token in v1.0
