# Codex Agent

A full-stack agentic AI harness with a streaming React UI and a Python FastAPI backend. The harness orchestrates a plan → execute → tool-call → memory loop against configurable model endpoints (Anthropic Claude or Azure AI Foundry / OpenAI).

```
┌────────────────────────────┐
│           AGUI             │
│  (React + Vite, SSE feed)  │
└────────────┬───────────────┘
             │  POST /run  (text/event-stream)
             ▼
┌─────────────────────────────────┐
│     Agent Harness API           │
│         (FastAPI)               │
│                                 │
│  • planner      (model call)   │
│  • executor loop               │
│  • skill loader (SKILL.md)     │
│  • tool router                 │
│  • memory manager              │
└────────────┬──────────────────┘
             │
  ┌──────────┼─────────────────────┐
  ▼          ▼                     ▼
Model     Skill System          Tool Registry
endpoint  (SKILL.md +           (web_search,
(Anthropic  skill.py)            azure_function,
 or Azure)                       mcp_call,
                                 read_file,
                                 write_file)
                │
                ▼
      Memory Layer
      (session dict + ChromaDB)
```

## Project layout

```
codex-agent/
├── api/
│   ├── main.py                    # FastAPI app — /health, /run (SSE)
│   ├── state.py                   # AgentState dataclass
│   ├── requirements.txt
│   ├── .env.example
│   ├── agent_framework/
│   │   ├── agent.py               # Agent class + stream() loop
│   │   ├── planner.py             # Planner step
│   │   ├── skill_manager.py       # Dynamic skill loader
│   │   ├── tool_router.py         # Tool registry + async dispatcher
│   │   ├── memory.py              # Session dict + ChromaDB vector store
│   │   └── model_client.py        # Anthropic / Azure model abstraction
│   ├── skills/
│   │   └── example/
│   │       ├── SKILL.md           # Skill spec (injected into system prompt)
│   │       └── skill.py           # Skill class with run() method
│   └── tools/
│       ├── __init__.py            # build_tool_router() factory
│       ├── web_search.py          # Tavily / Bing search
│       ├── azure_function.py      # Azure Function HTTP caller
│       ├── mcp_client.py          # MCP JSON-RPC client
│       └── file_rw.py             # Local file read / write
└── ui/
    ├── index.html
    ├── vite.config.ts             # Dev proxy: /run → localhost:8000
    └── src/
        ├── App.tsx
        ├── hooks/
        │   └── useAgentStream.ts  # SSE reader, typed AgentEvent union
        └── components/
            ├── ChatPanel.tsx      # Task input, run/stop/clear, event feed
            └── StreamEvent.tsx    # Per-event renderer (plan, text, tools…)
```

## Quick start

### 1. API

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in ANTHROPIC_API_KEY (or AZURE_OPENAI_* vars and set MODEL_PROVIDER=azure)

uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs   (Swagger UI)
```

### 2. UI

```bash
cd ui
npm install
npm run dev
# → http://localhost:5173
```

The Vite dev server proxies `/run` and `/health` to the API on port 8000.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_PROVIDER` | `anthropic` | `anthropic` or `azure` |
| `ANTHROPIC_API_KEY` | — | Required when provider is `anthropic` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model ID |
| `AZURE_OPENAI_API_KEY` | — | Required when provider is `azure` |
| `AZURE_OPENAI_ENDPOINT` | — | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | Deployment name |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | API version |
| `SEARCH_PROVIDER` | `tavily` | `tavily` or `bing` |
| `TAVILY_API_KEY` | — | Required when using Tavily |
| `BING_SEARCH_API_KEY` | — | Required when using Bing |
| `AZURE_FUNCTION_KEY` | — | Optional; sent as `x-functions-key` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

## API reference

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness check |
| `POST` | `/run` | `{task, system_prompt?, max_iterations?}` | Run agent; returns `text/event-stream` |

### SSE event types

Each `data:` line is a JSON object `{type, content}`:

| `type` | `content` shape | When emitted |
|---|---|---|
| `plan` | `string[]` | After planner step |
| `text` | `string` | Each model text response |
| `tool_calls` | `{name, input}[]` | When model requests tools |
| `tool_results` | `{id, output}[]` | After tools execute |
| `done` | `{session_id, iterations}` | Loop finished |
| `error` | `string` | Unhandled exception |

## Adding a skill

```bash
mkdir api/skills/my_skill
```

`api/skills/my_skill/SKILL.md` — describe what the skill does, when to use it, its inputs and steps. This text is injected verbatim into the system prompt.

`api/skills/my_skill/skill.py` — implement a `Skill` class with a `run()` method for direct invocation.

Restart the API; the skill is auto-discovered at startup.

## Adding a tool

Register a function in `api/tools/__init__.py`:

```python
router.register(
    my_function,
    description="...",
    input_schema={"type": "object", "properties": {...}, "required": [...]},
)
```

The tool is automatically surfaced to the model in every executor step.

## See also

- [Architecture](docs/architecture.md)
- [Developer guide](docs/developer.md)
