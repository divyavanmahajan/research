# stock_movements

**Full name:** `main.inventory.stock_movements`  
**Type:** MANAGED  
**Schema:** inventory  
**Catalog:** main

> Audit log of every stock change event. One row per movement. Use this table for stock history; use stock_levels for current state.

**Approximate row count:** 24,000,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `movement_id` | BIGINT | NO | Primary key. |
| 1 | `product_id` | BIGINT | NO | FK → `main.sales.products`.`product_id` |
| 2 | `warehouse_id` | INT | NO | FK → `main.inventory.warehouses`.`warehouse_id` |
| 3 | `movement_type` | STRING | NO | Values: `receipt`, `shipment`, `adjustment`, `transfer_in`, `transfer_out`, `return`. |
| 4 | `quantity` | INT | NO | Units moved. Positive for inbound (receipt, return, transfer_in); negative for outbound. |
| 5 | `reference_id` | BIGINT | YES | ID of the source document (order_id, po_id, etc.). |
| 6 | `reference_type` | STRING | YES | Type of source document. Values: `order`, `purchase_order`, `manual_adjustment`, `transfer`. |
| 7 | `movement_date` | DATE | NO | Date movement occurred. |
| 8 | `notes` | STRING | YES | Optional notes about the movement. |

## Relationships

**References (this table → other):**
- `product_id` → `main.sales.products`.`product_id` (N:1) _inferred_naming_
- `warehouse_id` → `main.inventory.warehouses`.`warehouse_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- _(none — append-only event log)_

## Example Joins

```sql
-- Net stock change per product per warehouse over the last 30 days
SELECT
    p.sku,
    p.product_name,
    w.warehouse_name,
    SUM(sm.quantity)                                     AS net_units_change,
    SUM(CASE WHEN sm.quantity > 0 THEN sm.quantity ELSE 0 END)  AS units_in,
    SUM(CASE WHEN sm.quantity < 0 THEN sm.quantity ELSE 0 END)  AS units_out
FROM main.inventory.stock_movements sm
JOIN main.sales.products p       ON sm.product_id  = p.product_id
JOIN main.inventory.warehouses w ON sm.warehouse_id = w.warehouse_id
WHERE sm.movement_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY p.sku, p.product_name, w.warehouse_name
ORDER BY net_units_change ASC;
```

```sql
-- Shipment movements linked back to originating orders
SELECT
    sm.movement_id,
    sm.movement_date,
    sm.quantity,
    p.product_name,
    w.warehouse_name,
    o.order_id,
    o.order_date,
    c.customer_name
FROM main.inventory.stock_movements sm
JOIN main.sales.products p       ON sm.product_id   = p.product_id
JOIN main.inventory.warehouses w ON sm.warehouse_id  = w.warehouse_id
JOIN main.sales.orders o         ON sm.reference_id  = o.order_id
JOIN main.sales.customers c      ON o.customer_id    = c.customer_id
WHERE sm.movement_type  = 'shipment'
  AND sm.reference_type = 'order'
  AND sm.movement_date >= '2025-01-01';
```
