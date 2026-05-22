# purchase_order_items

**Full name:** `main.purchasing.purchase_order_items`  
**Type:** MANAGED  
**Schema:** purchasing  
**Catalog:** main

> Line items within a purchase order. One row per product per PO.

**Approximate row count:** 190,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `item_id` | BIGINT | NO | Primary key. |
| 1 | `po_id` | BIGINT | NO | FK → `main.purchasing.purchase_orders`.`po_id` |
| 2 | `product_id` | BIGINT | NO | FK → `main.sales.products`.`product_id` |
| 3 | `quantity_ordered` | INT | NO | Units ordered from supplier. |
| 4 | `quantity_received` | INT | NO | Units actually received so far. Zero until delivery. |
| 5 | `unit_cost` | DECIMAL(10,2) | NO | Agreed cost per unit in USD. |
| 6 | `line_total` | DECIMAL(12,2) | NO | Computed: quantity_ordered × unit_cost. |

## Relationships

**References (this table → other):**
- `po_id` → `main.purchasing.purchase_orders`.`po_id` (N:1) _inferred_naming_
- `product_id` → `main.sales.products`.`product_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- _(none)_

## Example Joins

```sql
-- Partially received PO lines: quantity gap between ordered and received
SELECT
    poi.item_id,
    po.po_id,
    po.order_date,
    po.expected_date,
    s.supplier_name,
    p.sku,
    p.product_name,
    poi.quantity_ordered,
    poi.quantity_received,
    poi.quantity_ordered - poi.quantity_received AS quantity_outstanding,
    poi.unit_cost,
    (poi.quantity_ordered - poi.quantity_received) * poi.unit_cost AS outstanding_value_usd
FROM main.purchasing.purchase_order_items poi
JOIN main.purchasing.purchase_orders po ON poi.po_id       = po.po_id
JOIN main.purchasing.suppliers s        ON po.supplier_id  = s.supplier_id
JOIN main.sales.products p              ON poi.product_id  = p.product_id
WHERE po.status IN ('sent', 'partial')
  AND poi.quantity_received < poi.quantity_ordered
ORDER BY outstanding_value_usd DESC;
```

```sql
-- Average unit cost per product across all received POs (for margin analysis)
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    p.unit_price                                          AS current_retail_price,
    ROUND(AVG(poi.unit_cost), 2)                          AS avg_cost_price,
    ROUND((p.unit_price - AVG(poi.unit_cost))
          / p.unit_price * 100, 2)                        AS avg_margin_pct
FROM main.purchasing.purchase_order_items poi
JOIN main.purchasing.purchase_orders po ON poi.po_id      = po.po_id
JOIN main.sales.products p              ON poi.product_id = p.product_id
WHERE po.status = 'received'
GROUP BY p.product_id, p.sku, p.product_name, p.unit_price
ORDER BY avg_margin_pct ASC;
```
