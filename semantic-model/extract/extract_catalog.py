#!/usr/bin/env python3
"""
extract_catalog.py — Pull raw schema metadata from Unity Catalog via Databricks SDK.

Outputs a JSON file per schema: model/raw/{catalog}/{schema}.json
These raw files are the input for build_model.py.
"""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import click
import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import TableType
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class ColumnMeta:
    name: str
    data_type: str
    comment: Optional[str]
    nullable: bool
    position: int
    partition_index: Optional[int] = None


@dataclass
class TableMeta:
    catalog: str
    schema: str
    name: str
    full_name: str  # catalog.schema.table
    table_type: str  # MANAGED, EXTERNAL, VIEW, etc.
    comment: Optional[str]
    columns: list[ColumnMeta] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    storage_location: Optional[str] = None
    view_definition: Optional[str] = None
    row_count: Optional[int] = None


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_client(cfg: dict) -> WorkspaceClient:
    host = cfg["databricks"].get("host") or os.environ.get("DATABRICKS_HOST", "")
    token = cfg["databricks"].get("token") or os.environ.get("DATABRICKS_TOKEN", "")

    if not host:
        console.print("[red]Error:[/red] DATABRICKS_HOST not set in config or environment.")
        sys.exit(1)
    if not token:
        console.print("[red]Error:[/red] DATABRICKS_TOKEN not set in config or environment.")
        sys.exit(1)

    return WorkspaceClient(host=host, token=token)


def list_target_schemas(client: WorkspaceClient, target: dict) -> list[tuple[str, str]]:
    """Returns list of (catalog, schema) pairs to extract."""
    catalog_name = target["catalog"]
    schema_patterns = target.get("schemas", ["*"])

    pairs = []
    try:
        schemas = list(client.schemas.list(catalog_name=catalog_name))
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not list schemas in {catalog_name}: {e}")
        return []

    for schema in schemas:
        if schema.name in ("information_schema",):
            continue
        if "*" in schema_patterns or schema.name in schema_patterns:
            pairs.append((catalog_name, schema.name))

    return pairs


def extract_table(client: WorkspaceClient, catalog: str, schema: str, table_name: str) -> Optional[TableMeta]:
    full_name = f"{catalog}.{schema}.{table_name}"
    try:
        t = client.tables.get(full_name=full_name)
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not get table {full_name}: {e}")
        return None

    columns = []
    for col in sorted(t.columns or [], key=lambda c: c.position or 0):
        columns.append(ColumnMeta(
            name=col.name,
            data_type=col.type_text or str(col.type_name),
            comment=col.comment,
            nullable=col.nullable if col.nullable is not None else True,
            position=col.position or 0,
            partition_index=col.partition_index,
        ))

    row_count = None
    if t.properties:
        # Unity Catalog sometimes stores stats in properties
        row_count_str = t.properties.get("delta.stats.numRecords") or t.properties.get("numRows")
        if row_count_str:
            try:
                row_count = int(row_count_str)
            except ValueError:
                pass

    return TableMeta(
        catalog=catalog,
        schema=schema,
        name=table_name,
        full_name=full_name,
        table_type=str(t.table_type or TableType.MANAGED),
        comment=t.comment,
        columns=columns,
        properties=dict(t.properties or {}),
        storage_location=t.storage_location,
        view_definition=t.view_definition,
        row_count=row_count,
    )


def extract_schema(
    client: WorkspaceClient,
    catalog: str,
    schema: str,
    output_dir: Path,
) -> list[TableMeta]:
    raw_dir = output_dir / "raw" / catalog / schema
    raw_dir.mkdir(parents=True, exist_ok=True)

    try:
        tables = list(client.tables.list(catalog_name=catalog, schema_name=schema))
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not list tables in {catalog}.{schema}: {e}")
        return []

    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task(f"  Extracting {catalog}.{schema} ({len(tables)} tables)...", total=len(tables))
        for t in tables:
            progress.update(task, description=f"  {catalog}.{schema}.{t.name}")
            meta = extract_table(client, catalog, schema, t.name)
            if meta:
                results.append(meta)
            progress.advance(task)

    # Save raw JSON for this schema
    output_file = raw_dir / "_schema.json"
    with open(output_file, "w") as f:
        json.dump([asdict(m) for m in results], f, indent=2)

    console.print(f"  [green]✓[/green] {catalog}.{schema}: {len(results)} tables → {output_file}")
    return results


@click.command()
@click.option("--config", default="config.yaml", help="Path to config.yaml", type=click.Path(exists=True))
@click.option("--output", default=None, help="Override output directory from config")
def main(config: str, output: Optional[str]):
    """Extract Unity Catalog metadata and save raw JSON files."""
    cfg = load_config(Path(config))
    config_dir = Path(config).parent
    output_dir = Path(output) if output else config_dir / cfg.get("output_dir", "../model")
    output_dir = output_dir.resolve()

    console.print(f"\n[bold]Unity Catalog Extractor[/bold]")
    console.print(f"Output: {output_dir}\n")

    client = get_client(cfg)

    all_tables: list[TableMeta] = []
    for target in cfg.get("targets", []):
        catalog = target["catalog"]
        console.print(f"[bold blue]Catalog:[/bold blue] {catalog}")
        for cat, schema in list_target_schemas(client, target):
            tables = extract_schema(client, cat, schema, output_dir)
            all_tables.extend(tables)

    console.print(f"\n[bold green]Done.[/bold green] Extracted {len(all_tables)} tables total.")
    console.print("Next step: run [bold]build_model.py[/bold] to generate the semantic model.\n")


if __name__ == "__main__":
    main()
