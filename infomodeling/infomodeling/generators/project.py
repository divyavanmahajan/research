"""Generate dbt_project.yml and profiles.yml."""

from __future__ import annotations

import yaml

from ..model import ConceptualModel


def generate_dbt_project_yml(model: ConceptualModel) -> str:
    """Return a dbt_project.yml string."""
    project_name = _to_project_name(model.name)
    data = {
        "name": project_name,
        "version": "1.0.0",
        "config-version": 2,
        "profile": project_name,
        "model-paths": ["models"],
        "seed-paths": ["seeds"],
        "test-paths": ["tests"],
        "analysis-paths": ["analyses"],
        "macro-paths": ["macros"],
        "target-path": "target",
        "clean-targets": ["target", "dbt_packages"],
        "models": {
            project_name: {
                "staging": {
                    "+materialized": "view",
                },
                "marts": {
                    "+materialized": "table",
                },
            }
        },
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_profiles_yml(project_name: str | None = None, db_path: str = "dev.duckdb") -> str:
    """Return a profiles.yml string configured for DuckDB."""
    name = project_name or "infomodel_project"
    data = {
        name: {
            "target": "dev",
            "outputs": {
                "dev": {
                    "type": "duckdb",
                    "path": db_path,
                    "threads": 4,
                }
            },
        }
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _to_project_name(model_name: str) -> str:
    """Convert a human model name to a valid dbt project name (snake_case, no spaces)."""
    import re
    name = re.sub(r"[^a-zA-Z0-9 ]", "", model_name)
    return re.sub(r"\s+", "_", name).lower()
