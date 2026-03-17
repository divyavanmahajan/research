"""FastAPI integration tests."""

import io
import os
import zipfile

import pytest
import yaml
from fastapi.testclient import TestClient

from infomodeling.api.main import app, _current_model
import infomodeling.api.main as api_main

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
ORG_MODEL_PATH = os.path.join(EXAMPLES_DIR, "org_model.yaml")


@pytest.fixture(autouse=True)
def reset_model():
    """Reset the in-memory model between tests."""
    api_main._current_model = None
    yield
    api_main._current_model = None


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def client_with_model(client):
    """Client with the org model already uploaded."""
    with open(ORG_MODEL_PATH, "rb") as f:
        response = client.post("/model/upload", files={"file": ("org_model.yaml", f, "application/yaml")})
    assert response.status_code == 200
    return client


def _org_model_file():
    return open(ORG_MODEL_PATH, "rb")


# ---------------------------------------------------------------------------
# /model/upload
# ---------------------------------------------------------------------------

class TestUploadModel:
    def test_upload_valid_model(self, client):
        with _org_model_file() as f:
            response = client.post("/model/upload", files={"file": ("org_model.yaml", f)})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corp Information Model"
        assert data["entity_count"] == 10

    def test_upload_invalid_yaml(self, client):
        bad_yaml = b":\t: bad yaml [\n"
        response = client.post("/model/upload", files={"file": ("bad.yaml", io.BytesIO(bad_yaml))})
        assert response.status_code == 422

    def test_upload_invalid_model(self, client):
        bad_model = b"version: '1.0'\nname: Test\nentities:\n  - name: Foo\n    attributes: []\n"
        response = client.post("/model/upload", files={"file": ("model.yaml", io.BytesIO(bad_model))})
        assert response.status_code == 422

    def test_upload_returns_entities(self, client):
        with _org_model_file() as f:
            response = client.post("/model/upload", files={"file": ("org_model.yaml", f)})
        data = response.json()
        entity_names = [e["name"] for e in data["entities"]]
        assert "Person" in entity_names
        assert "OrganizationalUnit" in entity_names

    def test_upload_entity_has_attributes(self, client):
        with _org_model_file() as f:
            response = client.post("/model/upload", files={"file": ("org_model.yaml", f)})
        data = response.json()
        person = next(e for e in data["entities"] if e["name"] == "Person")
        attr_names = [a["name"] for a in person["attributes"]]
        assert "person_id" in attr_names
        assert "email" in attr_names


# ---------------------------------------------------------------------------
# /model/validate
# ---------------------------------------------------------------------------

class TestValidateModel:
    def test_valid_model_returns_true(self, client):
        with _org_model_file() as f:
            response = client.post("/model/validate", files={"file": ("org_model.yaml", f)})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_invalid_model_returns_false(self, client):
        bad_model = b"version: '1.0'\nname: Test\nentities:\n  - name: Foo\n    attributes: []\n"
        response = client.post("/model/validate", files={"file": ("model.yaml", io.BytesIO(bad_model))})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


# ---------------------------------------------------------------------------
# /model/entities
# ---------------------------------------------------------------------------

class TestGetEntities:
    def test_no_model_returns_400(self, client):
        response = client.get("/model/entities")
        assert response.status_code == 400

    def test_returns_model_after_upload(self, client_with_model):
        response = client_with_model.get("/model/entities")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_count"] == 10


# ---------------------------------------------------------------------------
# /generate/preview
# ---------------------------------------------------------------------------

class TestGeneratePreview:
    def test_no_model_returns_400(self, client):
        response = client.post("/generate/preview", json={})
        assert response.status_code == 400

    def test_preview_contains_expected_files(self, client_with_model):
        response = client_with_model.post("/generate/preview", json={"include_seeds": False})
        assert response.status_code == 200
        files = response.json()["files"]
        assert "dbt_project.yml" in files
        assert "models/sources.yml" in files
        assert "models/staging/stg_person.sql" in files
        assert "models/schema.yml" in files

    def test_preview_with_seeds(self, client_with_model):
        response = client_with_model.post("/generate/preview", json={"seed_rows": 5, "seed": 42, "include_seeds": True})
        assert response.status_code == 200
        files = response.json()["files"]
        assert "seeds/person.csv" in files

    def test_staging_sql_content(self, client_with_model):
        response = client_with_model.post("/generate/preview", json={"include_seeds": False})
        files = response.json()["files"]
        assert "config(materialized='view')" in files["models/staging/stg_person.sql"]

    def test_schema_yml_is_valid_yaml(self, client_with_model):
        response = client_with_model.post("/generate/preview", json={"include_seeds": False})
        files = response.json()["files"]
        schema = yaml.safe_load(files["models/schema.yml"])
        assert schema["version"] == 2
        assert "models" in schema


# ---------------------------------------------------------------------------
# /generate/download
# ---------------------------------------------------------------------------

class TestGenerateDownload:
    def test_no_model_returns_400(self, client):
        response = client.post("/generate/download", json={})
        assert response.status_code == 400

    def test_returns_zip_file(self, client_with_model):
        response = client_with_model.post("/generate/download", json={"include_seeds": False, "seed": 42})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_zip_contains_expected_files(self, client_with_model):
        response = client_with_model.post("/generate/download", json={"include_seeds": False, "seed": 42})
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert any("dbt_project.yml" in n for n in names)
        assert any("stg_person.sql" in n for n in names)


# ---------------------------------------------------------------------------
# /seed/preview
# ---------------------------------------------------------------------------

class TestSeedPreview:
    def test_no_model_returns_400(self, client):
        response = client.post("/seed/preview", json={})
        assert response.status_code == 400

    def test_returns_seed_previews(self, client_with_model):
        response = client_with_model.post("/seed/preview", json={"seed_rows": 20, "seed": 42})
        assert response.status_code == 200
        previews = response.json()
        assert len(previews) == 10  # one per entity

    def test_preview_has_correct_structure(self, client_with_model):
        response = client_with_model.post("/seed/preview", json={"seed_rows": 20, "seed": 42})
        previews = response.json()
        person_preview = next(p for p in previews if p["entity_name"] == "person")
        assert "columns" in person_preview
        assert "rows" in person_preview
        assert "person_id" in person_preview["columns"]
        assert len(person_preview["rows"]) <= 10

    def test_preview_rows_respect_seed_rows_limit(self, client_with_model):
        response = client_with_model.post("/seed/preview", json={"seed_rows": 5, "seed": 42})
        previews = response.json()
        for preview in previews:
            assert len(preview["rows"]) <= 5
