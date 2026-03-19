"""Unit tests for the seed data generator."""

import os
import uuid as uuid_mod

import pytest

from infomodeling.model import ConceptualModel
from infomodeling.parser import load, parse
from infomodeling.seeds.generator import generate_seeds, seeds_to_csv, write_seeds
from infomodeling.seeds.topological import topological_sort

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _load_org_model() -> ConceptualModel:
    return load(os.path.join(EXAMPLES_DIR, "org_model.yaml"))


def _minimal_parent_child_model() -> ConceptualModel:
    return parse({
        "version": "1.0",
        "name": "Test",
        "entities": [
            {
                "name": "Parent",
                "attributes": [{"name": "parent_id", "type": "uuid", "primary_key": True}],
            },
            {
                "name": "Child",
                "attributes": [
                    {"name": "child_id", "type": "uuid", "primary_key": True},
                    {"name": "parent_id", "type": "uuid"},
                ],
                "relationships": [{"to": "Parent", "via": "parent_id", "cardinality": "many_to_one"}],
            },
        ],
    })


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_independent_entities_any_order(self):
        model = parse({
            "version": "1.0",
            "name": "Test",
            "entities": [
                {"name": "A", "attributes": [{"name": "a_id", "type": "uuid", "primary_key": True}]},
                {"name": "B", "attributes": [{"name": "b_id", "type": "uuid", "primary_key": True}]},
            ],
        })
        result = topological_sort(model)
        assert len(result) == 2

    def test_parent_before_child(self):
        model = _minimal_parent_child_model()
        result = topological_sort(model)
        names = [e.name for e in result]
        assert names.index("Parent") < names.index("Child")

    def test_self_referential_included(self):
        model = parse({
            "version": "1.0",
            "name": "Test",
            "entities": [{
                "name": "Node",
                "attributes": [
                    {"name": "node_id", "type": "uuid", "primary_key": True},
                    {"name": "parent_node_id", "type": "uuid", "nullable": True},
                ],
                "relationships": [{"to": "Node", "via": "parent_node_id", "cardinality": "many_to_one", "type": "self_referential"}],
            }],
        })
        result = topological_sort(model)
        assert len(result) == 1

    def test_org_model_all_entities_present(self):
        model = _load_org_model()
        result = topological_sort(model)
        assert len(result) == len(model.entities)

    def test_org_model_org_before_org_unit(self):
        model = _load_org_model()
        result = topological_sort(model)
        names = [e.name for e in result]
        assert names.index("Organization") < names.index("OrganizationalUnit")

    def test_org_model_org_unit_before_person(self):
        model = _load_org_model()
        result = topological_sort(model)
        names = [e.name for e in result]
        assert names.index("OrganizationalUnit") < names.index("Person")


# ---------------------------------------------------------------------------
# Seed generator: structure
# ---------------------------------------------------------------------------

class TestSeedGenerator:
    def test_returns_dict_of_entity_names(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=5, seed=42)
        assert "person" in seeds
        assert "organizational_unit" in seeds
        assert "organization" in seeds

    def test_correct_row_count(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=10, seed=42)
        for rows in seeds.values():
            assert len(rows) == 10

    def test_all_entities_present(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=5, seed=42)
        for entity in model.entities:
            assert entity.snake_name in seeds

    def test_row_has_all_columns(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=5, seed=42)
        person_entity = model.entity_by_name("Person")
        attr_names = {a.name for a in person_entity.attributes}
        for row in seeds["person"]:
            assert set(row.keys()) == attr_names

    def test_uuid_fields_are_valid_uuids(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=10, seed=42)
        for row in seeds["person"]:
            # person_id is a UUID
            uuid_str = row["person_id"]
            # Should not raise
            uuid_mod.UUID(uuid_str)

    def test_enum_values_are_valid(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=20, seed=42)
        person_entity = model.entity_by_name("Person")
        emp_type_attr = next(a for a in person_entity.attributes if a.name == "employment_type")
        valid_values = set(emp_type_attr.enum)
        for row in seeds["person"]:
            assert row["employment_type"] in valid_values

    def test_boolean_values_are_bool(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=10, seed=42)
        for row in seeds["person"]:
            assert isinstance(row["is_active"], bool)


# ---------------------------------------------------------------------------
# FK consistency
# ---------------------------------------------------------------------------

class TestFKConsistency:
    def test_child_fk_references_parent_pk(self):
        model = _minimal_parent_child_model()
        seeds = generate_seeds(model, rows_per_entity=20, seed=42)
        parent_ids = {r["parent_id"] for r in seeds["parent"]}
        for child_row in seeds["child"]:
            assert child_row["parent_id"] in parent_ids

    def test_person_unit_id_references_valid_unit(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=20, seed=42)
        valid_unit_ids = {r["unit_id"] for r in seeds["organizational_unit"]}
        for row in seeds["person"]:
            assert row["unit_id"] in valid_unit_ids

    def test_org_unit_org_id_references_valid_org(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=10, seed=42)
        valid_org_ids = {r["org_id"] for r in seeds["organization"]}
        for row in seeds["organizational_unit"]:
            assert row["org_id"] in valid_org_ids

    def test_self_referential_parent_is_none_or_valid(self):
        model = _load_org_model()
        seeds = generate_seeds(model, rows_per_entity=20, seed=42)
        unit_ids = {r["unit_id"] for r in seeds["organizational_unit"]}
        for row in seeds["organizational_unit"]:
            parent = row.get("parent_unit_id")
            if parent is not None:
                assert parent in unit_ids


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_same_output(self):
        model = _load_org_model()
        seeds1 = generate_seeds(model, rows_per_entity=10, seed=42)
        seeds2 = generate_seeds(model, rows_per_entity=10, seed=42)
        for snake_name in seeds1:
            assert seeds1[snake_name] == seeds2[snake_name]

    def test_different_seeds_different_output(self):
        model = _load_org_model()
        seeds1 = generate_seeds(model, rows_per_entity=10, seed=1)
        seeds2 = generate_seeds(model, rows_per_entity=10, seed=999)
        # At least one entity should differ (extremely unlikely to collide)
        diffs = sum(
            1 for name in seeds1
            if seeds1[name] != seeds2[name]
        )
        assert diffs > 0


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

class TestCsvOutput:
    def test_seeds_to_csv_has_header(self):
        rows = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
        csv_str = seeds_to_csv(rows)
        lines = csv_str.strip().split("\n")
        assert lines[0] == "id,name"

    def test_seeds_to_csv_correct_row_count(self):
        rows = [{"id": str(i)} for i in range(10)]
        csv_str = seeds_to_csv(rows)
        lines = [l for l in csv_str.strip().split("\n") if l]
        assert len(lines) == 11  # header + 10 rows

    def test_seeds_to_csv_empty(self):
        assert seeds_to_csv([]) == ""

    def test_write_seeds_creates_files(self, tmp_path):
        model = _load_org_model()
        write_seeds(model, str(tmp_path), rows_per_entity=5, seed=42)
        seeds_dir = os.path.join(str(tmp_path), "seeds")
        assert os.path.exists(seeds_dir)
        files = os.listdir(seeds_dir)
        assert "person.csv" in files
        assert "organization.csv" in files

    def test_write_seeds_dry_run_no_files(self, tmp_path):
        model = _load_org_model()
        written = write_seeds(model, str(tmp_path), rows_per_entity=5, dry_run=True)
        assert len(written) > 0
        assert not os.path.exists(os.path.join(str(tmp_path), "seeds"))
