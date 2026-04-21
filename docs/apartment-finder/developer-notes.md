# Apartment Finder — Developer Notes

**Updated:** 2026-04-18

---

## Local Dev Setup

```bash
cd apartment-finder
npm run install:all  # installs root + frontend deps
npm run dev          # Vite on :5173, Wrangler Pages dev on :8788
```

Open http://localhost:5173 (Vite with HMR). Port :8788 is the Wrangler Pages dev server (routes `/api/*` to `functions/`); the `--proxy` flag it uses is deprecated in Wrangler 4 and currently broken — use :5173 for frontend development.

---

## Scraper: How qasa.se Works

qasa.se is a Next.js app. The fastest and most stable way to extract data is to read the embedded JSON blob in the page HTML rather than parsing DOM elements.

Look for:
```html
<script id="__NEXT_DATA__" type="application/json">{ ... }</script>
```

For a listing page, the apartment data lives at a path like:
```
__NEXT_DATA__.props.pageProps.home
```

For search results:
```
__NEXT_DATA__.props.pageProps.homes  (array)
```

These paths may drift when qasa deploys updates. If scraping breaks, open the listing in a browser, view source, find `__NEXT_DATA__`, and inspect the structure.

**Fallback:** If `__NEXT_DATA__` is absent (e.g., client-only routes), use cheerio to parse meta tags and OG tags as a last resort.

---

## Nominatim Geocoding

Free, no API key. Usage policy requires:
- Max 1 request/second
- `User-Agent` header identifying your app

Example call from backend:
```js
const res = await axios.get('https://nominatim.openstreetmap.org/search', {
  params: { q: address, format: 'json', limit: 1 },
  headers: { 'User-Agent': 'ApartmentFinder/1.0' }
});
const { lat, lon } = res.data[0];
```

Geocoding is done in the backend (not frontend) to avoid CORS issues with Nominatim.

---

## IndexedDB Schema

Database name: `apartment-finder`
Store: `apartments`

Created via idb `openDB`:
```js
openDB('apartment-finder', 1, {
  upgrade(db) {
    const store = db.createObjectStore('apartments', { keyPath: 'id' });
    store.createIndex('addedAt', 'addedAt');
    store.createIndex('priority', 'priority');
    store.createIndex('status', 'status');
  }
});
```

---

## Adding Support for a New Rental Site

1. Create `backend/scrapers/<sitename>.js` exporting `scrapeUrl(url)` and `scrapeSearch(params)`
2. In `backend/server.js`, detect the domain from the URL and route to the correct scraper
3. Update `spec.md` Non-Goals section
4. Note any site-specific quirks here

---

## Common Issues

### Scraper returns empty fields
- qasa may have changed their `__NEXT_DATA__` structure. Log the raw JSON and re-map the paths in `qasa.js`.

### Map pins not appearing
- Check that `lat`/`lng` are numbers, not null. The apartment was likely saved before geocoding was implemented. Open the detail view to trigger re-geocode, or delete and re-add.

### Wrangler :8788 returns 404 for all routes
- The `--proxy` flag in `wrangler pages dev` is deprecated in Wrangler 4 and does not work correctly. Use Vite directly at :5173 for frontend development. The Functions (`/api/*`) can be tested independently via `npm run test:functions`.

### Photos not loading
- qasa photo URLs may be signed/time-limited CDN URLs. Nothing to do — re-scrape the listing to refresh them.

---

## Updating This File

Add a dated entry for any non-obvious decision, workaround, or discovered quirk:

```
### YYYY-MM-DD — <topic>
<description>
```

---

## 2026-04-18 — Why tests didn't catch the post-migration breakage

Three bugs were introduced during the TypeScript migration and architecture change to Cloudflare Pages, none caught by `npm test`:

| Bug | Location | Why tests missed it |
|---|---|---|
| `main.jsx` → should be `main.tsx` | `frontend/index.html` | `index.html` is the Vite entry point — never touched by Vitest/jsdom, which imports components directly as ES modules |
| Missing `)` syntax error | `frontend/src/views/MapView.tsx:45` | No `MapView.test.tsx` exists; the module was never loaded by any test |
| Vite `root` not set — dev server served from wrong directory | `frontend/vite.config.ts` | No test starts the dev server or runs a build; configuration errors are invisible to unit tests |

### What the test suite actually covers

The frontend tests (Vitest + jsdom) import components directly via ES modules. They never exercise:
- The HTML entry point (`index.html`)
- The Vite dev server or build pipeline
- Any file not imported by a tested component

`npm run typecheck` would have caught the `MapView.tsx` syntax error, but it is not wired into `npm test`.

### What to do differently

**1. Add typecheck to the test pipeline.**
`npm test` should fail on TypeScript errors across all files, not just the ones covered by tests. In `package.json`:
```json
"test": "npm run typecheck && concurrently ..."
```
This would have caught the MapView syntax error immediately.

**2. Add a build verification step.**
`npm run build` exercises the Vite config and `index.html` together. Any file reference error or config mistake surfaces here. Run it in CI (or locally before merging) — it's the cheapest smoke test for the whole frontend pipeline.

**3. Cover every view with at least one render test.**
`MapView` had no test. A single `render(<MapView />)` wrapped in a MemoryRouter would have failed on import due to the syntax error, catching it before the browser.

**4. After a large migration, do a dev-server smoke check first.**
When the primary change is architectural (e.g., moving from Express to Cloudflare Pages, migrating JS → TS), start the dev server and open the browser before running unit tests. Unit tests can all pass while the app is completely broken at the integration seam (HTML entry point, build config, proxy routing).
