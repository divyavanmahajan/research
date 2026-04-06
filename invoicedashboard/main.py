from fastapi import FastAPI, HTTPException

from databricks_client import fetch_dashboard_counts
from schemas import InvoiceDashboard, PendingInvoices, ProcessedInvoices

app = FastAPI(
    title="Invoice Dashboard API",
    description="Live invoice workflow metrics from Databricks SQL Warehouse.",
    version="2.0.0",
)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard", response_model=InvoiceDashboard, tags=["Dashboard"])
def get_dashboard():
    """Return all invoice metrics in a single call."""
    try:
        data = fetch_dashboard_counts()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Databricks query failed: {exc}")

    return InvoiceDashboard(
        pending_invoices=PendingInvoices(**data["pending"]),
        processed_invoices=ProcessedInvoices(**data["processed"]),
    )


# ── Pending Invoices ──────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard/pending", response_model=PendingInvoices, tags=["Pending Invoices"])
def get_pending():
    """Return only the pending invoice metrics."""
    try:
        data = fetch_dashboard_counts()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Databricks query failed: {exc}")

    return PendingInvoices(**data["pending"])


# ── Processed Invoices ────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard/processed", response_model=ProcessedInvoices, tags=["Processed Invoices"])
def get_processed():
    """Return only the posted/parked/rejected invoice metrics."""
    try:
        data = fetch_dashboard_counts()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Databricks query failed: {exc}")

    return ProcessedInvoices(**data["processed"])
