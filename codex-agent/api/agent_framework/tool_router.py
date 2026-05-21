from __future__ import annotations

import inspect
from typing import Any, Callable


class ToolRouter:
    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, fn: Callable, name: str | None = None, description: str = "", input_schema: dict | None = None) -> None:
        tool_name = name or fn.__name__
        self._tools[tool_name] = {
            "name": tool_name,
            "description": description or (inspect.getdoc(fn) or ""),
            "input_schema": input_schema or {"type": "object", "properties": {}},
            "fn": fn,
        }

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in self._tools.values()
        ]

    async def execute(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for call in tool_calls:
            name = call["name"]
            inputs = call.get("input", {})
            call_id = call.get("id", name)

            if name not in self._tools:
                results.append({"id": call_id, "output": f"Unknown tool: {name}"})
                continue

            fn = self._tools[name]["fn"]
            try:
                if inspect.iscoroutinefunction(fn):
                    output = await fn(**inputs)
                else:
                    output = fn(**inputs)
                results.append({"id": call_id, "output": str(output)})
            except Exception as exc:
                results.append({"id": call_id, "output": f"Tool error: {exc}"})

        return results
