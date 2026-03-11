"""
diagram.py — Mermaid ER / class diagram generation from SQLite CMDB data.

Two diagram types are produced:
  1. **Inheritance diagram** (``erDiagram`` / ``classDiagram``) showing how CI
     classes extend each other (cmdb_ci → cmdb_ci_hardware → cmdb_ci_server …).
  2. **Reference diagram** (``erDiagram``) showing foreign-key / reference-field
     relationships between tables.

The diagrams are written as ``.mmd`` (Mermaid) files which render natively in
GitHub, GitLab, VS Code (Markdown Preview Mermaid), Notion, and Claude.

Usage example::

    from sn_cmdb.diagram import DiagramGenerator
    gen = DiagramGenerator(db, schema_discovery)
    gen.write_inheritance_diagram(Path("cmdb_inheritance.mmd"))
    gen.write_reference_diagram(Path("cmdb_references.mmd"))
    gen.write_combined_diagram(Path("cmdb_full.mmd"))
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .db import Database

logger = logging.getLogger(__name__)

# Maximum number of tables to include in the combined diagram before splitting
# (Mermaid renders slowly for very large graphs)
MAX_NODES_COMBINED = 80


class DiagramGenerator:
    """
    Generates Mermaid diagrams from CMDB data in a local SQLite database.

    Args:
        db:         Open Database instance.
        rel_map:    Inheritance map {child_table: [parent_table]} from SchemaDiscovery.
        ref_fields: Reference-field edges [{table, field, references_table}].
    """

    def __init__(
        self,
        db: Database,
        rel_map: dict[str, list[str]] | None = None,
        ref_fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.db = db
        self.rel_map: dict[str, list[str]] = rel_map or {}
        self.ref_fields: list[dict[str, str]] = ref_fields or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_inheritance_diagram(self, output_path: Path) -> Path:
        """
        Write a Mermaid classDiagram showing the CMDB class hierarchy.

        Edges represent ``extends`` relationships (super_class in sys_db_object).
        """
        lines: list[str] = [
            "---",
            "title: ServiceNow CMDB — Class Inheritance",
            "---",
            "classDiagram",
            "",
        ]

        # Add nodes (classes)
        tables_in_db = set(self.db.list_data_tables())
        all_tables: set[str] = set(self.rel_map.keys())
        for parents in self.rel_map.values():
            all_tables.update(parents)

        for table in sorted(all_tables):
            row_count = self.db.count_table(table)
            note = f"  class {_safe(table)}" + " {"
            if table in tables_in_db:
                note += f"\n    +{row_count} rows"
            note += "\n  }"
            lines.append(note)

        lines.append("")

        # Add inheritance edges
        for child, parents in sorted(self.rel_map.items()):
            for parent in parents:
                lines.append(f"  {_safe(parent)} <|-- {_safe(child)}")

        mermaid = "\n".join(lines)
        output_path.write_text(mermaid, encoding="utf-8")
        logger.info("Inheritance diagram written to %s", output_path)
        return output_path

    def write_reference_diagram(self, output_path: Path) -> Path:
        """
        Write a Mermaid erDiagram showing reference-field relationships.

        Each edge is labelled with the field name that carries the reference.
        Only tables that exist in the local database are included.
        """
        local_tables = set(self.db.list_data_tables())

        lines: list[str] = [
            "---",
            "title: ServiceNow CMDB — Reference Relationships",
            "---",
            "erDiagram",
            "",
        ]

        # Collect entities (tables that appear in at least one edge)
        entities: set[str] = set()
        edges: list[str] = []

        for ref in self.ref_fields:
            src = ref.get("table", "")
            dst = ref.get("references_table", "")
            field = ref.get("field", "")
            if not src or not dst:
                continue
            if src not in local_tables or dst not in local_tables:
                continue
            entities.add(src)
            entities.add(dst)
            edges.append(f'  {_safe(src)} ||--o| {_safe(dst)} : "{field}"')

        # Add entity blocks with column names
        for table in sorted(entities):
            cols = self.db.table_columns(table)
            lines.append(f"  {_safe(table)} {{")
            for col in cols[:15]:  # Limit columns shown to keep diagram readable
                lines.append(f"    string {_safe(col)}")
            if len(cols) > 15:
                lines.append(f"    %% ... and {len(cols) - 15} more fields")
            lines.append("  }")
            lines.append("")

        lines.extend(edges)
        mermaid = "\n".join(lines)
        output_path.write_text(mermaid, encoding="utf-8")
        logger.info("Reference diagram written to %s", output_path)
        return output_path

    def write_combined_diagram(self, output_path: Path) -> Path:
        """
        Write a combined overview diagram.

        For small CMDBs (≤ MAX_NODES_COMBINED tables) produces a single
        classDiagram with row counts.  For larger CMDBs, produces a simplified
        top-level inheritance tree showing only tables with >0 rows.
        """
        local_tables = set(self.db.list_data_tables())

        # Filter to tables that have data
        populated = {t: self.db.count_table(t) for t in local_tables if self.db.count_table(t) > 0}

        lines: list[str] = [
            "---",
            f"title: ServiceNow CMDB — Overview ({len(populated)} tables with data)",
            "---",
            "classDiagram",
            "",
            "  note \"Row counts shown inside each class\"",
            "",
        ]

        # Class nodes
        for table in sorted(populated):
            count = populated[table]
            lines.append(f"  class {_safe(table)} {{")
            lines.append(f"    +{count:,} rows")
            lines.append("  }")

        lines.append("")

        # Inheritance edges (only between populated tables)
        for child, parents in sorted(self.rel_map.items()):
            if child not in populated:
                continue
            for parent in parents:
                if parent not in populated:
                    continue
                lines.append(f"  {_safe(parent)} <|-- {_safe(child)}")

        mermaid = "\n".join(lines)
        output_path.write_text(mermaid, encoding="utf-8")
        logger.info("Combined diagram written to %s", output_path)
        return output_path

    def generate_summary_markdown(self) -> str:
        """
        Return a Markdown string embedding all generated diagrams inline.
        Suitable for saving as a README or report.
        """
        local_tables = sorted(self.db.list_data_tables())
        states = {s["table_name"]: s for s in self.db.list_states()}

        rows_md = "\n".join(
            f"| `{t}` | {self.db.count_table(t):,} | "
            f"{states.get(t, {}).get('status', 'unknown')} |"
            for t in local_tables
        )

        inheritance_mmd = self._build_inheritance_mermaid_inline()
        reference_mmd = self._build_reference_mermaid_inline()

        return f"""# ServiceNow CMDB Extraction Report

## Tables Downloaded

| Table | Rows | Status |
|-------|------|--------|
{rows_md}

## Class Inheritance Diagram

```mermaid
{inheritance_mmd}
```

## Reference Relationships

```mermaid
{reference_mmd}
```
"""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_inheritance_mermaid_inline(self) -> str:
        local_tables = set(self.db.list_data_tables())
        lines = ["classDiagram"]
        for child, parents in sorted(self.rel_map.items()):
            if child not in local_tables:
                continue
            for parent in parents:
                lines.append(f"  {_safe(parent)} <|-- {_safe(child)}")
        return "\n".join(lines)

    def _build_reference_mermaid_inline(self) -> str:
        local_tables = set(self.db.list_data_tables())
        lines = ["erDiagram"]
        seen: set[tuple[str, str]] = set()
        for ref in self.ref_fields:
            src, dst, field = ref.get("table", ""), ref.get("references_table", ""), ref.get("field", "")
            if src not in local_tables or dst not in local_tables:
                continue
            key = (src, dst)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'  {_safe(src)} ||--o| {_safe(dst)} : "{field}"')
        return "\n".join(lines)


def _safe(name: str) -> str:
    """Return a Mermaid-safe identifier (replace hyphens/dots)."""
    return name.replace("-", "_").replace(".", "_")
