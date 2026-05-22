# Business Glossary

Map business terms to their physical table/column equivalents.
This file is maintained manually. Add entries as your team uses this model.

## Format

```
## <Business Term>

**Definition:** One sentence definition.
**Tables:** `catalog.schema.table` (column: `col_name`)
**Notes:** Any caveats, alternate terms, or related metrics.
```

---

## Revenue

**Definition:** Total invoiced amount collected from customers, in USD.
**Tables:** `main.sales.orders` (column: `net_amount`)
**Notes:** Use `net_amount` for post-discount revenue; use `total_amount` for gross. Exclude `status IN ('cancelled', 'refunded')`.

---

## GMV (Gross Merchandise Value)

**Definition:** Total value of all orders placed, regardless of returns or cancellations.
**Tables:** `main.sales.orders` (column: `total_amount`, all statuses)
**Notes:** Different from Revenue — GMV includes cancelled orders.

---

<!-- Add your business terms below this line -->
