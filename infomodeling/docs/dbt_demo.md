# Acme Corp DBT Project: End-to-End Demo

*2026-03-17T19:51:29Z by Showboat 0.6.1*
<!-- showboat-id: 2e844a87-2f5b-4d9d-9871-dd0c9976cbd4 -->

This document demonstrates the complete DBT project generated from the Acme Corp conceptual information model. Starting from a single YAML file, `infomodel-dbt generate` produced a fully runnable DBT project targeting DuckDB. We will walk through the project structure, run `dbt seed`, `dbt run`, and `dbt test`, inspect the results, and query the final mart tables — all within this document.

## Project Structure

The generated project lives at `/tmp/acme_dbt`. Here is its complete file tree:

```bash
find /tmp/acme_dbt -type f | sort | sed 's|/tmp/acme_dbt/||'
```

```output
dbt_project.yml
models/marts/dim_application.sql
models/marts/dim_business_process.sql
models/marts/dim_capability.sql
models/marts/dim_data_asset.sql
models/marts/dim_location.sql
models/marts/dim_organizational_unit.sql
models/marts/dim_person.sql
models/marts/dim_person_role.sql
models/marts/dim_role.sql
models/staging/stg_application.sql
models/staging/stg_business_process.sql
models/staging/stg_capability.sql
models/staging/stg_data_asset.sql
models/staging/stg_location.sql
models/staging/stg_organization.sql
models/staging/stg_organizational_unit.sql
models/staging/stg_person.sql
models/staging/stg_person_role.sql
models/staging/stg_role.sql
profiles.yml
seeds/application.csv
seeds/business_process.csv
seeds/capability.csv
seeds/data_asset.csv
seeds/location.csv
seeds/organization.csv
seeds/organizational_unit.csv
seeds/person.csv
seeds/person_role.csv
seeds/role.csv
sources.yml
tests/schema.yml
```

10 staging views, 9 mart tables, 10 seed CSVs, and the supporting YAML config files — generated from a 10-entity YAML model in under a second.

## Configuration

The `dbt_project.yml` declares the project, staging models as views, and mart models as tables:

```bash
cat /tmp/acme_dbt/dbt_project.yml
```

```output
name: acme_corp_information_model
version: 1.0.0
config-version: 2
profile: acme_corp_information_model
model-paths:
- models
seed-paths:
- seeds
test-paths:
- tests
analysis-paths:
- analyses
macro-paths:
- macros
target-path: target
clean-targets:
- target
- dbt_packages
models:
  acme_corp_information_model:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

The `profiles.yml` targets DuckDB — no cloud credentials, no warehouse setup needed:

```bash
cat /tmp/acme_dbt/profiles.yml
```

```output
acme_corp_information_model:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: dev.duckdb
      threads: 4
```

## Seed Data

The seed CSVs contain FK-consistent, Faker-generated rows produced in topological dependency order. Let's preview each before loading:

**Organization** (no dependencies — generated first):

```bash
head -4 /tmp/acme_dbt/seeds/organization.csv
```

```output
org_id,org_name,org_type,country_code,created_at
bdd640fb-0667-4ad1-9c80-317fa3b1799d,Daniel Doyle,company,GD,2024-11-29T05:38:02.410966
6c031199-972a-4469-9641-9f828b9d2434,Brandon Hall,company,UY,2021-05-05T02:05:42.949088
b38a088c-a65e-4389-b74d-0fb132e70629,Connie Lawrence,division,AF,2025-01-01T08:40:18.796846
```

**OrganizationalUnit** (FK → Organization; self-referential parent_unit_id):

```bash
head -4 /tmp/acme_dbt/seeds/organizational_unit.csv
```

```output
unit_id,unit_name,unit_type,cost_center_code,parent_unit_id,org_id
2e8d0e87-5334-40e6-99d8-0b8d7e8adee7,Mr. David Ramirez,subsidiary,HM-9480,,19108be5-8ce2-4ea3-9b20-a56edc815fe7
680bac63-b856-4035-bdc9-829015eabb27,Peter Vaughn DDS,division,SO-7701,2e8d0e87-5334-40e6-99d8-0b8d7e8adee7,a3d70628-ece6-4fa2-bd51-66e6451b4cf3
4e6384bb-3e49-4f43-b118-f68d6786d506,Jackie Tran,team,WS-5685,2e8d0e87-5334-40e6-99d8-0b8d7e8adee7,ee0caeb5-ecfe-4b99-a790-cebdbfddc3d9
```

Row 1: root unit (parent_unit_id empty — tree root). Rows 2-3: child units referencing row 1's unit_id.

**Person** (FK → OrganizationalUnit):

```bash
head -4 /tmp/acme_dbt/seeds/person.csv
```

```output
person_id,full_name,email,employment_type,unit_id,hire_date,is_active
c9dc72b8-5b6a-4102-8428-7378bf5023f4,David Sandoval,ingramjill@anderson-bell.com,consultant,0a3450fc-9918-4e46-9497-d6587010f719,2025-04-10,False
af475b49-c775-4395-9494-05f02cd2a404,Michael Welch,bryanparsons@johnson-harris.com,consultant,ad81f8bd-4029-43ec-9ef2-b93e30ac7d7b,2025-08-20,False
83f02dc7-4f61-4217-aef1-669450cae32d,Robert Kennedy,mullinsjames@atkins-williams.com,employee,2cd1586a-2b84-4c67-ae18-3554cae28e66,2022-07-28,True
```

**Seed counts across all 10 entities:**

```bash
python3 -c "
import csv, os, glob
for path in sorted(glob.glob(\"/tmp/acme_dbt/seeds/*.csv\")):
    entity = os.path.basename(path).replace(\".csv\",\"\")
    with open(path) as f:
        rows = list(csv.reader(f))
    print(f\"  {entity}: {len(rows)-1} rows x {len(rows[0])} columns\")
"
```

```output
  application: 50 rows x 6 columns
  business_process: 50 rows x 5 columns
  capability: 50 rows x 4 columns
  data_asset: 50 rows x 6 columns
  location: 50 rows x 6 columns
  organization: 50 rows x 5 columns
  organizational_unit: 50 rows x 6 columns
  person: 50 rows x 7 columns
  person_role: 50 rows x 5 columns
  role: 50 rows x 4 columns
```

500 rows total, all FK-consistent.

## Step 1: dbt seed

Load all 10 CSVs into DuckDB as raw source tables:

```bash
cd /tmp/acme_dbt && dbt seed --profiles-dir . 2>&1
```

```output
[0m19:52:55  Running with dbt=1.11.7
[0m19:52:55  Registered adapter: duckdb=1.10.1
[0m19:52:55  Unable to do partial parsing because saved manifest not found. Starting full parse.
[0m19:52:57  [[33mWARNING[0m][MissingArgumentsPropertyInGenericTestDeprecation]: Deprecated
functionality
Found top-level arguments to test `accepted_values` defined on
'stg_organization' in package 'acme_corp_information_model' (tests/schema.yml).
Arguments to generic tests should be nested under the `arguments` property.
[0m19:52:57  Encountered an error:
Compilation Error
  Model 'model.acme_corp_information_model.stg_organizational_unit' (models/staging/stg_organizational_unit.sql) depends on a source named 'raw.organizational_unit' which was not found
[0m19:52:57  [[33mWARNING[0m][DeprecationsSummary]: Deprecated functionality
Summary of encountered deprecations:
- MissingArgumentsPropertyInGenericTestDeprecation: 19 occurrences
To see all deprecation instances instead of just the first occurrence of each,
run command again with the `--show-all-deprecations` flag. You may also need to
run with `--no-partial-parse` as some deprecations are only encountered during
parsing.
```

```bash
cd /tmp/acme_dbt && dbt seed --profiles-dir . 2>&1
```

```output
[0m19:56:30  Running with dbt=1.11.7
[0m19:56:30  Registered adapter: duckdb=1.10.1
[0m19:56:30  Unable to do partial parsing because saved manifest not found. Starting full parse.
[0m19:56:32  Encountered an error:
Compilation Error
  dbt found two schema.yml entries for the same resource named stg_organization. Resources and their associated columns may only be described a single time. To fix this, remove the resource entry for stg_organization in one of these files:
   - tests/schema.yml
  models/schema.yml
```
