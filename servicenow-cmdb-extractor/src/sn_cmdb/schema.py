"""
schema.py — ServiceNow schema and CMDB table discovery.

Uses the authenticated browser session to query:
  - sys_db_object  — catalogue of all database tables (name, label, super_class)
  - sys_dictionary — field definitions per table (element, internal_type, reference)

CMDB tables are identified by:
  1. Tables whose name starts with ``cmdb_``
  2. Tables that extend ``cmdb_ci`` (transitively, via super_class hierarchy)

This module also provides helpers to build the relationships map used for
Mermaid diagram generation.
"""

from __future__ import annotations

import logging
from typing import Any

from playwright.sync_api import Page

from .extractor import Extractor

logger = logging.getLogger(__name__)

# Fields to retrieve from sys_db_object
_DB_OBJECT_FIELDS = [
    "name",
    "label",
    "super_class",
    "sys_id",
    "is_extendable",
]

# Fields to retrieve from sys_dictionary
_DICT_FIELDS = [
    "name",           # Table name
    "element",        # Field/column name
    "internal_type",  # String, Integer, Reference, etc.
    "reference",      # Referenced table (for Reference type fields)
    "label",
    "max_length",
    "mandatory",
    "default_value",
]

# Prefix that marks a CMDB table
CMDB_PREFIX = "cmdb"


class SchemaDiscovery:
    """
    Discovers CMDB tables and their field definitions from a live ServiceNow instance.

    Args:
        extractor: Initialised Extractor instance (has an active browser page).
        db:        Open Database instance — schema data is cached here.
    """

    def __init__(self, extractor: Extractor) -> None:
        self.extractor = extractor
        self.db = extractor.db
        self.page = extractor.page
        self.instance_url = extractor.instance_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_cmdb_tables(self, *, force_refresh: bool = False) -> list[str]:
        """
        Return a sorted list of CMDB table names discovered from sys_db_object.

        On first call downloads sys_db_object into the local SQLite database.
        Subsequent calls read from the cache unless force_refresh=True.

        Returns:
            Sorted list of table name strings, e.g. ['cmdb_ci', 'cmdb_ci_server', ...]
        """
        # Download sys_db_object if not already cached
        state = self.db.get_state("sys_db_object")
        if not state or state["status"] != "complete" or force_refresh:
            logger.info("Downloading sys_db_object for table discovery…")
            self.extractor.download_table(
                "sys_db_object",
                fields=_DB_OBJECT_FIELDS,
                force_refresh=force_refresh,
            )

        rows = self.db.conn.execute(
            'SELECT name FROM sys_db_object WHERE name LIKE "cmdb%" ORDER BY name'
        ).fetchall()
        tables = [r[0] for r in rows if r[0]]
        logger.info("Discovered %d CMDB tables via sys_db_object", len(tables))
        return tables

    def discover_all_cmdb_tables_extended(
        self, *, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Return full metadata rows (name, label, super_class) for all CMDB tables.
        """
        state = self.db.get_state("sys_db_object")
        if not state or state["status"] != "complete" or force_refresh:
            self.extractor.download_table(
                "sys_db_object",
                fields=_DB_OBJECT_FIELDS,
                force_refresh=force_refresh,
            )
        rows = self.db.conn.execute(
            'SELECT name, label, super_class FROM sys_db_object '
            'WHERE name LIKE "cmdb%" ORDER BY name'
        ).fetchall()
        return [{"name": r[0], "label": r[1], "super_class": r[2]} for r in rows]

    def discover_fields(
        self,
        table_name: str,
        *,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return field definitions for *table_name* from sys_dictionary.
        Downloads sys_dictionary slice for this table if not cached.

        Returns:
            List of dicts with keys: element, internal_type, reference, label, etc.
        """
        # Use a scoped URL to pull only this table's entries
        url = (
            f"{self.instance_url}/api/now/table/sys_dictionary"
            f"?sysparm_query=name={table_name}"
            f"&sysparm_fields={','.join(_DICT_FIELDS)}"
            f"&sysparm_limit=500"
            f"&sysparm_exclude_reference_link=true"
        )
        result = self.extractor._fetch_page(url)
        records = result.get("data", {}).get("result", [])
        return records

    def build_relationship_map(self) -> dict[str, list[str]]:
        """
        Build a map of {table_name: [parent_table, ...]} using the super_class
        hierarchy in sys_db_object.

        Returns:
            Dict where each key is a CMDB table and values are the names of
            tables it directly extends.
        """
        rows = self.db.conn.execute(
            "SELECT name, super_class FROM sys_db_object WHERE name LIKE 'cmdb%'"
        ).fetchall()

        # Build sys_id → name lookup
        id_rows = self.db.conn.execute(
            "SELECT sys_id, name FROM sys_db_object WHERE name LIKE 'cmdb%'"
        ).fetchall()
        id_to_name: dict[str, str] = {r[0]: r[1] for r in id_rows if r[0]}

        rel_map: dict[str, list[str]] = {}
        for row in rows:
            name, super_class_id = row[0], row[1]
            if not name:
                continue
            parent = id_to_name.get(super_class_id or "")
            if parent:
                rel_map.setdefault(name, []).append(parent)

        return rel_map

    def get_reference_fields(self) -> list[dict[str, str]]:
        """
        Return all Reference-type fields across downloaded tables.
        Used to draw foreign-key edges in the Mermaid diagram.

        Returns:
            List of dicts: {table, field, references_table}
        """
        try:
            rows = self.db.conn.execute(
                """SELECT name, element, reference
                   FROM sys_dictionary
                   WHERE internal_type = 'reference'
                     AND reference IS NOT NULL
                     AND reference != ''"""
            ).fetchall()
            return [
                {"table": r[0], "field": r[1], "references_table": r[2]}
                for r in rows
            ]
        except Exception:
            return []
