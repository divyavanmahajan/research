# customers

**Full name:** `main.sales.customers`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Master record of all registered customers. One row per customer account.

**Approximate row count:** 1,200,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `customer_id` | BIGINT | NO | Primary key. Unique customer identifier. |
| 1 | `customer_name` | STRING | NO | Full name of the customer or business. |
| 2 | `email` | STRING | NO | Primary contact email address. |
| 3 | `phone` | STRING | YES | Contact phone number in E.164 format. |
| 4 | `address_line1` | STRING | YES | Street address line 1. |
| 5 | `city` | STRING | YES | City of residence or business. |
| 6 | `country` | STRING | NO | ISO 3166-1 alpha-2 country code (e.g. US, GB). |
| 7 | `segment` | STRING | YES | Customer segment. Values: `individual`, `small_business`, `enterprise`. |
| 8 | `created_date` | DATE | NO | Date customer account was created. |
| 9 | `is_active` | BOOLEAN | NO | Whether account is currently active. |
| 10 | `lifetime_value` | DECIMAL(14,2) | YES | Total net revenue from customer to date in USD. |
| 11 | `tier` | STRING | YES | Loyalty tier. Values: `bronze`, `silver`, `gold`, `platinum`. |

## Relationships

**References (this table → other):**
- _(none)_

**Referenced by (other tables → this):**
- `main.sales.orders`.`customer_id` → `customer_id` (N:1)
- `main.finance.invoices`.`customer_id` → `customer_id` (N:1)

## Example Joins

```sql
-- Total lifetime revenue per customer segment
SELECT
    c.segment,
    c.tier,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    SUM(o.total_amount)           AS total_revenue
FROM main.sales.customers c
JOIN main.sales.orders o ON c.customer_id = o.customer_id
WHERE c.is_active = TRUE
GROUP BY c.segment, c.tier
ORDER BY total_revenue DESC;
```

```sql
-- Customers with outstanding invoices
SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    COUNT(i.invoice_id) AS open_invoices,
    SUM(i.total_amount) AS amount_outstanding
FROM main.sales.customers c
JOIN main.finance.invoices i
    ON c.customer_id = i.customer_id
WHERE i.status IN ('sent', 'overdue')
GROUP BY c.customer_id, c.customer_name, c.email;
```
