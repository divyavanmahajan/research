# Changelog

## v0.1.1 — 2026-04-21

### Fixed

- **Export modal hidden behind map** — All modal dialogs (HTML export, import confirm, delete confirm) are now rendered via React Portal directly under `<body>`, ensuring they always appear above the Leaflet map regardless of CSS stacking context.
- **Search field default** — The area field now defaults to `se/gothenburg` and the placeholder shows the required `country-code/city` format (e.g. `se/stockholm`, `no/oslo`). Previously the default `stockholm` did not resolve on Qasa.

### Added

- README with full feature guide, area identifier reference table, and development setup instructions.

---

## v0.1.0 — 2026-04-21

Initial release.

- Search Qasa listings by city, rent, rooms, size, and other filters.
- Add listings by pasting a Qasa URL directly.
- Save, tag, and annotate apartments with timestamped notes.
- Interactive map (Leaflet + OpenStreetMap) with colour-coded pins per tag.
- Commute times via Google Maps for up to several destinations, all four transport modes (drive, transit, walk, cycle).
- HTML export — self-contained shareable report with summary table and per-apartment sections.
- JSON backup and restore (merge or replace).
- Save and re-run named search presets.
- Dark mode following system appearance.
- All data stored locally in browser localStorage — nothing sent to external servers except Qasa (listing data) and Google Maps (commute times).
