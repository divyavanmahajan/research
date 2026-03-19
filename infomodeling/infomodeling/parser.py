"""YAML parser and validator for conceptual information model files."""

from __future__ import annotations

import yaml

from .exceptions import ModelValidationError, ParseError
from .model import (
    VALID_CARDINALITIES,
    VALID_TYPES,
    Attribute,
    ConceptualModel,
    Entity,
    Relationship,
)


def load(path: str) -> ConceptualModel:
    """Parse a YAML file and return a validated ConceptualModel."""
    try:
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise ParseError(f"Model file not found: {path}")
    except yaml.YAMLError as e:
        raise ParseError(f"YAML parse error in {path}: {e}")

    return parse(raw)


def parse(raw: dict) -> ConceptualModel:
    """Parse a raw dict (from YAML) into a validated ConceptualModel."""
    errors: list[str] = []

    if not isinstance(raw, dict):
        raise ParseError("Model file must be a YAML mapping at the top level")

    version = str(raw.get("version", "1.0"))
    name = raw.get("name", "")
    description = raw.get("description", "")

    if not name:
        errors.append("Model 'name' is required")

    raw_entities = raw.get("entities", [])
    if not isinstance(raw_entities, list):
        errors.append("'entities' must be a list")
        _fail_if_errors(errors)

    entities: list[Entity] = []
    entity_names: set[str] = set()

    for i, raw_entity in enumerate(raw_entities):
        entity, entity_errors = _parse_entity(raw_entity, i)
        errors.extend(entity_errors)
        if entity:
            if entity.name in entity_names:
                errors.append(f"Duplicate entity name: '{entity.name}'")
            else:
                entity_names.add(entity.name)
                entities.append(entity)

    # Cross-entity relationship validation (done after all entities are parsed)
    for entity in entities:
        attr_names = {a.name for a in entity.attributes}
        for rel in entity.relationships:
            if rel.to != entity.name and rel.to not in entity_names:
                errors.append(
                    f"Entity '{entity.name}' has relationship to unknown entity '{rel.to}'"
                )
            if rel.via not in attr_names:
                errors.append(
                    f"Entity '{entity.name}' relationship via '{rel.via}' references unknown attribute"
                )

    _fail_if_errors(errors)

    return ConceptualModel(
        name=name,
        version=version,
        description=description,
        entities=entities,
    )


def _parse_entity(raw: dict, index: int) -> tuple[Entity | None, list[str]]:
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append(f"Entity at index {index} must be a mapping")
        return None, errors

    name = raw.get("name", "")
    if not name:
        errors.append(f"Entity at index {index} missing 'name'")
        return None, errors

    description = raw.get("description", "")
    raw_tags = raw.get("tags", [])
    tags = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else []
    raw_attrs = raw.get("attributes", [])
    raw_rels = raw.get("relationships", [])

    if not isinstance(raw_attrs, list):
        errors.append(f"Entity '{name}' 'attributes' must be a list")
        return None, errors

    attributes: list[Attribute] = []
    attr_names: set[str] = set()
    pk_count = 0

    for j, raw_attr in enumerate(raw_attrs):
        attr, attr_errors = _parse_attribute(raw_attr, name, j)
        errors.extend(attr_errors)
        if attr:
            if attr.name in attr_names:
                errors.append(f"Entity '{name}' has duplicate attribute '{attr.name}'")
            else:
                attr_names.add(attr.name)
                attributes.append(attr)
                if attr.primary_key:
                    pk_count += 1

    if pk_count == 0:
        errors.append(f"Entity '{name}' has no primary key (set primary_key: true on one attribute)")
    elif pk_count > 1:
        errors.append(f"Entity '{name}' has {pk_count} primary keys; exactly one is required")

    relationships: list[Relationship] = []
    if isinstance(raw_rels, list):
        for k, raw_rel in enumerate(raw_rels):
            rel, rel_errors = _parse_relationship(raw_rel, name, k)
            errors.extend(rel_errors)
            if rel:
                relationships.append(rel)

    if errors:
        return None, errors

    return Entity(
        name=name,
        description=description,
        attributes=attributes,
        relationships=relationships,
        tags=tags,
    ), []


def _parse_attribute(raw: dict, entity_name: str, index: int) -> tuple[Attribute | None, list[str]]:
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append(f"Entity '{entity_name}' attribute at index {index} must be a mapping")
        return None, errors

    name = raw.get("name", "")
    if not name:
        errors.append(f"Entity '{entity_name}' attribute at index {index} missing 'name'")
        return None, errors

    type_ = raw.get("type", "string")
    if type_ not in VALID_TYPES:
        errors.append(f"Entity '{entity_name}' attribute '{name}' has invalid type '{type_}'; must be one of {sorted(VALID_TYPES)}")

    enum = raw.get("enum", [])
    if enum and not isinstance(enum, list):
        errors.append(f"Entity '{entity_name}' attribute '{name}' 'enum' must be a list")
        enum = []
    elif enum:
        enum = [str(v) for v in enum]
        if len(enum) == 0:
            errors.append(f"Entity '{entity_name}' attribute '{name}' 'enum' must be non-empty if specified")

    if errors:
        return None, errors

    return Attribute(
        name=name,
        type=type_,
        primary_key=bool(raw.get("primary_key", False)),
        nullable=bool(raw.get("nullable", False)),
        description=str(raw.get("description", "")),
        enum=enum,
    ), []


def _parse_relationship(raw: dict, entity_name: str, index: int) -> tuple[Relationship | None, list[str]]:
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append(f"Entity '{entity_name}' relationship at index {index} must be a mapping")
        return None, errors

    to = raw.get("to", "")
    via = raw.get("via", "")
    cardinality = raw.get("cardinality", "")

    if not to:
        errors.append(f"Entity '{entity_name}' relationship at index {index} missing 'to'")
    if not via:
        errors.append(f"Entity '{entity_name}' relationship at index {index} missing 'via'")
    if cardinality not in VALID_CARDINALITIES:
        errors.append(
            f"Entity '{entity_name}' relationship at index {index} has invalid cardinality '{cardinality}'; "
            f"must be one of {sorted(VALID_CARDINALITIES)}"
        )

    if errors:
        return None, errors

    return Relationship(
        to=to,
        via=via,
        cardinality=cardinality,
        type=raw.get("type"),
    ), []


def _fail_if_errors(errors: list[str]) -> None:
    if errors:
        raise ModelValidationError(
            f"Conceptual model validation failed with {len(errors)} error(s):",
            errors,
        )
