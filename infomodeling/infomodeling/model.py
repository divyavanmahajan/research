"""Domain dataclasses for the conceptual information model."""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_TYPES = {"string", "integer", "float", "boolean", "date", "timestamp", "uuid"}
VALID_CARDINALITIES = {"many_to_one", "one_to_many", "many_to_many", "one_to_one"}


@dataclass
class Relationship:
    to: str                        # Target entity name (PascalCase)
    via: str                       # FK field name in this entity
    cardinality: str               # one of VALID_CARDINALITIES
    type: str | None = None        # e.g. "self_referential"


@dataclass
class Attribute:
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = False
    description: str = ""
    enum: list[str] = field(default_factory=list)


@dataclass
class Entity:
    name: str                                         # PascalCase
    description: str = ""
    attributes: list[Attribute] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def snake_name(self) -> str:
        """Convert PascalCase entity name to snake_case."""
        import re
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", self.name)
        return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s).lower()

    @property
    def primary_key(self) -> Attribute | None:
        """Return the primary key attribute, or None."""
        for attr in self.attributes:
            if attr.primary_key:
                return attr
        return None

    @property
    def many_to_one_relationships(self) -> list[Relationship]:
        return [r for r in self.relationships if r.cardinality == "many_to_one"]


@dataclass
class ConceptualModel:
    name: str
    version: str
    description: str = ""
    entities: list[Entity] = field(default_factory=list)

    def entity_by_name(self, name: str) -> Entity | None:
        for e in self.entities:
            if e.name == name:
                return e
        return None
