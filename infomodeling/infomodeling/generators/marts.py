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

    # Build column list in Python to avoid Jinja comma-between-loops bugs
    select_columns: list[str] = []
    # All columns from the primary entity
    for attr in entity.attributes:
        select_columns.append(f"{entity.snake_name}.{attr.name}")

    # CTEs to join and their ON conditions
    seen_ctes: set[str] = set()
    cte_joins: list[tuple[str, str]] = []  # (cte_name, join_condition)
    related_cols: list[str] = []

    for rel in entity.many_to_one_relationships:
        related = model.entity_by_name(rel.to)
        if related is None or related.name == entity.name:
            continue  # skip self-referential
        if related.snake_name in seen_ctes:
            continue  # skip duplicate joins
        seen_ctes.add(related.snake_name)

        if related.primary_key is None:
            continue

        join_condition = (
            f"{entity.snake_name}.{rel.via} = "
            f"{related.snake_name}.{related.primary_key.name}"
        )
        cte_joins.append((related.snake_name, join_condition))

        for attr in related.attributes:
            if not attr.primary_key:
                alias = f"{related.snake_name}_{attr.name}"
                related_cols.append(
                    f"{related.snake_name}.{attr.name} as {alias}"
                )

    select_columns.extend(related_cols)

    return template.render(
        primary=entity,
        select_columns=select_columns,
        cte_joins=cte_joins,
    )


def needs_mart(entity: Entity) -> bool:
    """Return True if this entity should have a mart model generated."""
    return len(entity.many_to_one_relationships) > 0
