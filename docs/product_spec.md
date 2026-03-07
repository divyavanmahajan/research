# Warehouse Management System — Product Specification

**Version:** 1.0
**Date:** 2026-03-07
**Status:** In Development

---

## 1. Overview

A web-based Warehouse Management System (WMS) that allows warehouse operators and administrators to manage physical storage structures, track inventory at the bin level, and generate optimised picking routes for order fulfilment.

---

## 2. Goals

- Provide a clear, real-time view of warehouse inventory and capacity
- Enforce a physical structure model: Aisles → Racks → Levels (max 3) → Bins
- Track items at the bin level with volume-based capacity constraints
- Generate S-shape traversal pick routes to minimise walking distance
- Support multiple users with role-based access (Admin / Operator)

---

## 3. Users

| Role | Capabilities |
|---|---|
| **Admin** | All operator capabilities plus: manage users, manage warehouse structure (aisles, racks, levels, bins), manage item catalogue |
| **Operator** | Stock/unstock bins, search inventory, create and execute pick sessions |

---

## 4. Warehouse Structure

```
Warehouse
└── Aisle (A1, A2, ...)
    └── Rack (R1, R2, ...)
        └── Level (L1, L2, L3  — max 3 per rack)
            └── Bin (B1, B2, ...)
```

Every bin is uniquely identified by its **location code**: `A{n}-R{n}-L{n}-B{n}`
Example: `A1-R2-L3-B4`

### Bin Capacity

Bins are **volume-based**. Each bin has:
- Width (cm), Height (cm), Depth (cm)
- Total volume = W × H × D (cm³)
- Items placed in a bin consume `item_volume × quantity` from available capacity
- The system prevents overfilling beyond total bin volume

### Size Categories (informational labels)

| Label | Typical Dimensions |
|---|---|
| S | ≤ 20×20×20 cm |
| M | ≤ 40×40×40 cm |
| L | ≤ 80×60×60 cm |
| XL | > 80×60×60 cm |

---

## 5. Key Features

### 5.1 Warehouse Structure Management (Admin)
- Create, rename, and delete aisles, racks, levels, and bins
- Configure bin dimensions on creation
- View the full warehouse tree (collapsible, HTMX-driven)

### 5.2 Item Catalogue (Admin)
- Create items with: SKU, name, description, dimensions (W×H×D cm)
- Edit and delete items

### 5.3 Inventory Management (Operator)
- Add items to bins (quantity-aware, volume-checked)
- Remove items from bins
- View current contents of any bin

### 5.4 Search
- Live search by item name or SKU (300 ms debounce)
- Results show all bin locations holding the item, with quantity
- Search by location code to view bin contents

### 5.5 Pick Session Workflow
1. Operator navigates to **New Pick** and searches for items
2. Items are added to a **pick basket** (server-side draft session)
3. Operator clicks **Generate Route** — the system assigns items to bins and sorts stops using the S-shape algorithm
4. An **interactive checklist** is presented, ordered by route
5. Operator checks off each stop; a progress bar updates live via HTMX
6. On completion, bin inventory is decremented automatically

### 5.6 Dashboard
- Summary cards: Total Aisles, Racks, Bins, Items, Overall Capacity %
- Recent pick sessions with status

### 5.7 User Management (Admin)
- Create, view, and delete users
- Assign roles: admin or operator

---

## 6. Picking Algorithm — S-Shape Traversal

Odd-numbered aisles are traversed **forward** (low rack/bin to high), even-numbered aisles **backward**. Within each aisle, levels are visited bottom-up (L1 → L2 → L3).

```
A1 (odd):  R1-L1-B1 → R1-L2-B1 → R2-L1-B1 → ...  (ascending)
A2 (even): R3-L3-B4 → R3-L2-B4 → R2-L3-B4 → ...  (descending)
A3 (odd):  R1-L1-B1 → ...                          (ascending)
```

When an item exists in multiple bins, the system selects the bin that best fits the current route.

---

## 7. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Response time | < 500 ms for all page loads |
| Authentication | JWT stored in HTTP-only cookies, 8-hour expiry |
| Storage | SQLite (file-based, single-server) |
| Concurrency | Single-user write safety via SQLAlchemy sessions |
| Browser support | Modern browsers (Chrome, Firefox, Safari) |

---

## 8. Out of Scope (v1.0)

- Barcode / RFID scanning
- Multi-warehouse support
- Receiving / purchase orders
- Stock level alerts / reorder points
- Mobile app

---

## 9. Demo

A reproducible end-to-end demo is provided in `warehouse/demo/`:
- `seed.py` — populates the database with realistic sample data
- `demo.sh` — drives the browser via `rodney` and documents workflows using `showboat`
- `warehouse_demo.md` — the generated, verifiable demo document
