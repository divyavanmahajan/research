"""Generate mart SQL models from a ConceptualModel."""

from __future__ import annotations

import os

from jinja2 import Environment, FileSystemLoader

from ..model import ConceptualModel, Entity

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        keep_trailing_newline=True,
    )


def generate_mart_sql(entity: Entity, model: ConceptualModel) -> str:
    """Return the mart SQL string for an entity with many_to_one relationships."""
    env = _get_env()
    template = env.get_template("mart.sql.j2")
    return template.render(entity=entity, model=model)


def needs_mart(entity: Entity) -> bool:
    """Return True if this entity should have a mart model generated."""
    return len(entity.many_to_one_relationships) > 0
