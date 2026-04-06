"""
Databricks SQL Warehouse client.

Required environment variables:
    DATABRICKS_SERVER_HOSTNAME  e.g. adb-1234567890.12.azuredatabricks.net
    DATABRICKS_HTTP_PATH        e.g. /sql/1.0/warehouses/abcdef1234567890
    DATABRICKS_ACCESS_TOKEN     personal access token or service principal token
"""

import os
from contextlib import contextmanager
from databricks import sql


def _connect():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_ACCESS_TOKEN"],
    )


@contextmanager
def get_cursor():
    conn = _connect()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()


# ── Stage → schema field mapping ──────────────────────────────────────────────
# Key   : validation_stage value returned by Databricks (case-sensitive)
# Value : (section, field_name) where section is "pending" or "processed"

STAGE_MAP: dict[str, tuple[str, str]] = {
    # Pending
    "Extraction & Classification": ("pending", "extraction_and_classification"),
    "Waiting for Coding":          ("pending", "waiting_for_coding"),
    "Tax Coding":                  ("pending", "tax_coding"),
    "SAP Errors":                  ("pending", "sap_errors"),
    "Master Data":                 ("pending", "master_data"),
    "RPA Auto Post":               ("pending", "rpa_auto_post"),
    # Processed
    "Posted in SAP":                    ("processed", "posted_in_sap"),
    "Parked in SAP without Line Item":  ("processed", "parked_in_sap"),
    "Parked in SAP with Line Item":     ("processed", "parked_in_sap"),
    "Non Invoice":                      ("processed", "non_invoice"),
    "Duplicate":                        ("processed", "duplicate"),
    "Non Compliant":                    ("processed", "non_compliant"),
    "No PO/No Pay":                     ("processed", "non_po_no_pay"),
    "Bad Scan":                         ("processed", "bad_scan"),
    "ICA Document":                     ("processed", "ica_document"),
}

QUERY = """
    SELECT validation_stage, COUNT(validation_stage) AS cnt
    FROM prod_l1.e2e.invoice_validation_result
    GROUP BY validation_stage
"""


def fetch_dashboard_counts() -> dict:
    """
    Run the Databricks query and return a nested dict:
        {
          "pending":   { field: count, ... },
          "processed": { field: count, ... },
        }
    Unmapped stages are silently ignored; missing fields default to 0.
    """
    pending: dict[str, int] = {
        "extraction_and_classification": 0,
        "waiting_for_coding": 0,
        "master_data": 0,
        "tax_coding": 0,
        "sap_errors": 0,
        "rpa_auto_post": 0,
    }
    processed: dict[str, int] = {
        "posted_in_sap": 0,
        "parked_in_sap": 0,
        "non_invoice": 0,
        "duplicate": 0,
        "non_compliant": 0,
        "non_po_no_pay": 0,
        "bad_scan": 0,
        "ica_document": 0,
    }

    with get_cursor() as cursor:
        cursor.execute(QUERY)
        for row in cursor.fetchall():
            stage: str = row["validation_stage"]
            count: int = int(row["cnt"])
            mapping = STAGE_MAP.get(stage)
            if mapping:
                section, field = mapping
                target = pending if section == "pending" else processed
                target[field] = target.get(field, 0) + count

    pending["overall_invoice_workflow"] = sum(pending.values())
    return {"pending": pending, "processed": processed}
