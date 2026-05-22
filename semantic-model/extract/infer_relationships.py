#!/usr/bin/env python3
"""
infer_relationships.py — Detect table relationships from column naming conventions.

Heuristics applied (in order of confidence):
  1. Column `{x}_id` matches table named `{x}`, `{x}s`, `dim_{x}`, `fact_{x}`, etc.
  2. Column name exactly matches a PK column name in another table (e.g. `customer_id` ↔ `customer_id`)
  3. Column `{x}_key` / `{x}_code` patterns with the same matching logic.

Output: a list of Relationship objects, each with a confidence score.
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import inflect

# Table name prefixes to strip before matching
TABLE_PREFIXES = ("dim_", "fact_", "fct_", "stg_", "raw_", "int_", "rpt_", "mart_", "bridge_", "ref_")

# Column suffixes that suggest a FK
FK_SUFFIXES = ("_id", "_key", "_code", "_fk", "_ref")

_inflect = inflect.engine()


@dataclass
class Relationship:
    from_table: str     # catalog.schema.table
    from_column: str
    to_table: str       # catalog.schema.table
    to_column: str
    cardinality: str    # many_to_one | one_to_one | unknown
    confidence: str     # explicit | inferred_naming | inferred_type


def _candidate_table_names(stem: str) -> list[str]:
    """Given a FK stem like 'customer', return candidate table names to match against."""
    candidates = set()
    candidates.add(stem)
    # plural
    plural = _inflect.plural(stem)
    if plural:
        candidates.add(plural)
    # with common prefixes
    for pfx in TABLE_PREFIXES:
        candidates.add(pfx + stem)
        if plural:
            candidates.add(pfx + plural)
    return list(candidates)


def _strip_prefixes(table_name: str) -> str:
    for pfx in TABLE_PREFIXES:
        if table_name.startswith(pfx):
            return table_name[len(pfx):]
    return table_name


def _likely_pk(columns: list[dict], table_name: str) -> Optional[str]:
    """Guess the primary key column of a table."""
    bare = _strip_prefixes(table_name)
    # Prefer column named exactly <table>_id or <bare>_id or just 'id'
    for col in columns:
        name = col["name"].lower()
        if name in (f"{bare}_id", f"{table_name}_id", "id"):
            return col["name"]
    # Fall back to any column ending in _id at position 0
    for col in sorted(columns, key=lambda c: c["position"]):
        if col["name"].lower().endswith("_id"):
            return col["name"]
    return None


def _extract_fk_stem(col_name: str) -> Optional[str]:
    """Extract the entity stem from a FK column name, or None if not a FK pattern."""
    lower = col_name.lower()
    for suffix in FK_SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix):
            return lower[: -len(suffix)]
    return None


def infer_relationships(all_tables: list[dict], cfg: dict) -> list[Relationship]:
    """
    all_tables: list of TableMeta dicts (from raw JSON).
    Returns a deduplicated list of Relationship objects.
    """
    inference_cfg = cfg.get("inference", {})
    strip_prefixes = inference_cfg.get("strip_table_prefixes", True)

    # Build lookup: bare_name → [table_dict, ...]  (lowercased)
    name_index: dict[str, list[dict]] = {}
    for t in all_tables:
        bare = _strip_prefixes(t["name"]) if strip_prefixes else t["name"]
        key = bare.lower()
        name_index.setdefault(key, []).append(t)
        # Also index by full name
        name_index.setdefault(t["name"].lower(), []).append(t)

    relationships: list[Relationship] = []
    seen: set[tuple] = set()

    for table in all_tables:
        from_full = table["full_name"]
        for col in table["columns"]:
            stem = _extract_fk_stem(col["name"])
            if stem is None:
                continue

            candidates = _candidate_table_names(stem)
            for cand in candidates:
                matches = name_index.get(cand.lower(), [])
                for target in matches:
                    if target["full_name"] == from_full:
                        continue  # skip self-references

                    to_pk = _likely_pk(target["columns"], target["name"])
                    if to_pk is None:
                        continue

                    key = (from_full, col["name"], target["full_name"], to_pk)
                    if key in seen:
                        continue
                    seen.add(key)

                    relationships.append(Relationship(
                        from_table=from_full,
                        from_column=col["name"],
                        to_table=target["full_name"],
                        to_column=to_pk,
                        cardinality="many_to_one",
                        confidence="inferred_naming",
                    ))

    return relationships


def load_all_raw(output_dir: Path) -> list[dict]:
    """Load all raw schema JSON files from the model/raw directory."""
    all_tables = []
    raw_dir = output_dir / "raw"
    if not raw_dir.exists():
        return []
    for json_file in raw_dir.glob("**/_schema.json"):
        with open(json_file) as f:
            all_tables.extend(json.load(f))
    return all_tables


def save_relationships(relationships: list[Relationship], output_dir: Path):
    out_file = output_dir / "raw" / "_relationships.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump([asdict(r) for r in relationships], f, indent=2)
    return out_file


if __name__ == "__main__":
    import sys
    import yaml

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    config_dir = config_path.parent
    output_dir = (config_dir / cfg.get("output_dir", "../model")).resolve()

    tables = load_all_raw(output_dir)
    print(f"Loaded {len(tables)} tables from raw files.")

    rels = infer_relationships(tables, cfg)
    out = save_relationships(rels, output_dir)
    print(f"Inferred {len(rels)} relationships → {out}")
