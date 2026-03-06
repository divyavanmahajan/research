from __future__ import annotations
import json
import aiosqlite
from financeflow_api.models import Transaction, Project, Rule, DataDump

CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    date TEXT,
    amount REAL,
    currency TEXT,
    merchant TEXT,
    category_id TEXT,
    tags TEXT,
    project_id TEXT,
    notes TEXT,
    type TEXT,
    splits TEXT
)
"""

CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    budget REAL,
    currency TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT
)
"""

CREATE_RULES = """
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    pattern TEXT,
    category_id TEXT,
    priority INTEGER
)
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TRANSACTIONS)
        await db.execute(CREATE_PROJECTS)
        await db.execute(CREATE_RULES)
        await db.commit()


# ── Transactions ──────────────────────────────────────────────────────────────

def _row_to_transaction(row: tuple) -> Transaction:
    return Transaction(
        id=row[0],
        date=row[1],
        amount=row[2],
        currency=row[3],
        merchant=row[4],
        category_id=row[5],
        tags=json.loads(row[6]) if row[6] else [],
        project_id=row[7],
        notes=row[8],
        type=row[9],
        splits=json.loads(row[10]) if row[10] else None,
    )


async def get_all_transactions(db: aiosqlite.Connection) -> list[Transaction]:
    async with db.execute("SELECT * FROM transactions ORDER BY date DESC") as cur:
        rows = await cur.fetchall()
    return [_row_to_transaction(r) for r in rows]


async def upsert_transaction(db: aiosqlite.Connection, t: Transaction) -> None:
    await db.execute(
        """INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             date=excluded.date, amount=excluded.amount, currency=excluded.currency,
             merchant=excluded.merchant, category_id=excluded.category_id,
             tags=excluded.tags, project_id=excluded.project_id,
             notes=excluded.notes, type=excluded.type, splits=excluded.splits""",
        (
            t.id, t.date, t.amount, t.currency, t.merchant, t.category_id,
            json.dumps(t.tags or []),
            t.project_id, t.notes, t.type,
            json.dumps(t.splits) if t.splits is not None else None,
        ),
    )


async def delete_transaction(db: aiosqlite.Connection, txn_id: str) -> bool:
    cur = await db.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    return cur.rowcount > 0


# ── Projects ──────────────────────────────────────────────────────────────────

def _row_to_project(row: tuple) -> Project:
    return Project(
        id=row[0], name=row[1], budget=row[2], currency=row[3],
        start_date=row[4], end_date=row[5], status=row[6],
    )


async def get_all_projects(db: aiosqlite.Connection) -> list[Project]:
    async with db.execute("SELECT * FROM projects") as cur:
        rows = await cur.fetchall()
    return [_row_to_project(r) for r in rows]


async def upsert_project(db: aiosqlite.Connection, p: Project) -> None:
    await db.execute(
        """INSERT INTO projects VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, budget=excluded.budget, currency=excluded.currency,
             start_date=excluded.start_date, end_date=excluded.end_date,
             status=excluded.status""",
        (p.id, p.name, p.budget, p.currency, p.start_date, p.end_date, p.status),
    )


async def delete_project(db: aiosqlite.Connection, project_id: str) -> bool:
    cur = await db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return cur.rowcount > 0


# ── Rules ─────────────────────────────────────────────────────────────────────

def _row_to_rule(row: tuple) -> Rule:
    return Rule(id=row[0], pattern=row[1], category_id=row[2], priority=row[3])


async def get_all_rules(db: aiosqlite.Connection) -> list[Rule]:
    async with db.execute("SELECT * FROM rules ORDER BY priority") as cur:
        rows = await cur.fetchall()
    return [_row_to_rule(r) for r in rows]


async def upsert_rule(db: aiosqlite.Connection, r: Rule) -> None:
    await db.execute(
        """INSERT INTO rules VALUES (?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             pattern=excluded.pattern, category_id=excluded.category_id,
             priority=excluded.priority""",
        (r.id, r.pattern, r.category_id, r.priority),
    )


async def delete_rule(db: aiosqlite.Connection, rule_id: str) -> bool:
    cur = await db.execute("DELETE FROM rules WHERE id=?", (rule_id,))
    return cur.rowcount > 0


# ── Bulk ──────────────────────────────────────────────────────────────────────

async def get_data_dump(db: aiosqlite.Connection) -> DataDump:
    return DataDump(
        transactions=await get_all_transactions(db),
        projects=await get_all_projects(db),
        rules=await get_all_rules(db),
    )


async def replace_all_data(db: aiosqlite.Connection, data: DataDump) -> None:
    await db.execute("DELETE FROM transactions")
    await db.execute("DELETE FROM projects")
    await db.execute("DELETE FROM rules")
    for t in data.transactions:
        await upsert_transaction(db, t)
    for p in data.projects:
        await upsert_project(db, p)
    for r in data.rules:
        await upsert_rule(db, r)
    await db.commit()
