# CLAUDE.md — Codex Agent

Instructions for Claude Code when working in this project.

## Project structure

```
codex-agent/
├── api/          Python FastAPI backend (agent harness)
└── ui/           React + TypeScript + Vite frontend
```

The API and UI are independent — run them separately.

## Commands

### API (run from api/)

```bash
source .venv/bin/activate          # activate venv (created with python3 -m venv .venv)
pip install -r requirements.txt    # install / sync deps
uvicorn main:app --reload          # start dev server on :8000
```

Check liveness:
```bash
curl http://localhost:8000/health
```

Run a task manually via curl:
```bash
curl -N -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "List three benefits of async Python"}' \
  --no-buffer
```

### UI (run from ui/)

```bash
npm install      # first time
npm run dev      # Vite dev server on :5173
npm run build    # production build → dist/
```

## Key files

| File | What it does |
|---|---|
| `api/main.py` | FastAPI app, `/health`, `/run` SSE endpoint |
| `api/state.py` | `AgentState` dataclass — the single source of truth per run |
| `api/agent_framework/agent.py` | `Agent.stream()` — the main plan → execute → tool → memory loop |
| `api/agent_framework/model_client.py` | `model_call()` — switches between Anthropic and Azure via `MODEL_PROVIDER` |
| `api/agent_framework/skill_manager.py` | Scans `api/skills/*/`, reads SKILL.md, imports `Skill` class |
| `api/agent_framework/tool_router.py` | `ToolRouter.register()` + async `execute()` |
| `api/agent_framework/memory.py` | Session dict + optional ChromaDB vector store |
| `api/tools/__init__.py` | `build_tool_router()` factory — registers all tools |
| `ui/src/hooks/useAgentStream.ts` | SSE reader hook; `AgentEvent` discriminated union |
| `ui/src/components/ChatPanel.tsx` | Main AGUI component |

## Environment

Copy `.env.example` to `.env` before starting the API. The minimum required key is either `ANTHROPIC_API_KEY` (default) or the three `AZURE_OPENAI_*` vars with `MODEL_PROVIDER=azure`.

## How to add a tool

1. Create `api/tools/<name>.py` with an async or sync function.
2. Import and register it in `api/tools/__init__.py` inside `build_tool_router()`.
3. Provide a `description` and a JSON Schema `input_schema`. These are passed directly to the model.

## How to add a skill

1. Create `api/skills/<name>/SKILL.md` — plain English spec injected into the system prompt.
2. Create `api/skills/<name>/skill.py` with a `Skill` class and a `run()` method.
3. Restart the API. `SkillManager` discovers skills at startup; the cache is populated on the first request.

## How to add a model provider

Add a new branch in `api/agent_framework/model_client.py`:

```python
async def model_call(...) -> ModelResponse:
    provider = os.getenv("MODEL_PROVIDER", "anthropic").lower()
    if provider == "azure":
        return await _azure_call(...)
    if provider == "my_provider":        # new branch
        return await _my_provider_call(...)
    return await _anthropic_call(...)
```

Return a `ModelResponse(output, tool_calls, final)` regardless of provider.

## Conventions

- All `agent_framework/` imports of `state.py` use absolute imports (`from state import AgentState`), not relative, because `api/` is not itself a package.
- Tools are registered with explicit `input_schema` JSON Schema dicts — never rely on function signatures alone.
- Skills are stateless relative to the request; do not store mutable state in `Skill` instances that spans requests.
- SSE events are newline-delimited `data: <json>\n\n` — do not change this format or the UI hook breaks.
- The `AgentState.messages` list is the canonical conversation history; append to it only through `add_user`, `add_assistant`, and `add_tool_results`.
