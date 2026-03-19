# Phase 3 Progress: Seed Data Generator

**Status:** COMPLETE
**Date:** 2026-03-17
**Tests:** 24/24 passing

## Deliverables Completed

| File | Description |
|------|-------------|
| `infomodeling/seeds/topological.py` | Kahn's algorithm topological sort of entity dependency graph |
| `infomodeling/seeds/faker_mapper.py` | Type + field name heuristic → Faker provider mapping |
| `infomodeling/seeds/generator.py` | `generate_seeds()`, `seeds_to_csv()`, `write_seeds()` |
| `infomodeling/seeds/script_generator.py` | Standalone `generate_seeds.py` script generator |
| `tests/test_seeds.py` | 24 unit tests |

## Key Design Decisions

- **Topological ordering** (Kahn's algorithm) guarantees parent entities are generated before children — FK pools are always available when child rows are being generated
- **Self-referential FK handling**: first rows get `None` (tree roots); subsequent rows may reference any earlier row in the same batch
- **Faker seeding**: `Faker.seed(n)` + `random.Random(n)` together ensure full determinism; `uuid.uuid4()` replaced with `fake.uuid4()` which respects the seed
- **FK pool sampling**: for each child entity, the full set of parent PK values is used as the pool — `rng.choice(pool)` gives uniform distribution
- **Nullable FK fields**: ~10% chance of `None` for nullable FK attributes (e.g., `producing_app_id` in `DataAsset`)
- **Enum fields always win**: if an attribute has `enum`, the enum values are always used regardless of type

## Bug Fixed

- Initial implementation used `str(uuid.uuid4())` which bypasses Faker's seed → non-deterministic UUIDs. Fixed by using `fake.uuid4()` which is seeded via `Faker.seed()`.

## Seed Generation for 10-entity Acme Corp model (50 rows/entity)

```
organization.csv       →  50 rows (no FKs; generated first)
organizational_unit.csv → 50 rows (FK → organization; self-referential parent_unit_id)
role.csv               →  50 rows (FK → organizational_unit)
person.csv             →  50 rows (FK → organizational_unit)
application.csv        →  50 rows (FK → organizational_unit)
capability.csv         →  50 rows (self-referential parent_capability_id)
location.csv           →  50 rows (FK → organization)
business_process.csv   →  50 rows (FK → organizational_unit)
data_asset.csv         →  50 rows (FK → organizational_unit, application)
person_role.csv        →  50 rows (FK → person, role)
Total: 500 rows across 10 files
```
