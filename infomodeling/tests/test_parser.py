"""Unit tests for the YAML parser and validator."""

import os
import tempfile

import pytest
import yaml

from infomodeling.exceptions import ModelValidationError, ParseError
from infomodeling.model import ConceptualModel
from infomodeling.parser import load, parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _write_yaml(tmp_path: str, data: dict) -> str:
    path = os.path.join(tmp_path, "model.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(data, f)
    return path


def _minimal_entity(name: str = "Widget", extra_attrs: list | None = None) -> dict:
    attrs = [{"name": "widget_id", "type": "uuid", "primary_key": True}]
    if extra_attrs:
        attrs.extend(extra_attrs)
    return {"name": name, "attributes": attrs}


def _minimal_model(entities: list | None = None) -> dict:
    return {
        "version": "1.0",
        "name": "Test Model",
        "entities": entities or [_minimal_entity()],
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestValidModel:
    def test_parse_returns_conceptual_model(self):
        model = parse(_minimal_model())
        assert isinstance(model, ConceptualModel)

    def test_model_name_and_version(self):
        model = parse(_minimal_model())
        assert model.name == "Test Model"
        assert model.version == "1.0"

    def test_entity_count(self):
        model = parse(_minimal_model([_minimal_entity("Foo"), _minimal_entity("Bar")]))
        assert len(model.entities) == 2

    def test_entity_snake_name(self):
        model = parse(_minimal_model([_minimal_entity("OrganizationalUnit")]))
        assert model.entities[0].snake_name == "organizational_unit"

    def test_primary_key_attribute(self):
        model = parse(_minimal_model())
        pk = model.entities[0].primary_key
        assert pk is not None
        assert pk.name == "widget_id"
        assert pk.primary_key is True

    def test_attribute_defaults(self):
        data = _minimal_model([{
            "name": "Thing",
            "attributes": [
                {"name": "thing_id", "type": "uuid", "primary_key": True},
                {"name": "thing_name", "type": "string"},
            ],
        }])
        model = parse(data)
        attr = model.entities[0].attributes[1]
        assert attr.nullable is False
        assert attr.description == ""
        assert attr.enum == []

    def test_enum_attribute(self):
        entity = {
            "name": "Foo",
            "attributes": [
                {"name": "foo_id", "type": "uuid", "primary_key": True},
                {"name": "status", "type": "string", "enum": ["active", "inactive"]},
            ],
        }
        model = parse(_minimal_model([entity]))
        status_attr = model.entities[0].attributes[1]
        assert status_attr.enum == ["active", "inactive"]

    def test_nullable_attribute(self):
        entity = {
            "name": "Foo",
            "attributes": [
                {"name": "foo_id", "type": "uuid", "primary_key": True},
                {"name": "notes", "type": "string", "nullable": True},
            ],
        }
        model = parse(_minimal_model([entity]))
        assert model.entities[0].attributes[1].nullable is True

    def test_all_valid_types(self):
        types = ["string", "integer", "float", "boolean", "date", "timestamp", "uuid"]
        for t in types:
            data = _minimal_model([{
                "name": "Thing",
                "attributes": [{"name": "thing_id", "type": t, "primary_key": True}],
            }])
            model = parse(data)
            assert model.entities[0].attributes[0].type == t

    def test_relationship_parsed(self):
        data = _minimal_model([
            {
                "name": "Child",
                "attributes": [
                    {"name": "child_id", "type": "uuid", "primary_key": True},
                    {"name": "parent_id", "type": "uuid"},
                ],
                "relationships": [{"to": "Parent", "via": "parent_id", "cardinality": "many_to_one"}],
            },
            {
                "name": "Parent",
                "attributes": [{"name": "parent_id", "type": "uuid", "primary_key": True}],
            },
        ])
        model = parse(data)
        child = model.entities[0]
        assert len(child.relationships) == 1
        rel = child.relationships[0]
        assert rel.to == "Parent"
        assert rel.via == "parent_id"
        assert rel.cardinality == "many_to_one"

    def test_self_referential_relationship(self):
        data = _minimal_model([{
            "name": "Node",
            "attributes": [
                {"name": "node_id", "type": "uuid", "primary_key": True},
                {"name": "parent_node_id", "type": "uuid", "nullable": True},
            ],
            "relationships": [
                {"to": "Node", "via": "parent_node_id", "cardinality": "many_to_one", "type": "self_referential"}
            ],
        }])
        model = parse(data)
        rel = model.entities[0].relationships[0]
        assert rel.type == "self_referential"
        assert rel.to == "Node"

    def test_entity_by_name(self):
        data = _minimal_model([_minimal_entity("Alpha"), _minimal_entity("Beta")])
        model = parse(data)
        assert model.entity_by_name("Alpha") is not None
        assert model.entity_by_name("Gamma") is None

    def test_many_to_one_relationships_property(self):
        data = _minimal_model([
            {
                "name": "Child",
                "attributes": [
                    {"name": "child_id", "type": "uuid", "primary_key": True},
                    {"name": "parent_id", "type": "uuid"},
                ],
                "relationships": [
                    {"to": "Parent", "via": "parent_id", "cardinality": "many_to_one"},
                ],
            },
            {
                "name": "Parent",
                "attributes": [{"name": "parent_id", "type": "uuid", "primary_key": True}],
            },
        ])
        model = parse(data)
        assert len(model.entities[0].many_to_one_relationships) == 1

    def test_load_example_org_model(self):
        path = os.path.join(EXAMPLES_DIR, "org_model.yaml")
        model = load(path)
        assert len(model.entities) == 10
        assert model.name == "Acme Corp Information Model"


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_missing_name(self):
        with pytest.raises(ModelValidationError) as exc:
            parse({"version": "1.0", "entities": [_minimal_entity()]})
        assert "name" in str(exc.value)

    def test_duplicate_entity_names(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([_minimal_entity("Foo"), _minimal_entity("Foo")]))
        assert "Duplicate entity name" in str(exc.value)

    def test_no_primary_key(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([{
                "name": "Foo",
                "attributes": [{"name": "foo_id", "type": "uuid"}],
            }]))
        assert "primary key" in str(exc.value)

    def test_multiple_primary_keys(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([{
                "name": "Foo",
                "attributes": [
                    {"name": "id1", "type": "uuid", "primary_key": True},
                    {"name": "id2", "type": "uuid", "primary_key": True},
                ],
            }]))
        assert "2 primary keys" in str(exc.value)

    def test_invalid_attribute_type(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([{
                "name": "Foo",
                "attributes": [{"name": "foo_id", "type": "blob", "primary_key": True}],
            }]))
        assert "invalid type" in str(exc.value)

    def test_duplicate_attribute_names(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([{
                "name": "Foo",
                "attributes": [
                    {"name": "foo_id", "type": "uuid", "primary_key": True},
                    {"name": "foo_id", "type": "string"},
                ],
            }]))
        assert "duplicate attribute" in str(exc.value).lower()

    def test_relationship_unknown_target(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([{
                "name": "Foo",
                "attributes": [
                    {"name": "foo_id", "type": "uuid", "primary_key": True},
                    {"name": "bar_id", "type": "uuid"},
                ],
                "relationships": [{"to": "Bar", "via": "bar_id", "cardinality": "many_to_one"}],
            }]))
        assert "unknown entity" in str(exc.value)

    def test_relationship_unknown_via_field(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([
                {
                    "name": "Foo",
                    "attributes": [{"name": "foo_id", "type": "uuid", "primary_key": True}],
                    "relationships": [{"to": "Bar", "via": "nonexistent_id", "cardinality": "many_to_one"}],
                },
                {
                    "name": "Bar",
                    "attributes": [{"name": "bar_id", "type": "uuid", "primary_key": True}],
                },
            ]))
        assert "unknown attribute" in str(exc.value)

    def test_invalid_cardinality(self):
        with pytest.raises(ModelValidationError) as exc:
            parse(_minimal_model([
                {
                    "name": "Foo",
                    "attributes": [
                        {"name": "foo_id", "type": "uuid", "primary_key": True},
                        {"name": "bar_id", "type": "uuid"},
                    ],
                    "relationships": [{"to": "Bar", "via": "bar_id", "cardinality": "lots"}],
                },
                {
                    "name": "Bar",
                    "attributes": [{"name": "bar_id", "type": "uuid", "primary_key": True}],
                },
            ]))
        assert "cardinality" in str(exc.value)

    def test_non_list_entities(self):
        with pytest.raises(ModelValidationError):
            parse({"version": "1.0", "name": "X", "entities": "not a list"})

    def test_not_a_dict_top_level(self):
        with pytest.raises(ParseError):
            parse("just a string")


# ---------------------------------------------------------------------------
# File I/O tests
# ---------------------------------------------------------------------------


class TestFileIO:
    def test_load_valid_file(self, tmp_path):
        path = _write_yaml(str(tmp_path), _minimal_model())
        model = load(path)
        assert isinstance(model, ConceptualModel)

    def test_load_missing_file(self):
        with pytest.raises(ParseError) as exc:
            load("/nonexistent/path/model.yaml")
        assert "not found" in str(exc.value)

    def test_load_invalid_yaml(self, tmp_path):
        path = os.path.join(str(tmp_path), "bad.yaml")
        with open(path, "w") as f:
            f.write(":\t: bad: yaml: [\n")
        with pytest.raises(ParseError) as exc:
            load(path)
        assert "YAML parse error" in str(exc.value)
