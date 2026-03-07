# Warehouse Management System — End-User Demo

*2026-03-07T14:29:35Z by Showboat 0.6.1*
<!-- showboat-id: 3992a09b-ca8e-477e-a61d-cf2de2b2c7a6 -->

This document is a live, reproducible demonstration of all key workflows
in the Warehouse Management System. Every screenshot was captured by automating
a real Chrome browser. Run `showboat verify warehouse_demo.md` to confirm
all outputs still match.

## Workflow 1 — Admin Login

The admin logs in with username `admin` and password `admin123`.
The system validates credentials and redirects to the Dashboard.

```bash {image}
/home/user/research/warehouse/demo/shots/01_login_page.png
```

![02b3b642-2026-03-07](02b3b642-2026-03-07.png)

```bash {image}
/home/user/research/warehouse/demo/shots/02_dashboard_admin.png
```

![d7311239-2026-03-07](d7311239-2026-03-07.png)

Dashboard shows summary cards: total aisles, racks, bins, item types, and
overall capacity utilisation.

## Workflow 2 — Warehouse Structure

The Structure page shows all aisles. Clicking an aisle expands it via HTMX
to show its racks, levels, and bins — no page reload required.

```bash {image}
/home/user/research/warehouse/demo/shots/03_structure_collapsed.png
```

![efedad0a-2026-03-07](efedad0a-2026-03-07.png)

Clicking Aisle A1 loads its racks inline.

```bash {image}
/home/user/research/warehouse/demo/shots/04_structure_expanded.png
```

![24a3443a-2026-03-07](24a3443a-2026-03-07.png)

## Workflow 3 — Bins & Capacity

Every bin displays its location code, dimensions, and a colour-coded capacity bar:
green (<70%), amber (70–90%), red (>90%).

```bash {image}
/home/user/research/warehouse/demo/shots/05_bins_capacity.png
```

![9d1f7793-2026-03-07](9d1f7793-2026-03-07.png)

## Workflow 4 — Item Catalogue

The Items page shows all registered SKUs with their dimensions and volume.
Admins can add new items using the form at the top.

```bash {image}
/home/user/research/warehouse/demo/shots/06_items_list.png
```

![f3274852-2026-03-07](f3274852-2026-03-07.png)

Adding a new item: **Allen Key 3mm**.

```bash {image}
/home/user/research/warehouse/demo/shots/07_item_added.png
```

![9483fea6-2026-03-07](9483fea6-2026-03-07.png)

## Workflow 5 — Add Stock to Bin

The Inventory page allows stocking a bin. The system checks the item's volume
against available bin space and rejects overfills.

```bash {image}
/home/user/research/warehouse/demo/shots/08_inventory_page.png
```

![6e778d63-2026-03-07](6e778d63-2026-03-07.png)

Adding 50× Allen Key 3mm to bin A1-R3-L2-B1.

```bash {image}
/home/user/research/warehouse/demo/shots/09_inventory_updated.png
```

![3085b295-2026-03-07](3085b295-2026-03-07.png)

## Workflow 6 — Live Inventory Search

Search updates results as the operator types (300 ms debounce via HTMX).
Results show every bin location and quantity for each matching item.

```bash {image}
/home/user/research/warehouse/demo/shots/10_search_empty.png
```

![311c67fd-2026-03-07](311c67fd-2026-03-07.png)

Searching for **bolt** shows all bolt SKUs and their locations.

```bash {image}
/home/user/research/warehouse/demo/shots/11_search_bolt.png
```

![f95bcf6f-2026-03-07](f95bcf6f-2026-03-07.png)

Searching for **usb** shows cable locations across two aisles.

```bash {image}
/home/user/research/warehouse/demo/shots/12_search_usb.png
```

![7c67d35a-2026-03-07](7c67d35a-2026-03-07.png)

## Workflow 7 — Build a Pick Basket

The operator creates a new pick session and adds items to the basket.
HTMX updates the basket panel without reloading the page.

```bash {image}
/home/user/research/warehouse/demo/shots/13_pick_basket_empty.png
```

![a9cf695c-2026-03-07](a9cf695c-2026-03-07.png)

Adding Bolt M6 25mm (qty 10) to basket.

```bash {image}
/home/user/research/warehouse/demo/shots/14_basket_item1.png
```

![4342fc44-2026-03-07](4342fc44-2026-03-07.png)

Adding USB Cable 2m to basket.

```bash {image}
/home/user/research/warehouse/demo/shots/15_basket_item2.png
```

![21efb7a0-2026-03-07](21efb7a0-2026-03-07.png)

Adding Ethernet Cat6 5m to basket.

```bash {image}
/home/user/research/warehouse/demo/shots/16_basket_three_items.png
```

![a8ecf124-2026-03-07](a8ecf124-2026-03-07.png)

## Workflow 8 — Generate Optimised S-Shape Route

Clicking **Generate Route** sends the basket to the server. The system assigns
items to bins using nearest-aisle greedy selection, then sorts stops by
S-shape traversal (odd aisles ascending, even aisles descending).

```bash {image}
/home/user/research/warehouse/demo/shots/17_pick_route_generated.png
```

![c22268db-2026-03-07](c22268db-2026-03-07.png)

The pick session shows stops ordered for minimum walking distance.

## Workflow 9 — Interactive Pick Checklist

The operator works through the ordered list and checks off each stop.
HTMX updates the progress bar and marks the row green — no page reload.

Checking off stop 1 (first bin in route).

```bash {image}
/home/user/research/warehouse/demo/shots/18_pick_stop1_done.png
```

![433b6603-2026-03-07](433b6603-2026-03-07.png)

Checking off stop 2.

```bash {image}
/home/user/research/warehouse/demo/shots/19_pick_stop2_done.png
```

![c40e4cdd-2026-03-07](c40e4cdd-2026-03-07.png)

Checking off final stop — session auto-completes.

```bash {image}
/home/user/research/warehouse/demo/shots/20_pick_completed.png
```

![8a721758-2026-03-07](8a721758-2026-03-07.png)

## Workflow 10 — Dashboard After Picking

Returning to the dashboard shows updated capacity statistics and the
completed session in Recent Pick Sessions.

```bash {image}
/home/user/research/warehouse/demo/shots/21_dashboard_post_pick.png
```

![6ea9721b-2026-03-07](6ea9721b-2026-03-07.png)

## Workflow 11 — Pick History

All sessions are recorded with status, operator, and progress.

```bash {image}
/home/user/research/warehouse/demo/shots/22_pick_history.png
```

![77bb2358-2026-03-07](77bb2358-2026-03-07.png)

## Workflow 12 — User Management (Admin Only)

Administrators can create, view, and delete users with operator or admin roles.

```bash {image}
/home/user/research/warehouse/demo/shots/23_users_list.png
```

![109fe28e-2026-03-07](109fe28e-2026-03-07.png)

Creating a new operator: **operator2**.

```bash {image}
/home/user/research/warehouse/demo/shots/24_user_created.png
```

![250a0277-2026-03-07](250a0277-2026-03-07.png)

## Summary

All 12 key user workflows demonstrated:

| # | Workflow | Status |
|---|---|---|
| 1 | Admin login | ✓ |
| 2 | Warehouse structure (HTMX expand) | ✓ |
| 3 | Bins with capacity bars | ✓ |
| 4 | Item catalogue + add item | ✓ |
| 5 | Add stock to bin (volume check) | ✓ |
| 6 | Live inventory search | ✓ |
| 7 | Build pick basket (HTMX) | ✓ |
| 8 | S-shape route generation | ✓ |
| 9 | Interactive pick checklist | ✓ |
| 10 | Dashboard post-pick stats | ✓ |
| 11 | Pick history | ✓ |
| 12 | Admin user management | ✓ |
