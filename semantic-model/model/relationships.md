# Table Relationships

_Generated: 2025-05-22_  
_8 relationships across 7 tables_

## Join Map

| From Table | From Column | To Table | To Column | Cardinality | Confidence |
|------------|-------------|----------|-----------|-------------|------------|
| `main.sales.order_items` | `order_id` | `main.sales.orders` | `order_id` | N:1 | inferred_naming |
| `main.sales.order_items` | `product_id` | `main.sales.products` | `product_id` | N:1 | inferred_naming |
| `main.sales.orders` | `customer_id` | `main.sales.customers` | `customer_id` | N:1 | inferred_naming |
| `main.sales.products` | `category_id` | `main.sales.product_categories` | `category_id` | N:1 | inferred_naming |
| `main.finance.invoices` | `order_id` | `main.sales.orders` | `order_id` | N:1 | inferred_naming |
| `main.finance.invoices` | `customer_id` | `main.sales.customers` | `customer_id` | N:1 | inferred_naming |
| `main.finance.payments` | `invoice_id` | `main.finance.invoices` | `invoice_id` | N:1 | inferred_naming |

## Join Paths by Schema

### main.sales

- `order_items.order_id` → `orders.order_id`
- `order_items.product_id` → `products.product_id`
- `orders.customer_id` → `customers.customer_id`
- `products.category_id` → `product_categories.category_id`

### main.sales → main.finance

- `invoices.order_id` → `orders.order_id`
- `invoices.customer_id` → `customers.customer_id`

### main.finance

- `payments.invoice_id` → `invoices.invoice_id`
