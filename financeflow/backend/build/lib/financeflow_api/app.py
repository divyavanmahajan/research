from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from financeflow_api import db as _db
from financeflow_api.models import DataDump, Project, Rule, Transaction


def create_app(db_path: str, cors_origins: list[str]) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await _db.init_db(db_path)
        yield

    app = FastAPI(title="FinanceFlow API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # helper: open a connection for the duration of a request
    async def _conn():
        return await aiosqlite.connect(db_path).__aenter__()

    # ── Health ────────────────────────────────────────────────────────────────

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        async with aiosqlite.connect(db_path) as conn:
            txn_count = (await (await conn.execute("SELECT COUNT(*) FROM transactions")).fetchone())[0]
            proj_count = (await (await conn.execute("SELECT COUNT(*) FROM projects")).fetchone())[0]
            rule_count = (await (await conn.execute("SELECT COUNT(*) FROM rules")).fetchone())[0]
        return {
            "status": "ok",
            "db_path": db_path,
            "counts": {"transactions": txn_count, "projects": proj_count, "rules": rule_count},
        }

    # ── Transactions ──────────────────────────────────────────────────────────

    @app.get("/api/transactions", response_model=list[Transaction])
    async def list_transactions():
        async with aiosqlite.connect(db_path) as conn:
            return await _db.get_all_transactions(conn)

    @app.post("/api/transactions", response_model=Transaction, status_code=201)
    async def create_transaction(txn: Transaction):
        async with aiosqlite.connect(db_path) as conn:
            await _db.upsert_transaction(conn, txn)
            await conn.commit()
        return txn

    @app.put("/api/transactions/{txn_id}", response_model=Transaction)
    async def update_transaction(txn_id: str, txn: Transaction):
        txn.id = txn_id
        async with aiosqlite.connect(db_path) as conn:
            await _db.upsert_transaction(conn, txn)
            await conn.commit()
        return txn

    @app.delete("/api/transactions/{txn_id}")
    async def delete_transaction(txn_id: str):
        async with aiosqlite.connect(db_path) as conn:
            found = await _db.delete_transaction(conn, txn_id)
            await conn.commit()
        if not found:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"ok": True}

    # ── Projects ──────────────────────────────────────────────────────────────

    @app.get("/api/projects", response_model=list[Project])
    async def list_projects():
        async with aiosqlite.connect(db_path) as conn:
            return await _db.get_all_projects(conn)

    @app.post("/api/projects", response_model=Project, status_code=201)
    async def create_project(project: Project):
        async with aiosqlite.connect(db_path) as conn:
            await _db.upsert_project(conn, project)
            await conn.commit()
        return project

    @app.put("/api/projects/{project_id}", response_model=Project)
    async def update_project(project_id: str, project: Project):
        project.id = project_id
        async with aiosqlite.connect(db_path) as conn:
            await _db.upsert_project(conn, project)
            await conn.commit()
        return project

    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str):
        async with aiosqlite.connect(db_path) as conn:
            found = await _db.delete_project(conn, project_id)
            await conn.commit()
        if not found:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"ok": True}

    # ── Rules ─────────────────────────────────────────────────────────────────

    @app.get("/api/rules", response_model=list[Rule])
    async def list_rules():
        async with aiosqlite.connect(db_path) as conn:
            return await _db.get_all_rules(conn)

    @app.post("/api/rules", response_model=Rule, status_code=201)
    async def create_rule(rule: Rule):
        async with aiosqlite.connect(db_path) as conn:
            await _db.upsert_rule(conn, rule)
            await conn.commit()
        return rule

    @app.delete("/api/rules/{rule_id}")
    async def delete_rule(rule_id: str):
        async with aiosqlite.connect(db_path) as conn:
            found = await _db.delete_rule(conn, rule_id)
            await conn.commit()
        if not found:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"ok": True}

    # ── Bulk data ─────────────────────────────────────────────────────────────

    @app.get("/api/data", response_model=DataDump)
    async def export_data():
        async with aiosqlite.connect(db_path) as conn:
            return await _db.get_data_dump(conn)

    @app.post("/api/data")
    async def import_data(data: DataDump):
        async with aiosqlite.connect(db_path) as conn:
            await _db.replace_all_data(conn, data)
        return {
            "imported": {
                "transactions": len(data.transactions),
                "projects": len(data.projects),
                "rules": len(data.rules),
            }
        }

    return app
