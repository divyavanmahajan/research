# Architecture — Codex Agent

## Overview

Codex Agent is a two-process application: a **Python FastAPI backend** that runs the agent harness, and a **React + Vite frontend** that streams events from it over Server-Sent Events (SSE).

```
┌────────────────────────────┐
│           AGUI             │
│  React / Vite / TypeScript │
│  useAgentStream hook       │
│  ChatPanel + StreamEvent   │
└────────────┬───────────────┘
             │  POST /run  →  text/event-stream
             ▼
┌─────────────────────────────────────────────────────┐
│              Agent Harness API  (FastAPI)            │
│                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Planner  │  │ Executor     │  │ Skill Manager │ │
│  │ (model   │  │ Loop         │  │ (SKILL.md +   │ │
│  │  call)   │  │ (model call  │  │  skill.py)    │ │
│  └──────────┘  │  + tools)   │  └───────────────┘ │
│                └──────┬───────┘                     │
│                       │                             │
│         ┌─────────────┼─────────────┐               │
│         ▼             ▼             ▼               │
│   ToolRouter    MemoryManager   AgentState          │
└─────────┬──────────────────────────────────────────┘
          │
  ┌───────┼────────────────────────────────┐
  ▼       ▼            ▼                  ▼
Model  web_search  azure_function   mcp_call
client (Tavily/   (HTTP caller)    (JSON-RPC)
(Anth  Bing)
-ropic
/Azure)
          read_file   write_file
          (local FS)  (local FS)
```

---

## Components

### AGUI (`ui/`)

Single-page React application. Communicates with the API exclusively through the `/run` SSE endpoint. No state is persisted in the browser beyond the current session.

| File | Responsibility |
|---|---|
| `hooks/useAgentStream.ts` | Opens the SSE connection, parses `data:` lines, maintains the `AgentEvent[]` state, exposes `run()` / `clear()` |
| `components/ChatPanel.tsx` | Task input, run/stop/clear controls, scrollable event feed |
| `components/StreamEvent.tsx` | Renders a single `AgentEvent` with type-appropriate styling |
| `vite.config.ts` | Dev proxy forwards `/run` and `/health` to `:8000` |

**SSE event union:**

```typescript
type AgentEvent =
  | { type: "plan";         content: string[] }
  | { type: "text";         content: string }
  | { type: "tool_calls";   content: { name: string; input: Record<string, unknown> }[] }
  | { type: "tool_results"; content: { id: string; output: string }[] }
  | { type: "done";         content: { session_id: string; iterations: number } }
  | { type: "error";        content: string }
```

---

### Agent Harness API (`api/`)

FastAPI application. Exposes two HTTP routes:

- `GET /health` — liveness probe
- `POST /run` — accepts `{task, system_prompt?, max_iterations?}`, returns `text/event-stream`

The application object is created in `main.py`. All harness components are instantiated once at startup and shared across requests (the `AgentState` is created fresh per request).

---

### AgentState (`state.py`)

A `dataclasses.dataclass` that holds all mutable state for a single agent run.

| Field | Type | Description |
|---|---|---|
| `task` | `str` | The original user task |
| `system_prompt` | `str` | Optional caller-supplied system prompt |
| `session_id` | `str` | UUID, generated at construction |
| `messages` | `list[dict]` | Full conversation history (user / assistant / tool) |
| `plan` | `list[str]` | Numbered steps from the planner |
| `done` | `bool` | Set to `True` when the loop should terminate |
| `iteration` | `int` | Current loop count |
| `max_iterations` | `int` | Safety ceiling (default 20) |

Helper methods (`add_user`, `add_assistant`, `add_tool_results`) are the only sanctioned ways to append to `messages`.

---

### Agent (`agent_framework/agent.py`)

The central orchestrator. Constructor accepts:
- `tool_router: ToolRouter`
- `skill_manager: SkillManager` (optional)
- `memory: MemoryManager` (optional)
- `use_planner: bool` (default `True`)

**`Agent.stream(state)` — the executor loop:**

```
1.  Add task to messages as a user message
2.  Load skill context from SkillManager
3.  If use_planner: call planner → yield {type: "plan"}
4.  Build system prompt from: system_prompt + skill context + plan
5.  LOOP while not state.done and iteration < max_iterations:
      a. iteration += 1
      b. model_call(messages, system, tools, mode="executor")
      c. If response.output: yield {type: "text"}
      d. If response.tool_calls:
           yield {type: "tool_calls"}
           execute tools → yield {type: "tool_results"}
           add results to messages
      e. Append assistant output to messages
      f. memory.store(state)
      g. If response.final and no tool_calls: state.done = True
6.  yield {type: "done"}
```

---

### Planner (`agent_framework/planner.py`)

Makes a single model call in `mode="planner"` before the executor loop. The system prompt instructs the model to output only a numbered list of steps. Tools are not offered during planning.

The resulting steps are stored in `state.plan` and prepended to the executor system prompt so every turn is aware of the overall plan.

---

### Model Client (`agent_framework/model_client.py`)

Abstracts the two supported model backends behind a single `model_call()` function.

**Provider selection:** `MODEL_PROVIDER` environment variable (`"anthropic"` or `"azure"`).

| Provider | SDK | Auth env var |
|---|---|---|
| Anthropic | `anthropic` Python SDK | `ANTHROPIC_API_KEY` |
| Azure AI Foundry | `openai` Python SDK (`AsyncAzureOpenAI`) | `AZURE_OPENAI_API_KEY` + endpoint + deployment |

**`ModelResponse`** returned in both cases:
- `output: str` — text content
- `tool_calls: list[dict]` — `{id, name, input}` dicts
- `final: bool` — `True` when stop reason is not a tool call

Tool schemas are normalised to Anthropic format internally (`name`, `description`, `input_schema`) and translated to OpenAI function format for Azure calls.

---

### Skill Manager (`agent_framework/skill_manager.py`)

Scans `api/skills/` at startup. For each subdirectory:
1. Reads `SKILL.md` as the skill spec string.
2. Dynamically imports `skill.py` and instantiates the `Skill` class.

Results are cached in `_cache` after first discovery. The `load(task)` method returns all skill specs concatenated — they are injected wholesale into the system prompt. The `get_instance(name)` method returns the live `Skill` object for direct programmatic invocation.

**Skill file contract:**

```
skills/
└── <name>/
    ├── SKILL.md    # Plain-text spec; injected into system prompt
    └── skill.py    # Python class named `Skill` with a `run()` method
```

---

### Tool Router (`agent_framework/tool_router.py`)

An in-process registry of callable tools. Tools are registered with:
- A Python function (sync or async)
- A `description` string
- A JSON Schema `input_schema` dict

`list()` returns the tool manifest passed to the model. `execute(tool_calls)` dispatches each call, awaits async tools, and returns `{id, output}` results. Errors are caught per-tool and returned as error strings so one failed tool does not abort the run.

---

### Memory Manager (`agent_framework/memory.py`)

Two-tier storage:

| Tier | Backend | What is stored |
|---|---|---|
| Session | In-process `dict` keyed by `session_id` | `{task, iteration, plan, message_count}` summary |
| Vector | ChromaDB in-process client (`agent_memory` collection) | Last message text per turn, with `session_id` and `role` metadata |

`store(state)` is called after every executor turn. `recall(query, n)` performs a similarity search against the vector collection and returns up to `n` matching document strings.

ChromaDB initialisation is wrapped in a try/except — if it fails (e.g., missing package), the memory manager silently degrades to session-only mode.

---

### Tool Registry (`api/tools/`)

| Tool | File | Backend |
|---|---|---|
| `web_search` | `web_search.py` | Tavily API or Bing Search API (switchable via `SEARCH_PROVIDER`) |
| `azure_function` | `azure_function.py` | HTTP `GET` or `POST` to any Azure Function URL |
| `mcp_call` | `mcp_client.py` | JSON-RPC `tools/call` to any MCP server |
| `read_file` | `file_rw.py` | `Path.read_text()` |
| `write_file` | `file_rw.py` | `Path.write_text()` with `mkdir -p` |

All registered in `tools/__init__.py` via `build_tool_router()`.

---

## Data flow — single request

```
Browser
  POST /run {task: "..."}
      │
      ▼
  FastAPI /run handler
      │ creates AgentState
      ▼
  Agent.stream(state)
      │
      ├─ SkillManager.load()      ← reads SKILL.md files (cached)
      │
      ├─ planner.plan()           ← model_call (planner mode, no tools)
      │   └─ yields {type:"plan"}
      │
      └─ LOOP ──────────────────────────────────────────────────────┐
           │                                                        │
           ├─ model_call (executor mode, tools offered)             │
           │   ├─ yields {type:"text"}        (if text in response) │
           │   └─ if tool_calls:                                    │
           │       ├─ yields {type:"tool_calls"}                    │
           │       ├─ ToolRouter.execute()                          │
           │       └─ yields {type:"tool_results"}                  │
           │                                                        │
           ├─ MemoryManager.store()                                 │
           │                                                        │
           └─ if final & no tool calls → state.done = True ────────┘
                                              │
                                    yields {type:"done"}
                                              │
                                    SSE stream closed
```

Each `yield` in `Agent.stream()` is serialised to `data: <json>\n\n` by the FastAPI handler and pushed to the browser, where `useAgentStream` parses and appends it to the event list.

---

## Sequence diagram

```
Browser          FastAPI          Agent        Planner      Model       Tools
   │                │               │              │           │           │
   ├─ POST /run ───►│               │              │           │           │
   │                ├─ stream() ───►│              │           │           │
   │                │               ├─ plan() ────►│           │           │
   │                │               │              ├─ call ───►│           │
   │                │               │              │◄── resp ──┤           │
   │◄── plan ───────┤◄──────────────┤              │           │           │
   │                │               │                          │           │
   │                │               ├─────────── call ────────►│           │
   │                │               │◄────────── resp ─────────┤           │
   │◄── text ───────┤◄──────────────┤                          │           │
   │◄── tool_calls ─┤◄──────────────┤                          │           │
   │                │               ├──────────────────── exec ►──────────►│
   │                │               │◄──────────────────── res ◄───────────┤
   │◄── tool_results┤◄──────────────┤                          │           │
   │                │               │                          │           │
   │                │               ├─────────── call ────────►│           │
   │                │               │◄────────── resp ─────────┤           │
   │◄── text ───────┤◄──────────────┤                          │           │
   │◄── done ───────┤◄──────────────┤                          │           │
```
