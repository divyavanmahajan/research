# Apartment Finder — Implementation Plan

> **Last updated:** 2026-04-19  
> **Tracking:** Update status inline as work progresses.  
> **Status legend:** ⬜ Not started · 🔄 In progress · ✅ Done · ❌ Blocked

---

## Phase 0 — Project Scaffold

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.1 | Create `backend/` folder + `pyproject.toml` / `requirements.txt` | ✅ | |
| 0.2 | Create `frontend/` folder with `npm create vite@latest` (React + TS) | ✅ | |
| 0.3 | Configure Vite proxy (`/api` → `localhost:8000`) | ✅ | |
| 0.4 | Configure CORS in FastAPI | ✅ | |
| 0.5 | Set up pytest with `respx` | ✅ | |
| 0.6 | Set up Vitest + RTL + jsdom | ✅ | |
| 0.7 | `GET /api/health` endpoint + test | ✅ | |
| 0.8 | Initial `README.md` with quick-start instructions | ✅ | |
| 0.9 | `.gitignore` for Python (`__pycache__`, `.venv`) and Node (`node_modules`) | ✅ | |

---

## Phase 1 — Backend Core (TDD)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Write `test_fetch_listing_valid_id` (mock Qasa) | ✅ | |
| 1.2 | Implement `services/qasa_client.py` — `fetch_listing(home_id)` | ✅ | |
| 1.3 | Implement `GET /api/listing/{home_id}` router | ✅ | |
| 1.4 | Write tests: invalid ID (400), not found (404), upstream error (502) | ✅ | |
| 1.5 | Write `test_parse_url_valid` + `test_parse_url_invalid` | ✅ | |
| 1.6 | Implement `services/url_parser.py` | ✅ | |
| 1.7 | Implement `POST /api/parse-url` router | ✅ | |
| 1.8 | Write `test_search_basic` (mocked single-page response) | ✅ | |
| 1.9 | Write `test_search_pagination` (mocked multi-page response) | ✅ | |
| 1.10 | Implement `POST /api/search` router + pagination loop | ✅ | |
| 1.11 | Write `test_search_missing_area` (400) | ✅ | |
| 1.12 | Write `test_cors_header` | ✅ | |
| 1.13 | All backend tests passing ✅ | ✅ | |

---

## Phase 2 — Frontend Foundation (TDD)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Define all TypeScript types in `src/types/index.ts` | ✅ | |
| 2.2 | Write tests for `urlParser.ts` (valid + invalid URLs) | ✅ | |
| 2.3 | Implement `src/utils/urlParser.ts` | ✅ | |
| 2.4 | Write tests for `db.ts` (read, write, merge, replace, migration) | ✅ | |
| 2.5 | Implement `src/utils/db.ts` | ✅ | |
| 2.6 | Write tests for `pinColor.ts` | ✅ | |
| 2.7 | Implement `src/utils/pinColor.ts` | ✅ | |
| 2.8 | Implement `src/api/qasaApi.ts` (typed fetch wrappers) | ✅ | |
| 2.9 | Implement Zustand store `src/store/useAppStore.ts` with persist | ✅ | |

---

## Phase 3 — Frontend UI (TDD)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | App shell: `App.tsx` split layout (left panel + map) | ✅ | |
| 3.2 | `MapPanel.tsx` — Leaflet + OSM tiles, default Gothenburg | ✅ | |
| 3.3 | `LeftPanel.tsx` — tab navigation (My List / Search / Saved Searches) | ✅ | |
| 3.4 | Test + implement `TagInput.tsx` | ⬜ | |
| 3.5 | Test + implement `CommentThread.tsx` | ⬜ | |
| 3.6 | Test + implement `ApartmentCard.tsx` | ⬜ | |
| 3.7 | Test + implement `ApartmentDetail.tsx` (drawer) | ⬜ | |
| 3.8 | Test + implement `MyList.tsx` | 🔄 | |
| 3.9 | Test + implement `SearchPanel.tsx` (all filter fields) | ⬜ | |
| 3.10 | Test + implement `SearchResultCard.tsx` | ⬜ | |
| 3.11 | Test + implement `SearchResults.tsx` | ⬜ | |
| 3.12 | Test + implement `SavedSearches.tsx` | ⬜ | |
| 3.13 | Test + implement `ImportExport.tsx` | ⬜ | |
| 3.14 | `Toast.tsx` + `ConfirmDialog.tsx` | ⬜ | |
| 3.15 | URL-paste "Add by URL" field in left panel header | ⬜ | |

---

## Phase 4 — Map Integration

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Render saved apartment pins (coloured by tag) | ✅ | |
| 4.2 | Render search result pins (orange, hollow) | ✅ | |
| 4.3 | Click pin → select apartment + scroll list | ⬜ | |
| 4.4 | Click list row → pan map to pin | ⬜ | |
| 4.5 | Auto-fit bounds on tab switch | ✅ | |
| 4.6 | City selector changes map default centre | ⬜ | |

---

## Phase 5 — Polish & Integration Testing

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | End-to-end: add apartment by URL, add tag, add comment, export, import | ⬜ | Manual test |
| 5.2 | End-to-end: search, add result, verify map pin colour by tag | ⬜ | Manual test |
| 5.3 | End-to-end: save search, reload page, re-run saved search | ⬜ | Manual test |
| 5.4 | localStorage size warning (> 4 MB) | ⬜ | |
| 5.5 | Error states: toast on API failure, toast on invalid URL | ⬜ | |
| 5.6 | Duplicate add warning | ⬜ | |
| 5.7 | Final CSS polish and responsive column widths | ⬜ | |

---

## Completed Milestones

| Milestone | Date | Notes |
|-----------|------|-------|
| Spec, architecture, developer, user docs written | 2026-04-19 | |

---

## Known Issues / Blockers

_None yet._

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-19 | Backend fetches all search pages server-side | Simplifies frontend; avoids pagination state management |
| 2026-04-19 | Data stored in localStorage only | User requested; no backend database needed |
| 2026-04-19 | OpenStreetMap tiles via react-leaflet | Free, no API key, good coverage for Nordic cities |
| 2026-04-19 | Zustand with persist middleware | Lightweight; easier than Redux for this scale |
| 2026-04-19 | `HomeSearchCoordsQuery` not used | `HomeSearch` already returns coordinates in `location.point` |
