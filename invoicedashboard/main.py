from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import init_db, get_db
import models
from schemas import (
    InvoiceDashboard,
    InvoiceDashboardUpdate,
    PendingInvoices,
    PendingInvoicesUpdate,
    ProcessedInvoices,
    ProcessedInvoicesUpdate,
)

app = FastAPI(
    title="Invoice Dashboard API",
    description="REST API for invoice workflow metrics displayed on the dashboard.",
    version="1.0.0",
)

# ── Seed data (from the screenshot) ──────────────────────────────────────────

SEED_PENDING = dict(
    overall_invoice_workflow=2000,
    extraction_and_classification=800,
    waiting_for_coding=800,
    master_data=200,
    tax_coding=150,
    sap_errors=50,
    rpa_auto_post=0,
)

SEED_PROCESSED = dict(
    posted_in_sap=3000,
    parked_in_sap=100,
    non_invoice=50,
    duplicate=100,
    non_compliant=90,
    non_po_no_pay=50,
    bad_scan=10,
    ica_document=1,
)


def _get_or_create_pending(db: Session) -> models.PendingInvoiceMetrics:
    row = db.get(models.PendingInvoiceMetrics, 1)
    if not row:
        row = models.PendingInvoiceMetrics(id=1, **SEED_PENDING)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _get_or_create_processed(db: Session) -> models.ProcessedInvoiceMetrics:
    row = db.get(models.ProcessedInvoiceMetrics, 1)
    if not row:
        row = models.ProcessedInvoiceMetrics(id=1, **SEED_PROCESSED)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard", response_model=InvoiceDashboard, tags=["Dashboard"])
def get_dashboard(db: Session = Depends(get_db)):
    """Return all invoice metrics in a single response."""
    pending = _get_or_create_pending(db)
    processed = _get_or_create_processed(db)
    return InvoiceDashboard(
        pending_invoices=PendingInvoices.model_validate(pending, from_attributes=True),
        processed_invoices=ProcessedInvoices.model_validate(processed, from_attributes=True),
    )


@app.patch("/api/v1/dashboard", response_model=InvoiceDashboard, tags=["Dashboard"])
def update_dashboard(payload: InvoiceDashboardUpdate, db: Session = Depends(get_db)):
    """Partially update any combination of pending or processed metrics."""
    if payload.pending_invoices:
        _patch_row(db, _get_or_create_pending(db), payload.pending_invoices)
    if payload.processed_invoices:
        _patch_row(db, _get_or_create_processed(db), payload.processed_invoices)
    return get_dashboard(db)


# ── Pending Invoices ──────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard/pending", response_model=PendingInvoices, tags=["Pending Invoices"])
def get_pending(db: Session = Depends(get_db)):
    """Return only the pending invoice metrics."""
    row = _get_or_create_pending(db)
    return PendingInvoices.model_validate(row, from_attributes=True)


@app.patch("/api/v1/dashboard/pending", response_model=PendingInvoices, tags=["Pending Invoices"])
def update_pending(payload: PendingInvoicesUpdate, db: Session = Depends(get_db)):
    """Partially update pending invoice counts."""
    row = _get_or_create_pending(db)
    _patch_row(db, row, payload)
    return PendingInvoices.model_validate(row, from_attributes=True)


# ── Processed Invoices ────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard/processed", response_model=ProcessedInvoices, tags=["Processed Invoices"])
def get_processed(db: Session = Depends(get_db)):
    """Return only the posted/parked/rejected invoice metrics."""
    row = _get_or_create_processed(db)
    return ProcessedInvoices.model_validate(row, from_attributes=True)


@app.patch("/api/v1/dashboard/processed", response_model=ProcessedInvoices, tags=["Processed Invoices"])
def update_processed(payload: ProcessedInvoicesUpdate, db: Session = Depends(get_db)):
    """Partially update processed invoice counts."""
    row = _get_or_create_processed(db)
    _patch_row(db, row, payload)
    return ProcessedInvoices.model_validate(row, from_attributes=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_row(db: Session, row, payload) -> None:
    """Apply non-None fields from a Pydantic update model onto an ORM row."""
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
