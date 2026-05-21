from __future__ import annotations

import os
from pathlib import Path


def read_file(path: str) -> str:
    """Read and return the contents of a local file."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text()


def write_file(path: str, content: str) -> str:
    """Write content to a local file, creating parent directories as needed."""
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Written {len(content)} bytes to {p}"
