"""
tests/test_db.py — Unit tests for the SQLite database layer.
"""

import json
import tempfile
from pathlib import Path

import pytest

from sn_cmdb.db import (
    Database,
    STATUS_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    TOTAL_UNKNOWN,
)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.open()
    yield db
    db.close()


def test_open_creates_meta_tables(tmp_db: Database) -> None:
    tables = {
        row[0]
        for row in tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "_download_state" in tables
    assert "_instance_info" in tables


def test_upsert_and_get_state(tmp_db: Database) -> None:
    assert tmp_db.get_state("cmdb_ci") is None

    tmp_db.upsert_state("cmdb_ci", status=STATUS_IN_PROGRESS, total_records=500)
    state = tmp_db.get_state("cmdb_ci")

    assert state is not None
    assert state["status"] == STATUS_IN_PROGRESS
    assert state["total_records"] == 500


def test_upsert_state_update(tmp_db: Database) -> None:
    tmp_db.upsert_state("cmdb_ci", status=STATUS_IN_PROGRESS)
    tmp_db.upsert_state("cmdb_ci", status=STATUS_COMPLETE, downloaded=1000)
    state = tmp_db.get_state("cmdb_ci")
    assert state["status"] == STATUS_COMPLETE
    assert state["downloaded"] == 1000
    assert state["completed_at"] is not None


def test_reset_state(tmp_db: Database) -> None:
    tmp_db.upsert_state("cmdb_ci", status=STATUS_COMPLETE, downloaded=100)
    tmp_db.reset_state("cmdb_ci")
    state = tmp_db.get_state("cmdb_ci")
    assert state["status"] == STATUS_PENDING
    assert state["downloaded"] == 0
    assert state["last_offset"] == 0


def test_ensure_data_table_and_upsert_rows(tmp_db: Database) -> None:
    fields = ["sys_id", "name", "sys_class_name"]
    tmp_db.ensure_data_table("cmdb_ci", fields)

    rows = [
        {"sys_id": "abc123", "name": "server01", "sys_class_name": "cmdb_ci_server"},
        {"sys_id": "def456", "name": "server02", "sys_class_name": "cmdb_ci_server"},
    ]
    written = tmp_db.upsert_rows("cmdb_ci", rows)
    assert written == 2
    assert tmp_db.count_table("cmdb_ci") == 2


def test_upsert_rows_idempotent(tmp_db: Database) -> None:
    rows = [{"sys_id": "abc123", "name": "server01"}]
    tmp_db.upsert_rows("cmdb_ci", rows)
    tmp_db.upsert_rows("cmdb_ci", rows)  # same sys_id
    assert tmp_db.count_table("cmdb_ci") == 1


def test_nested_dict_coerced_to_json(tmp_db: Database) -> None:
    rows = [{"sys_id": "x1", "attributes": {"key": "value"}}]
    tmp_db.upsert_rows("cmdb_ci", rows)
    result = tmp_db.conn.execute(
        'SELECT attributes FROM "cmdb_ci" WHERE sys_id="x1"'
    ).fetchone()
    assert result is not None
    parsed = json.loads(result[0])
    assert parsed["key"] == "value"


def test_list_data_tables_excludes_meta(tmp_db: Database) -> None:
    tmp_db.ensure_data_table("cmdb_ci", ["sys_id", "name"])
    tables = tmp_db.list_data_tables()
    assert "cmdb_ci" in tables
    assert "_download_state" not in tables
    assert "_instance_info" not in tables


def test_instance_info(tmp_db: Database) -> None:
    tmp_db.set_instance_info("instance_url", "https://dev.service-now.com")
    assert tmp_db.get_instance_info("instance_url") == "https://dev.service-now.com"
    assert tmp_db.get_instance_info("nonexistent") is None


def test_add_column_on_new_field(tmp_db: Database) -> None:
    tmp_db.ensure_data_table("cmdb_ci", ["sys_id", "name"])
    # Second call with an extra field should add the column
    tmp_db.ensure_data_table("cmdb_ci", ["sys_id", "name", "ip_address"])
    cols = tmp_db.table_columns("cmdb_ci")
    assert "ip_address" in cols
