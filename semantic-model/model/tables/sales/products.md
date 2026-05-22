# products

**Full name:** `main.sales.products`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Product catalog. One row per SKU.

**Approximate row count:** 8,500

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `product_id` | BIGINT | NO | Primary key. |
| 1 | `category_id` | INT | NO | FK → `main.sales.product_categories`.`category_id` |
| 2 | `supplier_id` | INT | YES | FK → `main.purchasing.suppliers`.`supplier_id`. Primary supplier. |
| 3 | `product_name` | STRING | NO | Display name of the product. |
| 4 | `sku` | STRING | NO | Stock-keeping unit code. Unique per product. |
| 5 | `description` | STRING | YES | Product description. |
| 6 | `unit_price` | DECIMAL(10,2) | NO | Current retail price in USD. |
| 7 | `cost_price` | DECIMAL(10,2) | YES | Wholesale cost in USD. |
| 8 | `weight_kg` | DECIMAL(6,3) | YES | Weight in kilograms, used for shipping. |
| 9 | `is_active` | BOOLEAN | NO | Whether product is currently sold. |
| 10 | `created_date` | DATE | NO | Date product was added to catalog. |

## Relationships

**References (this table → other):**
- `category_id` → `main.sales.product_categories`.`category_id` (N:1) _inferred_naming_
- `supplier_id` → `main.purchasing.suppliers`.`supplier_id` (N:1) _inferred_naming_

**Referenced by (other tables → this):**
- `main.sales.order_items`.`product_id` → `product_id` (N:1)
- `main.inventory.stock_levels`.`product_id` → `product_id` (N:1)
- `main.inventory.stock_movements`.`product_id` → `product_id` (N:1)
- `main.purchasing.purchase_order_items`.`product_id` → `product_id` (N:1)

## Example Joins

```sql
-- Product catalog with category name and supplier details
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    pc.category_name,
    s.supplier_name,
    p.unit_price,
    p.cost_price,
    ROUND((p.unit_price - p.cost_price) / p.unit_price * 100, 2) AS margin_pct
FROM main.sales.products p
JOIN main.sales.product_categories pc  ON p.category_id  = pc.category_id
LEFT JOIN main.purchasing.suppliers s  ON p.supplier_id   = s.supplier_id
WHERE p.is_active = TRUE;
```

```sql
-- Products with current stock levels across all warehouses
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    w.warehouse_name,
    sl.quantity_on_hand,
    sl.quantity_reserved,
    sl.quantity_on_hand - sl.quantity_reserved AS quantity_available
FROM main.sales.products p
JOIN main.inventory.stock_levels sl ON p.product_id  = sl.product_id
JOIN main.inventory.warehouses w    ON sl.warehouse_id = w.warehouse_id
WHERE p.is_active = TRUE
ORDER BY p.product_id, w.warehouse_name;
```
