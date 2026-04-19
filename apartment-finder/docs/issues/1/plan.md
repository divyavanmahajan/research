# Phase 0 & 1 Implementation Plan

## Goals
- Scaffold backend (Python/FastAPI) and frontend (React/Vite/TS).
- Implement core Qasa API proxy functionality.
- Achieve 100% test coverage for core utilities and API wrappers via TDD.

## Steps
1. **Backend Scaffold**: Initialize FastAPI, CORS, and requirements.
2. **Qasa Client**: Implement async GraphQL client for HomeView and HomeSearch.
3. **URL Parsing**: Implement regex-based extraction of Qasa home IDs.
4. **Backend Routes**: Implement `/api/listing`, `/api/search`, and `/api/parse-url`.
5. **Frontend Scaffold**: Initialize Vite with React/TS/Vitest.
6. **Frontend Foundation**: Define TS types, implement DB, URL parser, and pinColor utilities.
7. **Frontend State**: Implement Zustand store with persistence.
8. **Frontend UI**: Build responsive split-panel layout with Leaflet map.
9. **Integration**: Connect frontend actions to backend API.
