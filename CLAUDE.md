# Claude Code — Research Repository

This repository contains independent research projects, each in its own folder. All code is LLM-generated.

## Active Project: Apartment Finder

A personal web app for tracking Swedish apartment listings from qasa.se.

| Doc | Purpose |
|---|---|
| [`docs/apartment-finder/spec.md`](docs/apartment-finder/spec.md) | Product spec — views, data model, user goals |
| [`docs/apartment-finder/architecture.md`](docs/apartment-finder/architecture.md) | Tech stack, repo layout, API contracts, storage schema |
| [`docs/apartment-finder/plan.md`](docs/apartment-finder/plan.md) | Milestone breakdown and decisions log — **update this as work progresses** |
| [`docs/apartment-finder/developer-notes.md`](docs/apartment-finder/developer-notes.md) | Scraper internals, gotchas, common issues |

### Key facts

- **Branch:** `claude/apartment-finder-app-KBkPR`
- **App folder:** `apartment-finder/`
- **Start command:** `npm run dev` from `apartment-finder/` (starts backend on 3001 + frontend on 5173 via concurrently)
- **Stack:** React + Vite (frontend) · Node/Express (backend scraping proxy) · IndexedDB (storage) · Leaflet/OSM (map)
- **Scrape target:** qasa.se — reads `__NEXT_DATA__` JSON blob embedded in page HTML

### Before writing any code

1. Read `spec.md` to understand what each view must do.
2. Read `architecture.md` for the folder structure and API contracts — do not deviate without updating the doc.
3. Check `plan.md` for current milestone status and mark tasks complete as you go.
4. Add any non-obvious decisions or workarounds to `developer-notes.md`.

### Conventions

- No comments unless the WHY is non-obvious.
- Tailwind for all styling — no inline styles, no CSS modules.
- All IndexedDB access goes through `frontend/src/db.js` — never call idb directly from components.
- Backend never stores data — it scrapes and returns JSON only.
- Geocoding happens in the backend (not frontend) to avoid Nominatim CORS issues.

## Other Projects

| Folder | Description |
|---|---|
| [`whatsup/`](whatsup/) | End-to-end encrypted messaging app (Rust, Signal Protocol) |
| [`financeflow/`](financeflow/) | Personal finance tracker (Python/FastAPI + Vite) |
| [`warehouse/`](warehouse/) | Warehouse management system (FastAPI + HTMX) |
| [`SamsungTVRemote/`](SamsungTVRemote/) | Samsung TV remote control app |
| [`dvm-haranalyzer/`](dvm-haranalyzer/) | HAR file analyzer |
| [`powerapp-appointments/`](powerapp-appointments/) | Power Apps appointments canvas app |
