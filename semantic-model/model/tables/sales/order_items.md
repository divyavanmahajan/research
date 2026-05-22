# order_items

**Full name:** `main.sales.order_items`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Individual line items within an order. One row per product per order.

**Approximate row count:** 18,400,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `item_id` | BIGINT | NO | Primary key. |
| 1 | `order_id` | BIGINT | NO | FK → `main.sales.orders`.`order_id` |
| 2 | `product_id` | BIGINT | NO | FK → `main.sales.products`.`product_id` |
| 3 | `quantity` | INT | NO | Number of units ordered. |
| 4 | `unit_price` | DECIMAL(10,2) | NO | Price per unit at time of order in USD. |
| 5 | `discount_pct` | DECIMAL(5,2) | YES | Discount percentage applied to this line (0–100). NULL = no discount. |
| 6 | `line_total` | DECIMAL(12,2) | NO | Computed: quantity × unit_price × (1 - discount_pct/100). |

## Relationships

**References (this table → other):**
- `order_id` → `main.sales.orders`.`order_id` (N:1) _inferred_naming_
- `product_id` → `main.sales.products`.`product_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- _(none)_

## Example Joins

```sql
-- Revenue breakdown by product and order
SELECT
    oi.order_id,
    p.product_name,
    p.sku,
    oi.quantity,
    oi.unit_price,
    COALESCE(oi.discount_pct, 0) AS discount_pct,
    oi.line_total
FROM main.sales.order_items oi
JOIN main.sales.products p ON oi.product_id = p.product_id
JOIN main.sales.orders o   ON oi.order_id   = o.order_id
WHERE o.order_date >= '2025-01-01';
```

```sql
-- Top 10 products by units sold in the last 90 days
SELECT
    p.product_id,
    p.product_name,
    p.sku,
    SUM(oi.quantity)    AS units_sold,
    SUM(oi.line_total)  AS gross_revenue
FROM main.sales.order_items oi
JOIN main.sales.products p ON oi.product_id = p.product_id
JOIN main.sales.orders o   ON oi.order_id   = o.order_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), 90)
GROUP BY p.product_id, p.product_name, p.sku
ORDER BY units_sold DESC
LIMIT 10;
```
