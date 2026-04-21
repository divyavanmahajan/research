# dmv-aptfind

A personal apartment research tool for [Qasa](https://qasa.com) listings in Sweden, Norway, and Finland. Search, save, tag, annotate, and compare apartments — all from your browser. No account required, no data leaves your machine.

## Quick start

```bash
uvx dmv-aptfind
```

This installs the tool in an isolated environment, starts a local server on port 8788, and opens the app in your browser. Run the same command again whenever you want to use it — `uvx` handles updates automatically.

---

## Features

### Search

Open the **Search** tab and pick a city. You can filter by:

| Filter | Values |
|--------|--------|
| City | Area identifier in the format `se/gothenburg` — see table below |
| Rooms | min / max |
| Rent | min / max (SEK) |
| Size | min / max (m²) |
| Furnished | yes / no / either |
| Home type | apartment, house, room |
| First-hand, student, senior, corporate | toggle |
| Sort | newest first or by rent |

The area field uses Qasa's internal identifier format — `country-code/city`:

| City | Area identifier |
|------|----------------|
| Gothenburg | `se/gothenburg` |
| Stockholm | `se/stockholm` |
| Malmö | `se/malmo` |
| Oslo | `no/oslo` |
| Helsinki | `fi/helsinki` |

Results appear as a list on the left and as pins on the map simultaneously. For large cities the search is capped at ~531 results to keep response times reasonable.

**Add by URL** — if you already have a Qasa listing URL, paste it directly into the field at the top of My List and press Add. No need to search first.

### Saved searches

Click **Save search** after configuring filters to store the preset. Saved searches are listed in the **Saved Searches** tab; clicking one reloads the filters and re-runs the search immediately.

### My list

Apartments you save accumulate in the **My List** tab. Each card shows the primary photo, address, rent, room count, size, tags, and comment count.

Click any card to open the detail panel on the right, which shows:

- Full rent, size, rooms, floor, address
- Link to the original Qasa listing
- Description from the landlord
- Tags (edit inline)
- Timestamped notes (add / delete individually)
- Commute times to your saved destinations
- All listing photos

Click a map pin to jump directly to that apartment's detail panel.

### Tags

Tags are freeform — type anything. The app ships with these suggestions:

| Tag | Map pin colour |
|-----|---------------|
| `favourite` | amber |
| `interested` | green |
| `applied` | blue |
| `visited` | purple |
| `rejected` | red |
| `not interested` | red |
| any other tag | grey |

The pin colour on the map reflects the first tag assigned. Apartments with no tags use grey.

### Commute times

The app calculates door-to-door travel times to your saved destinations simultaneously, using four transport modes:

🚗 driving · 🚌 transit · 🚶 walking · 🚲 cycling

To set up destinations:

1. Open any saved apartment's detail panel.
2. Scroll to the **Commute** section.
3. Click **Edit** and add destinations by name (e.g. "Chalmers University") or address.

Each time badge is a direct link to Google Maps directions for that exact route and mode. Commute destinations are shared across all apartments — add them once and they appear everywhere.

### HTML export (share by email)

Export a self-contained HTML report you can email to someone or open offline:

- From any apartment's detail panel: click **Share as HTML ✉** to export that single apartment.
- From the bottom of My List: click the full-list **Share as HTML ✉** button, choose which tags to include, and download.

The exported file includes:
- A summary table at the top with Qasa link, address, size, rent, tags, first note, commute times, and availability — sorted favourites first, then interested, then other tags alphabetically
- Individual sections per apartment with all notes, commute table with Google Maps links, description, and photos

The report is a single `.html` file with styling inlined — no internet connection needed to view it.

### JSON backup / restore

Use the **Export JSON** and **Import JSON** buttons at the bottom of My List to back up or restore your data.

On import you choose:
- **Merge** — adds new apartments without touching existing ones
- **Replace** — overwrites your entire list

The app warns you if your stored data grows beyond 4 MB.

### Dark mode

The app follows your system appearance (light / dark) automatically.

---

## Data storage

Everything is stored in your **browser's localStorage** under the key `apartment-finder-db`. Nothing is sent to any server except:

- Qasa's API (to fetch listing data when you search or add by URL)
- Google Maps (to calculate commute times, when you use that feature)

Clearing your browser's site data for `localhost` will erase your list — use **Export JSON** regularly if your list matters to you.

---

## Development setup

**Requirements:** Python 3.12+, Node 18+

```bash
git clone <repo>
cd apartment-finder

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

Run tests:

```bash
# Backend
cd backend && PYTHONPATH=. pytest -v

# Frontend
cd frontend && npm run test
```

Build and publish the PyPI package:

```bash
# From repo root (requires Node for the frontend build step)
pip install hatch twine
hatch build
twine upload dist/*
```
