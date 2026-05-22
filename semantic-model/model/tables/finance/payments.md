# payments

**Full name:** `main.finance.payments`  
**Type:** MANAGED  
**Schema:** finance  
**Catalog:** main

> Payment transactions applied against invoices. An invoice may have multiple partial payments.

**Approximate row count:** 5,300,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `payment_id` | BIGINT | NO | Primary key. |
| 1 | `invoice_id` | BIGINT | NO | FK → `main.finance.invoices`.`invoice_id` |
| 2 | `payment_date` | DATE | NO | Date payment was received. |
| 3 | `amount` | DECIMAL(12,2) | NO | Payment amount in USD. |
| 4 | `payment_method` | STRING | NO | Values: `credit_card`, `bank_transfer`, `check`, `cash`, `crypto`. |
| 5 | `reference_number` | STRING | YES | Bank reference or transaction ID. |
| 6 | `status` | STRING | NO | Values: `pending`, `cleared`, `failed`, `reversed`. |
| 7 | `processed_by` | STRING | YES | Staff member or system that processed the payment. |

## Relationships

**References (this table → other):**
- `invoice_id` → `main.finance.invoices`.`invoice_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- _(none)_

## Example Joins

```sql
-- Payment receipts with invoice and customer details
SELECT
    p.payment_id,
    p.payment_date,
    p.amount,
    p.payment_method,
    p.status,
    i.invoice_id,
    i.total_amount        AS invoice_total,
    c.customer_name,
    c.segment
FROM main.finance.payments p
JOIN main.finance.invoices i  ON p.invoice_id  = i.invoice_id
JOIN main.sales.customers c   ON i.customer_id = c.customer_id
WHERE p.status = 'cleared'
  AND p.payment_date >= '2025-01-01'
ORDER BY p.payment_date DESC;
```

```sql
-- Payments by method and month (revenue reconciliation)
SELECT
    DATE_TRUNC('month', payment_date) AS payment_month,
    payment_method,
    COUNT(*)        AS transaction_count,
    SUM(amount)     AS total_collected
FROM main.finance.payments
WHERE status = 'cleared'
GROUP BY DATE_TRUNC('month', payment_date), payment_method
ORDER BY payment_month DESC, total_collected DESC;
```
