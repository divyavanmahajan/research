"""Generate schema.yml with data quality tests from a ConceptualModel."""

from __future__ import annotations

import yaml

from ..model import ConceptualModel, Entity


def generate_schema_yml(model: ConceptualModel) -> str:
    """Return a schema.yml string with column-level tests for all entities."""
    models_section = []

    for entity in model.entities:
        columns = _generate_columns(entity, model)
        entry: dict = {
            "name": f"stg_{entity.snake_name}",
        }
        if entity.description:
            entry["description"] = entity.description
        entry["columns"] = columns
        models_section.append(entry)

    data = {"version": 2, "models": models_section}
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _generate_columns(entity: Entity, model: ConceptualModel) -> list[dict]:
    # Build a map of FK attribute name -> relationship (for FK tests)
    fk_map: dict[str, dict] = {}
    for rel in entity.many_to_one_relationships:
        related = model.entity_by_name(rel.to)
        if related and related.primary_key:
            fk_map[rel.via] = {
                "to": rel.to,
                "ref": f"stg_{related.snake_name}",
                "field": related.primary_key.name,
            }

    columns = []
    for attr in entity.attributes:
        col: dict = {"name": attr.name}
        if attr.description:
            col["description"] = attr.description

        tests: list = []

        # Primary key: unique + not_null
        if attr.primary_key:
            tests.append("unique")
            tests.append("not_null")
        elif not attr.nullable:
            # Non-nullable non-PK fields
            tests.append("not_null")

        # Enum → accepted_values (dbt 1.9+: arguments nested under 'arguments' key)
        if attr.enum:
            tests.append({"accepted_values": {"arguments": {"values": attr.enum}}})

        # FK → relationships test (dbt 1.9+: arguments nested under 'arguments' key)
        if attr.name in fk_map and not attr.nullable:
            fk_info = fk_map[attr.name]
            tests.append({
                "relationships": {
                    "arguments": {
                        "to": f"ref('{fk_info['ref']}')",
                        "field": fk_info["field"],
                    }
                }
            })

        if tests:
            col["tests"] = tests

        columns.append(col)

    return columns
