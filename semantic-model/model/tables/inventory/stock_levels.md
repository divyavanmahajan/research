# stock_levels

**Full name:** `main.inventory.stock_levels`  
**Type:** MANAGED  
**Schema:** inventory  
**Catalog:** main

> Current stock levels per product per warehouse. One row per product-warehouse combination. Updated on each stock movement.

**Approximate row count:** 92,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `stock_id` | BIGINT | NO | Primary key. |
| 1 | `product_id` | BIGINT | NO | FK → `main.sales.products`.`product_id` |
| 2 | `warehouse_id` | INT | NO | FK → `main.inventory.warehouses`.`warehouse_id` |
| 3 | `quantity_on_hand` | INT | NO | Units currently in stock. |
| 4 | `quantity_reserved` | INT | NO | Units reserved for pending orders. quantity_on_hand - quantity_reserved = available. |
| 5 | `reorder_point` | INT | YES | Threshold below which a purchase order should be created. |
| 6 | `last_updated` | TIMESTAMP | NO | Timestamp of last stock update. |

## Relationships

**References (this table → other):**
- `product_id` → `main.sales.products`.`product_id` (N:1) _inferred_naming_
- `warehouse_id` → `main.inventory.warehouses`.`warehouse_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- _(none — snapshot table)_

## Example Joins

```sql
-- Products that have fallen below their reorder point
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    w.warehouse_name,
    sl.quantity_on_hand,
    sl.quantity_reserved,
    sl.quantity_on_hand - sl.quantity_reserved AS quantity_available,
    sl.reorder_point
FROM main.inventory.stock_levels sl
JOIN main.sales.products p          ON sl.product_id   = p.product_id
JOIN main.inventory.warehouses w    ON sl.warehouse_id  = w.warehouse_id
WHERE sl.reorder_point IS NOT NULL
  AND sl.quantity_on_hand <= sl.reorder_point
  AND p.is_active = TRUE
  AND w.is_active = TRUE
ORDER BY sl.quantity_on_hand ASC;
```

```sql
-- Inventory value by warehouse
SELECT
    w.warehouse_name,
    SUM(sl.quantity_on_hand * p.cost_price)  AS inventory_cost_value,
    SUM(sl.quantity_on_hand * p.unit_price)  AS inventory_retail_value
FROM main.inventory.stock_levels sl
JOIN main.sales.products p       ON sl.product_id  = p.product_id
JOIN main.inventory.warehouses w ON sl.warehouse_id = w.warehouse_id
WHERE p.cost_price IS NOT NULL
GROUP BY w.warehouse_name
ORDER BY inventory_cost_value DESC;
```
