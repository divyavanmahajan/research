"""Pydantic request/response models for the FastAPI API."""

from __future__ import annotations

from pydantic import BaseModel


class AttributeSchema(BaseModel):
    name: str
    type: str
    primary_key: bool
    nullable: bool
    description: str
    enum: list[str]


class RelationshipSchema(BaseModel):
    to: str
    via: str
    cardinality: str
    type: str | None


class EntitySchema(BaseModel):
    name: str
    snake_name: str
    description: str
    attributes: list[AttributeSchema]
    relationships: list[RelationshipSchema]
    tags: list[str] = []


class ExportRequest(BaseModel):
    entity_names: list[str] = []  # empty = export all


class ModelSchema(BaseModel):
    name: str
    version: str
    description: str
    entities: list[EntitySchema]
    entity_count: int


class ValidationResult(BaseModel):
    valid: bool
    message: str
    errors: list[str]


class GenerateOptions(BaseModel):
    source_name: str = "raw"
    seed_rows: int = 50
    seed: int | None = None
    include_seeds: bool = True


class SeedPreviewRow(BaseModel):
    entity_name: str
    columns: list[str]
    rows: list[list[str | None]]  # first 10 rows as string values


class GeneratePreviewResult(BaseModel):
    files: dict[str, str]  # relative path → file content
