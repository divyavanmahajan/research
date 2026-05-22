# product_categories

**Full name:** `main.sales.product_categories`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Product category hierarchy. One row per category. Supports self-referencing parent-child hierarchy.

**Approximate row count:** 120

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `category_id` | INT | NO | Primary key. |
| 1 | `category_name` | STRING | NO | Display name of the category. |
| 2 | `parent_category_id` | INT | YES | FK → `main.sales.product_categories`.`category_id`. NULL for top-level categories. |
| 3 | `description` | STRING | YES | Description of what products belong in this category. |

## Relationships

**References (this table → other):**
- `parent_category_id` → `main.sales.product_categories`.`category_id` (N:1) _self_reference_

**Referenced by (other tables → this):**
- `main.sales.products`.`category_id` → `category_id` (N:1)

## Example Joins

```sql
-- Full two-level category hierarchy (parent → child)
SELECT
    parent.category_id   AS parent_id,
    parent.category_name AS parent_category,
    child.category_id    AS child_id,
    child.category_name  AS child_category,
    child.description
FROM main.sales.product_categories child
LEFT JOIN main.sales.product_categories parent
    ON child.parent_category_id = parent.category_id
ORDER BY parent.category_name NULLS FIRST, child.category_name;
```

```sql
-- Product count per top-level category
SELECT
    COALESCE(parent.category_name, child.category_name) AS top_level_category,
    COUNT(DISTINCT p.product_id) AS product_count
FROM main.sales.products p
JOIN main.sales.product_categories child  ON p.category_id          = child.category_id
LEFT JOIN main.sales.product_categories parent ON child.parent_category_id = parent.category_id
WHERE p.is_active = TRUE
GROUP BY COALESCE(parent.category_name, child.category_name)
ORDER BY product_count DESC;
```
