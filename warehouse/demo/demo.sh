#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WMS End-User Demo
# Uses: showboat (demo document builder) + rodney (Chrome automation)
#
# Run from the warehouse/ directory:
#   bash demo/demo.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
DEMO_DOC="$SCRIPT_DIR/warehouse_demo.md"
SHOTS_DIR="$SCRIPT_DIR/shots"
APP_URL="http://localhost:8000"

# Helpers
SB="uvx showboat"
RD="uvx rodney --local"

log() { echo "▶ $*"; }
shot() {
  local name="$1"
  local path="$SHOTS_DIR/${name}.png"
  $RD screenshot "$path"
  $SB image "$DEMO_DOC" "$path"
}
note() { $SB note "$DEMO_DOC" "$1"; }
exec_step() { $SB exec "$DEMO_DOC" bash "$1"; }

# ─────────────────────────────────────────────────────────────────────────────
# 0. Setup
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$SHOTS_DIR"
cd "$APP_DIR"

log "Preparing database…"
rm -f warehouse.db
python demo/seed.py

log "Starting WMS server…"
uvicorn main:app --host 127.0.0.1 --port 8000 &
APP_PID=$!
trap "kill $APP_PID 2>/dev/null; $RD stop 2>/dev/null || true" EXIT
sleep 2   # wait for server

log "Initialising showboat document…"
rm -f "$DEMO_DOC"
$SB init "$DEMO_DOC" "Warehouse Management System — End-User Demo"

note "This document is a live, reproducible demonstration of all key workflows
in the Warehouse Management System. Every screenshot was captured by automating
a real Chrome browser. Run \`showboat verify warehouse_demo.md\` to confirm
all outputs still match."

log "Starting Chrome (headless)…"
$RD start --local

# ─────────────────────────────────────────────────────────────────────────────
# 1. Login as Admin
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 1: Admin login"
note "## Workflow 1 — Admin Login

The admin logs in with username \`admin\` and password \`admin123\`.
The system validates credentials and redirects to the Dashboard."

$RD open "$APP_URL/login"
$RD waitload
$RD clear "#username"
$RD input "#username" "admin"
$RD input "#password" "admin123"
shot "01_login_page"
$RD click "[type=submit]"
$RD waitload
shot "02_dashboard_admin"

note "Dashboard shows summary cards: total aisles, racks, bins, item types, and
overall capacity utilisation."

# ─────────────────────────────────────────────────────────────────────────────
# 2. View Warehouse Structure
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 2: Warehouse structure"
note "## Workflow 2 — Warehouse Structure

The Structure page shows all aisles. Clicking an aisle expands it via HTMX
to show its racks, levels, and bins — no page reload required."

$RD open "$APP_URL/structure"
$RD waitload
shot "03_structure_collapsed"

note "Clicking Aisle A1 loads its racks inline."
$RD click "button[hx-get*='/aisles/1/racks']"
$RD waitstable
shot "04_structure_expanded"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Browse Bins with Capacity Bars
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 3: Bins capacity view"
note "## Workflow 3 — Bins & Capacity

Every bin displays its location code, dimensions, and a colour-coded capacity bar:
green (<70%), amber (70–90%), red (>90%)."

$RD open "$APP_URL/bins"
$RD waitload
shot "05_bins_capacity"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Item Catalogue
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 4: Item catalogue"
note "## Workflow 4 — Item Catalogue

The Items page shows all registered SKUs with their dimensions and volume.
Admins can add new items using the form at the top."

$RD open "$APP_URL/items"
$RD waitload
shot "06_items_list"

note "Adding a new item: **Allen Key 3mm**."
$RD clear "input[name=sku]"
$RD input "input[name=sku]" "KEY-HEX-3MM"
$RD input "input[name=name]" "Allen Key 3mm"
$RD input "input[name=description]" "Hex key, chrome vanadium"
$RD input "input[name=width_cm]" "1.5"
$RD input "input[name=height_cm]" "8.0"
$RD input "input[name=depth_cm]" "1.5"
$RD click "button[type=submit]"
$RD waitload
shot "07_item_added"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Add Inventory to a Bin
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 5: Add inventory"
note "## Workflow 5 — Add Stock to Bin

The Inventory page allows stocking a bin. The system checks the item's volume
against available bin space and rejects overfills."

$RD open "$APP_URL/inventory"
$RD waitload
shot "08_inventory_page"

note "Adding 50× Allen Key 3mm to bin A1-R3-L2-B1."
$RD js "document.querySelector('select[name=bin_id]').value='12'"
$RD js "(s=>Array.from(s.options).filter(o=>o.text.includes('KEY-HEX-3MM')).forEach(o=>o.selected=true))(document.querySelector('select[name=item_id]'))"
$RD js "document.querySelector('input[name=quantity]').value='50'"
$RD click "form[action='/inventory/add'] button[type=submit]"
$RD waitload
shot "09_inventory_updated"

# ─────────────────────────────────────────────────────────────────────────────
# 6. Live Search
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 6: Live search"
note "## Workflow 6 — Live Inventory Search

Search updates results as the operator types (300 ms debounce via HTMX).
Results show every bin location and quantity for each matching item."

$RD open "$APP_URL/search"
$RD waitload
shot "10_search_empty"

note "Searching for **bolt** shows all bolt SKUs and their locations."
$RD input "#search-input" "bolt"
$RD sleep 1
$RD waitstable
shot "11_search_bolt"

note "Searching for **usb** shows cable locations across two aisles."
$RD clear "#search-input"
$RD input "#search-input" "usb"
$RD sleep 1
$RD waitstable
shot "12_search_usb"

# ─────────────────────────────────────────────────────────────────────────────
# 7. Build a Pick Basket
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 7: Build pick basket"
note "## Workflow 7 — Build a Pick Basket

The operator creates a new pick session and adds items to the basket.
HTMX updates the basket panel without reloading the page."

$RD open "$APP_URL/pick/new"
$RD waitstable
shot "13_pick_basket_empty"

note "Adding Bolt M6 25mm (qty 10) to basket."
$RD js "Array.from(document.querySelectorAll('table tbody tr')).filter(r=>r.textContent.includes('BOLT-M6-25'))[0].querySelector('button').click()"
$RD waitstable
shot "14_basket_item1"

note "Adding USB Cable 2m to basket."
$RD js "Array.from(document.querySelectorAll('table tbody tr')).filter(r=>r.textContent.includes('CAB-USB-2M'))[0].querySelector('button').click()"
$RD waitstable
shot "15_basket_item2"

note "Adding Ethernet Cat6 5m to basket."
$RD js "Array.from(document.querySelectorAll('table tbody tr')).filter(r=>r.textContent.includes('CAB-ETH-5M'))[0].querySelector('button').click()"
$RD waitstable
shot "16_basket_three_items"

# ─────────────────────────────────────────────────────────────────────────────
# 8. Generate S-Shape Route
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 8: Generate pick route"
note "## Workflow 8 — Generate Optimised S-Shape Route

Clicking **Generate Route** sends the basket to the server. The system assigns
items to bins using nearest-aisle greedy selection, then sorts stops by
S-shape traversal (odd aisles ascending, even aisles descending)."

$RD js "document.querySelector('form[action*=\"/generate\"]').submit()"
$RD waitload
shot "17_pick_route_generated"

note "The pick session shows stops ordered for minimum walking distance."

# ─────────────────────────────────────────────────────────────────────────────
# 9. Execute Pick Session
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 9: Execute pick"
note "## Workflow 9 — Interactive Pick Checklist

The operator works through the ordered list and checks off each stop.
HTMX updates the progress bar and marks the row green — no page reload."

note "Checking off stop 1 (first bin in route)."
$RD js "document.querySelector('button[hx-post*=\"/check\"]').click()"
$RD waitstable
shot "18_pick_stop1_done"

note "Checking off stop 2."
$RD js "document.querySelector('button[hx-post*=\"/check\"]').click()"
$RD waitstable
shot "19_pick_stop2_done"

note "Checking off final stop — session auto-completes."
$RD js "document.querySelector('button[hx-post*=\"/check\"]').click()"
$RD waitstable
shot "20_pick_completed"

# ─────────────────────────────────────────────────────────────────────────────
# 10. Dashboard after Pick
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 10: Dashboard post-pick"
note "## Workflow 10 — Dashboard After Picking

Returning to the dashboard shows updated capacity statistics and the
completed session in Recent Pick Sessions."

$RD open "$APP_URL/dashboard"
$RD waitload
shot "21_dashboard_post_pick"

# ─────────────────────────────────────────────────────────────────────────────
# 11. Pick History
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 11: Pick history"
note "## Workflow 11 — Pick History

All sessions are recorded with status, operator, and progress."

$RD open "$APP_URL/pick/history"
$RD waitload
shot "22_pick_history"

# ─────────────────────────────────────────────────────────────────────────────
# 12. User Management (Admin)
# ─────────────────────────────────────────────────────────────────────────────
log "Workflow 12: User management"
note "## Workflow 12 — User Management (Admin Only)

Administrators can create, view, and delete users with operator or admin roles."

$RD open "$APP_URL/users"
$RD waitload
shot "23_users_list"

note "Creating a new operator: **operator2**."
$RD input "input[name=username]" "operator2"
$RD input "input[name=password]" "op456"
$RD click "button[type=submit]"
$RD waitload
shot "24_user_created"

# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────
note "## Summary

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
| 12 | Admin user management | ✓ |"

log "Demo document written to: $DEMO_DOC"
log "Verifying reproducibility…"
$SB verify "$DEMO_DOC" && echo "✓ All outputs verified." || echo "⚠ Some outputs changed — see diff above."

log "Done. Open $DEMO_DOC to view the full demo."
