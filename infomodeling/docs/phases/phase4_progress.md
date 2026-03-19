# Phase 4 Progress: CLI Interface

**Status:** COMPLETE
**Date:** 2026-03-17
**Tests:** 14/14 passing

## Deliverables Completed

| File | Description |
|------|-------------|
| `infomodeling/cli.py` | Click CLI with `validate`, `generate`, `diff`, `seed` commands |
| `tests/test_cli.py` | 14 CLI integration tests using Click's CliRunner |
| `pyproject.toml` | Entry point: `infomodel-dbt = "infomodeling.cli:cli"` |

## Commands

```
infomodel-dbt validate --model <path>
  → Parse + validate; exit 0 on success, 1 on error

infomodel-dbt generate --model <path> --output <dir> [options]
  --source-name TEXT    DBT source name (default: raw)
  --seed-rows INT       Rows per entity (default: 50)
  --seed INT            Random seed
  --overwrite           Disable merge protection
  --dry-run             Print manifest; write nothing
  --include-seeds / --no-seeds

infomodel-dbt diff --model <path> --output <dir>
  → Show files that would change; write nothing

infomodel-dbt seed --model <path> --output <dir>
  --rows INT
  --seed INT
  --dry-run
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation error or parse error |
| 2 | Click usage error (missing required option) |

## Sample Output

```
$ infomodel-dbt generate --model examples/org_model.yaml --output ./out --seed 42

  WRITTEN:
    + dbt_project.yml
    + models/staging/stg_organization.sql
    + models/staging/stg_organizational_unit.sql
    ... (22 DBT files)
    + seeds/organization.csv
    + seeds/person.csv
    ... (10 seed CSVs)

Generated 32 file(s) for 'Acme Corp Information Model' → ./out
```
