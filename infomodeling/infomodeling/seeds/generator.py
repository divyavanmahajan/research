"""Generate relational seed data from a ConceptualModel."""

from __future__ import annotations

import csv
import io
import os
import random
import uuid

from faker import Faker

from ..model import ConceptualModel
from .faker_mapper import generate_value
from .topological import topological_sort


def generate_seeds(
    model: ConceptualModel,
    rows_per_entity: int = 50,
    seed: int | None = None,
) -> dict[str, list[dict]]:
    """
    Generate seed rows for all entities in topological order.

    Returns a dict mapping entity snake_name → list of row dicts.
    All FK values are guaranteed to reference valid PK values from parent entities.
    """
    rng = random.Random(seed)
    fake = Faker()
    if seed is not None:
        Faker.seed(seed)

    order = topological_sort(model)
    generated: dict[str, list[dict]] = {}  # snake_name → rows

    for entity in order:
        rows = []
        # Build FK resolution map: attribute_name → list of valid PK values from parent
        fk_pools: dict[str, list] = {}
        for rel in entity.many_to_one_relationships:
            related = model.entity_by_name(rel.to)
            if related is None:
                continue
            if related.name == entity.name:
                # Self-referential: pool is from already-partially-generated rows + allow None
                fk_pools[rel.via] = "self"
            elif related.snake_name in generated and related.primary_key:
                pk_name = related.primary_key.name
                fk_pools[rel.via] = [r[pk_name] for r in generated[related.snake_name]]

        for i in range(rows_per_entity):
            row: dict = {}
            for attr in entity.attributes:
                # FK field: sample from parent pool
                if attr.name in fk_pools:
                    pool = fk_pools[attr.name]
                    if pool == "self":
                        # Self-referential: first ~20% get None (roots), rest reference earlier rows
                        if i == 0 or rng.random() < 0.2:
                            row[attr.name] = None
                        else:
                            # Reference a previously generated row in this batch
                            parent_pks = [r[entity.primary_key.name] for r in rows[:i] if entity.primary_key]
                            row[attr.name] = rng.choice(parent_pks) if parent_pks else None
                    elif pool:
                        if attr.nullable and rng.random() < 0.1:
                            row[attr.name] = None
                        else:
                            row[attr.name] = rng.choice(pool)
                    else:
                        row[attr.name] = None
                else:
                    row[attr.name] = generate_value(
                        attr_name=attr.name,
                        attr_type=attr.type,
                        enum=attr.enum,
                        nullable=attr.nullable,
                        fake=fake,
                        rng=rng,
                    )

            rows.append(row)

        generated[entity.snake_name] = rows

    return generated


def seeds_to_csv(rows: list[dict]) -> str:
    """Convert a list of row dicts to a CSV string."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def write_seeds(
    model: ConceptualModel,
    output_dir: str,
    rows_per_entity: int = 50,
    seed: int | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Generate seed CSVs and write them to output_dir/seeds/. Returns list of written paths."""
    seeds = generate_seeds(model, rows_per_entity=rows_per_entity, seed=seed)
    seeds_dir = os.path.join(output_dir, "seeds")
    written = []

    for snake_name, rows in seeds.items():
        csv_content = seeds_to_csv(rows)
        rel_path = os.path.join("seeds", f"{snake_name}.csv")
        full_path = os.path.join(output_dir, rel_path)
        if not dry_run:
            os.makedirs(seeds_dir, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(csv_content)
        written.append(rel_path)

    return written
