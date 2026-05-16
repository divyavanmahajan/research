import sys
from pathlib import Path

# Ensure sibling modules resolve when imported as a package
sys.path.insert(0, str(Path(__file__).parent))

from agent_local import run_local  # noqa: E402
from agent_managed import run_managed  # noqa: E402

__all__ = ["run_local", "run_managed"]
