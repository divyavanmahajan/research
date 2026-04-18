# Apartment Finder — Developer Notes

**Updated:** 2026-04-18

---

## Local Dev Setup

```bash
cd apartment-finder
npm install          # installs root deps (concurrently)
cd backend && npm install
cd ../frontend && npm install
cd ..
npm run dev          # starts backend (3001) + frontend (5173)
```

Open http://localhost:5173

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

### Vite proxy not forwarding to backend
- Ensure `backend/server.js` is running on port 3001 before starting Vite. Check `vite.config.js` proxy target.

### Photos not loading
- qasa photo URLs may be signed/time-limited CDN URLs. Nothing to do — re-scrape the listing to refresh them.

---

## Updating This File

Add a dated entry for any non-obvious decision, workaround, or discovered quirk:

```
### YYYY-MM-DD — <topic>
<description>
```
