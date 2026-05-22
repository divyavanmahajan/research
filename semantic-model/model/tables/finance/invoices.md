# invoices

**Full name:** `main.finance.invoices`  
**Type:** MANAGED  
**Schema:** finance  
**Catalog:** main

> Customer invoices generated after an order is placed. One row per invoice, which usually corresponds to one order.

**Approximate row count:** 5,100,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `invoice_id` | BIGINT | NO | Primary key. |
| 1 | `order_id` | BIGINT | NO | FK → `main.sales.orders`.`order_id` |
| 2 | `customer_id` | BIGINT | NO | FK → `main.sales.customers`.`customer_id` |
| 3 | `invoice_date` | DATE | NO | Date the invoice was issued. |
| 4 | `due_date` | DATE | NO | Payment due date. |
| 5 | `subtotal` | DECIMAL(12,2) | NO | Order amount before tax in USD. |
| 6 | `tax_amount` | DECIMAL(10,2) | NO | Tax charged in USD. |
| 7 | `total_amount` | DECIMAL(12,2) | NO | Total invoice amount including tax in USD. |
| 8 | `status` | STRING | NO | Invoice status. Values: `draft`, `sent`, `paid`, `overdue`, `cancelled`. |
| 9 | `payment_terms` | STRING | YES | Terms like NET30, NET60, IMMEDIATE. |

## Relationships

**References (this table → other):**
- `order_id` → `main.sales.orders`.`order_id` (N:1) _inferred_naming_
- `customer_id` → `main.sales.customers`.`customer_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- `main.finance.payments`.`invoice_id` → `invoice_id` (N:1)

## Example Joins

```sql
-- Invoice aging summary: amount outstanding by status and customer tier
SELECT
    c.tier,
    i.status,
    COUNT(i.invoice_id)  AS invoice_count,
    SUM(i.total_amount)  AS total_billed,
    SUM(i.total_amount - COALESCE(paid.amount_paid, 0)) AS amount_outstanding
FROM main.finance.invoices i
JOIN main.sales.customers c ON i.customer_id = c.customer_id
LEFT JOIN (
    SELECT invoice_id, SUM(amount) AS amount_paid
    FROM main.finance.payments
    WHERE status = 'cleared'
    GROUP BY invoice_id
) paid ON i.invoice_id = paid.invoice_id
WHERE i.status IN ('sent', 'overdue')
GROUP BY c.tier, i.status
ORDER BY c.tier, i.status;
```

```sql
-- Match invoices to their originating orders
SELECT
    i.invoice_id,
    i.invoice_date,
    i.due_date,
    i.total_amount,
    i.status,
    o.order_date,
    o.shipping_address
FROM main.finance.invoices i
JOIN main.sales.orders o ON i.order_id = o.order_id
WHERE i.invoice_date >= '2025-01-01'
ORDER BY i.invoice_date DESC;
```
