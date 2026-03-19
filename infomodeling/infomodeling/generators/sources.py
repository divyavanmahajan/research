"""Generate sources.yml from a ConceptualModel."""

from __future__ import annotations

import yaml

from ..model import ConceptualModel


def generate_sources_yml(model: ConceptualModel, source_name: str = "raw") -> str:
    """Return a sources.yml string for all entities in the model."""
    tables = []
    for entity in model.entities:
        columns = [
            {
                "name": attr.name,
                **({"description": attr.description} if attr.description else {}),
            }
            for attr in entity.attributes
        ]
        tables.append({"name": entity.snake_name, "columns": columns})

    data = {
        "version": 2,
        "sources": [
            {
                "name": source_name,
                "tables": tables,
            }
        ],
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
