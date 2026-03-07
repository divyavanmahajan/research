# FinanceFlow

A full-stack personal finance tracker. Track transactions, set budgets, drill into spending by category, and answer "can I spend this?" questions.

## Features

- Transaction entry with category and project tagging
- Budget rules engine with configurable limits per category
- Dashboard with spending overview and category breakdown
- Transaction drill-down by category or project
- "Can I spend?" quick check view
- FastAPI backend with async SQLite; Vite frontend

## Architecture

```
financeflow/
├── backend/               Python FastAPI + aiosqlite backend
│   └── src/
│       └── financeflow_api/
│           ├── app.py     FastAPI app factory, routes, CORS
│           ├── db.py      Database init and helpers
│           ├── models.py  Pydantic models (Transaction, Project, Rule)
│           └── main.py    Entry point
├── vite-app/              Frontend (Vite + React)
├── docs/                  Documentation and screenshots
│   ├── getting-started.md Quick-start guide
│   ├── walkthrough.md     Code walkthrough
│   └── user-walkthrough.md Visual guide with screenshots
└── finance-tracker.jsx    Standalone JSX prototype
```

## Quick Start

```bash
# Backend
cd backend
pip install -e .
uvicorn financeflow_api.main:app --reload

# Frontend (separate terminal)
cd vite-app
npm install
npm run dev
```

## Documentation

| Document | Description |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | Prerequisites, setup options, first steps |
| [`docs/walkthrough.md`](docs/walkthrough.md) | Full code walkthrough — data model, budget engine, every view |
| [`docs/user-walkthrough.md`](docs/user-walkthrough.md) | Visual user guide with annotated screenshots |
