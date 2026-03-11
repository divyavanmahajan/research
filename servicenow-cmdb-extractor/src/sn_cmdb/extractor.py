"""
extractor.py — Core data extraction engine.

Approach:
  The tool injects JavaScript into the authenticated browser page to call
  ServiceNow's REST Table API (/api/now/table/<table>) using the browser's
  own fetch() with the existing session cookies.  This means no API credentials
  are needed — only an active browser session.

Paging:
  Uses sysparm_offset / sysparm_limit.  The X-Total-Count response header
  provides the total count for progress display.

Resume:
  Each table's progress (offset, status, count) is persisted in the SQLite
  `_download_state` table.  Interrupted downloads continue from
  `last_offset` unless --force-refresh is specified.

Progress:
  Uses Rich's Progress bar with live updates per page and per table.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from playwright.sync_api import Page
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from .db import (
    Database,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    TOTAL_UNKNOWN,
)

logger = logging.getLogger(__name__)
console = Console()

# Maximum retries per page request before marking a table as failed
MAX_PAGE_RETRIES = 3

# Delay between retries (seconds)
RETRY_DELAY_S = 2.0


class ExtractorError(Exception):
    """Raised when extraction cannot proceed."""


# ---------------------------------------------------------------------------
# JavaScript injected into the browser to call the ServiceNow REST API
# ---------------------------------------------------------------------------

_JS_FETCH_PAGE = """
async (url) => {
    const resp = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-UserToken': window.g_ck || '',
        }
    });
    const totalCount = resp.headers.get('X-Total-Count');
    const body = await resp.json();
    return {
        status: resp.status,
        total_count: totalCount ? parseInt(totalCount, 10) : -1,
        data: body,
    };
}
"""


class Extractor:
    """
    Downloads ServiceNow CMDB tables via the authenticated browser.

    Args:
        page:         Active Playwright page (authenticated).
        db:           Open Database instance.
        instance_url: Base URL of the ServiceNow instance.
        page_size:    Records per API request (default 1000).
    """

    def __init__(
        self,
        page: Page,
        db: Database,
        instance_url: str,
        page_size: int = 1000,
    ) -> None:
        self.page = page
        self.db = db
        self.instance_url = instance_url.rstrip("/")
        self.page_size = page_size
        self._ensure_base_page_loaded()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download_table(
        self,
        table_name: str,
        *,
        fields: list[str] | None = None,
        force_refresh: bool = False,
        progress: Progress | None = None,
        task_id: TaskID | None = None,
        on_page: Callable[[int, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Download all records from ``table_name`` into the SQLite database.

        Args:
            table_name:    ServiceNow table name (e.g. ``cmdb_ci_server``).
            fields:        Optional list of fields to retrieve. Defaults to all fields.
            force_refresh: Ignore saved progress and re-download from scratch.
            progress:      Rich Progress instance for live display.
            task_id:       Rich task id within the progress.
            on_page:       Optional callback(offset, page_count, total) called after each page.

        Returns:
            dict with keys: table_name, status, downloaded, total, elapsed_s
        """
        state = self.db.get_state(table_name)
        start_offset = 0

        if state:
            if state["status"] == STATUS_COMPLETE and not force_refresh:
                logger.info("Table %s already complete — skipping.", table_name)
                return {
                    "table_name": table_name,
                    "status": STATUS_COMPLETE,
                    "downloaded": state["downloaded"],
                    "total": state["total_records"],
                    "elapsed_s": 0,
                    "skipped": True,
                }
            if state["status"] == STATUS_IN_PROGRESS and not force_refresh:
                start_offset = state["last_offset"]
                console.print(
                    f"[yellow]Resuming[/yellow] {table_name} from offset {start_offset}"
                )
            elif force_refresh:
                self.db.reset_state(table_name)
                # Drop and recreate the data table
                try:
                    self.db.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                    self.db.conn.commit()
                except Exception:
                    pass

        self.db.upsert_state(
            table_name,
            status=STATUS_IN_PROGRESS,
            last_offset=start_offset,
            instance_url=self.instance_url,
        )

        t0 = time.monotonic()
        offset = start_offset
        total = TOTAL_UNKNOWN
        downloaded_this_run = 0

        try:
            while True:
                url = self._build_url(table_name, offset=offset, fields=fields)
                result = self._fetch_page(url)

                records: list[dict] = result.get("data", {}).get("result", [])
                if result.get("total_count", TOTAL_UNKNOWN) > 0:
                    total = result["total_count"]

                if not records:
                    break  # Last page

                # Discover fields from first page
                if offset == start_offset and records:
                    all_fields = list(records[0].keys())
                    self.db.upsert_state(table_name, fields=all_fields, total_records=total)
                    self.db.ensure_data_table(table_name, all_fields)

                written = self.db.upsert_rows(table_name, records)
                downloaded_this_run += written
                offset += len(records)

                prior_downloaded = (state or {}).get("downloaded", 0)
                cumulative = (prior_downloaded if force_refresh is False else 0) + downloaded_this_run

                self.db.upsert_state(
                    table_name,
                    downloaded=cumulative,
                    last_offset=offset,
                    total_records=total if total != TOTAL_UNKNOWN else None,
                )

                # Update Rich progress bar
                if progress and task_id is not None:
                    progress.update(
                        task_id,
                        completed=cumulative,
                        total=total if total != TOTAL_UNKNOWN else None,
                        description=f"[cyan]{table_name}[/cyan] ({cumulative:,} rows)",
                    )

                # Fire optional callback
                if on_page:
                    on_page(offset, written, total)

                logger.debug(
                    "%s: offset=%d page_count=%d total=%s",
                    table_name,
                    offset,
                    written,
                    total,
                )

                # Stop if we've received fewer records than the page size
                if len(records) < self.page_size:
                    break

            self.db.upsert_state(table_name, status=STATUS_COMPLETE)
            elapsed = time.monotonic() - t0
            console.print(
                f"[green]✓[/green] {table_name}: "
                f"{downloaded_this_run:,} new rows in {elapsed:.1f}s"
            )
            return {
                "table_name": table_name,
                "status": STATUS_COMPLETE,
                "downloaded": downloaded_this_run,
                "total": total,
                "elapsed_s": elapsed,
            }

        except Exception as exc:
            self.db.upsert_state(
                table_name, status=STATUS_FAILED, error_message=str(exc)
            )
            logger.error("Failed to download %s: %s", table_name, exc)
            raise

    def download_tables(
        self,
        table_names: list[str],
        *,
        force_refresh: bool = False,
        fields_map: dict[str, list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Download multiple tables sequentially with an overall progress bar.

        Args:
            table_names:   Ordered list of table names.
            force_refresh: Re-download all tables from scratch.
            fields_map:    Optional per-table field lists.

        Returns:
            List of result dicts (one per table).
        """
        results: list[dict[str, Any]] = []
        fields_map = fields_map or {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=4,
        ) as progress:
            overall = progress.add_task(
                f"[bold]Downloading {len(table_names)} table(s)[/bold]",
                total=len(table_names),
            )

            for table_name in table_names:
                table_task = progress.add_task(
                    f"[cyan]{table_name}[/cyan]",
                    total=None,  # Unknown until first page
                )
                try:
                    result = self.download_table(
                        table_name,
                        fields=fields_map.get(table_name),
                        force_refresh=force_refresh,
                        progress=progress,
                        task_id=table_task,
                    )
                    results.append(result)
                except Exception as exc:
                    progress.update(
                        table_task,
                        description=f"[red]FAILED {table_name}: {exc}[/red]",
                    )
                    results.append(
                        {
                            "table_name": table_name,
                            "status": STATUS_FAILED,
                            "error": str(exc),
                        }
                    )
                finally:
                    progress.advance(overall)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_base_page_loaded(self) -> None:
        """
        Navigate to the instance home if the page is blank, so that
        browser-injected fetch() requests carry session cookies.
        """
        current = self.page.url
        if not current or current == "about:blank":
            try:
                self.page.goto(
                    f"{self.instance_url}/now/nav/ui/classic",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
            except Exception:
                # Fall back to root if nav path doesn't exist
                self.page.goto(self.instance_url, wait_until="domcontentloaded", timeout=30_000)

    def _build_url(
        self,
        table_name: str,
        *,
        offset: int = 0,
        fields: list[str] | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        params = [
            f"sysparm_limit={self.page_size}",
            f"sysparm_offset={offset}",
            "sysparm_exclude_reference_link=true",
            "sysparm_display_value=false",
        ]
        if fields:
            params.append(f"sysparm_fields={','.join(fields)}")
        if extra_params:
            params.extend(f"{k}={v}" for k, v in extra_params.items())
        return f"{self.instance_url}/api/now/table/{table_name}?{'&'.join(params)}"

    def _fetch_page(self, url: str) -> dict[str, Any]:
        """
        Inject a fetch() call into the browser and return the parsed response.
        Retries up to MAX_PAGE_RETRIES times on failure.
        """
        last_exc: Exception | None = None
        for attempt in range(1, MAX_PAGE_RETRIES + 1):
            try:
                result = self.page.evaluate(_JS_FETCH_PAGE, url)
                if result["status"] == 401:
                    raise ExtractorError(
                        "Session expired (HTTP 401). Run `sn-cmdb login` to refresh."
                    )
                if result["status"] == 403:
                    raise ExtractorError(
                        f"Access denied (HTTP 403) for URL: {url}\n"
                        "Check that the logged-in user has the itil or admin role."
                    )
                if result["status"] not in (200, 206):
                    raise ExtractorError(
                        f"Unexpected HTTP {result['status']} for {url}"
                    )
                return result
            except ExtractorError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Page fetch attempt %d/%d failed: %s", attempt, MAX_PAGE_RETRIES, exc
                )
                if attempt < MAX_PAGE_RETRIES:
                    time.sleep(RETRY_DELAY_S * attempt)

        raise ExtractorError(
            f"Failed to fetch page after {MAX_PAGE_RETRIES} attempts: {last_exc}"
        )
