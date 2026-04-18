# Apartment Finder — User Guide

> **Version:** 1.0 · 2026-04-19

---

## What is this app?

Apartment Finder is a personal research tool for browsing and tracking apartments on [Qasa.com](https://qasa.com). It lets you:

- Search for apartments using detailed filters
- Save interesting listings to your personal list
- Tag and comment on each listing so you remember your thoughts
- See all your saved apartments on a map
- Export and import your data

**Your data stays in your browser** — nothing is sent to any cloud service.

---

## Getting Started

1. Start the backend (see `docs/developer.md`)
2. Start the frontend (`npm run dev` in the `frontend/` folder)
3. Open **http://localhost:5173** in your browser

---

## The Layout

The screen is split into two panels:

```
┌────────────────────────┬────────────────────────────────────────┐
│   LEFT PANEL (tabs)    │          MAP (always visible)          │
│                        │                                        │
│  My List | Search |    │   [OpenStreetMap with apartment pins]  │
│  Saved Searches        │                                        │
│                        │                                        │
└────────────────────────┴────────────────────────────────────────┘
```

The map is always visible. As you switch between tabs, the map updates its pins to show relevant apartments.

---

## Adding an Apartment

### Option A — Paste a Qasa URL

1. Find an apartment on [qasa.com](https://qasa.com) that you like.
2. Copy the URL from your browser address bar. It looks like:
   `https://qasa.com/se/en/home/1348599`
3. In the app, paste it into the **"Add by URL"** field at the top of the left panel.
4. Press **Add** (or hit Enter).
5. The apartment is fetched and added to your **My List** tab. A pin appears on the map immediately.

### Option B — Search and Browse

1. Go to the **Search** tab.
2. Set your filters (city, rooms, rent, etc.) — see [Search Filters](#search-filters) below.
3. Click **Search**. All matching Qasa listings load (this may take a few seconds for large result sets).
4. Results appear in the list and as **orange pins** on the map.
5. Click any result or pin to preview it.
6. Click **Add to my list** to save it.

---

## Search Filters

| Filter | What it does |
|--------|-------------|
| **City** | Choose the area to search. Default: Gothenburg. Options: Gothenburg, Stockholm, Malmö, Oslo, Helsinki |
| **Min / Max Rooms** | Minimum and maximum room count (Swedish counting: 2 rooms = 1 bedroom + living room) |
| **Min / Max Rent** | Monthly rent range in the selected currency |
| **Min / Max Size** | Apartment size in m² |
| **Currency** | SEK (default), EUR, NOK, HUF |
| **Furnished** | Filter for furnished only |
| **Pets Allowed** | Filter for pet-friendly listings |
| **Home Type** | Apartment, House, or Room |
| **First Hand** | First-hand (hyresrätt) contracts only |
| **Student** | Student housing only |
| **Senior** | Senior housing only |
| **Corporate** | Corporate listings only |
| **Sort By** | Newest first, Oldest first, Cheapest first, Most expensive first |

---

## Saving a Search

If you have filters you use regularly (e.g. "Gothenburg, 2+ rooms, max 12,000 SEK"):

1. Set up your filters in the **Search** tab.
2. Click **Save Search**.
3. Give it a name (e.g. "Gothenburg budget").
4. It appears in the **Saved Searches** tab.

To re-run a saved search: click on its name. The filters load and the search runs automatically.

To delete a saved search: click the **×** next to its name.

---

## Managing Your Saved Apartments

### Viewing your list

Click the **My List** tab. Each row shows:
- Thumbnail photo
- Address (street + city)
- Rent per month
- Your tags
- Number of comments

Click any row to open the **Detail Drawer** on the right side.

### Tagging

In the detail drawer, the **Tags** field lets you add any label you want:

- Type a tag and press Enter (or comma) to add it.
- Suggestions appear as you type: `interested`, `applied`, `rejected`, `visited`, `not interested`, `favourite`.
- Add as many tags as you like.
- Click the **×** on a tag chip to remove it.

**Map pin colours** change based on your first tag:

| Tag | Pin Colour |
|-----|-----------|
| `interested` | 🟢 Green |
| `favourite` | 🟡 Amber |
| `applied` | 🔵 Blue |
| `visited` | 🟣 Purple |
| `rejected` / `not interested` | 🔴 Red |
| Any other / none | ⚫ Grey |

### Commenting

In the detail drawer, the **Comments** section lets you keep a diary:

1. Type your note in the text box.
2. Click **Add Comment** (or press Ctrl+Enter).
3. Your comment is saved with the current date and time.
4. Comments are shown newest-first.
5. Click the **trash** icon to delete a comment.

### Removing an apartment

In the detail drawer, click **Remove from list**. A confirmation dialog appears. Once confirmed, the listing is removed from your list and the map.

---

## The Map

- **Coloured solid pins** = your saved apartments (colour by tag, see above)
- **Orange outline circles** = search results (not yet saved)
- **Click any pin** = open the detail drawer for that apartment
- The map auto-zooms to fit all visible pins when you switch tabs

---

## Exporting Your Data

Click the **Export** button in the top bar.

A file named `apartment-finder-export-2026-04-19.json` will download. It contains all your saved apartments, tags, comments, and saved searches.

---

## Importing Data

Click the **Import** button in the top bar and select a previously exported `.json` file.

You will be asked whether to:
- **Merge** — add imported apartments to your existing list (apartments already in your list are kept as-is)
- **Replace** — replace your entire list with the imported data

A summary shows how many apartments were imported and how many already existed.

---

## Tips

- **Your data is local** — if you clear your browser's storage or use a different browser, your list will be gone. Use **Export** regularly as a backup.
- **Adding an already-saved apartment** — you'll see a warning "Already in your list". No duplicate is created.
- **Large searches** — searching Gothenburg with minimal filters can return 600+ results. The app loads them all. Give it 5–10 seconds.
- **Sharing** — export your JSON and send it to someone else. They can import it into their own instance of the app.
