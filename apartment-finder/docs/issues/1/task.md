# Issue #1 — Phase 0: Project Scaffold + Phase 1: Backend Core (TDD)

## User Story

> As a developer, I want the project scaffolded with backend (Python FastAPI) and frontend (React + Vite + TypeScript) directories, and all backend endpoints implemented with full test coverage using TDD, so that the frontend can be built against a working API.

## Acceptance Criteria

### Phase 0 — Scaffold
- [x] `backend/` folder with `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- [x] `frontend/` folder created with Vite (React + TypeScript)
- [x] Vite proxy configured (`/api` → `localhost:8000`)
- [x] CORS configured in FastAPI for `localhost:5173`
- [x] pytest with `respx` configured
- [x] Vitest + RTL + jsdom configured
- [x] `GET /api/health` endpoint + test
- [x] Updated `README.md` with quick-start instructions
- [x] `.gitignore` for Python + Node

### Phase 1 — Backend Core (TDD)
- [x] `test_fetch_listing_valid_id` (mock Qasa) → `services/qasa_client.py` + `GET /api/listing/{home_id}`
- [x] Tests: invalid ID (400), not found (404), upstream error (502)
- [x] `test_parse_url_valid` + `test_parse_url_invalid` → `services/url_parser.py` + `POST /api/parse-url`
- [x] `test_search_basic` (mocked single-page response) → `POST /api/search`
- [x] `test_search_pagination` (mocked multi-page response)
- [x] `test_search_missing_area` (400)
- [x] `test_cors_header`
- [x] All backend tests passing ✅

## References
- [spec.md](../spec.md) — Full specification
- [architecture.md](../architecture.md) — Architecture details
- [developer.md](../developer.md) — Developer guide
- [qasa-protocol.md](../../protocol/qasa-protocol.md) — Qasa API protocol
