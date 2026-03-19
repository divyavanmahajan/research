# Implementation Plan: infomodel-dbt-generator

**Version:** 1.0
**Date:** 2026-03-17

---

## Overview

Five sequential phases. Each phase delivers a working, tested increment. Later phases depend on earlier ones. The library (Phase 1–3) must be complete and tested before the CLI (Phase 4) or Web UI (Phase 5) are built on top of it.

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
(Library)  (Generators) (Seeds)     (CLI)       (Web UI)
```

---

## Phase 1: Project Scaffold + Core Library

**Goal:** Establish the Python package structure, implement the YAML parser/validator, and define the internal domain model (Python dataclasses) that all generators consume.

**Deliverables:**
- `infomodeling/` Python package with `__init__.py`
- `infomodeling/model.py` — dataclasses: `ConceptualModel`, `Entity`, `Attribute`, `Relationship`
- `infomodeling/parser.py` — YAML → dataclasses with full validation
- `infomodeling/exceptions.py` — typed exceptions: `ModelValidationError`, `ParseError`
- `tests/test_parser.py` — unit tests covering valid and invalid YAML inputs
- `examples/org_model.yaml` — reference example conceptual model (10+ entities)
- `pyproject.toml` / `requirements.txt` — dependency declaration
- `docs/phases/phase1_progress.md` — phase summary

**Key tasks:**
1. Create `pyproject.toml` with `pyyaml`, `jsonschema`, `jinja2`, `faker`, `click`, `fastapi`, `uvicorn`, `pytest` dependencies
2. Define dataclasses in `model.py`
3. Implement `Parser.load(path) -> ConceptualModel` in `parser.py`
4. Implement validation: PK uniqueness, FK resolution, relationship target resolution, enum non-empty
5. Write 15+ unit tests; all pass

**Exit criteria:**
- `pytest tests/test_parser.py` → all green
- `Parser.load('examples/org_model.yaml')` returns a valid `ConceptualModel` with no errors
- Invalid YAML raises `ModelValidationError` with a human-readable message

---

## Phase 2: DBT Artifact Generators

**Goal:** Implement the four generators that transform a `ConceptualModel` into DBT files. Each generator is an independent, testable function.

**Deliverables:**
- `infomodeling/generators/sources.py` — `generate_sources_yml(model) -> str`
- `infomodeling/generators/staging.py` — `generate_staging_sql(entity) -> str`
- `infomodeling/generators/marts.py` — `generate_mart_sql(entity, model) -> str`
- `infomodeling/generators/schema.py` — `generate_schema_yml(model) -> str`
- `infomodeling/generators/project.py` — `generate_dbt_project_yml(model) -> str`, `generate_profiles_yml() -> str`
- `infomodeling/merger.py` — merge logic for regeneration (protected block strategy)
- `infomodeling/writer.py` — `write_project(model, output_dir, options)` orchestrates all generators and writes files
- `tests/test_generators.py` — unit tests for each generator
- `tests/test_merger.py` — tests for regeneration/merge logic
- `docs/phases/phase2_progress.md`

**Key tasks:**
1. Implement Jinja2 templates for staging SQL and mart SQL (in `infomodeling/templates/`)
2. Implement `generate_sources_yml` using PyYAML
3. Implement `generate_schema_yml` — map PK → unique+not_null, nullable → not_null, enum → accepted_values, FK → relationships
4. Implement mart generator: only for entities with `many_to_one` relationships; build join chain
5. Implement `merger.py`: parse `BEGIN GENERATED` / `END GENERATED` blocks; replace only that section
6. Implement `writer.py` orchestrator with `--dry-run` support
7. Integration test: load `examples/org_model.yaml` → write to temp dir → verify all files exist and are valid YAML/SQL

**Exit criteria:**
- `pytest tests/test_generators.py tests/test_merger.py` → all green
- Generated `schema.yml` is valid dbt YAML (parseable by PyYAML, correct structure)
- Generated SQL files are syntactically valid (basic SQL parse check)
- Regenerating the same model twice produces identical output (idempotency test)

---

## Phase 3: Seed Data Generator

**Goal:** Generate relational seed CSVs and a reproducible Python seed generation script from the conceptual model.

**Deliverables:**
- `infomodeling/seeds/generator.py` — `generate_seeds(model, rows, seed) -> dict[str, list[dict]]`
- `infomodeling/seeds/topological.py` — `topological_sort(model) -> list[Entity]` (Kahn's algorithm)
- `infomodeling/seeds/faker_mapper.py` — YAML type + field name heuristics → Faker provider
- `infomodeling/seeds/script_generator.py` — `generate_seed_script(model) -> str` (Python script as string)
- `tests/test_seeds.py` — unit tests for topological sort, FK consistency, determinism
- `docs/phases/phase3_progress.md`

**Key tasks:**
1. Implement `topological_sort`: build DAG from relationships; Kahn's algorithm; detect cycles and raise error
2. Implement `faker_mapper`: map `uuid` → `uuid4`, `string` + field name heuristics (`name`, `email`, `phone`, `address`) → appropriate Faker provider, `integer` → random int, `date` → Faker date, `timestamp` → Faker date_time, `enum` → random.choice(values)
3. Implement `generate_seeds`: iterate entities in topological order; for each FK field, sample from already-generated parent rows
4. Add `--seed-rows` and `--seed` options plumbed through to this generator
5. Implement `script_generator`: produce a standalone `generate_seeds.py` that embeds the model-derived logic
6. Determinism test: `generate_seeds(model, 50, seed=42)` called twice → identical output

**Exit criteria:**
- `pytest tests/test_seeds.py` → all green
- All FK values in generated CSVs reference valid PK values from parent CSVs
- `generate_seeds(model, 50, seed=42)` is deterministic across calls
- Topological sort correctly handles self-referential entities (nullable FK)

---

## Phase 4: CLI

**Goal:** Wire everything together into an `infomodel-dbt` command-line tool using Click.

**Deliverables:**
- `infomodeling/cli.py` — Click CLI with `generate`, `validate`, `diff`, `seed` commands
- `tests/test_cli.py` — CLI integration tests using Click's `CliRunner`
- Updated `pyproject.toml` with `[project.scripts]` entry point
- `docs/phases/phase4_progress.md`

**Commands:**

```
infomodel-dbt validate --model <path>
  → Parse + validate YAML; print errors/warnings; exit 0 on success, 1 on error

infomodel-dbt generate --model <path> --output <dir> [options]
  → Full generation pipeline; print file manifest on completion

infomodel-dbt diff --model <path> --output <dir>
  → Show which files would change without writing anything

infomodel-dbt seed --model <path> --output <dir> [--seed-rows N] [--seed INT]
  → (Re)generate seed CSVs only
```

**Key tasks:**
1. Define Click commands; wire to library functions
2. Add `--dry-run` flag to `generate` (calls `writer.py` with dry_run=True; prints file tree)
3. Add `--overwrite` flag (disables merge protection)
4. Pretty-print file manifest table on successful generate
5. Exit code 1 on validation errors; print error details to stderr
6. CLI integration tests: `CliRunner.invoke(generate, ['--model', 'examples/org_model.yaml', '--output', tmpdir])`

**Exit criteria:**
- `infomodel-dbt validate --model examples/org_model.yaml` exits 0 and prints "Model valid: 10 entities"
- `infomodel-dbt generate --model examples/org_model.yaml --output /tmp/test_dbt` writes all expected files
- `infomodel-dbt diff` reports no changes when run twice on same model
- All CLI tests pass

---

## Phase 5: Web UI

**Goal:** Build a FastAPI backend and React frontend for interactive model browsing, artifact preview, and zip download.

**Deliverables:**
- `infomodeling/api/` — FastAPI app with endpoints from spec §8.1
- `infomodeling/api/schemas.py` — Pydantic request/response models
- `web/` — React app (Vite + TypeScript)
  - `web/src/pages/Upload.tsx` — drag-and-drop YAML upload
  - `web/src/pages/Explorer.tsx` — entity graph (React Flow)
  - `web/src/pages/Preview.tsx` — file tree + syntax-highlighted content
  - `web/src/pages/Seeds.tsx` — table view of seed data
  - `web/src/pages/Download.tsx` — download zip
- `tests/test_api.py` — FastAPI TestClient tests for all endpoints
- `docs/phases/phase5_progress.md`

**Key tasks:**
1. FastAPI app: implement all 6 endpoints from spec
2. `/generate/download` endpoint: generate to in-memory `zipfile.ZipFile`; return as `StreamingResponse`
3. React app scaffolded with Vite; `npm create vite@latest web -- --template react-ts`
4. Implement Upload page: file drop → POST `/model/upload` → navigate to Explorer
5. Implement Explorer: render entity list with attributes; show relationships as edges using React Flow
6. Implement Preview: call POST `/generate/preview`; render file tree; show selected file with syntax highlighting (Prism.js or Shiki)
7. Implement Seeds: call POST `/seed/preview`; render per-entity data tables
8. Implement Download: call POST `/generate/download`; trigger browser download

**Exit criteria:**
- All API tests pass (`pytest tests/test_api.py`)
- Upload → Explorer → Preview → Download flow works end-to-end in browser
- Downloaded zip contains all expected DBT project files
- `dbt run` + `dbt test` on extracted zip succeeds against DuckDB

---

## Dependencies Between Phases

```
Phase 1 (model.py, parser.py)
    └──► Phase 2 (generators consume ConceptualModel dataclass)
              └──► Phase 3 (seeds consume same dataclass)
                        └──► Phase 4 (CLI calls generators + seeds)
                                  └──► Phase 5 (API wraps CLI logic)
```

Phases 2 and 3 can be developed in parallel once Phase 1 is complete.
Phase 5 backend can be developed in parallel with Phase 5 frontend once Phase 4 is complete.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| YAML parsing | `pyyaml` |
| Templating | `jinja2` |
| Validation | `jsonschema` |
| Fake data | `faker` |
| CLI | `click` |
| API | `fastapi` + `uvicorn` |
| API data models | `pydantic` |
| Frontend scaffold | Vite + React + TypeScript |
| Graph visualization | React Flow |
| Syntax highlighting | Shiki (frontend) |
| Testing | `pytest` + `httpx` (for FastAPI) |
| DBT integration | `dbt-core` + `dbt-duckdb` |
| Packaging | `pyproject.toml` (PEP 517) |

---

## Testing Strategy

| Level | Tool | Coverage target |
|-------|------|----------------|
| Unit (parser, generators, seeds) | pytest | ≥ 90% |
| CLI integration | Click CliRunner | All commands |
| API integration | FastAPI TestClient | All endpoints |
| End-to-end | `dbt run` + `dbt test` on generated project | 100% dbt test pass |

---

## File Layout (Final)

```
infomodeling/
  infomodeling/              # Python package
    __init__.py
    model.py
    parser.py
    exceptions.py
    merger.py
    writer.py
    generators/
      __init__.py
      sources.py
      staging.py
      marts.py
      schema.py
      project.py
    templates/
      staging.sql.j2
      mart.sql.j2
      dbt_project.yml.j2
    seeds/
      __init__.py
      generator.py
      topological.py
      faker_mapper.py
      script_generator.py
    api/
      __init__.py
      main.py
      schemas.py
    cli.py
  web/                       # React frontend
    src/
      pages/
      components/
  tests/
    test_parser.py
    test_generators.py
    test_merger.py
    test_seeds.py
    test_cli.py
    test_api.py
  examples/
    org_model.yaml
  docs/
    SPEC.md
    IMPLEMENTATION_PLAN.md
    phases/
      phase1_progress.md
      phase2_progress.md
      phase3_progress.md
      phase4_progress.md
      phase5_progress.md
  pyproject.toml
  README.md
```
