#!/usr/bin/env python3
"""
Seed the WMS database with realistic demo data.

Run from the warehouse/ directory:
    python demo/seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import engine, SessionLocal, Base
import models
from auth import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # ── Guard: don't re-seed ────────────────────────────────────────────────
    if db.query(models.User).count() > 0:
        print("Database already seeded. Delete warehouse.db to start fresh.")
        db.close()
        return

    print("Seeding database…")

    # ── Users ────────────────────────────────────────────────────────────────
    admin = models.User(username="admin",     password_hash=hash_password("admin123"), role="admin")
    op1   = models.User(username="operator1", password_hash=hash_password("op123"),    role="operator")
    db.add_all([admin, op1])
    db.flush()
    print("  ✓ Users: admin, operator1")

    # ── Aisles ────────────────────────────────────────────────────────────────
    a1 = models.Aisle(code="A1", name="Fasteners & Hardware")
    a2 = models.Aisle(code="A2", name="Electronics & Cables")
    db.add_all([a1, a2])
    db.flush()
    print("  ✓ Aisles: A1, A2")

    # ── Racks ─────────────────────────────────────────────────────────────────
    a1r1 = models.Rack(aisle_id=a1.id, code="R1", name="Rack 1")
    a1r2 = models.Rack(aisle_id=a1.id, code="R2", name="Rack 2")
    a1r3 = models.Rack(aisle_id=a1.id, code="R3", name="Rack 3")
    a2r1 = models.Rack(aisle_id=a2.id, code="R1", name="Rack 1")
    a2r2 = models.Rack(aisle_id=a2.id, code="R2", name="Rack 2")
    db.add_all([a1r1, a1r2, a1r3, a2r1, a2r2])
    db.flush()
    print("  ✓ Racks: A1-R1..R3, A2-R1..R2")

    # ── Levels (3 per rack) ───────────────────────────────────────────────────
    levels = []
    for rack in [a1r1, a1r2, a1r3, a2r1, a2r2]:
        for n in [1, 2, 3]:
            lv = models.Level(rack_id=rack.id, level_num=n)
            db.add(lv)
            levels.append(lv)
    db.flush()
    print("  ✓ Levels: 3 per rack (15 total)")

    # Helper: get level object
    def get_level(rack, level_num):
        return next(lv for lv in levels if lv.rack_id == rack.id and lv.level_num == level_num)

    # ── Bins ──────────────────────────────────────────────────────────────────
    bin_defs = [
        # (rack, level_num, code, size, w, h, d)
        # A1-R1
        (a1r1, 1, "B1", "M", 40, 40, 40),
        (a1r1, 1, "B2", "M", 40, 40, 40),
        (a1r1, 2, "B1", "M", 40, 40, 40),
        (a1r1, 2, "B2", "L", 80, 60, 60),
        (a1r1, 3, "B1", "S", 20, 20, 20),
        # A1-R2
        (a1r2, 1, "B1", "M", 40, 40, 40),
        (a1r2, 1, "B2", "M", 40, 40, 40),
        (a1r2, 2, "B1", "L", 80, 60, 60),
        (a1r2, 3, "B1", "M", 40, 40, 40),
        (a1r2, 3, "B2", "S", 20, 20, 20),
        # A1-R3
        (a1r3, 1, "B1", "XL", 100, 80, 80),
        (a1r3, 2, "B1", "M",   40, 40, 40),
        (a1r3, 3, "B1", "M",   40, 40, 40),
        # A2-R1
        (a2r1, 1, "B1", "M", 40, 40, 40),
        (a2r1, 1, "B2", "M", 40, 40, 40),
        (a2r1, 2, "B1", "L", 80, 60, 60),
        (a2r1, 3, "B1", "M", 40, 40, 40),
        # A2-R2
        (a2r2, 1, "B1", "M", 40, 40, 40),
        (a2r2, 2, "B1", "M", 40, 40, 40),
        (a2r2, 3, "B1", "S", 20, 20, 20),
    ]

    bins = {}
    for rack, level_num, code, size, w, h, d in bin_defs:
        lv = get_level(rack, level_num)
        b = models.Bin(level_id=lv.id, code=code, size_category=size,
                       width_cm=w, height_cm=h, depth_cm=d)
        db.add(b)
        bins[(rack.id, level_num, code)] = b
    db.flush()
    print(f"  ✓ Bins: {len(bin_defs)} total")

    # ── Items ─────────────────────────────────────────────────────────────────
    item_defs = [
        # (sku, name, description, w, h, d)
        ("BOLT-M6-25",  "Bolt M6 25mm",         "Hex head bolt, stainless", 1.0, 2.5, 1.0),
        ("BOLT-M8-40",  "Bolt M8 40mm",         "Hex head bolt, stainless", 1.5, 4.0, 1.5),
        ("NUT-M6",      "Nut M6",               "Hex nut, zinc plated",     1.0, 0.5, 1.0),
        ("NUT-M8",      "Nut M8",               "Hex nut, zinc plated",     1.5, 0.6, 1.5),
        ("WASH-M6",     "Washer M6",            "Flat washer, steel",       2.0, 0.2, 2.0),
        ("WASH-M8",     "Washer M8",            "Flat washer, steel",       2.5, 0.2, 2.5),
        ("SCREW-M4-10", "Screw M4 10mm",        "Pan head machine screw",   0.5, 1.0, 0.5),
        ("CAB-USB-2M",  "USB Cable 2m",         "USB-A to USB-C, braided", 8.0, 2.0, 2.0),
        ("CAB-ETH-5M",  "Ethernet Cat6 5m",     "RJ45 patch cable, blue",  12.0, 2.0, 2.0),
        ("CONN-RJ45",   "RJ45 Connector",       "Cat6 crimp connector",     2.0, 1.5, 1.5),
    ]

    items = {}
    for sku, name, desc, w, h, d in item_defs:
        it = models.Item(sku=sku, name=name, description=desc,
                         width_cm=w, height_cm=h, depth_cm=d)
        db.add(it)
        items[sku] = it
    db.flush()
    print(f"  ✓ Items: {len(item_defs)} SKUs")

    # ── Bin Items (stock) ─────────────────────────────────────────────────────
    def get_bin(rack, level_num, code):
        return bins[(rack.id, level_num, code)]

    stock = [
        # (bin_ref, item_sku, quantity)
        (get_bin(a1r1, 1, "B1"), "BOLT-M6-25", 200),
        (get_bin(a1r1, 1, "B2"), "BOLT-M8-40", 150),
        (get_bin(a1r1, 2, "B1"), "NUT-M6",     500),
        (get_bin(a1r1, 2, "B2"), "NUT-M8",     300),
        (get_bin(a1r1, 3, "B1"), "WASH-M6",    800),
        (get_bin(a1r2, 1, "B1"), "WASH-M8",    600),
        (get_bin(a1r2, 1, "B2"), "SCREW-M4-10",1000),
        (get_bin(a1r2, 2, "B1"), "BOLT-M6-25", 100),  # secondary location
        (get_bin(a2r1, 1, "B1"), "CAB-USB-2M",  50),
        (get_bin(a2r1, 1, "B2"), "CAB-ETH-5M",  30),
        (get_bin(a2r1, 2, "B1"), "CONN-RJ45",  200),
        (get_bin(a2r2, 1, "B1"), "CAB-USB-2M",  20),  # secondary location
    ]

    for bin_, sku, qty in stock:
        db.add(models.BinItem(bin_id=bin_.id, item_id=items[sku].id, quantity=qty))
    db.flush()
    print(f"  ✓ Stock: {len(stock)} bin-item assignments")

    db.commit()
    db.close()
    print("\nSeed complete! Login at http://localhost:8000")
    print("  admin    / admin123")
    print("  operator1 / op123")


if __name__ == "__main__":
    seed()
