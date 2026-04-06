// ── Response types ────────────────────────────────────────────────────────────

export interface PendingInvoices {
  /** Sum of all pending stage counts */
  overall_invoice_workflow: number;
  /** Invoices being extracted/classified */
  extraction_and_classification: number;
  /** Invoices awaiting GL coding */
  waiting_for_coding: number;
  /** Invoices blocked on master data issues */
  master_data: number;
  /** Invoices awaiting tax coding */
  tax_coding: number;
  /** Invoices with SAP posting errors */
  sap_errors: number;
  /** Invoices queued for RPA auto-posting */
  rpa_auto_post: number;
}

export interface ProcessedInvoices {
  /** Invoices successfully posted in SAP */
  posted_in_sap: number;
  /** Invoices parked in SAP (with or without line) */
  parked_in_sap: number;
  /** Documents classified as non-invoice */
  non_invoice: number;
  /** Duplicate invoice documents */
  duplicate: number;
  /** Invoices failing compliance checks */
  non_compliant: number;
  /** Invoices with no PO or no-pay status */
  non_po_no_pay: number;
  /** Invoices rejected due to bad scan quality */
  bad_scan: number;
  /** Inter-company accounting documents */
  ica_document: number;
}

export interface InvoiceDashboard {
  pending_invoices: PendingInvoices;
  processed_invoices: ProcessedInvoices;
}

// ── API client ────────────────────────────────────────────────────────────────

export class InvoiceDashboardClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8001") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /** GET /api/v1/dashboard — full dashboard */
  async getDashboard(): Promise<InvoiceDashboard> {
    return this.get<InvoiceDashboard>("/api/v1/dashboard");
  }

  /** GET /api/v1/dashboard/pending — pending invoices only */
  async getPending(): Promise<PendingInvoices> {
    return this.get<PendingInvoices>("/api/v1/dashboard/pending");
  }

  /** GET /api/v1/dashboard/processed — posted/parked/rejected invoices only */
  async getProcessed(): Promise<ProcessedInvoices> {
    return this.get<ProcessedInvoices>("/api/v1/dashboard/processed");
  }

  private async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`Invoice Dashboard API error ${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
  }
}
