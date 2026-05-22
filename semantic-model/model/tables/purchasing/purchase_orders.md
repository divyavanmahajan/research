# purchase_orders

**Full name:** `main.purchasing.purchase_orders`  
**Type:** MANAGED  
**Schema:** purchasing  
**Catalog:** main

> Purchase orders sent to suppliers to restock inventory. One row per PO.

**Approximate row count:** 48,000

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `po_id` | BIGINT | NO | Primary key. |
| 1 | `supplier_id` | INT | NO | FK → `main.purchasing.suppliers`.`supplier_id` |
| 2 | `warehouse_id` | INT | NO | FK → `main.inventory.warehouses`.`warehouse_id`. Destination warehouse. |
| 3 | `order_date` | DATE | NO | Date the PO was placed. |
| 4 | `expected_date` | DATE | YES | Expected delivery date. |
| 5 | `received_date` | DATE | YES | Actual date PO was fully received. NULL if not yet received. |
| 6 | `status` | STRING | NO | Values: `draft`, `sent`, `partial`, `received`, `cancelled`. |
| 7 | `total_amount` | DECIMAL(14,2) | NO | Total cost of the PO in USD. |
| 8 | `notes` | STRING | YES | Internal notes about the PO. |

## Relationships

**References (this table → other):**
- `supplier_id` → `main.purchasing.suppliers`.`supplier_id` (N:1) _inferred_naming_
- `warehouse_id` → `main.inventory.warehouses`.`warehouse_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- `main.purchasing.purchase_order_items`.`po_id` → `po_id` (N:1)

## Example Joins

```sql
-- Open POs with supplier and destination warehouse details
SELECT
    po.po_id,
    po.order_date,
    po.expected_date,
    po.status,
    po.total_amount,
    s.supplier_name,
    s.country        AS supplier_country,
    w.warehouse_name AS destination_warehouse,
    DATEDIFF(CURRENT_DATE(), po.expected_date) AS days_overdue
FROM main.purchasing.purchase_orders po
JOIN main.purchasing.suppliers s       ON po.supplier_id  = s.supplier_id
JOIN main.inventory.warehouses w       ON po.warehouse_id = w.warehouse_id
WHERE po.status IN ('sent', 'partial')
ORDER BY po.expected_date ASC;
```

```sql
-- PO line items with product details for a given PO
SELECT
    po.po_id,
    po.order_date,
    s.supplier_name,
    poi.item_id,
    p.sku,
    p.product_name,
    poi.quantity_ordered,
    poi.quantity_received,
    poi.unit_cost,
    poi.line_total
FROM main.purchasing.purchase_orders po
JOIN main.purchasing.suppliers s              ON po.supplier_id  = s.supplier_id
JOIN main.purchasing.purchase_order_items poi ON po.po_id        = poi.po_id
JOIN main.sales.products p                    ON poi.product_id  = p.product_id
WHERE po.status != 'cancelled'
ORDER BY po.po_id, poi.item_id;
```
