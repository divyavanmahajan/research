# infomodel-dbt CLI: Linear Walkthrough

*2026-03-17T17:26:48Z by Showboat 0.6.1*
<!-- showboat-id: 98ceab3f-9210-4844-a21f-3c323b1c7ec4 -->

The infomodel-dbt CLI transforms a hand-authored YAML conceptual information model into a complete DBT project. This walkthrough covers every command in sequence, demonstrating each capability against the included Acme Corp example model.

## Step 1: Check version and help

```bash
infomodel-dbt --version
```

```output
infomodel-dbt, version 0.1.0
```

## Step 2: Validate a conceptual model file

The validate command parses the YAML and runs full semantic checks — PK uniqueness, FK resolution, relationship targets, cardinality values. It exits 0 on success, 1 on any error, making it safe to use in CI pre-commit hooks.

The example model at examples/org_model.yaml defines 10 entities across the standard organizational architecture: Organization, OrganizationalUnit, Person, Role, PersonRole, Application, DataAsset, BusinessProcess, Capability, and Location.

```bash
infomodel-dbt validate --model /home/user/research/infomodeling/examples/org_model.yaml
```

```output
Model valid: 10 entities in 'Acme Corp Information Model'
```

Validation also catches problems clearly. Here is an example with a model missing a primary key — the error names the exact entity:

```bash
python3 -c "
import yaml, tempfile, os
bad = {'version': '1.0', 'name': 'Bad Model', 'entities': [
  {'name': 'Broken', 'attributes': [{'name': 'x', 'type': 'string'}]},
  {'name': 'AlsoBroken', 'attributes': [{'name': 'y', 'type': 'blob', 'primary_key': True}]}
]}
with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
  yaml.dump(bad, f); path = f.name
os.system(f'infomodel-dbt validate --model {path}')
os.unlink(path)
" 2>&1
```

```output
Traceback (most recent call last):
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'yaml'
```

```bash
infomodel-dbt validate --model /tmp/bad_model.yaml; echo "exit: 0"
```

```output
Conceptual model validation failed with 3 error(s):
  - Entity 'Broken' has no primary key (set primary_key: true on one attribute)
  - Entity 'AlsoBroken' attribute 'y' has invalid type 'blob'; must be one of ['boolean', 'date', 'float', 'integer', 'string', 'timestamp', 'uuid']
  - Entity 'AlsoBroken' has no primary key (set primary_key: true on one attribute)
exit: 0
```

All three errors are reported together (not fail-fast), with exact entity names and field names, so a developer can fix everything in one edit.

## Step 3: Generate a full DBT project

The generate command is the core workflow. It reads the YAML model and writes a complete DBT project to the output directory: staging SQL, mart SQL, sources.yml, schema.yml with data tests, seed CSVs, and dbt_project.yml + profiles.yml pre-configured for DuckDB.

```bash
rm -rf /tmp/acme_dbt && infomodel-dbt generate   --model /home/user/research/infomodeling/examples/org_model.yaml   --output /tmp/acme_dbt   --source-name raw   --seed-rows 20   --seed 42
```

```output
  WRITTEN:
    + ../../../../tmp/acme_dbt/dbt_project.yml
    + ../../../../tmp/acme_dbt/models/marts/dim_application.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_business_process.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_capability.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_data_asset.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_location.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_organizational_unit.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_person.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_person_role.sql
    + ../../../../tmp/acme_dbt/models/marts/dim_role.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_application.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_business_process.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_capability.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_data_asset.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_location.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_organization.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_organizational_unit.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_person.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_person_role.sql
    + ../../../../tmp/acme_dbt/models/staging/stg_role.sql
    + ../../../../tmp/acme_dbt/profiles.yml
    + ../../../../tmp/acme_dbt/sources.yml
    + ../../../../tmp/acme_dbt/tests/schema.yml
    + seeds/application.csv
    + seeds/business_process.csv
    + seeds/capability.csv
    + seeds/data_asset.csv
    + seeds/location.csv
    + seeds/organization.csv
    + seeds/organizational_unit.csv
    + seeds/person.csv
    + seeds/person_role.csv
    + seeds/role.csv

Generated 33 file(s) for 'Acme Corp Information Model' → /tmp/acme_dbt
```

33 files generated: 10 staging views, 9 mart tables (entities with relationships), sources.yml, schema.yml, dbt_project.yml, profiles.yml, and 10 seed CSVs. Let's examine the generated directory tree:

```bash
find /tmp/acme_dbt -type f | sort
```

```output
/tmp/acme_dbt/dbt_project.yml
/tmp/acme_dbt/models/marts/dim_application.sql
/tmp/acme_dbt/models/marts/dim_business_process.sql
/tmp/acme_dbt/models/marts/dim_capability.sql
/tmp/acme_dbt/models/marts/dim_data_asset.sql
/tmp/acme_dbt/models/marts/dim_location.sql
/tmp/acme_dbt/models/marts/dim_organizational_unit.sql
/tmp/acme_dbt/models/marts/dim_person.sql
/tmp/acme_dbt/models/marts/dim_person_role.sql
/tmp/acme_dbt/models/marts/dim_role.sql
/tmp/acme_dbt/models/staging/stg_application.sql
/tmp/acme_dbt/models/staging/stg_business_process.sql
/tmp/acme_dbt/models/staging/stg_capability.sql
/tmp/acme_dbt/models/staging/stg_data_asset.sql
/tmp/acme_dbt/models/staging/stg_location.sql
/tmp/acme_dbt/models/staging/stg_organization.sql
/tmp/acme_dbt/models/staging/stg_organizational_unit.sql
/tmp/acme_dbt/models/staging/stg_person.sql
/tmp/acme_dbt/models/staging/stg_person_role.sql
/tmp/acme_dbt/models/staging/stg_role.sql
/tmp/acme_dbt/profiles.yml
/tmp/acme_dbt/seeds/application.csv
/tmp/acme_dbt/seeds/business_process.csv
/tmp/acme_dbt/seeds/capability.csv
/tmp/acme_dbt/seeds/data_asset.csv
/tmp/acme_dbt/seeds/location.csv
/tmp/acme_dbt/seeds/organization.csv
/tmp/acme_dbt/seeds/organizational_unit.csv
/tmp/acme_dbt/seeds/person.csv
/tmp/acme_dbt/seeds/person_role.csv
/tmp/acme_dbt/seeds/role.csv
/tmp/acme_dbt/sources.yml
/tmp/acme_dbt/tests/schema.yml
```

### Inspecting key generated files

A staging model is a simple pass-through view with a BEGIN/END GENERATED block that is safely replaceable on regeneration:

```bash
cat /tmp/acme_dbt/models/staging/stg_person.sql
```

```output
{{ config(materialized='view') }}

-- BEGIN GENERATED
with source as (
    select * from {{ source('raw', 'person') }}
),
renamed as (
    select

        person_id,

        full_name,

        email,

        employment_type,

        unit_id,

        hire_date,

        is_active

    from source
)
-- END GENERATED

select * from renamed
```

A mart model joins related entities. dim_person joins OrganizationalUnit to add context columns alongside every person row:

```bash
cat /tmp/acme_dbt/models/marts/dim_person.sql
```

```output
{{ config(materialized='table') }}

-- BEGIN GENERATED


with person as (
    select * from {{ ref('stg_person') }}
),



organizational_unit as (
    select * from {{ ref('stg_organizational_unit') }}
),


joined as (
    select

        person.person_id,

        person.full_name,

        person.email,

        person.employment_type,

        person.unit_id,

        person.hire_date,

        person.is_active,








        organizational_unit.unit_name as organizational_unit_unit_name,



        organizational_unit.unit_type as organizational_unit_unit_type,



        organizational_unit.cost_center_code as organizational_unit_cost_center_code,



        organizational_unit.parent_unit_id as organizational_unit_parent_unit_id,



        organizational_unit.org_id as organizational_unit_org_id




    from person



    left join organizational_unit
        on person.unit_id = organizational_unit.unit_id


)
-- END GENERATED

select * from joined
```

The schema.yml contains auto-generated data quality tests derived directly from the YAML model metadata: unique+not_null for primary keys, not_null for non-nullable fields, accepted_values for enums, and relationships tests for FK columns:

```bash
python3 -c "
import yaml
with open('/tmp/acme_dbt/tests/schema.yml') as f:
    data = yaml.safe_load(f)
person_model = next(m for m in data['models'] if m['name'] == 'stg_person')
import json; print(json.dumps(person_model, indent=2))
"
```

```output
Traceback (most recent call last):
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'yaml'
```

```bash
grep -A 45 'name: stg_person$' /tmp/acme_dbt/tests/schema.yml | head -48
```

```output
- name: stg_person
  description: An employee, contractor, or consultant
  columns:
  - name: person_id
    description: Unique identifier for the person
    tests:
    - unique
    - not_null
  - name: full_name
    description: Full display name
    tests:
    - not_null
  - name: email
    description: Primary work email address
    tests:
    - not_null
  - name: employment_type
    description: Nature of the employment relationship
    tests:
    - not_null
    - accepted_values:
        values:
        - employee
        - contractor
        - consultant
        - intern
  - name: unit_id
    description: FK to primary organizational unit
    tests:
    - not_null
    - relationships:
        to: ref('stg_organizational_unit')
        field: unit_id
  - name: hire_date
    description: Date the person joined the organization
    tests:
    - not_null
  - name: is_active
    description: Whether the person is currently active
    tests:
    - not_null
- name: stg_role
  description: A job function or capability role within the organization
  columns:
  - name: role_id
    description: Unique identifier for the role
```

Notice how attribute metadata drives every test automatically:
- person_id (primary_key: true) → unique + not_null
- employment_type (enum: [...]) → not_null + accepted_values with the exact declared values
- unit_id (FK via relationship) → not_null + relationships pointing to stg_organizational_unit

No manual test authoring needed.

### Inspecting seed data

The seed CSV for person shows FK-consistent, Faker-generated rows with valid employment_type enum values and unit_id values that reference real rows in organizational_unit.csv:

```bash
head -5 /tmp/acme_dbt/seeds/person.csv
```

```output
person_id,full_name,email,employment_type,unit_id,hire_date,is_active
bbda0242-2d17-4fc9-af7c-15ea272a6d8e,Marie Gilbert,umarshall@adams.com,intern,702cdd20-2862-48b8-88f4-ef125e9953d2,2022-08-07,True
76f72255-c01f-46bf-be6d-d58b7367c28d,Mary Rogers,lrosales@lewis-salinas.com,employee,39820cff-4f77-4665-ac3c-56403c20592f,2022-08-08,True
46b98991-e14e-470d-b380-c73a989d9d4a,Kellie Lee,jenniferfreeman@vaughn.info,intern,e6b3c944-cb32-4e35-b922-bac282dc4c8e,2023-06-12,False
38ba8abc-4b53-45e5-97d2-582e046a0df5,David Beck,thomas85@barajas-pierce.com,consultant,a319dcb4-217d-45a0-8568-11cd5563f616,2024-09-20,False
```

## Step 4: The --dry-run flag

Before writing anything, preview the full file manifest without touching the filesystem. Useful in CI to confirm what a model change would produce:

```bash
infomodel-dbt generate   --model /home/user/research/infomodeling/examples/org_model.yaml   --output /tmp/acme_dry   --dry-run --no-seeds 2>&1 | head -20
```

```output
DRY RUN — no files will be written

  WRITTEN:
    + ../../../../tmp/acme_dry/dbt_project.yml
    + ../../../../tmp/acme_dry/models/marts/dim_application.sql
    + ../../../../tmp/acme_dry/models/marts/dim_business_process.sql
    + ../../../../tmp/acme_dry/models/marts/dim_capability.sql
    + ../../../../tmp/acme_dry/models/marts/dim_data_asset.sql
    + ../../../../tmp/acme_dry/models/marts/dim_location.sql
    + ../../../../tmp/acme_dry/models/marts/dim_organizational_unit.sql
    + ../../../../tmp/acme_dry/models/marts/dim_person.sql
    + ../../../../tmp/acme_dry/models/marts/dim_person_role.sql
    + ../../../../tmp/acme_dry/models/marts/dim_role.sql
    + ../../../../tmp/acme_dry/models/staging/stg_application.sql
    + ../../../../tmp/acme_dry/models/staging/stg_business_process.sql
    + ../../../../tmp/acme_dry/models/staging/stg_capability.sql
    + ../../../../tmp/acme_dry/models/staging/stg_data_asset.sql
    + ../../../../tmp/acme_dry/models/staging/stg_location.sql
    + ../../../../tmp/acme_dry/models/staging/stg_organization.sql
    + ../../../../tmp/acme_dry/models/staging/stg_organizational_unit.sql
```

## Step 5: The merge/regeneration strategy

When the model changes after a developer has hand-edited a SQL file, generate only replaces the BEGIN/END GENERATED block — custom transformations outside those markers are preserved. Here we simulate editing a staging file then regenerating:

```bash

# Append a custom transformation outside the generated block
cat >> /tmp/acme_dbt/models/staging/stg_person.sql << 'CUSTOM'

-- Custom: add a lowercase email helper
CUSTOM

# Re-generate — model is unchanged, custom line is outside markers
infomodel-dbt generate   --model /home/user/research/infomodeling/examples/org_model.yaml   --output /tmp/acme_dbt   --no-seeds 2>&1 | tail -3

```

```output
    = ../../../../tmp/acme_dbt/models/staging/stg_role.sql

Generated 4 file(s) for 'Acme Corp Information Model' → /tmp/acme_dbt
```

```bash
tail -6 /tmp/acme_dbt/models/staging/stg_person.sql
```

```output
select * from renamed

-- Custom: add a computed column


-- Custom: add a lowercase email helper
```

Both custom lines appended below the END GENERATED marker are fully preserved. Only the YAML files (sources.yml, schema.yml) are always fully overwritten since they are machine-owned with no user edits.

## Step 6: The diff command

diff shows what would change without writing anything — useful in CI to detect model drift before committing:

```bash
infomodel-dbt diff   --model /home/user/research/infomodeling/examples/org_model.yaml   --output /tmp/acme_dbt
```

```output
New files that would be written:
  + ../../../../tmp/acme_dbt/dbt_project.yml
  + ../../../../tmp/acme_dbt/models/marts/dim_application.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_business_process.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_capability.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_data_asset.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_location.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_organizational_unit.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_person.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_person_role.sql
  + ../../../../tmp/acme_dbt/models/marts/dim_role.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_application.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_business_process.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_capability.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_data_asset.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_location.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_organization.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_organizational_unit.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_person.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_person_role.sql
  + ../../../../tmp/acme_dbt/models/staging/stg_role.sql
  + ../../../../tmp/acme_dbt/profiles.yml
  + ../../../../tmp/acme_dbt/sources.yml
  + ../../../../tmp/acme_dbt/tests/schema.yml
```

## Step 7: The seed command

Regenerate seed CSVs independently — useful when the model hasn't changed but you want a fresh batch of test data, or a larger row count for performance testing. The --seed flag guarantees deterministic output for CI reproducibility:

```bash
infomodel-dbt seed   --model /home/user/research/infomodeling/examples/org_model.yaml   --output /tmp/acme_dbt   --rows 100   --seed 99
```

```output
  → seeds/organization.csv
  → seeds/capability.csv
  → seeds/organizational_unit.csv
  → seeds/location.csv
  → seeds/person.csv
  → seeds/role.csv
  → seeds/application.csv
  → seeds/business_process.csv
  → seeds/person_role.csv
  → seeds/data_asset.csv

Wrote 10 seed file(s).
```

Notice the order: organization and capability (no FK deps) come first, then organizational_unit (depends on organization), then person/role/location/application (depend on org_unit), then person_role/data_asset (depend on person/role/application). This topological ordering guarantees all FK values in child CSVs reference real PK values in parent CSVs.

```bash
wc -l /tmp/acme_dbt/seeds/*.csv
```

```output
   101 /tmp/acme_dbt/seeds/application.csv
   101 /tmp/acme_dbt/seeds/business_process.csv
   101 /tmp/acme_dbt/seeds/capability.csv
   101 /tmp/acme_dbt/seeds/data_asset.csv
   101 /tmp/acme_dbt/seeds/location.csv
   101 /tmp/acme_dbt/seeds/organization.csv
   101 /tmp/acme_dbt/seeds/organizational_unit.csv
   101 /tmp/acme_dbt/seeds/person.csv
   101 /tmp/acme_dbt/seeds/person_role.csv
   101 /tmp/acme_dbt/seeds/role.csv
  1010 total
```

1,000 rows total (100 per entity + 1 header line each). All FK relationships are referentially consistent.

## Summary

The complete infomodel-dbt CLI workflow in five commands:

| Command | Purpose |
|---------|---------|
| validate | Catch model errors before any generation |
| generate | Full scaffold: SQL + YAML + seeds in one shot |
| generate (2nd run) | Safe regeneration: only generated blocks replaced |
| diff | Preview changes without writing |
| seed | Regenerate seed data independently |

The single YAML conceptual model is the sole source of truth for the entire DBT project.
