# FinanceFlow — Claude Code Guide

## Project Overview

Full-stack personal finance tracker. Python/FastAPI async backend (aiosqlite) with a Vite/React frontend.

## Backend

```bash
cd backend
pip install -e .

# Run dev server
uvicorn financeflow_api.main:app --reload --port 8000

# API health check
curl http://localhost:8000/api/health
```

### Key files

| File | Purpose |
|---|---|
| `backend/src/financeflow_api/app.py` | FastAPI app factory, all route definitions |
| `backend/src/financeflow_api/db.py` | DB init, schema, query helpers |
| `backend/src/financeflow_api/models.py` | Pydantic models: Transaction, Project, Rule, DataDump |
| `backend/src/financeflow_api/main.py` | Entry point, config |

### Data model

- **Transaction** — amount, date, category, description, project
- **Project** — named grouping for transactions
- **Rule** — budget limit per category with threshold alerts

## Frontend

```bash
cd vite-app
npm install
npm run dev    # dev server (proxies /api to backend)
npm run build  # production build → dist/
```

## CORS

Backend is configured to allow all origins in development. Adjust `cors_origins` in `main.py` for production.

## Documentation

Detailed docs and screenshots are in `docs/`. The `docs/walkthrough.md` is the best reference for understanding the full data flow.
