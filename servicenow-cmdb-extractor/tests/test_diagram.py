"""
tests/test_diagram.py — Unit tests for the Mermaid diagram generator.
"""

from pathlib import Path

import pytest

from sn_cmdb.db import Database
from sn_cmdb.diagram import DiagramGenerator, _safe


@pytest.fixture
def db_with_data(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.open()
    db.ensure_data_table("cmdb_ci", ["sys_id", "name", "sys_class_name"])
    db.upsert_rows("cmdb_ci", [{"sys_id": "1", "name": "A", "sys_class_name": "cmdb_ci"}])
    db.ensure_data_table("cmdb_ci_server", ["sys_id", "name", "os"])
    db.upsert_rows("cmdb_ci_server", [{"sys_id": "2", "name": "srv1", "os": "Linux"}])
    return db


def test_safe_identifier() -> None:
    assert _safe("cmdb-ci.server") == "cmdb_ci_server"
    assert _safe("normal_name") == "normal_name"


def test_inheritance_diagram_written(tmp_path: Path, db_with_data: Database) -> None:
    rel_map = {"cmdb_ci_server": ["cmdb_ci"]}
    gen = DiagramGenerator(db_with_data, rel_map=rel_map)
    out = tmp_path / "inherit.mmd"
    gen.write_inheritance_diagram(out)
    content = out.read_text()
    assert "classDiagram" in content
    assert "cmdb_ci_server" in content
    assert "cmdb_ci" in content


def test_combined_diagram_only_shows_populated_tables(
    tmp_path: Path, db_with_data: Database
) -> None:
    rel_map = {"cmdb_ci_server": ["cmdb_ci"]}
    gen = DiagramGenerator(db_with_data, rel_map=rel_map)
    out = tmp_path / "combined.mmd"
    gen.write_combined_diagram(out)
    content = out.read_text()
    # Both tables have rows so both should appear
    assert "cmdb_ci" in content
    assert "cmdb_ci_server" in content


def test_summary_markdown_contains_table_list(db_with_data: Database) -> None:
    gen = DiagramGenerator(db_with_data, rel_map={}, ref_fields=[])
    md = gen.generate_summary_markdown()
    assert "cmdb_ci" in md
    assert "cmdb_ci_server" in md
    assert "classDiagram" in md
