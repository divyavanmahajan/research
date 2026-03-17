"""CLI for infomodel-dbt-generator."""

from __future__ import annotations

import os
import sys

import click

from . import parser
from .exceptions import ModelValidationError, ParseError
from .seeds.generator import write_seeds
from .writer import WriteOptions, write_project


@click.group()
@click.version_option(version="0.1.0", prog_name="infomodel-dbt")
def cli():
    """Generate DBT projects from conceptual information model YAML files."""


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="Path to conceptual model YAML")
def validate(model: str):
    """Validate a conceptual model YAML file."""
    try:
        m = parser.load(model)
        click.echo(click.style(
            f"Model valid: {len(m.entities)} entities in '{m.name}'", fg="green"
        ))
        sys.exit(0)
    except (ParseError, ModelValidationError) as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="Path to conceptual model YAML")
@click.option("--output", default="./dbt_project", show_default=True, help="Output directory")
@click.option("--source-name", default="raw", show_default=True, help="DBT source name")
@click.option("--seed-rows", default=50, show_default=True, type=int, help="Rows per entity in seed files")
@click.option("--seed", default=None, type=int, help="Random seed for deterministic seed data")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing files (no merge protection)")
@click.option("--dry-run", is_flag=True, default=False, help="Print what would be generated; write nothing")
@click.option("--include-seeds/--no-seeds", default=True, show_default=True, help="Also generate seed CSV files")
def generate(model: str, output: str, source_name: str, seed_rows: int, seed: int | None,
             overwrite: bool, dry_run: bool, include_seeds: bool):
    """Generate a full DBT project from a conceptual model YAML."""
    try:
        m = parser.load(model)
    except (ParseError, ModelValidationError) as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    opts = WriteOptions(source_name=source_name, overwrite=overwrite, dry_run=dry_run)

    if dry_run:
        click.echo(click.style("DRY RUN — no files will be written\n", fg="yellow"))

    result = write_project(m, output, opts)

    seed_written: list[str] = []
    if include_seeds:
        seed_written = write_seeds(m, output, rows_per_entity=seed_rows, seed=seed, dry_run=dry_run)

    # Print manifest
    all_written = result.written + seed_written
    if all_written:
        click.echo(click.style("  WRITTEN", fg="green") + ":")
        for f in sorted(all_written):
            click.echo(f"    + {f}")
    if result.merged:
        click.echo(click.style("  MERGED", fg="cyan") + " (generated block updated, custom code preserved):")
        for f in sorted(result.merged):
            click.echo(f"    ~ {f}")
    if result.skipped:
        click.echo(click.style("  SKIPPED", fg="white", dim=True) + " (no changes):")
        for f in sorted(result.skipped):
            click.echo(f"    = {f}")

    total = len(all_written) + len(result.merged)
    action = "Would generate" if dry_run else "Generated"
    click.echo(click.style(
        f"\n{action} {total} file(s) for '{m.name}' → {output}",
        fg="green" if not dry_run else "yellow",
    ))


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="Path to conceptual model YAML")
@click.option("--output", default="./dbt_project", show_default=True, help="Existing output directory to compare against")
@click.option("--source-name", default="raw", show_default=True)
def diff(model: str, output: str, source_name: str):
    """Show what would change if regenerating from the model. Writes nothing."""
    try:
        m = parser.load(model)
    except (ParseError, ModelValidationError) as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    opts = WriteOptions(source_name=source_name, dry_run=True)
    result = write_project(m, output, opts)

    if not result.written and not result.merged:
        click.echo(click.style("No changes. Output is up to date.", fg="green"))
    else:
        if result.written:
            click.echo("New files that would be written:")
            for f in sorted(result.written):
                click.echo(f"  + {f}")
        if result.merged:
            click.echo("Files with generated block changes:")
            for f in sorted(result.merged):
                click.echo(f"  ~ {f}")


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="Path to conceptual model YAML")
@click.option("--output", default="./dbt_project", show_default=True, help="DBT project directory")
@click.option("--rows", default=50, show_default=True, type=int, help="Rows per entity")
@click.option("--seed", default=None, type=int, help="Random seed for deterministic output")
@click.option("--dry-run", is_flag=True, default=False)
def seed(model: str, output: str, rows: int, seed: int | None, dry_run: bool):
    """(Re)generate seed CSV files only."""
    try:
        m = parser.load(model)
    except (ParseError, ModelValidationError) as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    written = write_seeds(m, output, rows_per_entity=rows, seed=seed, dry_run=dry_run)

    for f in written:
        click.echo(f"  {'(dry) ' if dry_run else ''}→ {f}")

    click.echo(f"\n{'Would write' if dry_run else 'Wrote'} {len(written)} seed file(s).")
