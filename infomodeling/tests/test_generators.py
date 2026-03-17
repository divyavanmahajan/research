"""Unit tests for DBT artifact generators."""

import os
import tempfile

import pytest
import yaml

from infomodeling.generators.marts import generate_mart_sql, needs_mart
from infomodeling.generators.project import generate_dbt_project_yml, generate_profiles_yml
from infomodeling.generators.schema import generate_schema_yml
from infomodeling.generators.sources import generate_sources_yml
from infomodeling.generators.staging import generate_staging_sql
from infomodeling.merger import has_markers, merge
from infomodeling.model import ConceptualModel
from infomodeling.parser import load, parse
from infomodeling.writer import WriteOptions, write_project

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _load_org_model() -> ConceptualModel:
    return load(os.path.join(EXAMPLES_DIR, "org_model.yaml"))


# ---------------------------------------------------------------------------
# sources.yml
# ---------------------------------------------------------------------------

class TestSourcesGenerator:
    def test_returns_valid_yaml(self):
        model = _load_org_model()
        result = generate_sources_yml(model)
        data = yaml.safe_load(result)
        assert data["version"] == 2
        assert "sources" in data

    def test_all_entities_present(self):
        model = _load_org_model()
        result = generate_sources_yml(model)
        data = yaml.safe_load(result)
        table_names = [t["name"] for t in data["sources"][0]["tables"]]
        assert "organizational_unit" in table_names
        assert "person" in table_names

    def test_source_name_configurable(self):
        model = _load_org_model()
        result = generate_sources_yml(model, source_name="bronze")
        data = yaml.safe_load(result)
        assert data["sources"][0]["name"] == "bronze"

    def test_columns_present(self):
        model = _load_org_model()
        result = generate_sources_yml(model)
        data = yaml.safe_load(result)
        org_unit = next(t for t in data["sources"][0]["tables"] if t["name"] == "organizational_unit")
        col_names = [c["name"] for c in org_unit["columns"]]
        assert "unit_id" in col_names
        assert "unit_name" in col_names


# ---------------------------------------------------------------------------
# Staging SQL
# ---------------------------------------------------------------------------

class TestStagingGenerator:
    def test_returns_string(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_config_block(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity)
        assert "config(materialized='view')" in result

    def test_contains_source_ref(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity)
        assert "source('raw', 'person')" in result

    def test_contains_all_columns(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity)
        for attr in entity.attributes:
            assert attr.name in result

    def test_has_generated_markers(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity)
        assert has_markers(result)

    def test_custom_source_name(self):
        model = _load_org_model()
        entity = model.entity_by_name("Person")
        result = generate_staging_sql(entity, source_name="bronze")
        assert "source('bronze', 'person')" in result


# ---------------------------------------------------------------------------
# Mart SQL
# ---------------------------------------------------------------------------

class TestMartGenerator:
    def test_needs_mart_true_for_entity_with_relationships(self):
        model = _load_org_model()
        person = model.entity_by_name("Person")
        assert needs_mart(person) is True

    def test_needs_mart_false_for_entity_without_relationships(self):
        model = _load_org_model()
        org = model.entity_by_name("Organization")
        assert needs_mart(org) is False

    def test_mart_contains_config_block(self):
        model = _load_org_model()
        person = model.entity_by_name("Person")
        result = generate_mart_sql(person, model)
        assert "config(materialized='table')" in result

    def test_mart_contains_ref_to_staging(self):
        model = _load_org_model()
        person = model.entity_by_name("Person")
        result = generate_mart_sql(person, model)
        assert "ref('stg_person')" in result

    def test_mart_contains_join_to_related(self):
        model = _load_org_model()
        person = model.entity_by_name("Person")
        result = generate_mart_sql(person, model)
        assert "ref('stg_organizational_unit')" in result
        assert "left join" in result.lower()

    def test_mart_has_generated_markers(self):
        model = _load_org_model()
        person = model.entity_by_name("Person")
        result = generate_mart_sql(person, model)
        assert has_markers(result)


# ---------------------------------------------------------------------------
# schema.yml
# ---------------------------------------------------------------------------

class TestSchemaGenerator:
    def test_returns_valid_yaml(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        assert data["version"] == 2
        assert "models" in data

    def test_all_staging_models_present(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        model_names = [m["name"] for m in data["models"]]
        assert "stg_person" in model_names
        assert "stg_organizational_unit" in model_names

    def test_primary_key_gets_unique_and_not_null(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        person_model = next(m for m in data["models"] if m["name"] == "stg_person")
        pk_col = next(c for c in person_model["columns"] if c["name"] == "person_id")
        assert "unique" in pk_col["tests"]
        assert "not_null" in pk_col["tests"]

    def test_enum_field_gets_accepted_values_test(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        person_model = next(m for m in data["models"] if m["name"] == "stg_person")
        emp_col = next(c for c in person_model["columns"] if c["name"] == "employment_type")
        av_tests = [t for t in emp_col["tests"] if isinstance(t, dict) and "accepted_values" in t]
        assert len(av_tests) == 1
        assert "employee" in av_tests[0]["accepted_values"]["values"]

    def test_non_nullable_field_gets_not_null(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        person_model = next(m for m in data["models"] if m["name"] == "stg_person")
        name_col = next(c for c in person_model["columns"] if c["name"] == "full_name")
        assert "not_null" in name_col["tests"]

    def test_fk_field_gets_relationships_test(self):
        model = _load_org_model()
        result = generate_schema_yml(model)
        data = yaml.safe_load(result)
        person_model = next(m for m in data["models"] if m["name"] == "stg_person")
        unit_col = next(c for c in person_model["columns"] if c["name"] == "unit_id")
        rel_tests = [t for t in unit_col["tests"] if isinstance(t, dict) and "relationships" in t]
        assert len(rel_tests) == 1
        assert "stg_organizational_unit" in rel_tests[0]["relationships"]["to"]


# ---------------------------------------------------------------------------
# dbt_project.yml + profiles.yml
# ---------------------------------------------------------------------------

class TestProjectGenerator:
    def test_dbt_project_valid_yaml(self):
        model = _load_org_model()
        result = generate_dbt_project_yml(model)
        data = yaml.safe_load(result)
        assert "name" in data
        assert data["config-version"] == 2

    def test_profiles_yml_duckdb(self):
        result = generate_profiles_yml("my_project")
        data = yaml.safe_load(result)
        assert "my_project" in data
        assert data["my_project"]["outputs"]["dev"]["type"] == "duckdb"


# ---------------------------------------------------------------------------
# Merger
# ---------------------------------------------------------------------------

class TestMerger:
    def test_merge_replaces_generated_block(self):
        existing = "-- BEGIN GENERATED\nold content\n-- END GENERATED\n\ncustom stuff"
        new = "-- BEGIN GENERATED\nnew content\n-- END GENERATED\n\nignored"
        result = merge(existing, new)
        assert "new content" in result
        assert "old content" not in result
        assert "custom stuff" in result

    def test_merge_preserves_content_outside_markers(self):
        existing = "header\n-- BEGIN GENERATED\nold\n-- END GENERATED\nfooter"
        new = "-- BEGIN GENERATED\nnew\n-- END GENERATED"
        result = merge(existing, new)
        assert "header" in result
        assert "footer" in result
        assert "new" in result

    def test_merge_falls_back_to_new_if_no_existing_markers(self):
        existing = "just plain content"
        new = "-- BEGIN GENERATED\nnew\n-- END GENERATED"
        result = merge(existing, new)
        assert result == new

    def test_merge_falls_back_to_new_if_no_new_markers(self):
        existing = "-- BEGIN GENERATED\nold\n-- END GENERATED"
        new = "plain new content"
        result = merge(existing, new)
        assert result == new

    def test_has_markers_true(self):
        content = "-- BEGIN GENERATED\nfoo\n-- END GENERATED"
        assert has_markers(content) is True

    def test_has_markers_false(self):
        assert has_markers("no markers here") is False

    def test_idempotent_merge(self):
        content = "-- BEGIN GENERATED\ncontent\n-- END GENERATED\ncustom"
        result1 = merge(content, content)
        result2 = merge(result1, content)
        assert result1 == result2


# ---------------------------------------------------------------------------
# Writer (integration)
# ---------------------------------------------------------------------------

class TestWriter:
    def test_writes_all_expected_files(self, tmp_path):
        model = _load_org_model()
        result = write_project(model, str(tmp_path))
        written = result.written + result.merged + result.skipped
        # Check key files exist
        assert any("dbt_project.yml" in f for f in written)
        assert any("sources.yml" in f for f in written)
        assert any("schema.yml" in f for f in written)
        assert any("stg_person.sql" in f for f in written)

    def test_staging_files_created(self, tmp_path):
        model = _load_org_model()
        write_project(model, str(tmp_path))
        staging_dir = os.path.join(str(tmp_path), "models", "staging")
        assert os.path.exists(staging_dir)
        files = os.listdir(staging_dir)
        assert "stg_person.sql" in files
        assert "stg_organizational_unit.sql" in files

    def test_mart_files_created_only_for_entities_with_rels(self, tmp_path):
        model = _load_org_model()
        write_project(model, str(tmp_path))
        mart_dir = os.path.join(str(tmp_path), "models", "marts")
        assert os.path.exists(mart_dir)
        files = os.listdir(mart_dir)
        # Person has relationships → should have a mart
        assert "dim_person.sql" in files
        # Organization has no relationships → should NOT have a mart
        assert "dim_organization.sql" not in files

    def test_idempotent_generation(self, tmp_path):
        model = _load_org_model()
        write_project(model, str(tmp_path))
        result2 = write_project(model, str(tmp_path))
        # Second run: no new writes (either merged-with-no-diff or skipped)
        assert len(result2.written) == 0 or all(
            "yml" in f for f in result2.written
        )

    def test_dry_run_writes_nothing(self, tmp_path):
        model = _load_org_model()
        opts = WriteOptions(dry_run=True)
        result = write_project(model, str(tmp_path), opts)
        assert len(result.written) > 0  # dry_run records what WOULD be written
        assert not os.path.exists(os.path.join(str(tmp_path), "dbt_project.yml"))
