# Apartment Finder

A personal web app for tracking Swedish apartment listings from [qasa.se](https://qasa.se).

## Features

- **My List** — card grid of saved apartments with priority tiers (Must see / Nice / Skip), status tracking, and personal notes
- **Investigate** — paste a qasa.se URL or run a search; preview results and add them to your list
- **Map** — all saved apartments as color-coded pins on an OpenStreetMap map
- **Export / Import** — backup your list to JSON and restore it

Data is stored locally in your browser (IndexedDB). Nothing leaves your machine.

## Getting started

```bash
# From repo root
cd apartment-finder

# Install all dependencies (first time only)
npm run install:all

# Start backend (port 3001) + frontend (port 5173)
npm run dev
```

Open **http://localhost:5173**

## Running tests

```bash
npm test            # runs backend + frontend in parallel
npm run test:backend
npm run test:frontend
```

## Production build

```bash
npm run build       # builds frontend into frontend/dist/
npm start           # Express serves the built app on port 3001
```

Open **http://localhost:3001**

## Project structure

```
apartment-finder/
├── backend/
│   ├── server.js            # Express API (scrape + search)
│   └── scrapers/qasa.js     # qasa.se scraper
└── frontend/
    └── src/
        ├── db.js             # IndexedDB wrapper
        ├── views/            # ListView, DetailView, InvestigateView, MapView
        └── components/       # ApartmentCard, PriorityPicker, StatusStepper, …
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Routing | React Router v6 |
| Storage | IndexedDB (idb) |
| Map | Leaflet + react-leaflet + OpenStreetMap |
| Backend | Node.js + Express |
| Scraping | axios + cheerio (`__NEXT_DATA__` JSON blob) |
| Tests | Jest + Supertest (backend) · Vitest + Testing Library (frontend) |
