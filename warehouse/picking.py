"""
S-shape warehouse traversal algorithm.

Odd aisles are traversed ascending (low rack/level/bin → high).
Even aisles are traversed descending (high → low).
Within each aisle levels are visited bottom-up (L1 → L2 → L3).
"""
from __future__ import annotations

from typing import List, Tuple

import models


def _location_key(stop: models.PickStop) -> tuple:
    """Return a sort key that implements the S-shape order."""
    bin_ = stop.bin
    level = bin_.level
    rack = level.rack
    aisle = rack.aisle

    aisle_num = int(aisle.code[1:])
    rack_num = int(rack.code[1:])
    level_num = level.level_num
    bin_num = int(bin_.code[1:])

    if aisle_num % 2 == 1:  # odd aisle → ascending
        return (aisle_num, rack_num, level_num, bin_num)
    else:                   # even aisle → descending
        return (aisle_num, -rack_num, -level_num, -bin_num)


def _aisle_num(bin_: models.Bin) -> int:
    return int(bin_.level.rack.aisle.code[1:])


def assign_bins(
    pick_items: List[models.PickItem],
    db,
) -> List[Tuple[models.Bin, models.PickItem]]:
    """
    For each basket item find the best bin:
    - must hold the item with sufficient quantity
    - prefer the bin whose aisle is nearest to the last assigned stop
      (greedy nearest-aisle; falls back to first available bin)

    Returns a list of (bin, pick_item) pairs, not yet sorted.
    """
    assignments: List[Tuple[models.Bin, models.PickItem]] = []
    last_aisle = 1

    for pi in pick_items:
        # All bins that hold this item with enough stock
        candidates: List[models.BinItem] = (
            db.query(models.BinItem)
            .filter(
                models.BinItem.item_id == pi.item_id,
                models.BinItem.quantity >= pi.quantity_requested,
            )
            .all()
        )

        if not candidates:
            # Not enough stock anywhere — skip (caller should warn user)
            continue

        # Pick the candidate whose aisle is closest to last_aisle
        best = min(
            candidates,
            key=lambda bi: abs(_aisle_num(bi.bin) - last_aisle),
        )
        last_aisle = _aisle_num(best.bin)
        assignments.append((best.bin, pi))

    return assignments


def compute_route(stops: List[models.PickStop]) -> List[models.PickStop]:
    """Sort a list of PickStop objects into S-shape traversal order."""
    return sorted(stops, key=_location_key)
