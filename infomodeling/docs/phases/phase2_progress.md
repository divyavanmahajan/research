# Phase 2 Progress: DBT Artifact Generators

**Status:** COMPLETE
**Date:** 2026-03-17
**Tests:** 36/36 passing

## Deliverables Completed

| File | Description |
|------|-------------|
| `infomodeling/generators/sources.py` | `generate_sources_yml(model, source_name)` |
| `infomodeling/generators/staging.py` | `generate_staging_sql(entity, source_name)` |
| `infomodeling/generators/marts.py` | `generate_mart_sql(entity, model)` + `needs_mart(entity)` |
| `infomodeling/generators/schema.py` | `generate_schema_yml(model)` with full test generation |
| `infomodeling/generators/project.py` | `generate_dbt_project_yml(model)` + `generate_profiles_yml()` |
| `infomodeling/templates/staging.sql.j2` | Jinja2 template for staging SQL |
| `infomodeling/templates/mart.sql.j2` | Jinja2 template for mart SQL with joins |
| `infomodeling/merger.py` | Protected block merge strategy |
| `infomodeling/writer.py` | Orchestrator: writes full DBT project |
| `tests/test_generators.py` | 36 unit + integration tests |

## Test Generation Logic

| Attribute property | Generated test |
|-------------------|----------------|
| `primary_key: true` | `unique` + `not_null` |
| `nullable: false` (default) | `not_null` |
| `enum: [...]` | `accepted_values` |
| `via: <fk>` + `to: <entity>` (non-nullable) | `relationships` |

## Key Design Decisions

- Jinja2 templates live in `infomodeling/templates/` so they can be replaced/extended independently
- Mart models are only generated for entities with `many_to_one` relationships (`needs_mart()` guard)
- Self-referential joins (entity referencing itself) are skipped in mart generation to avoid circular CTEs
- `-- BEGIN GENERATED` / `-- END GENERATED` markers in every SQL file enable safe regeneration
- `writer.py` always overwrites YAML files (they are machine-owned); SQL files use merge strategy
- `dry_run=True` records what would be written without touching the filesystem

## Generated File Count for 10-entity Acme Corp model

- `dbt_project.yml`: 1
- `profiles.yml`: 1
- `sources.yml`: 1
- `tests/schema.yml`: 1
- `models/staging/stg_*.sql`: 10
- `models/marts/dim_*.sql`: 8 (entities with relationships)
- **Total: 22 files**
