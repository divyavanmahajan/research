# CLAUDE.md — sn-cmdb-extractor

This file gives an LLM (Claude or similar) everything it needs to understand,
use, and extend this project without human supervision.

---

## What this tool does

`sn-cmdb-extractor` downloads the CMDB (Configuration Management Database)
structure from a ServiceNow instance into a local SQLite database, using only
a browser session for authentication.

- **No REST API credentials needed** — the tool injects `fetch()` calls into
  an authenticated Playwright browser page.
- Supports any auth method the browser supports: SSO, Okta, Azure AD, MFA.
- Handles paging, resume, incremental refresh, and live progress display.
- Generates Mermaid ER / class diagrams from the extracted data.

---

## CLI Discovery

Run these commands to fully understand all features:

```bash
sn-cmdb --help                          # top-level command list
sn-cmdb login --help
sn-cmdb logout --help
sn-cmdb session status --help
sn-cmdb tables list --help
sn-cmdb download --help
sn-cmdb download table --help
sn-cmdb download all --help
sn-cmdb status --help
sn-cmdb reset --help
sn-cmdb export --help
sn-cmdb diagram --help
sn-cmdb db --help
sn-cmdb db info --help
sn-cmdb db query --help
```

---

## Typical Workflow (for an LLM to orchestrate)

```bash
# 1. Authenticate (opens visible browser — user must log in manually)
sn-cmdb login --instance https://dev12345.service-now.com

# 2. Download all core CMDB tables (headless, uses saved session)
sn-cmdb download all --instance https://dev12345.service-now.com

# OR: Discover and download ALL cmdb_* tables on the instance
sn-cmdb download all --discover --instance https://dev12345.service-now.com

# 3. Check progress
sn-cmdb status

# 4. Generate diagrams
sn-cmdb diagram

# 5. Query the data
sn-cmdb db query "SELECT name, sys_class_name, operational_status FROM cmdb_ci LIMIT 20"

# 6. Export a table for further analysis
sn-cmdb export cmdb_ci_server --format csv
```

---

## Environment Variables

Set these to avoid repeating flags on every command:

```bash
export SN_CMDB_INSTANCE_URL=https://dev12345.service-now.com
export SN_CMDB_DB_PATH=./cmdb.db
export SN_CMDB_PAGE_SIZE=1000
export SN_CMDB_HEADLESS=true
```

Or put them in a `.env` file in the working directory.

---

## Key Files

| File | Purpose |
|---|---|
| `src/sn_cmdb/cli.py` | All CLI commands — start here |
| `src/sn_cmdb/browser.py` | Playwright session management |
| `src/sn_cmdb/extractor.py` | Table download + paging engine |
| `src/sn_cmdb/schema.py` | Dynamic table/field discovery |
| `src/sn_cmdb/diagram.py` | Mermaid diagram generation |
| `src/sn_cmdb/db.py` | SQLite layer + download state |
| `src/sn_cmdb/config.py` | Settings + core table list |
| `docs/ARCHITECTURE.md` | System design + data flow |
| `docs/DEVELOPER.md` | How to extend the tool |

---

## Database Structure

The SQLite database (`cmdb.db` by default) contains:

- `_download_state` — tracks status/offset/count for every table
- `_instance_info` — key-value metadata (e.g. instance URL)
- One data table per downloaded ServiceNow table

Useful queries:

```sql
-- See all tables and their row counts
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '\_%' ESCAPE '\';

-- See download progress
SELECT table_name, status, downloaded, total_records FROM _download_state;

-- Count CIs by class
SELECT sys_class_name, count(*) as cnt FROM cmdb_ci GROUP BY sys_class_name ORDER BY cnt DESC;

-- Find servers
SELECT name, ip_address, os FROM cmdb_ci_server LIMIT 20;

-- Find relationships
SELECT parent, type, child FROM cmdb_rel_ci LIMIT 20;
```

---

## Adding a New Table Download

No code changes needed — just pass the table name:

```bash
sn-cmdb download table <any_servicenow_table_name> \
    --instance https://dev.service-now.com
```

---

## How Authentication Works

1. `sn-cmdb login` opens a visible Chromium browser.
2. User logs in (any method: SSO, MFA, etc.).
3. Tool detects post-login URL pattern and saves `storageState` (cookies +
   localStorage) to `~/.sn_cmdb/sessions/<hostname>.json`.
4. All subsequent commands load this file into a new Playwright context,
   giving headless access without re-authentication.
5. `sn-cmdb session status --validate` checks whether the session is still valid.

---

## How Extraction Works

1. Browser navigates to the instance home to establish cookie context.
2. For each table, the tool builds a URL:
   `/api/now/table/<table>?sysparm_limit=1000&sysparm_offset=<N>`
3. A `fetch()` snippet is injected via `page.evaluate()` — the browser
   sends it with all session cookies automatically.
4. Response JSON is parsed; `X-Total-Count` header gives the total.
5. Rows are upserted into SQLite with `sys_id` as primary key.
6. Offset is saved after each page — crashes are safely resumable.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `No saved session found` | Run `sn-cmdb login --instance <url>` |
| `Session expired (HTTP 401)` | Run `sn-cmdb login --instance <url>` again |
| `Access denied (HTTP 403)` | User needs `itil` or `admin` role on the instance |
| Browser doesn't open | Ensure `playwright install chromium` was run |
| Download stalls | Check `sn-cmdb status`; use `--force-refresh` to restart |
| Diagram is empty | Run `sn-cmdb download all` first to populate the DB |
