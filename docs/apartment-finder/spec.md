# Apartment Finder — Product Specification

**Version:** 1.0
**Date:** 2026-04-18
**Branch:** `claude/apartment-finder-app-KBkPR`

---

## Overview

A personal web application for tracking Swedish apartment listings. The user can search or import listings from qasa.se, annotate them with personal notes and a priority tier, view them on a map, and maintain a persistent local list with JSON backup/restore.

---

## User Goals

1. Never lose track of an interesting listing
2. Record personal impressions and next steps for each apartment
3. Visually compare apartment locations on a map
4. Quickly triage listings into Must see / Nice / Skip

---

## Views

### 1. My List (Home)

Default landing page showing all saved apartments.

| Element | Detail |
|---|---|
| Layout | Card grid (default) or sortable table |
| Columns/fields | Thumbnail · Address · Price/month · Size (m²) · Rooms · Priority · Status · Date added |
| Filters | Priority tier (all / Must see / Nice / Skip), Status |
| Sort | Price · Size · Date added · Priority |
| Empty state | Prompt to open Investigate mode |

### 2. Apartment Detail

Opens when a card is clicked.

| Section | Content |
|---|---|
| Gallery | Scraped photos, horizontal scroll |
| Key facts | Price, deposit, size, rooms, floor, available from |
| Map | Leaflet map, single geocoded pin, OpenStreetMap tiles |
| Priority | Must see / Nice / Skip selector (pill buttons) |
| Status | New → Contacted → Viewing scheduled → Applied → Rejected |
| Notes | Auto-saving textarea for personal comments |
| Actions | Open on qasa.se · Delete from list |

### 3. Investigate Mode

Two tabs:

**Search tab**
- Fields: City/area, min/max price, min/max size (m²), number of rooms
- Submits to backend → backend scrapes qasa.se search results
- Results shown as cards: photo, address, price, size, rooms
- Each card has "Add to My List" button (disabled if already added)

**URL tab**
- Paste a qasa.se listing URL
- Backend scrapes it, returns structured data
- Preview card shown before adding
- "Add to My List" button

### 4. Map View

- All saved apartments rendered as Leaflet markers
- Marker color by priority: green (Must see), amber (Nice), gray (Skip/unranked)
- Click marker → popup with thumbnail, address, price, priority badge, "Open detail" link
- Fits bounds to all markers on load

### 5. Export / Import

- **Export:** Downloads `apartments-<date>.json` with all records
- **Import:** Upload a JSON file; choose Merge (keep existing, add new) or Replace (overwrite all)

---

## Data Model

```ts
interface Apartment {
  id: string;                // UUID v4
  sourceUrl: string;         // Original qasa.se URL
  addedAt: string;           // ISO 8601
  updatedAt: string;         // ISO 8601

  // Scraped fields
  title: string;
  address: string;
  city: string;
  lat: number | null;
  lng: number | null;
  price: number;             // SEK/month
  deposit: number | null;    // SEK
  size: number;              // m²
  rooms: number;
  floor: string | null;
  availableFrom: string | null;
  photos: string[];          // absolute URLs
  description: string;

  // User fields
  priority: 'must_see' | 'nice' | 'skip' | 'unranked';
  status: 'new' | 'contacted' | 'viewing' | 'applied' | 'rejected';
  notes: string;
}
```

---

## Non-Goals (v1)

- User accounts or cloud sync
- Notifications or reminders
- Support for sites other than qasa.se
- Mobile native app
