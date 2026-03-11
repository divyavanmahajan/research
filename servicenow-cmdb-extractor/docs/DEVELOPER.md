# Developer Guide — sn-cmdb-extractor

## Prerequisites

- Python 3.11+
- `git`
- A ServiceNow developer instance (free at https://developer.servicenow.com)

---

## Setup

```bash
git clone https://github.com/your-org/servicenow-cmdb-extractor.git
cd servicenow-cmdb-extractor

python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev extras
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

---

## Project Layout

```
servicenow-cmdb-extractor/
├── src/
│   └── sn_cmdb/
│       ├── __init__.py      # version
│       ├── cli.py           # Typer CLI (entry point: sn-cmdb)
│       ├── browser.py       # Playwright session management
│       ├── extractor.py     # Data extraction + paging
│       ├── schema.py        # Table/field discovery
│       ├── diagram.py       # Mermaid diagram generation
│       ├── db.py            # SQLite layer
│       └── config.py        # Pydantic settings + constants
├── tests/
│   ├── test_db.py
│   ├── test_extractor.py
│   └── test_diagram.py
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPER.md         # ← you are here
│   └── CLAUDE.md
├── pyproject.toml
└── requirements.txt
```

---

## Running Tests

```bash
# Run all tests
pytest

# With verbose output
pytest -v

# A single test file
pytest tests/test_db.py

# With coverage
pytest --cov=sn_cmdb --cov-report=term-missing
```

Tests use `pytest-asyncio` but the core code is synchronous — async fixtures are
only needed for any future async helpers.

---

## Code Style

```bash
# Lint + auto-fix
ruff check src/ tests/ --fix

# Type checking
mypy src/sn_cmdb/
```

Line length: 100.  Configured in `pyproject.toml`.

---

## Adding a New CLI Command

1. Open `src/sn_cmdb/cli.py`.
2. Pick the right sub-app (`app`, `session_app`, `tables_app`, `download_app`, `db_app`).
3. Add a `@<sub_app>.command("<name>")` decorated function.
4. Write a detailed docstring — it becomes the `--help` text.
5. Use `typer.Option` / `typer.Argument` with explicit `help=` strings.
6. If the command needs a live browser, call `_run_with_browser(action=...)`.

Example skeleton:

```python
@app.command("my-command")
def cmd_my_command(
    some_arg: str = typer.Argument(..., help="What this argument does."),
    db_path: Path = typer.Option(Path("cmdb.db"), "--db", envvar="SN_CMDB_DB_PATH"),
) -> None:
    """
    One-line summary.

    Longer description explaining what the command does, when to use it,
    and any important caveats.

    Examples:
        sn-cmdb my-command foo
        sn-cmdb my-command bar --db /path/to.db
    """
    ...
```

---

## Adding Support for a New Table

The tool downloads any ServiceNow table by name — no code changes required.
The schema is discovered dynamically from the first API response page.

To add a table to the default "core" list downloaded by `sn-cmdb download all`:

```python
# src/sn_cmdb/config.py
CORE_CMDB_TABLES: list[str] = [
    ...
    "my_custom_cmdb_table",   # ← add here
]
```

---

## Extending the Diagram Generator

`diagram.py` contains three public methods:

- `write_inheritance_diagram(path)` — `classDiagram`
- `write_reference_diagram(path)` — `erDiagram`
- `write_combined_diagram(path)` — `classDiagram` (populated tables only)

To add a new diagram type:

1. Add a method `write_my_diagram(path: Path) -> Path` to `DiagramGenerator`.
2. Add a new `kind` value in `cmd_diagram()` in `cli.py`.
3. Call your method in the `if kind in (...)` block.

---

## Browser Session Internals

Playwright's `context.storage_state()` returns a dict containing:

```json
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://dev12345.service-now.com",
      "localStorage": [...]
    }
  ]
}
```

This is saved to `~/.sn_cmdb/sessions/<hostname>.json` and loaded via
`browser.new_context(storage_state=...)`.

To debug session issues:

```bash
# Run in visible mode to watch what the browser does
sn-cmdb download table cmdb_ci --visible --verbose \
    --instance https://dev.service-now.com
```

---

## Debugging the REST API Calls

The JavaScript injected into the browser:

```javascript
async (url) => {
    const resp = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Accept': 'application/json',
            'X-UserToken': window.g_ck || '',
        }
    });
    ...
}
```

`window.g_ck` is ServiceNow's CSRF token automatically available on all SN pages.

To inspect raw API responses, open the browser developer tools while running
in `--visible` mode, or add a `console.log` inside the JS snippet in
`extractor.py:_JS_FETCH_PAGE`.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `SN_CMDB_INSTANCE_URL` | — | Instance base URL (required for most commands) |
| `SN_CMDB_SESSION_DIR` | `~/.sn_cmdb/sessions` | Where session JSON files are stored |
| `SN_CMDB_DB_PATH` | `./cmdb.db` | SQLite database path |
| `SN_CMDB_PAGE_SIZE` | `1000` | Records per API page (max 10000) |
| `SN_CMDB_USERNAME` | — | Username for credential login fallback |
| `SN_CMDB_PASSWORD` | — | Password for credential login fallback |
| `SN_CMDB_HEADLESS` | `false` | Browser headless mode |
| `SN_CMDB_LOG_LEVEL` | `INFO` | Logging level |

---

## Release Process

1. Update `__version__` in `src/sn_cmdb/__init__.py`.
2. Update `version` in `pyproject.toml`.
3. Run tests: `pytest`.
4. Commit: `git commit -m "chore: release vX.Y.Z"`.
5. Tag: `git tag vX.Y.Z`.
6. Build: `pip install build && python -m build`.
7. Publish: `twine upload dist/*`.
