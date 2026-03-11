"""
db.py — SQLite database layer.

Responsibilities:
  - Open (or create) the SQLite database at a user-specified path.
  - Maintain a `_download_state` metadata table that tracks per-table
    download progress (offset, total, status, timestamps).
  - Dynamically create data tables based on the fields returned by the API.
  - Upsert rows using the ServiceNow `sys_id` as the primary key.
  - Provide helpers for querying download state and listing tables.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Download status values stored in _download_state
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"

# Sentinel for unknown total count
TOTAL_UNKNOWN = -1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """
    Synchronous SQLite wrapper.

    All heavy I/O happens in the browser/extractor layer; this class is kept
    synchronous intentionally so callers can use it from both sync and async
    contexts without needing aiosqlite for every operation.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> "Database":
        """Open (or create) the database and ensure schema is initialised."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_meta_tables()
        logger.info("Database opened: %s", self.path)
        return self

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        return self.open()

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not open. Call open() first.")
        return self._conn

    # ------------------------------------------------------------------
    # Meta-schema
    # ------------------------------------------------------------------

    def _ensure_meta_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS _download_state (
                table_name      TEXT PRIMARY KEY,
                status          TEXT NOT NULL DEFAULT 'pending',
                total_records   INTEGER NOT NULL DEFAULT -1,
                downloaded      INTEGER NOT NULL DEFAULT 0,
                last_offset     INTEGER NOT NULL DEFAULT 0,
                started_at      TEXT,
                completed_at    TEXT,
                error_message   TEXT,
                instance_url    TEXT,
                fields_json     TEXT   -- JSON list of field names as extracted
            );

            CREATE TABLE IF NOT EXISTS _instance_info (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Download state helpers
    # ------------------------------------------------------------------

    def get_state(self, table_name: str) -> dict[str, Any] | None:
        """Return the download state row for a table, or None if not started."""
        row = self.conn.execute(
            "SELECT * FROM _download_state WHERE table_name = ?", (table_name,)
        ).fetchone()
        return dict(row) if row else None

    def upsert_state(
        self,
        table_name: str,
        *,
        status: str | None = None,
        total_records: int | None = None,
        downloaded: int | None = None,
        last_offset: int | None = None,
        error_message: str | None = None,
        instance_url: str | None = None,
        fields: list[str] | None = None,
    ) -> None:
        """Create or update the download state for a table."""
        existing = self.get_state(table_name)
        if existing is None:
            self.conn.execute(
                """INSERT INTO _download_state
                   (table_name, status, total_records, downloaded, last_offset,
                    started_at, instance_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    table_name,
                    status or STATUS_PENDING,
                    total_records if total_records is not None else TOTAL_UNKNOWN,
                    downloaded or 0,
                    last_offset or 0,
                    _now_iso(),
                    instance_url,
                ),
            )
        else:
            updates: dict[str, Any] = {}
            if status is not None:
                updates["status"] = status
            if total_records is not None:
                updates["total_records"] = total_records
            if downloaded is not None:
                updates["downloaded"] = downloaded
            if last_offset is not None:
                updates["last_offset"] = last_offset
            if error_message is not None:
                updates["error_message"] = error_message
            if instance_url is not None:
                updates["instance_url"] = instance_url
            if fields is not None:
                updates["fields_json"] = json.dumps(fields)
            if status == STATUS_COMPLETE:
                updates["completed_at"] = _now_iso()
            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                self.conn.execute(
                    f"UPDATE _download_state SET {set_clause} WHERE table_name = ?",
                    list(updates.values()) + [table_name],
                )
        self.conn.commit()

    def list_states(self) -> list[dict[str, Any]]:
        """Return all rows from _download_state ordered by table name."""
        rows = self.conn.execute(
            "SELECT * FROM _download_state ORDER BY table_name"
        ).fetchall()
        return [dict(r) for r in rows]

    def reset_state(self, table_name: str) -> None:
        """Reset a table's download state so it will be re-downloaded from scratch."""
        self.conn.execute(
            """UPDATE _download_state
               SET status='pending', downloaded=0, last_offset=0,
                   started_at=NULL, completed_at=NULL, error_message=NULL
               WHERE table_name=?""",
            (table_name,),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Dynamic data table management
    # ------------------------------------------------------------------

    def _sanitize_column(self, name: str) -> str:
        """Return a safe SQLite column name."""
        return name.replace(".", "_").replace(" ", "_").replace("-", "_")

    def ensure_data_table(self, table_name: str, fields: list[str]) -> None:
        """
        Create the data table if it doesn't exist, or add any missing columns.
        sys_id is always the primary key.
        """
        safe_cols = [self._sanitize_column(f) for f in fields]
        col_defs = ", ".join(
            f'"{c}" TEXT' for c in safe_cols if c != "sys_id"
        )
        ddl = (
            f'CREATE TABLE IF NOT EXISTS "{table_name}" '
            f'("sys_id" TEXT PRIMARY KEY, {col_defs})'
        )
        self.conn.execute(ddl)
        self.conn.commit()

        # Add any columns that were discovered later
        existing = {
            row[1]
            for row in self.conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }
        for col in safe_cols:
            if col not in existing:
                self.conn.execute(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT'
                )
        self.conn.commit()

    def upsert_rows(self, table_name: str, rows: list[dict[str, Any]]) -> int:
        """
        Upsert a batch of rows into the named data table.
        Returns the number of rows written.
        """
        if not rows:
            return 0

        # Collect all field names across the batch
        all_fields: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for k in row:
                safe = self._sanitize_column(k)
                if safe not in seen:
                    seen.add(safe)
                    all_fields.append(safe)

        self.ensure_data_table(table_name, all_fields)

        cols = ", ".join(f'"{c}"' for c in all_fields)
        placeholders = ", ".join("?" for _ in all_fields)
        sql = (
            f'INSERT OR REPLACE INTO "{table_name}" ({cols}) VALUES ({placeholders})'
        )

        def _row_values(row: dict[str, Any]) -> list[Any]:
            return [
                _coerce(row.get(k) or row.get(self._sanitize_column(k)))
                for k in all_fields
            ]

        self.conn.executemany(sql, [_row_values(r) for r in rows])
        self.conn.commit()
        return len(rows)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def count_table(self, table_name: str) -> int:
        """Return the number of rows in a data table, or 0 if it doesn't exist."""
        try:
            row = self.conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            return 0

    def list_data_tables(self) -> list[str]:
        """Return names of all data tables (excluding internal _ tables)."""
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '\\_%' ESCAPE '\\'"
            " ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def table_columns(self, table_name: str) -> list[str]:
        """Return column names for a data table."""
        rows = self.conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
        return [r[1] for r in rows]

    def set_instance_info(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO _instance_info (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_instance_info(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM _instance_info WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _coerce(value: Any) -> Any:
    """Flatten nested dicts/lists to JSON strings for SQLite storage."""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value
