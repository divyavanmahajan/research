from __future__ import annotations

from .model_client import model_call

PLANNER_SYSTEM = """You are a task planner. Given a task and context, break it into a numbered list of clear, actionable steps.
Output ONLY the numbered steps — no preamble, no explanation."""


async def plan(task: str, skill_context: str, messages: list) -> list[str]:
    system = PLANNER_SYSTEM
    if skill_context:
        system = f"{PLANNER_SYSTEM}\n\nAvailable skills:\n{skill_context}"

    response = await model_call(
        messages=[{"role": "user", "content": f"Task: {task}"}],
        system=system,
        tools=None,
        mode="planner",
    )

    lines = [line.strip() for line in response.output.splitlines() if line.strip()]
    steps = [line for line in lines if line[0].isdigit() or line.startswith("-")]
    return steps if steps else [response.output]
