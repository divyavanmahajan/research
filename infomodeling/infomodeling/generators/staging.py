"""Generate staging SQL models from a ConceptualModel."""

from __future__ import annotations

import os

from jinja2 import Environment, FileSystemLoader

from ..model import Entity

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        keep_trailing_newline=True,
    )


def generate_staging_sql(entity: Entity, source_name: str = "raw") -> str:
    """Return the staging SQL string for a single entity."""
    env = _get_env()
    template = env.get_template("staging.sql.j2")
    return template.render(entity=entity, source_name=source_name)
