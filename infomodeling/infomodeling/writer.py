"""Orchestrator: write a full DBT project from a ConceptualModel."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .generators.marts import generate_mart_sql, needs_mart
from .generators.project import generate_dbt_project_yml, generate_profiles_yml, _to_project_name
from .generators.schema import generate_schema_yml
from .generators.sources import generate_sources_yml
from .generators.staging import generate_staging_sql
from .merger import has_markers, merge
from .model import ConceptualModel


@dataclass
class WriteOptions:
    source_name: str = "raw"
    overwrite: bool = False
    dry_run: bool = False


@dataclass
class WriteResult:
    written: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def write_project(model: ConceptualModel, output_dir: str, options: WriteOptions | None = None) -> WriteResult:
    """Generate and write a complete DBT project to output_dir."""
    if options is None:
        options = WriteOptions()

    result = WriteResult()
    project_name = _to_project_name(model.name)

    files: dict[str, str] = {}

    # dbt_project.yml
    files["dbt_project.yml"] = generate_dbt_project_yml(model)

    # profiles.yml
    files["profiles.yml"] = generate_profiles_yml(project_name)

    # sources.yml
    files["sources.yml"] = generate_sources_yml(model, options.source_name)

    # schema.yml (tests)
    files[os.path.join("tests", "schema.yml")] = generate_schema_yml(model)

    # Staging SQL — one per entity
    for entity in model.entities:
        path = os.path.join("models", "staging", f"stg_{entity.snake_name}.sql")
        files[path] = generate_staging_sql(entity, options.source_name)

    # Mart SQL — one per entity with relationships
    for entity in model.entities:
        if needs_mart(entity):
            path = os.path.join("models", "marts", f"dim_{entity.snake_name}.sql")
            files[path] = generate_mart_sql(entity, model)

    # Write files
    for rel_path, content in files.items():
        full_path = os.path.join(output_dir, rel_path)
        _write_file(full_path, content, options, result)

    return result


def _write_file(full_path: str, new_content: str, options: WriteOptions, result: WriteResult) -> None:
    rel = os.path.relpath(full_path)

    if options.dry_run:
        result.written.append(rel)
        return

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    if os.path.exists(full_path) and not options.overwrite:
        existing = open(full_path).read()
        if has_markers(existing) and has_markers(new_content):
            merged = merge(existing, new_content)
            if merged != existing:
                with open(full_path, "w") as f:
                    f.write(merged)
                result.merged.append(rel)
            else:
                result.skipped.append(rel)
            return
        else:
            # schema.yml and YAML files: always overwrite
            with open(full_path, "w") as f:
                f.write(new_content)
            result.written.append(rel)
            return

    with open(full_path, "w") as f:
        f.write(new_content)
    result.written.append(rel)
