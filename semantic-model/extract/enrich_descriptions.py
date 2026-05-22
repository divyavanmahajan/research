#!/usr/bin/env python3
"""
enrich_descriptions.py — Use Claude to generate descriptions for undocumented tables/columns.

Only runs when enrichment.enabled = true in config.yaml.
Enriched descriptions are saved back into the raw JSON so build_model.py picks them up.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import anthropic
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

SYSTEM_PROMPT = """You are a data engineer writing concise, business-friendly descriptions for database columns and tables.
Given a table name, schema context, and column information, write clear 1-2 sentence descriptions.
Focus on what the field MEANS in business terms, not just restating the column name.
Be specific about units, date formats, or status values if inferable from the name or type.
Output only the description text with no preamble."""

TABLE_PROMPT = """Table: {full_name}
Type: {table_type}
Columns (names only): {column_names}

Write a 1-2 sentence business description for this table. What does each row represent?"""

COLUMN_PROMPT = """Table: {full_name}
Table description: {table_description}
Column: {col_name} ({col_type}){nullable}
Other columns in table: {other_cols}

Write a 1-2 sentence business description for this column."""


def needs_description(text: Optional[str]) -> bool:
    return not text or text.strip() == ""


def enrich_table(client: anthropic.Anthropic, table: dict, model: str) -> str:
    col_names = [c["name"] for c in table["columns"]]
    prompt = TABLE_PROMPT.format(
        full_name=table["full_name"],
        table_type=table["table_type"],
        column_names=", ".join(col_names[:30]),  # cap to avoid huge prompts
    )
    msg = client.messages.create(
        model=model,
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def enrich_column(client: anthropic.Anthropic, table: dict, col: dict, model: str) -> str:
    other_cols = [c["name"] for c in table["columns"] if c["name"] != col["name"]]
    nullable_str = " (nullable)" if col.get("nullable", True) else " (not null)"
    prompt = COLUMN_PROMPT.format(
        full_name=table["full_name"],
        table_description=table.get("comment") or "No table description available.",
        col_name=col["name"],
        col_type=col["data_type"],
        nullable=nullable_str,
        other_cols=", ".join(other_cols[:20]),
    )
    msg = client.messages.create(
        model=model,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def run_enrichment(cfg: dict, output_dir: Path):
    enrichment_cfg = cfg.get("enrichment", {})
    if not enrichment_cfg.get("enabled", False):
        console.print("[yellow]Enrichment is disabled in config (enrichment.enabled: false). Skipping.[/yellow]")
        return

    model = enrichment_cfg.get("model", "claude-haiku-4-5-20251001")
    only_missing = enrichment_cfg.get("only_missing", True)
    max_columns = enrichment_cfg.get("max_columns", 500)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    raw_dir = output_dir / "raw"
    enriched_tables = 0
    enriched_columns = 0
    columns_budget = max_columns

    for json_file in sorted(raw_dir.glob("**/_schema.json")):
        with open(json_file) as f:
            tables = json.load(f)

        changed = False
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
            task = progress.add_task(f"Enriching {json_file.parent.name}...", total=len(tables))

            for table in tables:
                if only_missing and needs_description(table.get("comment")):
                    progress.update(task, description=f"  Table: {table['name']}")
                    try:
                        table["comment"] = enrich_table(client, table, model)
                        enriched_tables += 1
                        changed = True
                    except Exception as e:
                        console.print(f"[yellow]Warning:[/yellow] Could not enrich table {table['full_name']}: {e}")

                for col in table["columns"]:
                    if columns_budget <= 0:
                        break
                    if only_missing and needs_description(col.get("comment")):
                        progress.update(task, description=f"  Col: {table['name']}.{col['name']}")
                        try:
                            col["comment"] = enrich_column(client, table, col, model)
                            enriched_columns += 1
                            columns_budget -= 1
                            changed = True
                        except Exception as e:
                            console.print(f"[yellow]Warning:[/yellow] Could not enrich {table['full_name']}.{col['name']}: {e}")

                progress.advance(task)

        if changed:
            with open(json_file, "w") as f:
                json.dump(tables, f, indent=2)

        if columns_budget <= 0:
            console.print(f"[yellow]Column budget exhausted ({max_columns} columns). Stopping enrichment.[/yellow]")
            break

    console.print(f"\n[green]Enrichment complete.[/green] Tables: {enriched_tables}, Columns: {enriched_columns}")


if __name__ == "__main__":
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    config_dir = config_path.parent
    output_dir = (config_dir / cfg.get("output_dir", "../model")).resolve()
    run_enrichment(cfg, output_dir)
