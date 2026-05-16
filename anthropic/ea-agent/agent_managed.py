"""
Managed agents session runner.

Connects to a pre-created managed agent (via setup_agent.py) and streams the
research session. Custom tools (think, write_report) are handled client-side:
- think       → returns "Thought recorded." immediately
- write_report → saves the document locally using formatters.py

The session uses the agent_toolset built-in web_search for research.
"""

import json
import time
from pathlib import Path
from typing import Optional

import anthropic

from formatters import save_document

_CONFIG_FILE = Path(__file__).parent / ".ea_agent_config.json"


def load_agent_config() -> dict:
    """Load agent + environment IDs saved by setup_agent.py."""
    if not _CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No agent config found at {_CONFIG_FILE}.\n"
            "Run setup_agent.py first to create the managed agent and environment."
        )
    with open(_CONFIG_FILE) as f:
        return json.load(f)


def run_managed(
    topic: str,
    output_format: str = "md",
    output_path: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """
    Run the EA research agent via Anthropic Managed Agents.

    Args:
        topic: Research topic for the EA document
        output_format: 'md', 'html', or 'docx'
        output_path: File path for the final report
        verbose: Print all agent message chunks while streaming
    """
    config = load_agent_config()
    agent_id = config["agent_id"]
    agent_version = config["agent_version"]
    environment_id = config["environment_id"]

    client = anthropic.Anthropic()

    print(f"  [managed] Creating session for agent {agent_id[:20]}...")

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id, "version": agent_version},
        environment_id=environment_id,
    )
    session_id = session.id
    print(f"  [managed] Session {session_id[:24]}... started")

    prompt = (
        f"Research the following topic and produce a comprehensive Enterprise Architecture document.\n\n"
        f"TOPIC: {topic}\n\n"
        f"Steps:\n"
        f"1. Use the think tool to plan 4–6 research angles for this topic\n"
        f"2. Use web_search directly to gather broad and deep coverage (8–12 searches)\n"
        f"3. Synthesise all findings into a complete EA document with all 10 required sections\n"
        f"4. Call write_report with the FULL document content (do not truncate or omit sections)"
    )

    report_saved = False

    # Stream-first: open stream, then send the user message inside the context
    with client.beta.sessions.events.stream(session_id=session_id) as stream:
        client.beta.sessions.events.send(
            session_id=session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text" and verbose:
                        print(block.text, end="", flush=True)

            elif event.type == "agent.custom_tool_use":
                _handle_custom_tool(
                    client=client,
                    session_id=session_id,
                    event=event,
                    output_format=output_format,
                    output_path=output_path,
                )
                if event.name == "write_report":
                    report_saved = True

            elif event.type == "session.status_idle":
                print("\n  [managed] Session idle — done.")
                break

            elif event.type == "session.status_terminated":
                print("\n  [managed] Session terminated.")
                break

    if not report_saved:
        print("  [managed] Warning: write_report was not called by the agent.")


def _handle_custom_tool(
    client: anthropic.Anthropic,
    session_id: str,
    event,
    output_format: str,
    output_path: Optional[str],
) -> None:
    """Dispatch a custom tool call and send the result back to the session."""
    tool_name = event.name
    tool_input = event.input if isinstance(event.input, dict) else {}

    if tool_name == "think":
        thought = tool_input.get("thought", "")
        print(f"  [think] {thought[:100]}{'...' if len(thought) > 100 else ''}")
        result = "Thought recorded. Continue with your plan."

    elif tool_name == "write_report":
        content = tool_input.get("content", "")
        print(f"  [write_report] Saving {len(content):,} chars → {output_path}")
        try:
            save_document(content, output_format, output_path)
            result = f"Report successfully saved to: {output_path}"
        except Exception as e:
            result = f"Error saving report: {str(e)}"

    else:
        result = f"Unknown tool: {tool_name}"

    client.beta.sessions.events.send(
        session_id=session_id,
        events=[
            {
                "type": "user.custom_tool_result",
                "custom_tool_use_id": event.id,
                "content": [{"type": "text", "text": result}],
            }
        ],
    )
