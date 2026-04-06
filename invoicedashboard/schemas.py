from pydantic import BaseModel, Field


class PendingInvoices(BaseModel):
    overall_invoice_workflow: int = Field(..., description="Sum of all pending stage counts")
    extraction_and_classification: int = Field(..., description="Invoices being extracted/classified")
    waiting_for_coding: int = Field(..., description="Invoices awaiting GL coding")
    master_data: int = Field(..., description="Invoices blocked on master data issues")
    tax_coding: int = Field(..., description="Invoices awaiting tax coding")
    sap_errors: int = Field(..., description="Invoices with SAP posting errors")
    rpa_auto_post: int = Field(..., description="Invoices queued for RPA auto-posting")


class ProcessedInvoices(BaseModel):
    posted_in_sap: int = Field(..., description="Invoices successfully posted in SAP")
    parked_in_sap: int = Field(..., description="Invoices parked in SAP (with or without line)")
    non_invoice: int = Field(..., description="Documents classified as non-invoice")
    duplicate: int = Field(..., description="Duplicate invoice documents")
    non_compliant: int = Field(..., description="Invoices failing compliance checks")
    non_po_no_pay: int = Field(..., description="Invoices with no PO or no-pay status")
    bad_scan: int = Field(..., description="Invoices rejected due to bad scan quality")
    ica_document: int = Field(..., description="Inter-company accounting documents")


class InvoiceDashboard(BaseModel):
    pending_invoices: PendingInvoices
    processed_invoices: ProcessedInvoices
