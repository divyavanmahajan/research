# Product Specification: Information Conceptual Model → DBT Generation Pipeline

**Version:** 1.0
**Date:** 2026-03-17
**Status:** Draft

---

## 1. Overview

`infomodel-dbt-generator` is a model-driven code generation tool that transforms a hand-authored YAML conceptual information model into a fully structured, runnable DBT project — including staging SQL models, mart SQL models, `sources.yml`, `schema.yml` with data quality tests, and relational seed data for testing.

The tool is delivered as three interoperable components sharing a common Python core library:

| Component | Description |
|-----------|-------------|
| **Python library** | Core engine: parse, validate, generate — importable by pipelines |
| **CLI** | `infomodel-dbt generate` — human and CI/CD entrypoint |
| **Web UI** | FastAPI backend + React frontend for interactive model browsing and artifact preview |

---

## 2. Problem Statement

Enterprise architects define conceptual information models in EA tools (TOGAF, LeanIX, MEGA HOPEX) or in diagrams. These models describe **what** information the organization has — entities, attributes, relationships, cardinality — but the journey from that model to a running data warehouse schema requires weeks of manual DBT authoring.

The gap:
- EA model → hand-typed staging SQL → hand-typed mart SQL → hand-typed schema.yml tests → manually written seed data → run `dbt test`
- Errors accumulate at each hand-off; the conceptual model and the physical DBT project diverge over time

This tool collapses the entire chain into a **single source of truth**: the YAML conceptual model.

---

## 3. Users and Use Cases

| User | Use Case |
|------|----------|
| Enterprise Architect | Author the YAML model; preview the generated DBT project in the web UI before committing |
| Data Engineer | Bootstrap a new DBT project from an EA model; run CI regeneration on model changes |
| CI/CD Pipeline | `infomodel-dbt generate` on every commit to the model YAML; diff output; merge non-destructively |
| Data Analyst | Use the generated seed data to write and test DBT analyses locally with DuckDB |

---

## 4. Conceptual Model YAML Format

### 4.1 File Structure

```yaml
version: "1.0"
name: "Organization Name Information Model"
description: "Optional description"

entities:
  - name: EntityName              # PascalCase; becomes snake_case in SQL
    description: "..."
    attributes:
      - name: field_name          # snake_case
        type: string | integer | float | boolean | date | timestamp | uuid
        primary_key: true         # optional; exactly one per entity
        nullable: false           # default: false
        description: "..."        # optional; becomes dbt column description
        enum: [val1, val2]        # optional; drives accepted_values test
    relationships:
      - to: OtherEntityName
        via: foreign_key_field    # must reference a field in this entity's attributes
        cardinality: many_to_one | one_to_many | many_to_many | one_to_one
        type: self_referential    # optional; for recursive FKs
```

### 4.2 Supported Data Types

| YAML type | SQL (generic) | DuckDB |
|-----------|--------------|--------|
| `string` | `VARCHAR` | `VARCHAR` |
| `integer` | `INTEGER` | `INTEGER` |
| `float` | `DOUBLE` | `DOUBLE` |
| `boolean` | `BOOLEAN` | `BOOLEAN` |
| `date` | `DATE` | `DATE` |
| `timestamp` | `TIMESTAMP` | `TIMESTAMP` |
| `uuid` | `VARCHAR` | `VARCHAR` |

### 4.3 Validation Rules

The parser enforces:
- Each entity has exactly one `primary_key: true` attribute
- All `via` foreign key fields reference a declared attribute name in the same entity
- All `to` relationship targets reference a declared entity name in the same model file
- `enum` values must be non-empty strings
- Entity names must be unique; attribute names within an entity must be unique
- `cardinality` must be one of the four allowed values

---

## 5. Generated DBT Artifacts

### 5.1 Directory Layout

```
<output_dir>/
  dbt_project.yml
  profiles.yml                  # DuckDB profile pre-configured
  sources.yml                   # All entities as raw sources
  models/
    staging/
      stg_<entity>.sql          # One per entity
      stg_<entity>.yml          # Column-level docs (embedded in schema.yml alt.)
    marts/
      dim_<entity>.sql          # One per entity with relationships → joins
  tests/
    schema.yml                  # All data quality tests
  seeds/
    <entity>.csv                # One per entity; topologically ordered
  seed_generators/
    generate_seeds.py           # Reproducible; accepts --seed <int>
  docs/
    GENERATED.md                # What was generated, from which model version
```

### 5.2 `sources.yml`

Each entity → one source table under a configurable source name (default: `raw`).

```yaml
version: 2
sources:
  - name: raw
    tables:
      - name: organizational_unit
        columns:
          - name: unit_id
            description: "Primary key"
          - name: unit_name
```

### 5.3 Staging SQL (`stg_<entity>.sql`)

- Materialized as `view` by default
- Renames columns only if needed (pass-through pattern)
- Adds `_loaded_at` metadata column
- References `{{ source('raw', '<entity>') }}`

```sql
{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'organizational_unit') }}
),
renamed as (
    select
        unit_id,
        unit_name,
        parent_unit_id,
        unit_type,
        cost_center_code,
        current_timestamp as _loaded_at
    from source
)
select * from renamed
```

### 5.4 Mart SQL (`dim_<entity>.sql`)

- Materialized as `table` by default
- Generated only for entities with `relationships`
- Joins to each `many_to_one` related entity via `{{ ref('stg_<related>') }}`
- Selects all columns from the primary entity + descriptive (non-FK) columns from related entities

```sql
{{ config(materialized='table') }}

with persons as (
    select * from {{ ref('stg_person') }}
),
org_units as (
    select * from {{ ref('stg_organizational_unit') }}
),
joined as (
    select
        p.person_id,
        p.full_name,
        p.email,
        p.employment_type,
        o.unit_name,
        o.unit_type
    from persons p
    left join org_units o on p.unit_id = o.unit_id
)
select * from joined
```

### 5.5 `schema.yml` (Data Quality Tests)

Generated automatically from attribute metadata:

| Attribute property | Generated test |
|-------------------|----------------|
| `primary_key: true` | `unique` + `not_null` |
| `nullable: false` (default) | `not_null` |
| `enum: [...]` | `accepted_values` |
| `via: <fk>` + `to: <entity>` | `relationships` |

```yaml
version: 2
models:
  - name: stg_organizational_unit
    description: "A department or team within the organization"
    columns:
      - name: unit_id
        description: "Primary key"
        tests:
          - unique
          - not_null
      - name: unit_type
        tests:
          - accepted_values:
              values: ['department', 'team', 'division', 'subsidiary']
      - name: parent_unit_id
        tests:
          - relationships:
              to: ref('stg_organizational_unit')
              field: unit_id
```

### 5.6 Seed Data

- **50 rows** per entity by default (configurable via `--seed-rows`)
- Topological generation order: entities with no FK dependencies first
- Faker-based values per type; enums drawn randomly from declared values
- FK values are sampled from already-generated parent seed rows
- Deterministic with `--seed <int>` flag
- Output: one CSV per entity in `seeds/`

---

## 6. Merge / Regeneration Strategy (Scaffold + Regenerate mode)

To preserve manual edits when the model changes, the generator uses a **protected block** convention:

```sql
-- BEGIN GENERATED
{{ config(materialized='view') }}
with source as (
    select * from {{ source('raw', 'organizational_unit') }}
),
-- END GENERATED

-- Your custom transformations below this line are preserved on regeneration
renamed as (
    select *, my_custom_column from source
)
select * from renamed
```

Rules:
1. On first generation: full file is written
2. On regeneration: only the `BEGIN GENERATED` → `END GENERATED` block is replaced
3. Anything outside those markers is preserved verbatim
4. `schema.yml` is always fully regenerated (it is machine-owned)
5. A `GENERATED.md` diff summary is written on each run

---

## 7. CLI Interface

```
infomodel-dbt [OPTIONS] COMMAND

Commands:
  generate    Generate a full DBT project from a conceptual model YAML
  validate    Validate a conceptual model YAML (no output written)
  diff        Show what would change if regenerating from a new model version
  seed        (Re)generate seed CSVs only

Options for generate:
  --model PATH          Path to conceptual model YAML (required)
  --output PATH         Output directory (default: ./dbt_project)
  --source-name TEXT    DBT source name (default: raw)
  --seed-rows INT       Rows per entity in seed files (default: 50)
  --seed INT            Random seed for deterministic seed data
  --warehouse TEXT      Target warehouse hint: duckdb | generic (default: generic)
  --overwrite           Overwrite existing files (no merge protection)
  --dry-run             Print what would be generated; write nothing
```

---

## 8. Web UI

### 8.1 Backend (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/model/upload` | POST | Upload YAML; returns parsed model JSON |
| `/model/validate` | POST | Validate YAML; returns errors/warnings |
| `/model/entities` | GET | List all entities and their attributes |
| `/generate/preview` | POST | Generate all artifacts; return as in-memory zip |
| `/generate/download` | POST | Generate and return zip file download |
| `/seed/preview` | POST | Preview first 10 rows of seed data per entity |

### 8.2 Frontend (React)

Pages:
1. **Upload Model** — drag-and-drop YAML upload with live validation feedback
2. **Model Explorer** — entity/relationship graph visualization (using React Flow or D3)
3. **Artifact Preview** — file tree on left, syntax-highlighted file content on right
4. **Seed Preview** — table view of generated seed data per entity
5. **Download** — download full DBT project as zip

---

## 9. Non-Functional Requirements

| Concern | Requirement |
|---------|-------------|
| **Correctness** | Generated `dbt test` must pass 100% on generated seed data |
| **Determinism** | Same YAML + same `--seed` always produces identical output |
| **Idempotency** | Running generate twice on the same model produces no diff |
| **Performance** | Generate for a 50-entity model in < 5 seconds |
| **Test coverage** | Library core: ≥ 90% line coverage |
| **Python version** | 3.10+ |
| **DBT version** | dbt-core 1.7+ |

---

## 10. Out of Scope (v1)

- Import from LeanIX / MEGA HOPEX (post-v1)
- Many-to-many bridge table generation (post-v1)
- SCD Type 2 history models (post-v1)
- Snowflake / BigQuery dialect support (post-v1, generic SQL covers most cases)
- Authentication for Web UI (post-v1)
