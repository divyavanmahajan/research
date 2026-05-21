from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ModelResponse:
    output: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    final: bool = True


async def model_call(
    messages: list[dict],
    system: str,
    tools: list[dict] | None = None,
    mode: Literal["planner", "executor"] = "executor",
) -> ModelResponse:
    provider = os.getenv("MODEL_PROVIDER", "anthropic").lower()
    if provider == "azure":
        return await _azure_call(messages, system, tools, mode)
    return await _anthropic_call(messages, system, tools, mode)


async def _anthropic_call(messages, system, tools, mode) -> ModelResponse:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": messages,
    }
    if tools and mode == "executor":
        kwargs["tools"] = [_to_anthropic_tool(t) for t in tools]

    response = await client.messages.create(**kwargs)

    text_parts = [b.text for b in response.content if b.type == "text"]
    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

    tool_calls = [
        {"id": b.id, "name": b.name, "input": b.input}
        for b in tool_use_blocks
    ]

    return ModelResponse(
        output="\n".join(text_parts),
        tool_calls=tool_calls,
        final=response.stop_reason != "tool_use",
    )


async def _azure_call(messages, system, tools, mode) -> ModelResponse:
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    oai_messages = [{"role": "system", "content": system}] + messages
    kwargs: dict[str, Any] = {
        "model": deployment,
        "messages": oai_messages,
    }
    if tools and mode == "executor":
        kwargs["tools"] = [_to_openai_tool(t) for t in tools]
        kwargs["tool_choice"] = "auto"

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    msg = choice.message

    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append(
                {"id": tc.id, "name": tc.function.name, "input": json.loads(tc.function.arguments)}
            )

    return ModelResponse(
        output=msg.content or "",
        tool_calls=tool_calls,
        final=choice.finish_reason != "tool_calls",
    )


def _to_anthropic_tool(t: dict) -> dict:
    return {
        "name": t["name"],
        "description": t.get("description", ""),
        "input_schema": t.get("input_schema", {"type": "object", "properties": {}}),
    }


def _to_openai_tool(t: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
        },
    }
