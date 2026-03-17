"""Topological sort of entities based on their FK dependency graph (Kahn's algorithm)."""

from __future__ import annotations

from collections import defaultdict, deque

from ..model import ConceptualModel, Entity


def topological_sort(model: ConceptualModel) -> list[Entity]:
    """
    Return entities in topological order: entities with no FK dependencies first,
    then entities that depend on them.

    Self-referential relationships (entity → same entity) are excluded from the
    dependency graph since they cannot impose ordering.

    Raises ValueError if a cycle is detected.
    """
    entity_names = [e.name for e in model.entities]
    name_to_entity = {e.name: e for e in model.entities}

    # Build adjacency: dependency[A] = set of entities A depends on (A has FK → B)
    # We need B to be generated before A.
    in_degree: dict[str, int] = {name: 0 for name in entity_names}
    dependents: dict[str, list[str]] = defaultdict(list)  # B → [A, ...] (B must come before A)

    for entity in model.entities:
        seen_deps: set[str] = set()
        for rel in entity.many_to_one_relationships:
            target = rel.to
            if target == entity.name:
                continue  # self-referential: skip
            if target not in name_to_entity:
                continue  # already caught by validator
            if target not in seen_deps:
                seen_deps.add(target)
                in_degree[entity.name] += 1
                dependents[target].append(entity.name)

    # Kahn's algorithm
    queue: deque[str] = deque(name for name, deg in in_degree.items() if deg == 0)
    sorted_names: list[str] = []

    while queue:
        name = queue.popleft()
        sorted_names.append(name)
        for dependent in dependents[name]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(sorted_names) != len(entity_names):
        remaining = set(entity_names) - set(sorted_names)
        raise ValueError(f"Cycle detected in entity dependency graph involving: {remaining}")

    return [name_to_entity[n] for n in sorted_names]
