from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class Transaction(BaseModel):
    id: str
    date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[list[str]] = None
    project_id: Optional[str] = None
    notes: Optional[str] = None
    type: Optional[str] = None
    splits: Optional[list[dict[str, Any]]] = None


class Project(BaseModel):
    id: str
    name: Optional[str] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None


class Rule(BaseModel):
    id: str
    pattern: Optional[str] = None
    category_id: Optional[str] = None
    priority: Optional[int] = None


class DataDump(BaseModel):
    transactions: list[Transaction] = []
    projects: list[Project] = []
    rules: list[Rule] = []
