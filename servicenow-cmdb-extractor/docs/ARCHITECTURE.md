# Architecture — sn-cmdb-extractor

## Overview

The tool extracts CMDB data from ServiceNow by injecting JavaScript `fetch()`
calls into an authenticated Chromium browser page.  This approach avoids the
need for separate REST API credentials — the browser's own session cookies
authenticate every request.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         User / LLM                                   │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  CLI commands
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  cli.py   (Typer CLI)                                                │
│  • login / logout / session status                                   │
│  • download table / download all                                     │
│  • status / reset / export / diagram                                 │
│  • db info / db query                                                │
└──────┬────────────┬──────────────┬───────────────────────────────────┘
       │            │              │
       ▼            ▼              ▼
┌──────────┐ ┌──────────┐  ┌──────────────┐
│browser.py│ │extractor │  │  diagram.py  │
│          │ │  .py     │  │  schema.py   │
│Playwright│ │          │  │              │
│session   │ │JS fetch()│  │Mermaid gen.  │
│mgmt      │ │+ paging  │  │schema disco. │
└────┬─────┘ └────┬─────┘  └──────┬───────┘
     │            │               │
     └────────────┴───────────────┘
                  │
                  ▼
         ┌────────────────┐
         │    db.py       │
         │  SQLite        │
         │  + state table │
         └────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   cmdb.db      │
         │  (SQLite file) │
         └────────────────┘
```

---

## Components

### `cli.py` — Command Interface

- Built with [Typer](https://typer.tiangolo.com/) for automatic `--help` generation.
- Every command, argument, and option has a docstring used in help text.
- Commands are grouped into sub-apps: `session`, `tables`, `download`, `db`.
- The `_run_with_browser()` helper opens the database and browser context, builds
  an `Extractor`, then calls an `action(ctx)` callback — keeping browser lifecycle
  management centralised.

### `browser.py` — Session Management

- Wraps Playwright's `BrowserContext.storage_state()` / `storageState` for
  session persistence.
- **Interactive login**: opens a visible browser, polls for post-login URL
  patterns and the `glide_user_activity` cookie.
- **Credential login**: fills `#user_name` / `#user_password` and clicks
  `#sysverb_login` — only works for basic-auth instances.
- **Session file**: stored at `~/.sn_cmdb/sessions/<hostname>.json` with
  `chmod 600` permissions.
- **Validation**: loads the session in a headless browser and calls a lightweight
  API endpoint to check if the session is still accepted.
- `active_page()` is a context manager that yields an authenticated `Page`
  and saves updated cookies on exit.

### `extractor.py` — Data Extraction Engine

- Builds Table API URLs with `sysparm_limit` / `sysparm_offset` for paging.
- Injects the `_JS_FETCH_PAGE` snippet via `page.evaluate()` — this runs in
  the browser process, so all cookies are automatically included.
- Reads `X-Total-Count` response header for accurate progress bars.
- On the first page of each table, discovers the field list and creates/updates
  the SQLite table schema.
- After each page, persists `last_offset` + `downloaded` to `_download_state`
  — so any crash can be resumed from the last committed offset.
- Uses [Rich Progress](https://rich.readthedocs.io/en/stable/progress.html) for
  per-table and per-page live progress display.

### `schema.py` — Schema Discovery

- Downloads `sys_db_object` (table catalogue) to find all `cmdb_*` tables.
- Downloads `sys_dictionary` slices for field metadata (type, reference target).
- `build_relationship_map()` resolves `super_class` sys_id references to table
  names, producing the inheritance map used by the diagram generator.
- `get_reference_fields()` returns all `Reference`-type fields, used for FK
  edges in the ER diagram.

### `db.py` — SQLite Layer

- Synchronous `sqlite3` wrapper (keeps things simple; browser I/O is the bottleneck).
- `_download_state` metadata table tracks per-table status, offsets, timestamps,
  and the last known field list.
- `ensure_data_table()` creates a data table on first use and `ALTER TABLE … ADD COLUMN`
  for any new fields discovered in subsequent pages.
- `upsert_rows()` uses `INSERT OR REPLACE` with `sys_id` as the primary key,
  making repeated downloads idempotent.
- Nested dict/list values from the API are stored as JSON strings.

### `diagram.py` — Mermaid Generator

- Reads inheritance and reference data from the local SQLite database
  (no live instance needed).
- Produces three `.mmd` files and one `.md` report.
- Limits diagram nodes to keep Mermaid rendering fast.

### `config.py` — Configuration

- Pydantic `BaseModel` reads from environment variables (prefix `SN_CMDB_`).
- `.env` file support via `python-dotenv`.
- Default paths: `~/.sn_cmdb/sessions/` for sessions, `./cmdb.db` for data.

---

## Data Flow

```
Login (interactive / credential)
  └─► Save storageState JSON → ~/.sn_cmdb/sessions/<host>.json

Download run
  ├─► Open DB (create if new)
  ├─► Load storageState into Playwright context
  ├─► Navigate to instance home (establishes cookie context)
  └─► For each table:
        ├─► Check _download_state: resume offset or start from 0
        ├─► Page loop:
        │     ├─► page.evaluate(fetch /api/now/table/<table>?offset=N)
        │     ├─► Parse JSON result + X-Total-Count header
        │     ├─► ensure_data_table() — create/extend SQLite schema
        │     ├─► upsert_rows() — INSERT OR REPLACE
        │     ├─► Update _download_state (offset, count)
        │     └─► Repeat until last page
        └─► Mark _download_state.status = 'complete'
```

---

## Database Schema

### `_download_state` (metadata)

| Column | Type | Description |
|---|---|---|
| `table_name` | TEXT PK | ServiceNow table name |
| `status` | TEXT | pending / in_progress / complete / failed |
| `total_records` | INTEGER | Total count from X-Total-Count (-1 if unknown) |
| `downloaded` | INTEGER | Rows written so far |
| `last_offset` | INTEGER | Last page offset (resume point) |
| `started_at` | TEXT | ISO-8601 timestamp |
| `completed_at` | TEXT | ISO-8601 timestamp |
| `error_message` | TEXT | Last error (if failed) |
| `instance_url` | TEXT | Source instance |
| `fields_json` | TEXT | JSON array of field names |

### `_instance_info` (key-value metadata)

### Data tables (one per downloaded ServiceNow table)

- Dynamically created based on fields returned by the API.
- `sys_id TEXT PRIMARY KEY` always present.
- All other columns are `TEXT`.
- Nested objects / arrays serialised to JSON strings.

---

## Paging Strategy

ServiceNow Table API supports:

```
GET /api/now/table/<table>?sysparm_limit=1000&sysparm_offset=0
```

Response headers include `X-Total-Count` with the total record count.
The tool pages until fewer records than `sysparm_limit` are returned (last page).

Default page size: 1000 records.  Max: 10,000.  Configurable via `--page-size`
or `SN_CMDB_PAGE_SIZE`.

---

## Session Security

- Session files are stored with `chmod 600` (owner read/write only).
- Session files contain ServiceNow session cookies — treat them as passwords.
- `.gitignore` should include `~/.sn_cmdb/` and any local `.json` session files.
- To revoke a session: `sn-cmdb logout --instance <url>` or delete the JSON file.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| HTTP 401 | Raises `ExtractorError` with "run sn-cmdb login" message |
| HTTP 403 | Raises `ExtractorError` with role hint |
| Network error | Retries up to 3 times with exponential back-off |
| Crash mid-table | State saved; next run resumes from last offset |
| Invalid SQL in db query | `sqlite3.Error` caught, message printed |
