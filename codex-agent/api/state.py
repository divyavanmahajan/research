from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    task: str
    system_prompt: str = ""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[dict[str, Any]] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    done: bool = False
    iteration: int = 0
    max_iterations: int = 20

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        for result in results:
            self.messages.append({"role": "tool", "content": result["output"], "tool_use_id": result["id"]})
