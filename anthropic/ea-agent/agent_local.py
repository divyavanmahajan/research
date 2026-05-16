"""
Local agentic loop using the Anthropic SDK tool runner.

Architecture:
  Orchestrator (claude-opus-4-7)
    tools: think, delegate_to_researcher, write_report
      └─ delegate_to_researcher spawns a nested tool runner:
           Researcher (claude-opus-4-7)
             tools: web_search, fetch_page, think
"""

from typing import Optional

import anthropic
from anthropic import beta_tool

from prompts import EA_ORCHESTRATOR_PROMPT, EA_RESEARCHER_PROMPT
from tools import web_search, fetch_page, think
from formatters import save_document

DEFAULT_MODEL = "anthropic:claude-opus-4-7"


def _strip_provider_prefix(model_id: str) -> str:
    """Convert 'anthropic:claude-opus-4-7' → 'claude-opus-4-7'."""
    if ":" in model_id:
        return model_id.split(":", 1)[1]
    return model_id


def run_local(
    topic: str,
    output_format: str = "md",
    output_path: Optional[str] = None,
    model_id: str = DEFAULT_MODEL,
) -> None:
    """
    Run the EA research agent locally using the Anthropic SDK tool runner.

    Args:
        topic: Research topic / question for the EA document
        output_format: 'md', 'html', or 'docx'
        output_path: File path to write the final report
        model_id: Anthropic model ID (with or without 'anthropic:' prefix)
    """
    raw_model = _strip_provider_prefix(model_id)
    client = anthropic.Anthropic()

    # ── Researcher sub-agent ──────────────────────────────────────────────────
    # Defined as a closure so it captures client and raw_model.

    @beta_tool
    def delegate_to_researcher(research_task: str) -> str:
        """
        Delegate a research task to a specialist research analyst sub-agent.

        The researcher will search the web, fetch key pages, and return structured
        findings covering: key facts, industry trends, vendor landscape, standards,
        risks, and cited sources.

        Args:
            research_task: A specific, focused research question or topic to investigate.
        """
        print(f"  [researcher] → {research_task[:80]}{'...' if len(research_task) > 80 else ''}")

        researcher_runner = client.beta.messages.tool_runner(
            model=raw_model,
            max_tokens=8000,
            system=EA_RESEARCHER_PROMPT,
            tools=[web_search, fetch_page, think],
            messages=[{"role": "user", "content": research_task}],
        )

        last_msg = None
        for msg in researcher_runner:
            last_msg = msg

        if last_msg is None:
            return "Researcher returned no results."

        return next(
            (block.text for block in last_msg.content if block.type == "text"),
            "Researcher completed but returned no text.",
        )

    # ── Write-report tool (bound to format + path) ────────────────────────────

    @beta_tool
    def write_report(content: str) -> str:
        """
        Save the completed enterprise architecture research report to a file.

        Call this tool ONCE with the FULL, COMPLETE report in markdown format.
        Pass the entire document — all 10 sections — in a single call.
        Do not truncate, summarise, or split the content.

        Args:
            content: The complete markdown content of the EA report.
        """
        try:
            save_document(content, output_format, output_path)
            return f"Report successfully saved to: {output_path}"
        except Exception as e:
            return f"Error saving report: {str(e)}"

    # ── Orchestrator tool runner ───────────────────────────────────────────────

    prompt = (
        f"Research the following topic and produce a comprehensive Enterprise Architecture document.\n\n"
        f"TOPIC: {topic}\n\n"
        f"Steps:\n"
        f"1. Use the think tool to plan 4–6 research angles for this topic\n"
        f"2. Delegate research tasks to delegate_to_researcher — gather broad and deep coverage\n"
        f"3. Synthesise all findings into a complete EA document with all 10 required sections\n"
        f"4. Call write_report with the FULL document content (do not truncate or omit sections)\n\n"
        f"Output file: {output_path}"
    )

    orchestrator_runner = client.beta.messages.tool_runner(
        model=raw_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": EA_ORCHESTRATOR_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[think, delegate_to_researcher, write_report],
        messages=[{"role": "user", "content": prompt}],
    )

    for msg in orchestrator_runner:
        for block in msg.content:
            if block.type == "tool_use":
                if block.name not in ("think", "delegate_to_researcher", "write_report"):
                    print(f"  [orchestrator] tool: {block.name}")
            elif block.type == "text" and block.text.strip():
                # Print a short status snippet from orchestrator narration
                snippet = block.text.strip()[:120].replace("\n", " ")
                print(f"  [orchestrator] {snippet}...")
