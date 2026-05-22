# promotions

**Full name:** `main.sales.promotions`  
**Type:** MANAGED  
**Schema:** sales  
**Catalog:** main

> Promotional discount campaigns. One row per promotion. Applied at order level.

**Approximate row count:** 340

## Columns

| # | Column | Type | Nullable | Description |
|---|--------|------|----------|-------------|
| 0 | `promotion_id` | INT | NO | Primary key. |
| 1 | `promotion_name` | STRING | NO | Name of the promotion. |
| 2 | `discount_type` | STRING | NO | Values: `percentage`, `fixed_amount`, `free_shipping`. |
| 3 | `discount_value` | DECIMAL(8,2) | NO | Amount of discount: percentage (0–100) or fixed USD amount. |
| 4 | `start_date` | DATE | NO | First date promotion is valid. |
| 5 | `end_date` | DATE | NO | Last date promotion is valid (inclusive). |
| 6 | `min_order_amount` | DECIMAL(10,2) | YES | Minimum order total in USD required to apply. NULL = no minimum. |
| 7 | `promo_code` | STRING | YES | Coupon code to apply the promotion. NULL = auto-applied. |
| 8 | `is_active` | BOOLEAN | NO | Whether the promotion is currently available. |

## Relationships

**References (this table → other):**
- _(none)_

**Referenced by (other tables → this):**
- `main.sales.orders`.`promo_code` → `promo_code` (N:1) _via promo_code lookup_

## Example Joins

```sql
-- Orders with applied promotions and discount details
SELECT
    o.order_id,
    o.order_date,
    o.total_amount,
    pr.promotion_name,
    pr.discount_type,
    pr.discount_value
FROM main.sales.orders o
JOIN main.sales.promotions pr ON o.promo_code = pr.promo_code
WHERE o.order_date BETWEEN pr.start_date AND pr.end_date;
```

```sql
-- Currently active promotions
SELECT
    promotion_id,
    promotion_name,
    discount_type,
    discount_value,
    promo_code,
    end_date,
    DATEDIFF(end_date, CURRENT_DATE()) AS days_remaining
FROM main.sales.promotions
WHERE is_active = TRUE
  AND CURRENT_DATE() BETWEEN start_date AND end_date
ORDER BY end_date;
```
