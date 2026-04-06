from sqlalchemy import Column, Integer, String
from database import Base


class PendingInvoiceMetrics(Base):
    """Single-row table storing pending invoice counts."""
    __tablename__ = "pending_invoice_metrics"

    id: int = Column(Integer, primary_key=True, default=1)
    overall_invoice_workflow: int = Column(Integer, nullable=False, default=0)
    extraction_and_classification: int = Column(Integer, nullable=False, default=0)
    waiting_for_coding: int = Column(Integer, nullable=False, default=0)
    master_data: int = Column(Integer, nullable=False, default=0)
    tax_coding: int = Column(Integer, nullable=False, default=0)
    sap_errors: int = Column(Integer, nullable=False, default=0)
    rpa_auto_post: int = Column(Integer, nullable=False, default=0)


class ProcessedInvoiceMetrics(Base):
    """Single-row table storing posted/parked/rejected invoice counts."""
    __tablename__ = "processed_invoice_metrics"

    id: int = Column(Integer, primary_key=True, default=1)
    posted_in_sap: int = Column(Integer, nullable=False, default=0)
    parked_in_sap: int = Column(Integer, nullable=False, default=0)
    non_invoice: int = Column(Integer, nullable=False, default=0)
    duplicate: int = Column(Integer, nullable=False, default=0)
    non_compliant: int = Column(Integer, nullable=False, default=0)
    non_po_no_pay: int = Column(Integer, nullable=False, default=0)
    bad_scan: int = Column(Integer, nullable=False, default=0)
    ica_document: int = Column(Integer, nullable=False, default=0)
