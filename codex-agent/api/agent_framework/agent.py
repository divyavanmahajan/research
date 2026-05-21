from __future__ import annotations

from typing import AsyncIterator

from state import AgentState
from .memory import MemoryManager
from .model_client import model_call
from .planner import plan as planner_plan
from .skill_manager import SkillManager
from .tool_router import ToolRouter


class Agent:
    def __init__(
        self,
        tool_router: ToolRouter,
        skill_manager: SkillManager | None = None,
        memory: MemoryManager | None = None,
        use_planner: bool = True,
    ):
        self.tool_router = tool_router
        self.skill_manager = skill_manager or SkillManager()
        self.memory = memory or MemoryManager(use_vector=False)
        self.use_planner = use_planner

    async def run(self, state: AgentState) -> AgentState:
        """Run the agent loop to completion."""
        async for _ in self.stream(state):
            pass
        return state

    async def stream(self, state: AgentState) -> AsyncIterator[dict]:
        """Stream agent events as dicts: {type, content}."""
        state.add_user(state.task)

        skill_context = self.skill_manager.load(state.task)

        if self.use_planner:
            state.plan = await planner_plan(state.task, skill_context, state.messages)
            yield {"type": "plan", "content": state.plan}

        system = _build_system(state, skill_context)

        while not state.done and state.iteration < state.max_iterations:
            state.iteration += 1

            response = await model_call(
                messages=state.messages,
                system=system,
                tools=self.tool_router.list(),
                mode="executor",
            )

            if response.output:
                yield {"type": "text", "content": response.output}

            if response.tool_calls:
                yield {"type": "tool_calls", "content": response.tool_calls}
                results = await self.tool_router.execute(response.tool_calls)
                state.add_tool_results(results)
                yield {"type": "tool_results", "content": results}

            if response.output:
                state.add_assistant(response.output)

            self.memory.store(state)

            if response.final and not response.tool_calls:
                state.done = True

        yield {"type": "done", "content": {"session_id": state.session_id, "iterations": state.iteration}}


def _build_system(state: AgentState, skill_context: str) -> str:
    parts = []
    if state.system_prompt:
        parts.append(state.system_prompt)
    if skill_context:
        parts.append(f"Available skills:\n{skill_context}")
    if state.plan:
        plan_text = "\n".join(f"  {s}" for s in state.plan)
        parts.append(f"Execution plan:\n{plan_text}")
    return "\n\n".join(parts) if parts else "You are a helpful AI agent."
