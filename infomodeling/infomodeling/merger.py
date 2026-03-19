"""Merge strategy for regeneration: replace only BEGIN GENERATED / END GENERATED blocks."""

from __future__ import annotations

import re

BEGIN_MARKER = "-- BEGIN GENERATED"
END_MARKER = "-- END GENERATED"

_BLOCK_RE = re.compile(
    r"(-- BEGIN GENERATED\n)(.*?)(-- END GENERATED)",
    re.DOTALL,
)


def merge(existing: str, new_content: str) -> str:
    """
    Replace the BEGIN GENERATED ... END GENERATED block in `existing` with
    the equivalent block from `new_content`. Content outside the markers in
    `existing` is preserved verbatim.

    If `existing` has no markers, return `new_content` unchanged (first generation).
    If `new_content` has no markers, return `new_content` unchanged.
    """
    new_block_match = _BLOCK_RE.search(new_content)
    if not new_block_match:
        return new_content

    existing_block_match = _BLOCK_RE.search(existing)
    if not existing_block_match:
        return new_content

    new_block = new_block_match.group(0)
    merged = _BLOCK_RE.sub(new_block, existing, count=1)
    return merged


def has_markers(content: str) -> bool:
    """Return True if the content contains generated block markers."""
    return BEGIN_MARKER in content and END_MARKER in content
