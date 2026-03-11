"""
cli.py — Self-documenting Typer CLI for sn-cmdb-extractor.

Command tree:
  sn-cmdb                  Root group (shows version + help)
  ├── login                Authenticate and save browser session
  ├── logout               Delete saved session
  ├── session status       Show saved session details
  ├── tables list          List CMDB tables (discovered from instance or core list)
  ├── download table       Download a single named table
  ├── download all         Download all CMDB tables
  ├── status               Show download progress for all tables
  ├── reset                Reset download state (to re-download)
  ├── export               Export a table to JSON or CSV
  ├── diagram              Generate Mermaid diagram(s)
  ├── db info              Show database statistics
  └── db query             Run an arbitrary SQL query against the local DB

All commands accept --db / --instance / --headless / --verbose as global
options. All docstrings are intentionally detailed so an LLM can discover
every feature without running the tool.

LLM usage hint: run `sn-cmdb --help` then `sn-cmdb <command> --help` to
discover all available options. No configuration file is needed; all
settings can be passed as CLI flags or environment variables (SN_CMDB_*).
"""

from __future__ import annotations

import json
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from . import __version__
from .browser import SessionManager
from .config import CORE_CMDB_TABLES, AppConfig, load_config
from .db import Database, STATUS_COMPLETE, STATUS_FAILED, STATUS_IN_PROGRESS

console = Console()

# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="sn-cmdb",
    help=(
        "ServiceNow CMDB Extractor — download CMDB tables from a ServiceNow instance "
        "into a local SQLite database using only a browser session.\n\n"
        "[bold]LLM QUICK-START[/bold]\n"
        "  1. sn-cmdb login --instance https://dev12345.service-now.com\n"
        "  2. sn-cmdb download all --instance https://dev12345.service-now.com\n"
        "  3. sn-cmdb status\n"
        "  4. sn-cmdb diagram\n\n"
        "All settings can be set as environment variables (prefix SN_CMDB_).\n"
        "Run `sn-cmdb <command> --help` for detailed options."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

session_app = typer.Typer(
    help="Manage saved browser sessions.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
tables_app = typer.Typer(
    help="List and inspect available CMDB tables.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
download_app = typer.Typer(
    help="Download CMDB data from ServiceNow.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
db_app = typer.Typer(
    help="Inspect and query the local SQLite database.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

app.add_typer(session_app, name="session")
app.add_typer(tables_app, name="tables")
app.add_typer(download_app, name="download")
app.add_typer(db_app, name="db")


# ---------------------------------------------------------------------------
# Global callback — version flag
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sn-cmdb version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """ServiceNow CMDB Extractor."""


# ---------------------------------------------------------------------------
# Shared option factories
# ---------------------------------------------------------------------------

def _opt_instance() -> str | None:
    return typer.Option(
        None,
        "--instance",
        "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance base URL, e.g. https://dev12345.service-now.com",
        show_default=False,
    )

def _opt_db() -> Path:
    return typer.Option(
        Path("cmdb.db"),
        "--db",
        "-d",
        envvar="SN_CMDB_DB_PATH",
        help="Path to the SQLite database file.",
    )

def _opt_headless() -> bool:
    return typer.Option(
        False,
        "--headless/--visible",
        envvar="SN_CMDB_HEADLESS",
        help="Run browser headlessly (requires a saved session).",
    )

def _opt_verbose() -> bool:
    return typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable DEBUG logging.",
    )


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _require_instance(instance: str | None) -> str:
    if not instance:
        console.print(
            "[red]Error:[/red] --instance is required (or set SN_CMDB_INSTANCE_URL)."
        )
        raise typer.Exit(1)
    return instance.rstrip("/")


def _make_session_manager(
    instance: str, cfg: AppConfig, *, headless: bool
) -> SessionManager:
    return SessionManager(
        instance_url=instance,
        session_dir=cfg.session_dir,
        headless=headless,
    )


# ---------------------------------------------------------------------------
# login command
# ---------------------------------------------------------------------------

class LoginMode(str, Enum):
    interactive = "interactive"
    credentials = "credentials"
    auto = "auto"


@app.command("login")
def cmd_login(
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance URL.",
        show_default=False,
    ),
    mode: LoginMode = typer.Option(
        LoginMode.auto,
        "--mode", "-m",
        help=(
            "Login mode:\n\n"
            "  interactive — open a visible browser, user logs in manually "
            "(recommended for SSO/MFA)\n\n"
            "  credentials — automate username/password fields (basic auth only)\n\n"
            "  auto — try saved session first; if missing/expired, use interactive"
        ),
    ),
    username: Optional[str] = typer.Option(
        None,
        "--username", "-u",
        envvar="SN_CMDB_USERNAME",
        help="Username for credential-based login.",
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password", "-p",
        envvar="SN_CMDB_PASSWORD",
        help="Password for credential-based login.",
    ),
    session_dir: Optional[Path] = typer.Option(
        None,
        "--session-dir",
        envvar="SN_CMDB_SESSION_DIR",
        help="Directory to store browser session files.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG logging."),
) -> None:
    """
    Authenticate with ServiceNow and save the browser session.

    The saved session is stored as a JSON file under ~/.sn_cmdb/sessions/ (or
    --session-dir) and reused in subsequent commands, enabling headless operation.

    Login modes:
    - [bold]interactive[/bold]: Opens a visible browser. You log in manually (SSO, MFA, etc.).
      The tool detects when login completes and saves the session automatically.
    - [bold]credentials[/bold]: Automates username/password fields. Works for basic auth only.
    - [bold]auto[/bold] (default): Validates existing session; opens interactive login if needed.

    Examples:
        sn-cmdb login --instance https://dev12345.service-now.com
        sn-cmdb login --instance https://corp.service-now.com --mode credentials -u admin -p secret
    """
    _configure_logging(verbose)
    cfg = load_config()
    instance = _require_instance(instance)
    if session_dir:
        cfg.session_dir = session_dir

    mgr = _make_session_manager(instance, cfg, headless=False)

    if mode == LoginMode.auto:
        if mgr.session_exists():
            console.print("[cyan]Validating existing session…[/cyan]")
            if mgr.validate_session():
                console.print("[green]Session is valid — no login required.[/green]")
                return
            else:
                console.print("[yellow]Session expired — starting interactive login.[/yellow]")
        mode = LoginMode.interactive

    if mode == LoginMode.interactive:
        mgr.login_interactive()
    elif mode == LoginMode.credentials:
        if not username or not password:
            console.print(
                "[red]Error:[/red] --username and --password are required for credential login."
            )
            raise typer.Exit(1)
        ok = mgr.login_credentials(username, password)
        if not ok:
            raise typer.Exit(1)


# ---------------------------------------------------------------------------
# logout command
# ---------------------------------------------------------------------------

@app.command("logout")
def cmd_logout(
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance URL (used to locate the session file).",
    ),
    session_dir: Optional[Path] = typer.Option(
        None,
        "--session-dir",
        envvar="SN_CMDB_SESSION_DIR",
        help="Directory where session files are stored.",
    ),
) -> None:
    """
    Delete the saved browser session for an instance.

    This does NOT log out of the ServiceNow instance itself — it only removes
    the local session file. A new login will be required for the next extract.

    Example:
        sn-cmdb logout --instance https://dev12345.service-now.com
    """
    cfg = load_config()
    instance = _require_instance(instance)
    if session_dir:
        cfg.session_dir = session_dir
    mgr = _make_session_manager(instance, cfg, headless=False)
    mgr.delete_session()


# ---------------------------------------------------------------------------
# session status command
# ---------------------------------------------------------------------------

@session_app.command("status")
def cmd_session_status(
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance URL.",
    ),
    session_dir: Optional[Path] = typer.Option(
        None,
        "--session-dir",
        envvar="SN_CMDB_SESSION_DIR",
    ),
    validate: bool = typer.Option(
        False,
        "--validate",
        help="Actually open a headless browser to validate the session (slower).",
    ),
) -> None:
    """
    Show the status of the saved browser session.

    Without --validate, only checks that the session file exists.
    With --validate, opens a headless browser to verify the session is still
    accepted by ServiceNow.

    Example:
        sn-cmdb session status --instance https://dev12345.service-now.com --validate
    """
    cfg = load_config()
    instance = _require_instance(instance)
    if session_dir:
        cfg.session_dir = session_dir
    mgr = _make_session_manager(instance, cfg, headless=True)

    t = Table(title="Session Status")
    t.add_column("Property")
    t.add_column("Value")
    t.add_row("Instance", instance)
    t.add_row("Session file", str(mgr._session_file))
    t.add_row("Exists", "[green]yes[/green]" if mgr.session_exists() else "[red]no[/red]")

    if validate and mgr.session_exists():
        console.print("[cyan]Validating session (opening headless browser)…[/cyan]")
        valid = mgr.validate_session()
        t.add_row("Valid", "[green]yes[/green]" if valid else "[red]expired[/red]")

    console.print(t)


# ---------------------------------------------------------------------------
# tables list command
# ---------------------------------------------------------------------------

@tables_app.command("list")
def cmd_tables_list(
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance URL. If omitted, shows the built-in core table list.",
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
        help="SQLite database path.",
    ),
    discover: bool = typer.Option(
        False,
        "--discover",
        help=(
            "Dynamically discover CMDB tables from the live instance via sys_db_object. "
            "Requires a saved session and --instance."
        ),
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--visible",
        envvar="SN_CMDB_HEADLESS",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """
    List CMDB tables.

    Without --discover, prints the built-in core table list.
    With --discover, queries the live instance's sys_db_object to find all
    tables whose name starts with 'cmdb', including custom CI classes.

    Examples:
        sn-cmdb tables list
        sn-cmdb tables list --discover --instance https://dev12345.service-now.com
    """
    _configure_logging(verbose)

    if discover:
        instance = _require_instance(instance)
        cfg = load_config()
        _run_with_browser(
            instance=instance,
            cfg=cfg,
            db_path=db_path,
            headless=headless,
            action=_action_discover_tables,
        )
    else:
        t = Table(title="Core CMDB Tables (built-in list)")
        t.add_column("#", style="dim")
        t.add_column("Table Name")
        for i, tbl in enumerate(CORE_CMDB_TABLES, 1):
            t.add_row(str(i), tbl)
        console.print(t)
        console.print(
            f"\n[dim]{len(CORE_CMDB_TABLES)} tables. "
            "Use --discover to fetch the full list from a live instance.[/dim]"
        )


def _action_discover_tables(extractor_ctx: dict) -> None:
    from .schema import SchemaDiscovery
    sd = SchemaDiscovery(extractor_ctx["extractor"])
    tables = sd.discover_cmdb_tables()
    t = Table(title=f"CMDB Tables — {extractor_ctx['instance']}")
    t.add_column("#", style="dim")
    t.add_column("Table Name")
    for i, tbl in enumerate(tables, 1):
        t.add_row(str(i), tbl)
    console.print(t)
    console.print(f"\n[dim]{len(tables)} CMDB tables discovered.[/dim]")


# ---------------------------------------------------------------------------
# download table command
# ---------------------------------------------------------------------------

@download_app.command("table")
def cmd_download_table(
    table_name: str = typer.Argument(
        ...,
        help="ServiceNow table name to download, e.g. cmdb_ci_server",
    ),
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        help="ServiceNow instance URL.",
        show_default=False,
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    fields: Optional[str] = typer.Option(
        None,
        "--fields", "-f",
        help="Comma-separated list of fields to retrieve. Defaults to all fields.",
    ),
    page_size: int = typer.Option(
        1000,
        "--page-size",
        envvar="SN_CMDB_PAGE_SIZE",
        help="Records per API request (1–10000).",
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Ignore any saved progress and re-download from scratch.",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--visible",
        envvar="SN_CMDB_HEADLESS",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """
    Download a single ServiceNow table into the local SQLite database.

    Paging is handled automatically. If a previous download was interrupted,
    it resumes from the last saved offset unless --force-refresh is given.

    Examples:
        sn-cmdb download table cmdb_ci_server --instance https://dev.service-now.com
        sn-cmdb download table cmdb_rel_ci --force-refresh
        sn-cmdb download table cmdb_ci --fields sys_id,name,sys_class_name,operational_status
    """
    _configure_logging(verbose)
    instance = _require_instance(instance)
    cfg = load_config()
    cfg.page_size = page_size

    field_list = [f.strip() for f in fields.split(",")] if fields else None

    _run_with_browser(
        instance=instance,
        cfg=cfg,
        db_path=db_path,
        headless=headless,
        action=lambda ctx: ctx["extractor"].download_table(
            table_name,
            fields=field_list,
            force_refresh=force_refresh,
        ),
    )


# ---------------------------------------------------------------------------
# download all command
# ---------------------------------------------------------------------------

@download_app.command("all")
def cmd_download_all(
    instance: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        envvar="SN_CMDB_INSTANCE_URL",
        show_default=False,
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    discover: bool = typer.Option(
        False,
        "--discover",
        help=(
            "Discover all cmdb_* tables dynamically from the instance. "
            "Without this flag, only the built-in core table list is used."
        ),
    ),
    page_size: int = typer.Option(
        1000,
        "--page-size",
        envvar="SN_CMDB_PAGE_SIZE",
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Re-download all tables from scratch, ignoring saved progress.",
    ),
    skip_complete: bool = typer.Option(
        True,
        "--skip-complete/--no-skip-complete",
        help="Skip tables that were already fully downloaded.",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--visible",
        envvar="SN_CMDB_HEADLESS",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """
    Download all CMDB tables into the local SQLite database.

    By default uses the built-in core table list. Pass --discover to pull
    the complete table list from the live instance via sys_db_object.

    Already-complete tables are skipped unless --force-refresh is used.
    Interrupted downloads resume from their last saved offset.

    Examples:
        sn-cmdb download all --instance https://dev.service-now.com
        sn-cmdb download all --discover --instance https://corp.service-now.com
        sn-cmdb download all --force-refresh --instance https://dev.service-now.com
    """
    _configure_logging(verbose)
    instance = _require_instance(instance)
    cfg = load_config()
    cfg.page_size = page_size

    def action(ctx: dict) -> None:
        extractor = ctx["extractor"]
        if discover:
            from .schema import SchemaDiscovery
            sd = SchemaDiscovery(extractor)
            table_names = sd.discover_cmdb_tables()
        else:
            table_names = list(CORE_CMDB_TABLES)

        # Optionally filter out already-complete tables
        if skip_complete and not force_refresh:
            db: Database = ctx["db"]
            incomplete = []
            for tbl in table_names:
                state = db.get_state(tbl)
                if state and state["status"] == STATUS_COMPLETE:
                    continue
                incomplete.append(tbl)
            if len(incomplete) < len(table_names):
                skipped = len(table_names) - len(incomplete)
                console.print(f"[dim]Skipping {skipped} already-complete table(s).[/dim]")
            table_names = incomplete

        if not table_names:
            console.print("[green]All tables already downloaded.[/green]")
            return

        console.print(
            f"[bold]Downloading {len(table_names)} table(s)[/bold] "
            f"from [cyan]{instance}[/cyan]"
        )
        extractor.download_tables(table_names, force_refresh=force_refresh)

    _run_with_browser(
        instance=instance,
        cfg=cfg,
        db_path=db_path,
        headless=headless,
        action=action,
    )


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

@app.command("status")
def cmd_status(
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    show_complete: bool = typer.Option(
        True,
        "--show-complete/--hide-complete",
        help="Whether to show fully-downloaded tables in the status table.",
    ),
) -> None:
    """
    Show the download status for all tables in the local database.

    Displays table name, status (pending/in_progress/complete/failed),
    row count, and timestamps. Use --hide-complete to show only incomplete
    or failed tables.

    Example:
        sn-cmdb status
        sn-cmdb status --hide-complete
    """
    if not db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {db_path}")
        raise typer.Exit(0)

    with Database(db_path).open() as db:
        states = db.list_states()

    if not states:
        console.print("[dim]No download state recorded yet.[/dim]")
        return

    t = Table(title=f"Download Status — {db_path}")
    t.add_column("Table", style="bold")
    t.add_column("Status")
    t.add_column("Downloaded", justify="right")
    t.add_column("Total", justify="right")
    t.add_column("Started")
    t.add_column("Completed")

    status_style = {
        STATUS_COMPLETE: "[green]complete[/green]",
        STATUS_IN_PROGRESS: "[yellow]in_progress[/yellow]",
        STATUS_FAILED: "[red]failed[/red]",
    }

    for row in states:
        if not show_complete and row["status"] == STATUS_COMPLETE:
            continue
        t.add_row(
            row["table_name"],
            status_style.get(row["status"], row["status"]),
            f"{row['downloaded']:,}",
            str(row["total_records"]) if row["total_records"] != -1 else "?",
            (row.get("started_at") or "")[:19],
            (row.get("completed_at") or "")[:19],
        )

    console.print(t)

    total_rows = sum(r["downloaded"] for r in states)
    console.print(
        f"\n[dim]{len(states)} table(s) tracked · {total_rows:,} total rows[/dim]"
    )


# ---------------------------------------------------------------------------
# reset command
# ---------------------------------------------------------------------------

@app.command("reset")
def cmd_reset(
    table_name: Optional[str] = typer.Argument(
        None,
        help="Table name to reset. Omit to reset ALL tables.",
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """
    Reset download state so a table will be re-downloaded from scratch.

    Resets the offset and status in _download_state but does NOT delete the
    already-downloaded rows from the data table. Use `sn-cmdb download table
    <name> --force-refresh` to also purge existing rows.

    Examples:
        sn-cmdb reset cmdb_ci_server
        sn-cmdb reset --yes          # reset ALL tables
    """
    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(1)

    with Database(db_path).open() as db:
        if table_name:
            targets = [table_name]
        else:
            targets = [s["table_name"] for s in db.list_states()]

        if not yes:
            confirm = typer.confirm(
                f"Reset download state for {len(targets)} table(s)?"
            )
            if not confirm:
                raise typer.Abort()

        for tbl in targets:
            db.reset_state(tbl)
            console.print(f"[yellow]Reset:[/yellow] {tbl}")


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------

class ExportFormat(str, Enum):
    json = "json"
    csv = "csv"


@app.command("export")
def cmd_export(
    table_name: str = typer.Argument(..., help="Table name to export."),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path. Defaults to <table_name>.<format>.",
    ),
    fmt: ExportFormat = typer.Option(
        ExportFormat.json,
        "--format",
        help="Export format: json or csv.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of rows to export.",
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
) -> None:
    """
    Export a table from the local SQLite database to JSON or CSV.

    Examples:
        sn-cmdb export cmdb_ci_server
        sn-cmdb export cmdb_ci_server --format csv --output servers.csv
        sn-cmdb export cmdb_ci --limit 500 --format json
    """
    import csv as csv_mod
    import io

    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(1)

    output = output or Path(f"{table_name}.{fmt.value}")

    with Database(db_path).open() as db:
        limit_clause = f" LIMIT {limit}" if limit else ""
        rows = db.conn.execute(
            f'SELECT * FROM "{table_name}"{limit_clause}'
        ).fetchall()
        if not rows:
            console.print(f"[yellow]No rows found in table '{table_name}'.[/yellow]")
            raise typer.Exit(0)
        columns = [desc[0] for desc in db.conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT 0'
        ).description]

    if fmt == ExportFormat.json:
        data = [dict(zip(columns, row)) for row in rows]
        output.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    else:
        buf = io.StringIO()
        writer = csv_mod.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        writer.writerows(dict(zip(columns, row)) for row in rows)
        output.write_text(buf.getvalue(), encoding="utf-8")

    console.print(
        f"[green]Exported[/green] {len(rows):,} rows from [bold]{table_name}[/bold] "
        f"→ {output}"
    )


# ---------------------------------------------------------------------------
# diagram command
# ---------------------------------------------------------------------------

@app.command("diagram")
def cmd_diagram(
    output_dir: Path = typer.Option(
        Path("."),
        "--output-dir", "-o",
        help="Directory where .mmd diagram files are written.",
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    kind: str = typer.Option(
        "all",
        "--kind",
        help=(
            "Which diagram(s) to generate:\n"
            "  all         — inheritance + reference + combined (default)\n"
            "  inheritance — class hierarchy from sys_db_object\n"
            "  reference   — foreign-key edges from sys_dictionary\n"
            "  combined    — overview of populated tables only\n"
            "  report      — Markdown report embedding all diagrams"
        ),
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """
    Generate Mermaid diagram(s) from data in the local SQLite database.

    The diagrams render natively in GitHub, GitLab, VS Code, Notion, and Claude.
    Output files are placed in --output-dir (default: current directory).

    Diagram types:
    - [bold]inheritance[/bold]: classDiagram showing cmdb_ci class hierarchy.
    - [bold]reference[/bold]:   erDiagram showing reference-field relationships.
    - [bold]combined[/bold]:    Overview classDiagram for tables that have data.
    - [bold]report[/bold]:      Markdown file embedding all diagrams as code blocks.

    Examples:
        sn-cmdb diagram
        sn-cmdb diagram --kind inheritance --output-dir ./diagrams
        sn-cmdb diagram --kind report
    """
    _configure_logging(verbose)

    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    with Database(db_path).open() as db:
        from .diagram import DiagramGenerator
        from .schema import SchemaDiscovery

        # Build relationship data directly from cached DB (no live browser needed)
        rel_map = _load_rel_map(db)
        ref_fields = _load_ref_fields(db)
        gen = DiagramGenerator(db, rel_map=rel_map, ref_fields=ref_fields)

        generated: list[Path] = []

        if kind in ("all", "inheritance"):
            p = gen.write_inheritance_diagram(output_dir / "cmdb_inheritance.mmd")
            generated.append(p)

        if kind in ("all", "reference"):
            p = gen.write_reference_diagram(output_dir / "cmdb_references.mmd")
            generated.append(p)

        if kind in ("all", "combined"):
            p = gen.write_combined_diagram(output_dir / "cmdb_overview.mmd")
            generated.append(p)

        if kind in ("all", "report"):
            md = gen.generate_summary_markdown()
            report_path = output_dir / "cmdb_report.md"
            report_path.write_text(md, encoding="utf-8")
            generated.append(report_path)

    for p in generated:
        console.print(f"[green]✓[/green] {p}")


def _load_rel_map(db: Database) -> dict[str, list[str]]:
    """Load inheritance map from cached sys_db_object."""
    try:
        id_rows = db.conn.execute(
            "SELECT sys_id, name FROM sys_db_object WHERE name LIKE 'cmdb%'"
        ).fetchall()
        id_to_name = {r[0]: r[1] for r in id_rows if r[0]}
        rows = db.conn.execute(
            "SELECT name, super_class FROM sys_db_object WHERE name LIKE 'cmdb%'"
        ).fetchall()
        rel_map: dict[str, list[str]] = {}
        for name, super_id in rows:
            parent = id_to_name.get(super_id or "")
            if parent:
                rel_map.setdefault(name, []).append(parent)
        return rel_map
    except Exception:
        return {}


def _load_ref_fields(db: Database) -> list[dict[str, str]]:
    """Load reference fields from cached sys_dictionary."""
    try:
        rows = db.conn.execute(
            "SELECT name, element, reference FROM sys_dictionary "
            "WHERE internal_type='reference' AND reference IS NOT NULL"
        ).fetchall()
        return [{"table": r[0], "field": r[1], "references_table": r[2]} for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# db info command
# ---------------------------------------------------------------------------

@db_app.command("info")
def cmd_db_info(
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
) -> None:
    """
    Show statistics about the local SQLite database.

    Displays file size, number of tables, total row count, and per-table
    row counts.

    Example:
        sn-cmdb db info
        sn-cmdb db info --db /path/to/custom.db
    """
    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(1)

    size_mb = db_path.stat().st_size / (1024 * 1024)

    with Database(db_path).open() as db:
        data_tables = db.list_data_tables()
        states = {s["table_name"]: s for s in db.list_states()}

    console.print(f"\n[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Size:[/bold] {size_mb:.2f} MB")
    console.print(f"[bold]Data tables:[/bold] {len(data_tables)}")

    t = Table(title="Tables")
    t.add_column("Table", style="bold")
    t.add_column("Rows", justify="right")
    t.add_column("Status")

    status_style = {
        STATUS_COMPLETE: "[green]complete[/green]",
        STATUS_IN_PROGRESS: "[yellow]in_progress[/yellow]",
        STATUS_FAILED: "[red]failed[/red]",
    }

    total = 0
    with Database(db_path).open() as db:
        for tbl in sorted(data_tables):
            count = db.count_table(tbl)
            total += count
            state_row = states.get(tbl, {})
            status = state_row.get("status", "unknown")
            t.add_row(tbl, f"{count:,}", status_style.get(status, status))

    console.print(t)
    console.print(f"\n[dim]Total rows across all tables: {total:,}[/dim]")


# ---------------------------------------------------------------------------
# db query command
# ---------------------------------------------------------------------------

@db_app.command("query")
def cmd_db_query(
    sql: str = typer.Argument(
        ...,
        help="SQL query to execute against the local database.",
    ),
    db_path: Path = typer.Option(
        Path("cmdb.db"),
        "--db", "-d",
        envvar="SN_CMDB_DB_PATH",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON instead of a table.",
    ),
    limit: int = typer.Option(
        100,
        "--limit",
        help="Maximum number of rows to display.",
    ),
) -> None:
    """
    Run an arbitrary SQL query against the local SQLite database.

    Useful for quick ad-hoc analysis without an external SQLite client.
    Results are displayed as a Rich table, or as JSON with --json.

    Examples:
        sn-cmdb db query "SELECT name, sys_class_name FROM cmdb_ci LIMIT 10"
        sn-cmdb db query "SELECT count(*) FROM cmdb_ci_server" --json
        sn-cmdb db query "SELECT * FROM _download_state"
    """
    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(1)

    import sqlite3

    with Database(db_path).open() as db:
        try:
            cursor = db.conn.execute(sql)
            rows = cursor.fetchmany(limit)
            columns = [d[0] for d in (cursor.description or [])]
        except sqlite3.Error as exc:
            console.print(f"[red]SQL error:[/red] {exc}")
            raise typer.Exit(1)

    if not rows:
        console.print("[dim]No rows returned.[/dim]")
        return

    if output_json:
        data = [dict(zip(columns, row)) for row in rows]
        rprint(json.dumps(data, indent=2, default=str))
        return

    t = Table()
    for col in columns:
        t.add_column(col)
    for row in rows:
        t.add_row(*[str(v) if v is not None else "" for v in row])
    console.print(t)
    console.print(f"[dim]{len(rows)} row(s)[/dim]")


# ---------------------------------------------------------------------------
# Internal: browser context runner
# ---------------------------------------------------------------------------

def _run_with_browser(
    *,
    instance: str,
    cfg: AppConfig,
    db_path: Path,
    headless: bool,
    action: "Callable[[dict], None]",
) -> None:
    """
    Open the database and browser, build an Extractor, run action(ctx), close cleanly.

    ctx keys: extractor, db, instance, session_manager
    """
    from typing import Callable
    from .browser import SessionManager
    from .extractor import Extractor

    mgr = SessionManager(
        instance_url=instance,
        session_dir=cfg.session_dir,
        headless=headless,
    )

    if not mgr.session_exists():
        console.print(
            "[yellow]No saved session found.[/yellow] "
            "Run [bold]sn-cmdb login --instance[/bold] first."
        )
        raise typer.Exit(1)

    with Database(db_path).open() as db:
        db.set_instance_info("instance_url", instance)
        with mgr.active_page(headless=headless) as page:
            extractor = Extractor(
                page=page,
                db=db,
                instance_url=instance,
                page_size=cfg.page_size,
            )
            action({"extractor": extractor, "db": db, "instance": instance, "session_manager": mgr})
