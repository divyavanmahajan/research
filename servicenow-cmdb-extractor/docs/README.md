# sn-cmdb-extractor

A browser-based CLI tool that extracts your ServiceNow CMDB structure into a
local SQLite database — **no API credentials, no admin access required**.

The tool opens a Chromium browser (via Playwright), lets you log in once
(supporting SSO, MFA, and any web-based auth flow), then re-uses the saved
session to silently download data from any CMDB table via ServiceNow's REST
Table API.

---

## Features

| Feature | Details |
|---|---|
| **Browser-based auth** | Logs in via real browser — works with SSO, Okta, Azure AD, MFA |
| **Session persistence** | Login once; headless reuse in all subsequent runs |
| **Credential fallback** | Automate username/password for basic-auth instances |
| **All or single table** | Download one table or every `cmdb_*` table |
| **Dynamic discovery** | Enumerates the instance's actual CMDB tables via `sys_db_object` |
| **Paging** | Handles arbitrarily large tables with automatic offset paging |
| **Resume / incremental** | Interrupted downloads pick up from the last offset |
| **Force refresh** | Re-download any table from scratch with `--force-refresh` |
| **Rich progress bars** | Live per-table and per-page progress during extraction |
| **SQLite output** | Local, portable, queryable database — use any SQL tool |
| **JSON / CSV export** | Export any table to JSON or CSV from the CLI |
| **Mermaid diagrams** | Auto-generate inheritance and reference ER diagrams |
| **LLM-friendly CLI** | Every command is fully self-documented via `--help` |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.11 |
| Playwright | ≥ 1.44 |
| ServiceNow access | Any role that can read CMDB tables (itil or admin) |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/servicenow-cmdb-extractor.git
cd servicenow-cmdb-extractor

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Install Playwright's Chromium browser
playwright install chromium
```

---

## Quick Start

```bash
# Step 1 — Log in (opens a visible browser; supports SSO / MFA)
sn-cmdb login --instance https://dev12345.service-now.com

# Step 2 — Download all core CMDB tables
sn-cmdb download all --instance https://dev12345.service-now.com

# Step 3 — Check what was downloaded
sn-cmdb status

# Step 4 — Generate Mermaid diagrams
sn-cmdb diagram

# Step 5 — Query the data
sn-cmdb db query "SELECT name, sys_class_name FROM cmdb_ci LIMIT 20"
```

---

## Usage

### Login

```bash
# Interactive login (SSO / MFA friendly) — opens a visible browser
sn-cmdb login --instance https://dev.service-now.com

# Credential-based login (basic auth only)
sn-cmdb login --instance https://dev.service-now.com \
    --mode credentials --username admin --password secret

# Auto mode: validate saved session, open browser if expired (default)
sn-cmdb login --instance https://dev.service-now.com --mode auto
```

### Download

```bash
# Single table
sn-cmdb download table cmdb_ci_server --instance https://dev.service-now.com

# Single table — select specific fields only
sn-cmdb download table cmdb_ci \
    --fields sys_id,name,sys_class_name,operational_status \
    --instance https://dev.service-now.com

# All core CMDB tables
sn-cmdb download all --instance https://dev.service-now.com

# All tables discovered dynamically from the instance
sn-cmdb download all --discover --instance https://dev.service-now.com

# Re-download a table from scratch (purges existing rows)
sn-cmdb download table cmdb_ci_server --force-refresh \
    --instance https://dev.service-now.com
```

### Status & Reset

```bash
# Show all tables and their download state
sn-cmdb status

# Show only incomplete / failed tables
sn-cmdb status --hide-complete

# Reset a table's state (next download will resume from 0)
sn-cmdb reset cmdb_ci_server

# Reset ALL tables
sn-cmdb reset --yes
```

### Export

```bash
# Export a table to JSON
sn-cmdb export cmdb_ci_server

# Export to CSV
sn-cmdb export cmdb_ci_server --format csv --output servers.csv

# Export with row limit
sn-cmdb export cmdb_ci --limit 1000 --format json
```

### Diagrams

```bash
# Generate all diagrams (inheritance, reference, combined, report)
sn-cmdb diagram

# Only the class inheritance diagram
sn-cmdb diagram --kind inheritance

# Write to a custom directory
sn-cmdb diagram --output-dir ./my-diagrams

# Full Markdown report with embedded diagrams
sn-cmdb diagram --kind report
```

### Database inspection

```bash
# Database stats and per-table row counts
sn-cmdb db info

# Ad-hoc SQL query
sn-cmdb db query "SELECT name, sys_class_name, operational_status FROM cmdb_ci LIMIT 10"

# JSON output
sn-cmdb db query "SELECT count(*) as total FROM cmdb_ci_server" --json

# Use a different database file
sn-cmdb db info --db /path/to/other.db
```

### Session management

```bash
# Check if a saved session exists
sn-cmdb session status --instance https://dev.service-now.com

# Validate that the session is still active (opens headless browser)
sn-cmdb session status --instance https://dev.service-now.com --validate

# Delete the saved session
sn-cmdb logout --instance https://dev.service-now.com
```

---

## Configuration via Environment Variables

All CLI flags can be set as environment variables (or in a `.env` file):

```bash
export SN_CMDB_INSTANCE_URL=https://dev12345.service-now.com
export SN_CMDB_DB_PATH=./my_cmdb.db
export SN_CMDB_PAGE_SIZE=2000
export SN_CMDB_HEADLESS=true
export SN_CMDB_USERNAME=admin
export SN_CMDB_PASSWORD=secret
export SN_CMDB_SESSION_DIR=~/.sn_cmdb/sessions
export SN_CMDB_LOG_LEVEL=DEBUG
```

Then simply run:

```bash
sn-cmdb download all
```

---

## Output Files

| File | Description |
|---|---|
| `cmdb.db` | SQLite database with all downloaded data |
| `~/.sn_cmdb/sessions/<hostname>.json` | Saved browser session (sensitive — 600 permissions) |
| `cmdb_inheritance.mmd` | Mermaid class hierarchy diagram |
| `cmdb_references.mmd` | Mermaid reference/FK diagram |
| `cmdb_overview.mmd` | Mermaid overview of populated tables |
| `cmdb_report.md` | Markdown report embedding all diagrams |

---

## LLM Usage Guide

This CLI is designed to be fully discoverable by an LLM without human supervision:

```bash
# Discover all top-level commands
sn-cmdb --help

# Explore a sub-command group
sn-cmdb download --help
sn-cmdb session --help
sn-cmdb db --help
sn-cmdb tables --help

# Get full details on any command
sn-cmdb login --help
sn-cmdb download table --help
sn-cmdb diagram --help
```

All commands accept `--verbose` / `-v` for debug logging.
