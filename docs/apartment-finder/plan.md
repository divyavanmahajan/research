# Apartment Finder — Plan & Progress

**Version:** 1.0
**Date:** 2026-04-18
**Branch:** `claude/apartment-finder-app-KBkPR`

---

## Milestones

| # | Milestone | Status |
|---|---|---|
| 1 | Docs & project scaffold | ✅ Done |
| 2 | Backend scraper (qasa.se) | ✅ Done |
| 3 | Frontend shell + routing | ✅ Done |
| 4 | IndexedDB storage layer | ✅ Done |
| 5 | My List view | ✅ Done |
| 6 | Apartment Detail view | ✅ Done |
| 7 | Investigate mode (URL + search) | ✅ Done |
| 8 | Map view (Leaflet) | ✅ Done |
| 9 | Export / Import JSON | ✅ Done |
| 10 | Polish & production build | ⬜ Pending |

---

## Detailed Task Breakdown

### Milestone 1 — Docs & project scaffold ✅
- [x] Product spec (`docs/apartment-finder/spec.md`)
- [x] Architecture doc (`docs/apartment-finder/architecture.md`)
- [x] Plan & progress (`docs/apartment-finder/plan.md`)
- [x] Developer notes (`docs/apartment-finder/developer-notes.md`)
- [x] Root `CLAUDE.md`

### Milestone 2 — Backend scraper
- [ ] `apartment-finder/backend/package.json` (express, axios, cheerio, cors, nodemon)
- [ ] `apartment-finder/backend/server.js` — Express app, `/api/scrape`, `/api/search`
- [ ] `apartment-finder/backend/scrapers/qasa.js` — scrape single listing URL
- [ ] `apartment-finder/backend/scrapers/qasa.js` — scrape search results

### Milestone 3 — Frontend shell
- [ ] `apartment-finder/frontend/` Vite + React project init
- [ ] Tailwind CSS setup
- [ ] React Router routes (`/`, `/apartment/:id`, `/investigate`, `/map`)
- [ ] Nav bar component
- [ ] Vite proxy config for `/api`

### Milestone 4 — IndexedDB storage
- [ ] `src/db.js` with idb wrapper
- [ ] CRUD: `getAll`, `get`, `put`, `remove`
- [ ] `exportAll` / `importAll(mode)`

### Milestone 5 — My List view
- [ ] `ListView.jsx` — card grid layout
- [ ] `ApartmentCard.jsx` — thumbnail, address, price, size, rooms, priority badge, status
- [ ] Filter bar (priority, status)
- [ ] Sort controls (price, size, date)
- [ ] Empty state

### Milestone 6 — Apartment Detail view
- [ ] `DetailView.jsx` layout
- [ ] `PhotoGallery.jsx` — horizontal scroll
- [ ] Key facts grid
- [ ] `PriorityPicker.jsx` — pill buttons, persists to IndexedDB
- [ ] `StatusStepper.jsx` — persists to IndexedDB
- [ ] Notes textarea with auto-save (debounced)
- [ ] Leaflet map with single pin + Nominatim geocoding
- [ ] Delete with confirmation

### Milestone 7 — Investigate mode
- [ ] `InvestigateView.jsx` with URL / Search tabs
- [ ] URL tab: input, call `/api/scrape`, show preview card
- [ ] Search tab: filters form, call `/api/search`, show results
- [ ] "Add to My List" button (check duplicate by sourceUrl)

### Milestone 8 — Map view
- [ ] `MapView.jsx` with react-leaflet
- [ ] Load all apartments from IndexedDB, filter those with lat/lng
- [ ] Color-coded markers by priority
- [ ] Popup: thumbnail, address, price, priority, "Open detail" link
- [ ] Fit bounds to markers

### Milestone 9 — Export / Import
- [ ] `ExportImport.jsx` component
- [ ] Export: serialize IndexedDB → JSON download
- [ ] Import: file upload → parse → merge or replace modal

### Milestone 10 — Polish
- [ ] Root `apartment-finder/package.json` with `concurrently` dev script
- [ ] Production build: Express serves Vite `dist/`
- [ ] README in `apartment-finder/`
- [ ] Error boundaries and loading states throughout
- [ ] Test scraper against live qasa.se

---

## Decisions Log

| Date | Topic | Decision |
|---|---|---|
| 2026-04-18 | Platform | Web app (React + Vite) |
| 2026-04-18 | Storage | IndexedDB + JSON export/import |
| 2026-04-18 | Map | Leaflet + OpenStreetMap |
| 2026-04-18 | Ranking | Priority tiers: Must see / Nice / Skip |
| 2026-04-18 | Scraping | Node.js backend proxy (CORS workaround) |
| 2026-04-18 | Startup | Single `npm run dev` via concurrently |

---

## Known Risks

| Risk | Mitigation |
|---|---|
| qasa.se changes HTML structure | Scraper targets `__NEXT_DATA__` JSON blob, not fragile DOM selectors |
| Nominatim rate limit (1 req/s) | Geocode only on save; skip if lat/lng already set |
| Photo CORS | Images loaded directly via `<img>` — browsers permit cross-origin image loads |
| IndexedDB data loss | Export/import feature; user prompted to export before replacing |
