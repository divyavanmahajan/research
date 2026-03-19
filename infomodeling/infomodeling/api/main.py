"""FastAPI application for infomodel-dbt-generator."""

from __future__ import annotations

import io
import zipfile
from typing import Annotated

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .. import parser
from ..exceptions import ModelValidationError, ParseError
from ..generators.marts import generate_mart_sql, needs_mart
from ..generators.project import generate_dbt_project_yml, generate_profiles_yml, _to_project_name
from ..generators.schema import generate_schema_yml
from ..generators.sources import generate_sources_yml
from ..generators.staging import generate_staging_sql
from ..model import ConceptualModel
from ..seeds.generator import generate_seeds, seeds_to_csv
from .schemas import (
    AttributeSchema,
    EntitySchema,
    GenerateOptions,
    GeneratePreviewResult,
    ModelSchema,
    RelationshipSchema,
    SeedPreviewRow,
    ValidationResult,
)

app = FastAPI(
    title="infomodel-dbt-generator API",
    description="Generate DBT projects from conceptual information model YAML files",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory model store (single-session; stateless enough for v1)
_current_model: ConceptualModel | None = None


def _require_model() -> ConceptualModel:
    if _current_model is None:
        raise HTTPException(status_code=400, detail="No model loaded. POST to /model/upload first.")
    return _current_model


def _model_to_schema(m: ConceptualModel) -> ModelSchema:
    return ModelSchema(
        name=m.name,
        version=m.version,
        description=m.description,
        entity_count=len(m.entities),
        entities=[
            EntitySchema(
                name=e.name,
                snake_name=e.snake_name,
                description=e.description,
                attributes=[
                    AttributeSchema(
                        name=a.name,
                        type=a.type,
                        primary_key=a.primary_key,
                        nullable=a.nullable,
                        description=a.description,
                        enum=a.enum,
                    )
                    for a in e.attributes
                ],
                relationships=[
                    RelationshipSchema(to=r.to, via=r.via, cardinality=r.cardinality, type=r.type)
                    for r in e.relationships
                ],
            )
            for e in m.entities
        ],
    )


# ---------------------------------------------------------------------------
# Model endpoints
# ---------------------------------------------------------------------------

@app.post("/model/upload", response_model=ModelSchema)
async def upload_model(file: Annotated[UploadFile, File(description="Conceptual model YAML file")]):
    """Upload and parse a conceptual model YAML file."""
    global _current_model
    content = await file.read()
    try:
        raw = yaml.safe_load(content)
        m = parser.parse(raw)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=422, detail=f"YAML parse error: {e}")
    except (ParseError, ModelValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    _current_model = m
    return _model_to_schema(m)


@app.post("/model/validate", response_model=ValidationResult)
async def validate_model(file: Annotated[UploadFile, File(description="Conceptual model YAML file")]):
    """Validate a conceptual model YAML file without storing it."""
    content = await file.read()
    try:
        raw = yaml.safe_load(content)
        m = parser.parse(raw)
        return ValidationResult(
            valid=True,
            message=f"Model valid: {len(m.entities)} entities in '{m.name}'",
            errors=[],
        )
    except ModelValidationError as e:
        return ValidationResult(valid=False, message=str(e).split("\n")[0], errors=e.errors)
    except ParseError as e:
        return ValidationResult(valid=False, message=str(e), errors=[str(e)])


@app.get("/model/entities", response_model=ModelSchema)
async def get_entities():
    """Return the currently loaded model with all entities and attributes."""
    m = _require_model()
    return _model_to_schema(m)


# ---------------------------------------------------------------------------
# Generate endpoints
# ---------------------------------------------------------------------------

def _generate_all_files(m: ConceptualModel, opts: GenerateOptions) -> dict[str, str]:
    """Generate all DBT artifact file contents in memory."""
    project_name = _to_project_name(m.name)
    files: dict[str, str] = {}

    files["dbt_project.yml"] = generate_dbt_project_yml(m)
    files["profiles.yml"] = generate_profiles_yml(project_name)
    files["models/sources.yml"] = generate_sources_yml(m, opts.source_name)
    files["models/schema.yml"] = generate_schema_yml(m)

    for entity in m.entities:
        files[f"models/staging/stg_{entity.snake_name}.sql"] = generate_staging_sql(entity, opts.source_name)

    for entity in m.entities:
        if needs_mart(entity):
            files[f"models/marts/dim_{entity.snake_name}.sql"] = generate_mart_sql(entity, m)

    if opts.include_seeds:
        seeds = generate_seeds(m, rows_per_entity=opts.seed_rows, seed=opts.seed)
        for snake_name, rows in seeds.items():
            files[f"seeds/{snake_name}.csv"] = seeds_to_csv(rows)

    return files


@app.post("/generate/preview", response_model=GeneratePreviewResult)
async def generate_preview(opts: GenerateOptions):
    """Generate all artifacts and return them as in-memory content (no download)."""
    m = _require_model()
    files = _generate_all_files(m, opts)
    return GeneratePreviewResult(files=files)


@app.post("/generate/download")
async def generate_download(opts: GenerateOptions):
    """Generate all artifacts and return as a downloadable zip file."""
    m = _require_model()
    files = _generate_all_files(m, opts)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        project_dir = _to_project_name(m.name)
        for rel_path, content in files.items():
            zf.writestr(f"{project_dir}/{rel_path}", content)
    zip_buffer.seek(0)

    filename = f"{_to_project_name(m.name)}_dbt_project.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Seed preview
# ---------------------------------------------------------------------------

@app.post("/seed/preview", response_model=list[SeedPreviewRow])
async def seed_preview(opts: GenerateOptions):
    """Preview the first 10 rows of generated seed data per entity."""
    m = _require_model()
    seeds = generate_seeds(m, rows_per_entity=opts.seed_rows, seed=opts.seed)

    result = []
    for snake_name, rows in seeds.items():
        preview_rows = rows[:10]
        if not preview_rows:
            continue
        columns = list(preview_rows[0].keys())
        table_rows = [[str(row[col]) if row[col] is not None else None for col in columns] for row in preview_rows]
        result.append(SeedPreviewRow(entity_name=snake_name, columns=columns, rows=table_rows))

    return result
