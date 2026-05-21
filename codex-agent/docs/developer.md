# Developer Guide — Codex Agent

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 20+ |
| npm | 10+ |

## Initial setup

```bash
# API
cd codex-agent/api
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — fill in at least ANTHROPIC_API_KEY or the AZURE_OPENAI_* vars

# UI
cd codex-agent/ui
npm install
```

## Running locally

Start both processes in separate terminals:

```bash
# Terminal 1 — API
cd api && uvicorn main:app --reload

# Terminal 2 — UI
cd ui && npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/run` and `/health` to `:8000`.

## Adding a tool

**Step 1** — Create `api/tools/<name>.py`:

```python
# api/tools/my_tool.py
async def my_tool(param_a: str, param_b: int = 0) -> str:
    """Brief description used as fallback if description= is omitted."""
    result = ...
    return str(result)
```

The function can be async or sync. The `ToolRouter` detects `iscoroutinefunction` and awaits accordingly.

**Step 2** — Register in `api/tools/__init__.py` inside `build_tool_router()`:

```python
from .my_tool import my_tool

router.register(
    my_tool,
    description="Clear one-sentence description shown to the model.",
    input_schema={
        "type": "object",
        "properties": {
            "param_a": {"type": "string", "description": "What param_a is for"},
            "param_b": {"type": "integer", "description": "What param_b is for"},
        },
        "required": ["param_a"],
    },
)
```

Restart the API. The tool appears in the next `/run` request.

**Testing a tool in isolation:**

```python
# run from api/ with venv active
import asyncio
from tools.my_tool import my_tool

asyncio.run(my_tool("hello", 42))
```

---

## Adding a skill

Skills give the model domain-specific context and a workflow to follow. They are injected into the system prompt verbatim.

**Step 1** — Create the directory:

```bash
mkdir api/skills/my_skill
```

**Step 2** — Write `api/skills/my_skill/SKILL.md`:

```markdown
# Skill: My Skill

## Purpose
One sentence explaining what this skill enables.

## When to use
Describe the task types or keywords that should trigger this skill.

## Inputs
- `param` (string): What the caller provides.

## Steps
1. Use web_search to gather current information on <topic>.
2. Synthesise findings.
3. Return a structured report.
```

The full text is prepended to the system prompt for every executor turn. Keep it focused and under ~500 words.

**Step 3** — Optionally implement `api/skills/my_skill/skill.py`:

```python
class Skill:
    name = "my_skill"
    description = "One-line description."

    async def run(self, param: str) -> str:
        # Direct programmatic invocation path (not called by the model loop)
        return f"Result for {param}"
```

The `Skill` class is loaded by `SkillManager` and available via `skill_manager.get_instance("my_skill")` for cases where you want to call a skill from application code rather than via the model.

---

## Changing or adding a model provider

Edit `api/agent_framework/model_client.py`. Add a branch to `model_call()`:

```python
async def model_call(messages, system, tools=None, mode="executor") -> ModelResponse:
    provider = os.getenv("MODEL_PROVIDER", "anthropic").lower()
    if provider == "azure":
        return await _azure_call(messages, system, tools, mode)
    if provider == "openai":                    # new branch
        return await _openai_call(messages, system, tools, mode)
    return await _anthropic_call(messages, system, tools, mode)
```

Implement `_openai_call` to return a `ModelResponse(output, tool_calls, final)`. The rest of the harness is provider-agnostic.

---

## Modifying the executor loop

The loop lives in `Agent.stream()` in `api/agent_framework/agent.py`. Each `yield` in that generator becomes a `data:` SSE line. New event types need a matching renderer in `ui/src/components/StreamEvent.tsx`.

**Example — add a `{type: "iteration"}` progress event:**

```python
# agent.py — inside the while loop, before model_call
yield {"type": "iteration", "content": {"n": state.iteration, "max": state.max_iterations}}
```

```tsx
// StreamEvent.tsx — add a new case in EventBody
if (event.type === "iteration") {
  return <span>Turn {event.content.n} / {event.content.max}</span>;
}
```

Update the `AgentEvent` union in `useAgentStream.ts` to include the new type.

---

## Memory

### Session memory

`MemoryManager._session` is an in-process dict keyed by `session_id`. It survives only while the API process is running. Use it for lightweight within-process caching.

### Vector memory

ChromaDB runs embedded (no separate server). The collection name is `agent_memory`. To query it from outside the harness:

```python
import chromadb
client = chromadb.Client()
col = client.get_collection("agent_memory")
results = col.query(query_texts=["my query"], n_results=5)
```

To persist ChromaDB across restarts, replace the transient client:

```python
# memory.py — _init_chroma()
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")   # persists to disk
return client.get_or_create_collection(name)
```

---

## Frontend development

The UI is a plain React + TypeScript app. No component library or CSS framework — styles are inline `React.CSSProperties` objects in each component.

**`useAgentStream.ts`** is the boundary between the UI and the API. It owns:
- Opening the `fetch` + `ReadableStream` connection
- Parsing newline-delimited SSE frames
- Maintaining the `AgentEvent[]` state
- Exposing `run()`, `clear()`, and `running` to consumers

Do not add API calls anywhere else in the UI.

**`ChatPanel.tsx`** is the top-level layout. It consumes `useAgentStream` and renders the task form and event feed. Keep layout logic here and event rendering in `StreamEvent.tsx`.

### TypeScript strictness

`tsconfig.json` enables `strict`, `noUnusedLocals`, and `noUnusedParameters`. All types must be explicit; the `AgentEvent` discriminated union in `useAgentStream.ts` is the single source of truth for event shapes.

---

## Environment variables quick reference

```bash
# Minimum for Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Minimum for Azure
MODEL_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Optional
ANTHROPIC_MODEL=claude-sonnet-4-6
AZURE_OPENAI_API_VERSION=2024-02-01
SEARCH_PROVIDER=tavily          # or bing
TAVILY_API_KEY=tvly-...
BING_SEARCH_API_KEY=...
AZURE_FUNCTION_KEY=...
CORS_ORIGINS=http://localhost:5173
```

---

## Troubleshooting

**`ImportError: attempted relative import beyond top-level package`**
`agent_framework` imports `state.py` with `from state import AgentState` (absolute). If you see this error after adding a new file, check that it also uses absolute imports for anything in `api/` root rather than `from ..x import`.

**ChromaDB fails silently**
`MemoryManager` swallows `chromadb` import errors. Check `use_vector=True` is set and `chromadb` is installed (`pip install chromadb`). The API still runs without it.

**CORS errors in the browser**
Set `CORS_ORIGINS` to include the exact origin the browser uses (scheme + host + port, e.g. `http://localhost:5173`).

**SSE stream never ends**
The API emits `data: [DONE]\n\n` in the `finally` block of `event_stream()`. If you abort the request from the UI, the server-side generator is cancelled by FastAPI when the client disconnects.
