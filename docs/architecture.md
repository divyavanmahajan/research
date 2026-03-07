# Warehouse Management System — Architecture

**Version:** 1.0
**Date:** 2026-03-07

---

## 1. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web Framework | FastAPI (Python) | HTTP routing, dependency injection, template serving |
| Templating | Jinja2 | Server-side HTML rendering |
| Dynamic UI | HTMX 1.9 | Partial page updates without a JS framework |
| Styling | Tailwind CSS (CDN) | Utility-first CSS, dashboard layout |
| ORM | SQLAlchemy 2.x | Database abstraction |
| Database | SQLite | File-based relational storage (`warehouse.db`) |
| Auth | python-jose (JWT) + passlib (bcrypt) | Token-based auth via HTTP-only cookies |

---

## 2. Directory Layout

```
warehouse/
├── main.py               # FastAPI app factory, router registration, exception handlers
├── database.py           # SQLAlchemy engine, session factory, Base
├── models.py             # ORM table definitions
├── schemas.py            # Pydantic request/response schemas
├── auth.py               # JWT encode/decode, password hashing, auth dependencies
├── picking.py            # S-shape route algorithm
├── routers/
│   ├── auth.py           # GET/POST /login, GET /logout
│   ├── aisles.py         # CRUD for aisles
│   ├── racks.py          # CRUD for racks
│   ├── levels.py         # CRUD for levels (max 3 per rack enforced here)
│   ├── bins.py           # CRUD for bins
│   ├── items.py          # CRUD for item catalogue
│   ├── inventory.py      # Stock/unstock bins, view bin contents
│   ├── pick.py           # Pick session lifecycle
│   └── users.py          # User management (admin only)
├── templates/
│   ├── base.html         # Sidebar layout shell
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
│   └── partials/         # HTML fragments returned by HTMX endpoints
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
└── plan.md
```

---

## 3. Data Model

```
users
  id PK
  username UNIQUE
  password_hash
  role  {admin | operator}

aisles
  id PK
  code UNIQUE   e.g. "A1"
  name

racks
  id PK
  aisle_id FK→aisles
  code            e.g. "R1"
  name

levels
  id PK
  rack_id FK→racks
  level_num  {1 | 2 | 3}

bins
  id PK
  level_id FK→levels
  code           e.g. "B1"
  size_category  {S | M | L | XL}
  width_cm, height_cm, depth_cm FLOAT
  [computed] volume_cm3 = w*h*d
  [computed] location_code = "A1-R2-L3-B4"

items
  id PK
  sku UNIQUE
  name
  description
  width_cm, height_cm, depth_cm FLOAT
  [computed] volume_cm3 = w*h*d

bin_items
  id PK
  bin_id  FK→bins   CASCADE DELETE
  item_id FK→items  CASCADE DELETE
  quantity INT
  added_at DATETIME
  UNIQUE(bin_id, item_id)

pick_sessions
  id PK
  operator_id FK→users
  created_at DATETIME
  status  {draft | open | completed}

pick_items          -- basket before route generation
  id PK
  session_id FK→pick_sessions CASCADE DELETE
  item_id    FK→items
  quantity_requested INT

pick_stops          -- ordered route stops
  id PK
  session_id FK→pick_sessions CASCADE DELETE
  bin_id     FK→bins
  item_id    FK→items
  quantity   INT
  order_index INT
  picked     BOOLEAN DEFAULT false
```

### Key Constraints

- `levels.level_num` is enforced ≤ 3 at the application layer (router returns 400 if exceeded)
- Bin volume check: `used_volume + item_volume * qty ≤ bin_volume` before inserting BinItem
- Pick basket (`pick_items`) is replaced by `pick_stops` after route generation; session status changes `draft → open`

---

## 4. Authentication Flow

```
Browser                      FastAPI
  │                            │
  ├─ POST /auth/login ─────────►│
  │   {username, password}      │ validate credentials (bcrypt)
  │                            │ encode JWT {sub: user_id, role}
  │◄── 303 /dashboard ─────────┤
  │    Set-Cookie: access_token=<jwt>; HttpOnly; SameSite=Lax
  │                            │
  ├─ GET /dashboard ───────────►│
  │   Cookie: access_token=... │ decode JWT → user from DB
  │◄── 200 HTML ───────────────┤
  │                            │
  ├─ GET /logout ──────────────►│
  │◄── 303 /login ─────────────┤
  │    Set-Cookie: access_token=; Max-Age=0
```

Two FastAPI dependencies are injected into every protected route:
- `require_user(request)` — decodes JWT, fetches user, raises `NotAuthenticated` if invalid
- `require_admin(user)` — wraps `require_user`, raises `NotAuthorized` if role ≠ admin

Exception handlers convert these to redirect responses:
- `NotAuthenticated` → `303 /login`
- `NotAuthorized` → `303 /dashboard?error=forbidden`

---

## 5. HTMX Interaction Map

| Page | Trigger | Endpoint | Target | Response |
|---|---|---|---|---|
| structure.html | Click aisle row | `GET /structure/aisles/{id}/racks` | `#rack-panel` | `partials/rack_row.html` |
| search.html | Keyup on input (300 ms) | `GET /search/results?q=` | `#results` | `partials/search_results.html` |
| pick_new.html | Click "Add" on result | `POST /pick/{id}/basket/add` | `#basket-list` | updated basket HTML |
| pick_new.html | Click "Remove" on basket row | `DELETE /pick/{id}/basket/{item_id}` | basket row | empty string (removes row) |
| pick_session.html | Check off a stop | `POST /pick/{id}/stop/{stop_id}/check` | `#stop-{stop_id}` + `#progress` | `partials/pick_stop.html` + `partials/pick_progress.html` |

---

## 6. Picking Algorithm Detail

**File:** `picking.py` → `compute_route(stops) → List[stop]`

```
Input:  list of (bin, item_id, quantity)
Output: same list sorted by S-shape order

Sort key per stop:
  aisle_num  = int(aisle.code[1:])   # A1 → 1
  rack_num   = int(rack.code[1:])    # R2 → 2
  level_num  = level.level_num       # 1..3
  bin_num    = int(bin.code[1:])     # B4 → 4

  if aisle_num is odd:
      key = (aisle_num, +rack_num, +level_num, +bin_num)   # ascending
  else:
      key = (aisle_num, -rack_num, -level_num, -bin_num)   # descending
```

When one item exists in multiple bins, `pick.py` selects the bin whose `aisle_num` is **closest to the aisle of the previously added stop** (greedy nearest-aisle selection) before sorting.

---

## 7. Capacity Calculation

Computed on the fly per bin:

```python
used_volume = sum(bi.item.volume_cm3 * bi.quantity for bi in bin.bin_items)
pct = used_volume / bin.volume_cm3 * 100

colour:
  pct < 70   → green
  pct < 90   → amber
  else        → red
```

Dashboard "Overall Capacity" is the average across all bins.

---

## 8. Running Locally

```bash
cd warehouse
pip install -r requirements.txt
uvicorn main:app --reload
# App available at http://localhost:8000
```

### Demo

```bash
cd warehouse
python demo/seed.py          # seed database with sample data
bash demo/demo.sh            # run full browser demo (requires uvx)
```
