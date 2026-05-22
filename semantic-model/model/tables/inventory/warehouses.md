# warehouses

**Full name:** `main.inventory.warehouses`  
**Type:** MANAGED  
**Schema:** inventory  
**Catalog:** main

> Physical warehouse locations. One row per warehouse facility.

**Approximate row count:** 12

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `warehouse_id` | INT | NO | Primary key. |
| 1 | `warehouse_name` | STRING | NO | Short name of the warehouse. |
| 2 | `address` | STRING | YES | Street address. |
| 3 | `city` | STRING | NO | City where warehouse is located. |
| 4 | `country` | STRING | NO | ISO country code. |
| 5 | `capacity_sqft` | INT | YES | Total floor space in square feet. |
| 6 | `manager_name` | STRING | YES | Name of the warehouse manager. |
| 7 | `is_active` | BOOLEAN | NO | Whether warehouse is currently operational. |

## Relationships

**References (this table → other):**
- _(none)_

**Referenced by (other tables → this):**
- `main.inventory.stock_levels`.`warehouse_id` → `warehouse_id` (N:1)
- `main.inventory.stock_movements`.`warehouse_id` → `warehouse_id` (N:1)
- `main.purchasing.purchase_orders`.`warehouse_id` → `warehouse_id` (N:1)

## Example Joins

```sql
-- Total units on hand across all active warehouses
SELECT
    w.warehouse_id,
    w.warehouse_name,
    w.city,
    w.country,
    COUNT(DISTINCT sl.product_id) AS distinct_products,
    SUM(sl.quantity_on_hand)      AS total_units_on_hand
FROM main.inventory.warehouses w
JOIN main.inventory.stock_levels sl ON w.warehouse_id = sl.warehouse_id
WHERE w.is_active = TRUE
GROUP BY w.warehouse_id, w.warehouse_name, w.city, w.country
ORDER BY total_units_on_hand DESC;
```

```sql
-- Pending purchase orders due for delivery per warehouse
SELECT
    w.warehouse_name,
    COUNT(po.po_id)         AS pending_pos,
    SUM(po.total_amount)    AS pending_value_usd,
    MIN(po.expected_date)   AS earliest_expected
FROM main.inventory.warehouses w
JOIN main.purchasing.purchase_orders po ON w.warehouse_id = po.warehouse_id
WHERE po.status IN ('sent', 'partial')
GROUP BY w.warehouse_name
ORDER BY earliest_expected;
```
