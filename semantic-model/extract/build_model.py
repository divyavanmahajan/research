#!/usr/bin/env python3
"""
build_model.py — Generate the layered semantic model from raw extracted JSON.

Reads:  model/raw/**/_schema.json  +  model/raw/_relationships.json
Writes:
  model/catalog_index.yaml          — compact index, always inject into LLM context
  model/relationships.md            — full join graph for complex queries
  model/glossary.md                 — placeholder for business terms
  model/tables/{schema}/{table}.md  — per-table detail (one file per table)
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_type(data_type: str) -> str:
    """Shorten verbose Spark/Delta types for readability."""
    return (data_type
            .replace("StringType", "STRING")
            .replace("LongType", "BIGINT")
            .replace("IntegerType", "INT")
            .replace("DoubleType", "DOUBLE")
            .replace("FloatType", "FLOAT")
            .replace("BooleanType", "BOOLEAN")
            .replace("TimestampType", "TIMESTAMP")
            .replace("DateType", "DATE"))


def _cardinality_symbol(cardinality: str) -> str:
    return {"many_to_one": "N:1", "one_to_one": "1:1", "one_to_many": "1:N"}.get(cardinality, "?:?")


def _domain_from_schema(schema: str) -> str:
    """Use the schema name as the domain label."""
    return schema


# ---------------------------------------------------------------------------
# Load raw data
# ---------------------------------------------------------------------------

def load_raw(output_dir: Path) -> tuple[list[dict], list[dict]]:
    raw_dir = output_dir / "raw"
    tables: list[dict] = []
    for f in sorted(raw_dir.glob("**/_schema.json")):
        with open(f) as fh:
            tables.extend(json.load(fh))

    rels_file = raw_dir / "_relationships.json"
    relationships = []
    if rels_file.exists():
        with open(rels_file) as fh:
            relationships = json.load(fh)

    return tables, relationships


# ---------------------------------------------------------------------------
# Build catalog_index.yaml
# ---------------------------------------------------------------------------

def build_index(tables: list[dict], relationships: list[dict], output_dir: Path):
    # Group tables by catalog > schema
    by_catalog: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for t in tables:
        by_catalog[t["catalog"]][t["schema"]].append(t)

    # Build relationship lookup: table → list of joined tables
    table_joins: dict[str, list[str]] = defaultdict(list)
    for r in relationships:
        table_joins[r["from_table"]].append(r["to_table"])
        # Mark the reverse direction too (for discovery)
        table_joins[r["to_table"]].append(r["from_table"])

    index = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Compact index of all tables and relationships. "
            "For column-level detail, load model/tables/{schema}/{table}.md"
        ),
        "catalogs": [],
    }

    for catalog_name, schemas in sorted(by_catalog.items()):
        catalog_entry = {"name": catalog_name, "schemas": []}
        for schema_name, schema_tables in sorted(schemas.items()):
            schema_entry = {
                "name": schema_name,
                "tables": [],
            }
            for t in sorted(schema_tables, key=lambda x: x["name"]):
                joins = sorted(set(table_joins.get(t["full_name"], [])))
                entry = {
                    "name": t["name"],
                    "full_name": t["full_name"],
                    "type": t["table_type"],
                    "description": t.get("comment") or "",
                    "columns": len(t["columns"]),
                    "detail_file": f"tables/{schema_name}/{t['name']}.md",
                }
                if joins:
                    entry["joins_to"] = joins
                if t.get("row_count"):
                    entry["approx_rows"] = t["row_count"]
                schema_entry["tables"].append(entry)
            catalog_entry["schemas"].append(schema_entry)
        index["catalogs"].append(catalog_entry)

    out_file = output_dir / "catalog_index.yaml"
    with open(out_file, "w") as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    console.print(f"[green]✓[/green] {out_file}")


# ---------------------------------------------------------------------------
# Build per-table Markdown files
# ---------------------------------------------------------------------------

def _render_table_md(table: dict, rels_for_table: list[dict], all_tables_index: dict[str, dict]) -> str:
    name = table["name"]
    schema = table["schema"]
    catalog = table["catalog"]
    full_name = table["full_name"]
    description = table.get("comment") or "_No description available._"
    table_type = table["table_type"]

    lines = [
        f"# {name}",
        "",
        f"**Full name:** `{full_name}`  ",
        f"**Type:** {table_type}  ",
        f"**Schema:** {schema}  ",
        f"**Catalog:** {catalog}",
        "",
        f"> {description}",
        "",
    ]

    if table.get("row_count"):
        lines += [f"**Approximate row count:** {table['row_count']:,}", ""]

    # Columns table
    lines += [
        "## Columns",
        "",
        "| # | Column | Type | Nullable | Description |",
        "|---|--------|------|----------|-------------|",
    ]

    # Build a set of FK columns for annotation
    fk_cols = {r["from_column"]: r for r in rels_for_table if r["from_table"] == full_name}

    for col in sorted(table["columns"], key=lambda c: c["position"]):
        col_name = col["name"]
        col_type = _fmt_type(col["data_type"])
        nullable = "YES" if col.get("nullable", True) else "NO"
        desc = col.get("comment") or ""

        # Annotate FK columns
        if col_name in fk_cols:
            rel = fk_cols[col_name]
            desc = (desc + f" FK → `{rel['to_table']}`.`{rel['to_column']}`").strip()

        # Escape pipe characters in description
        desc = desc.replace("|", "\\|")
        lines.append(f"| {col['position']} | `{col_name}` | {col_type} | {nullable} | {desc} |")

    lines.append("")

    # Relationships section
    outgoing = [r for r in rels_for_table if r["from_table"] == full_name]
    incoming = [r for r in rels_for_table if r["to_table"] == full_name]

    if outgoing or incoming:
        lines += ["## Relationships", ""]

    if outgoing:
        lines.append("**References (this table → other):**")
        lines.append("")
        for r in outgoing:
            card = _cardinality_symbol(r["cardinality"])
            conf = f" _{r['confidence']}_" if r["confidence"] != "explicit" else ""
            lines.append(f"- `{r['from_column']}` → `{r['to_table']}`.`{r['to_column']}` ({card}){conf}")
        lines.append("")

    if incoming:
        lines.append("**Referenced by (other tables → this):**")
        lines.append("")
        for r in incoming:
            card = _cardinality_symbol(r["cardinality"])
            lines.append(f"- `{r['from_table']}`.`{r['from_column']}` → `{r['to_column']}` ({card})")
        lines.append("")

    # Example JOIN snippets
    if outgoing:
        lines += ["## Example Joins", ""]
        for r in outgoing[:3]:  # cap at 3 examples
            to_alias = r["to_table"].split(".")[-1][:3]
            from_alias = name[:3]
            lines += [
                f"```sql",
                f"-- Join {name} to {r['to_table'].split('.')[-1]}",
                f"SELECT *",
                f"FROM {full_name} {from_alias}",
                f"JOIN {r['to_table']} {to_alias}",
                f"  ON {from_alias}.{r['from_column']} = {to_alias}.{r['to_column']}",
                f"```",
                "",
            ]

    # View definition (for views)
    if table.get("view_definition"):
        lines += [
            "## View Definition",
            "",
            "```sql",
            table["view_definition"],
            "```",
            "",
        ]

    return "\n".join(lines)


def build_table_files(tables: list[dict], relationships: list[dict], output_dir: Path):
    tables_dir = output_dir / "tables"

    # Index relationships by tables involved
    full_name_set = {t["full_name"] for t in tables}
    all_tables_index = {t["full_name"]: t for t in tables}

    for table in tables:
        full_name = table["full_name"]
        schema = table["schema"]
        name = table["name"]

        rels_for_table = [
            r for r in relationships
            if r["from_table"] == full_name or r["to_table"] == full_name
        ]

        md = _render_table_md(table, rels_for_table, all_tables_index)

        out_dir = tables_dir / schema
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{name}.md"
        with open(out_file, "w") as f:
            f.write(md)

    console.print(f"[green]✓[/green] {len(tables)} table files → {tables_dir}/")


# ---------------------------------------------------------------------------
# Build relationships.md
# ---------------------------------------------------------------------------

def build_relationships_md(tables: list[dict], relationships: list[dict], output_dir: Path):
    table_lookup = {t["full_name"]: t for t in tables}

    lines = [
        "# Table Relationships",
        "",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_  ",
        f"_{len(relationships)} relationships across {len(tables)} tables_",
        "",
        "## Join Map",
        "",
        "| From Table | From Column | To Table | To Column | Cardinality | Confidence |",
        "|------------|-------------|----------|-----------|-------------|------------|",
    ]

    for r in sorted(relationships, key=lambda x: (x["from_table"], x["from_column"])):
        card = _cardinality_symbol(r["cardinality"])
        lines.append(
            f"| `{r['from_table']}` | `{r['from_column']}` "
            f"| `{r['to_table']}` | `{r['to_column']}` "
            f"| {card} | {r['confidence']} |"
        )

    lines += ["", "## Join Paths by Schema", ""]

    # Group by schema pair
    by_schema: dict[str, list[dict]] = defaultdict(list)
    for r in relationships:
        from_schema = ".".join(r["from_table"].split(".")[:2])
        to_schema = ".".join(r["to_table"].split(".")[:2])
        key = from_schema if from_schema == to_schema else f"{from_schema} → {to_schema}"
        by_schema[key].append(r)

    for schema_pair, rels in sorted(by_schema.items()):
        lines += [f"### {schema_pair}", ""]
        for r in rels:
            from_name = r["from_table"].split(".")[-1]
            to_name = r["to_table"].split(".")[-1]
            lines.append(f"- `{from_name}.{r['from_column']}` → `{to_name}.{r['to_column']}`")
        lines.append("")

    out_file = output_dir / "relationships.md"
    with open(out_file, "w") as f:
        f.write("\n".join(lines))
    console.print(f"[green]✓[/green] {out_file}")


# ---------------------------------------------------------------------------
# Build glossary.md (starter template)
# ---------------------------------------------------------------------------

def build_glossary(output_dir: Path):
    out_file = output_dir / "glossary.md"
    if out_file.exists():
        console.print(f"[yellow]~[/yellow] {out_file} already exists, skipping (edit manually).")
        return

    content = """\
# Business Glossary

Map business terms to their physical table/column equivalents.
This file is maintained manually. Add entries as your team uses this model.

## Format

Each entry follows this pattern:

```
## <Business Term>

**Definition:** One sentence definition.
**Tables:** `catalog.schema.table` (column: `col_name`)
**Notes:** Any caveats, alternate terms, or related metrics.
```

---

## Example: Revenue

**Definition:** Total invoiced amount before discounts, in USD.
**Tables:** `main.sales.orders` (column: `total_amount`)
**Notes:** Use `net_amount` for post-discount revenue. Excludes cancelled orders (status = 'cancelled').

---

<!-- Add your business terms below this line -->
"""
    with open(out_file, "w") as f:
        f.write(content)
    console.print(f"[green]✓[/green] {out_file} (starter template)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import click

    @click.command()
    @click.option("--config", default="config.yaml", type=click.Path(exists=True))
    @click.option("--output", default=None)
    def run(config: str, output: Optional[str]):
        """Build the semantic model from raw extracted JSON."""
        with open(config) as f:
            cfg = yaml.safe_load(f)
        config_dir = Path(config).parent
        output_dir = Path(output) if output else config_dir / cfg.get("output_dir", "../model")
        output_dir = output_dir.resolve()

        console.print(f"\n[bold]Building Semantic Model[/bold] → {output_dir}\n")

        tables, relationships = load_raw(output_dir)
        if not tables:
            console.print("[red]No raw data found. Run extract_catalog.py first.[/red]")
            sys.exit(1)

        console.print(f"Loaded {len(tables)} tables, {len(relationships)} relationships.\n")

        build_index(tables, relationships, output_dir)
        build_table_files(tables, relationships, output_dir)
        build_relationships_md(tables, relationships, output_dir)
        build_glossary(output_dir)

        console.print(f"\n[bold green]Done.[/bold green]")
        console.print(f"  Index:         {output_dir}/catalog_index.yaml")
        console.print(f"  Table files:   {output_dir}/tables/")
        console.print(f"  Relationships: {output_dir}/relationships.md")
        console.print(f"  Glossary:      {output_dir}/glossary.md\n")

    run()


if __name__ == "__main__":
    main()
