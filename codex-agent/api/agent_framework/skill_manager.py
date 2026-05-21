from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any


class SkillManager:
    def __init__(self, skills_dir: str | Path = "skills"):
        self.skills_dir = Path(skills_dir)
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, task: str) -> str:
        """Return a combined skill context string relevant to the given task."""
        skills = self._discover()
        blocks = []
        for name, skill in skills.items():
            blocks.append(f"## Skill: {name}\n{skill['spec']}")
        return "\n\n".join(blocks) if blocks else ""

    def get_instance(self, name: str) -> Any | None:
        skills = self._discover()
        return skills.get(name, {}).get("instance")

    def _discover(self) -> dict[str, dict[str, Any]]:
        if self._cache:
            return self._cache

        if not self.skills_dir.exists():
            return {}

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            spec_path = skill_dir / "SKILL.md"
            impl_path = skill_dir / "skill.py"

            spec = spec_path.read_text() if spec_path.exists() else ""
            instance = None
            if impl_path.exists():
                instance = self._load_class(impl_path, name)

            self._cache[name] = {"spec": spec, "instance": instance}

        return self._cache

    def _load_class(self, path: Path, name: str) -> Any | None:
        try:
            mod_spec = importlib.util.spec_from_file_location(f"skills.{name}", path)
            module = importlib.util.module_from_spec(mod_spec)
            mod_spec.loader.exec_module(module)
            cls = getattr(module, "Skill", None)
            return cls() if cls else None
        except Exception:
            return None
