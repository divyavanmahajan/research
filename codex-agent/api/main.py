from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_framework import Agent, MemoryManager, SkillManager
from state import AgentState
from tools import build_tool_router

app = FastAPI(title="Codex Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_skills_dir = Path(__file__).parent / "skills"
_tool_router = build_tool_router()
_skill_manager = SkillManager(_skills_dir)
_memory = MemoryManager(use_vector=True)
_agent = Agent(tool_router=_tool_router, skill_manager=_skill_manager, memory=_memory)


class RunRequest(BaseModel):
    task: str
    system_prompt: str = ""
    max_iterations: int = 20


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run")
async def run_agent(req: RunRequest):
    state = AgentState(
        task=req.task,
        system_prompt=req.system_prompt,
        max_iterations=req.max_iterations,
    )

    async def event_stream():
        try:
            async for event in _agent.stream(state):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
