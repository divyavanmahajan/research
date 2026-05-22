# suppliers

**Full name:** `main.purchasing.suppliers`  
**Type:** MANAGED  
**Schema:** purchasing  
**Catalog:** main

> Supplier (vendor) master data. One row per supplier company.

**Approximate row count:** 580

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `supplier_id` | INT | NO | Primary key. |
| 1 | `supplier_name` | STRING | NO | Legal company name of the supplier. |
| 2 | `contact_name` | STRING | YES | Primary contact person. |
| 3 | `email` | STRING | YES | Contact email address. |
| 4 | `phone` | STRING | YES | Contact phone number. |
| 5 | `city` | STRING | YES | City of business. |
| 6 | `country` | STRING | NO | ISO country code. |
| 7 | `payment_terms` | STRING | YES | Standard payment terms e.g. NET30, NET60. |
| 8 | `is_active` | BOOLEAN | NO | Whether supplier is currently used. |
| 9 | `rating` | DECIMAL(3,1) | YES | Internal supplier quality rating 1.0–5.0. |

## Relationships

**References (this table → other):**
- _(none)_

**Referenced by (other tables → this):**
- `main.sales.products`.`supplier_id` → `supplier_id` (N:1)
- `main.purchasing.purchase_orders`.`supplier_id` → `supplier_id` (N:1)

## Example Joins

```sql
-- Supplier performance: POs placed, received, and average rating
SELECT
    s.supplier_id,
    s.supplier_name,
    s.country,
    s.rating,
    COUNT(po.po_id)                                          AS total_pos,
    SUM(CASE WHEN po.status = 'received' THEN 1 ELSE 0 END) AS completed_pos,
    SUM(po.total_amount)                                     AS total_spend_usd
FROM main.purchasing.suppliers s
LEFT JOIN main.purchasing.purchase_orders po ON s.supplier_id = po.supplier_id
WHERE s.is_active = TRUE
GROUP BY s.supplier_id, s.supplier_name, s.country, s.rating
ORDER BY total_spend_usd DESC;
```

```sql
-- Products sourced from each supplier with current stock levels
SELECT
    s.supplier_name,
    p.sku,
    p.product_name,
    SUM(sl.quantity_on_hand) AS total_on_hand
FROM main.purchasing.suppliers s
JOIN main.sales.products p           ON s.supplier_id  = p.supplier_id
JOIN main.inventory.stock_levels sl  ON p.product_id   = sl.product_id
WHERE s.is_active = TRUE
  AND p.is_active = TRUE
GROUP BY s.supplier_name, p.sku, p.product_name
ORDER BY s.supplier_name, total_on_hand ASC;
```
