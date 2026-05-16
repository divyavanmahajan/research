"""
One-time setup: create the Managed Agent and Environment, then save their IDs.

Run this ONCE before using --mode managed:

    python setup_agent.py

The agent and environment are reusable across many sessions. Re-running this
script creates new resources (incurring extra cost); use --show to inspect
existing config instead.

Usage:
    python setup_agent.py           # create agent + env, save config
    python setup_agent.py --show    # print existing config
    python setup_agent.py --delete  # delete saved agent + env (irreversible)
"""

import argparse
import json
import os
import sys
from pathlib import Path

_CONFIG_FILE = Path(__file__).parent / ".ea_agent_config.json"

# Add this directory to sys.path so sibling imports work when run as a script
sys.path.insert(0, str(Path(__file__).parent))

from prompts import EA_MANAGED_PROMPT  # noqa: E402


def _load_config() -> dict | None:
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE) as f:
            return json.load(f)
    return None


def _save_config(data: dict) -> None:
    with open(_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Config saved to: {_CONFIG_FILE}")


def cmd_show() -> None:
    cfg = _load_config()
    if cfg is None:
        print("No config file found. Run setup_agent.py to create the agent.")
        sys.exit(1)
    print(json.dumps(cfg, indent=2))


def cmd_delete(client) -> None:
    cfg = _load_config()
    if cfg is None:
        print("No config found — nothing to delete.")
        return

    try:
        client.beta.agents.delete(cfg["agent_id"])
        print(f"Deleted agent {cfg['agent_id']}")
    except Exception as e:
        print(f"Could not delete agent: {e}")

    try:
        client.beta.environments.delete(cfg["environment_id"])
        print(f"Deleted environment {cfg['environment_id']}")
    except Exception as e:
        print(f"Could not delete environment: {e}")

    _CONFIG_FILE.unlink(missing_ok=True)
    print("Config file removed.")


def cmd_create(client) -> None:
    existing = _load_config()
    if existing:
        print("Existing config found:")
        print(json.dumps(existing, indent=2))
        ans = input("\nCreate NEW agent + environment anyway? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted. Use --show to inspect, or --delete to remove the existing config.")
            return

    print("Creating environment...")
    env = client.beta.environments.create(
        name="ea-agent-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"  Environment: {env.id}")

    print("Creating agent...")
    agent = client.beta.agents.create(
        name="Enterprise Architecture Research Agent",
        model="claude-opus-4-7",
        system=EA_MANAGED_PROMPT,
        tools=[
            {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
            {
                "type": "custom",
                "name": "think",
                "description": (
                    "Plan, reflect, and organise your thinking before acting. "
                    "Use this to identify research gaps, evaluate findings, and plan next steps."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "thought": {
                            "type": "string",
                            "description": "Your analytical thought, plan, or reflection.",
                        }
                    },
                    "required": ["thought"],
                },
            },
            {
                "type": "custom",
                "name": "write_report",
                "description": (
                    "Save the completed enterprise architecture research report. "
                    "Call this tool ONCE with the FULL, COMPLETE report in markdown format. "
                    "Pass the entire document — all 10 sections — in a single call. "
                    "Do not truncate, summarise, or split the content."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The complete markdown content of the EA report.",
                        }
                    },
                    "required": ["content"],
                },
            },
        ],
    )
    print(f"  Agent: {agent.id}  (version {agent.version})")

    config = {
        "agent_id": agent.id,
        "agent_version": agent.version,
        "environment_id": env.id,
        "agent_name": agent.name,
        "model": agent.model,
    }
    _save_config(config)

    print("\nSetup complete. You can now run:")
    print('  python run.py "Your Topic" --mode managed')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="setup_agent",
        description="One-time setup for the Managed Agent EA research assistant.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--show", action="store_true", help="Print existing agent config")
    group.add_argument("--delete", action="store_true", help="Delete agent + environment")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic()

    if args.show:
        cmd_show()
    elif args.delete:
        cmd_delete(client)
    else:
        cmd_create(client)


if __name__ == "__main__":
    main()
