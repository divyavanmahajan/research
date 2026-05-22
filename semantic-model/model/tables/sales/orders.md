# orders

**Full name:** `main.sales.orders`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Customer purchase orders placed through all sales channels. One row per order. Orders move through a status lifecycle from 'pending' to 'delivered' or 'cancelled'.

**Approximate row count:** 5,243,891

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `order_id` | BIGINT | NO | Primary key. Unique identifier for each order. |
| 1 | `customer_id` | BIGINT | NO | FK → `main.sales.customers`.`customer_id` |
| 2 | `order_date` | DATE | NO | Calendar date when the order was placed. |
| 3 | `shipped_date` | DATE | YES | Date order was dispatched. NULL if not yet shipped. |
| 4 | `delivered_date` | DATE | YES | Date order was marked delivered. NULL if not yet delivered. |
| 5 | `status` | STRING | NO | Current order state. Values: `pending`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`. |
| 6 | `channel` | STRING | YES | Sales channel. Values: `web`, `mobile`, `phone`, `store`. |
| 7 | `total_amount` | DECIMAL(12,2) | NO | Gross order value in USD before discounts. |
| 8 | `net_amount` | DECIMAL(12,2) | YES | Post-discount order value in USD. NULL if no discount applied. |

## Relationships

**References (this table → other):**

- `customer_id` → `main.sales.customers`.`customer_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**

- `main.sales.order_items`.`order_id` → `order_id` (N:1)
- `main.finance.invoices`.`order_id` → `order_id` (N:1)

## Example Joins

```sql
-- Orders with customer info
SELECT o.order_id, o.order_date, o.status, c.customer_name, c.email
FROM main.sales.orders o
JOIN main.sales.customers c ON o.customer_id = c.customer_id
```

```sql
-- Orders with line items and products
SELECT o.order_id, o.order_date, p.product_name, oi.quantity, oi.unit_price
FROM main.sales.orders o
JOIN main.sales.order_items oi ON o.order_id = oi.order_id
JOIN main.sales.products p ON oi.product_id = p.product_id
```

```sql
-- Revenue by month (completed orders only)
SELECT
  DATE_TRUNC('month', order_date) AS month,
  SUM(net_amount) AS revenue,
  COUNT(*) AS order_count
FROM main.sales.orders
WHERE status = 'delivered'
GROUP BY 1
ORDER BY 1
```
