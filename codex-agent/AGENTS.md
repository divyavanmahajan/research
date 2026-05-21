# AGENTS.md — Codex Agent

Instructions for AI agents executing tasks through this harness.

## What you are

You are an agent running inside the Codex Agent harness. Each request gives you a `task` string, an optional `system_prompt`, and up to `max_iterations` (default 20) turns to complete it.

Before the executor loop starts, a **planner** step produces a numbered list of steps. That plan is included in your system prompt for every executor turn.

## Execution model

Each turn of the loop:
1. You receive the full conversation history plus your system prompt (skill context + plan).
2. You may respond with text, request tool calls, or both.
3. If you request tools, they are executed and their results are appended as `tool` messages.
4. The loop continues until you produce a response with no tool calls and `stop_reason` is not `tool_use` (`finish_reason != "tool_calls"` for Azure).
5. The loop also stops after `max_iterations` turns.

Signal that you are finished by producing a final text response with no further tool calls.

## Available tools

### `web_search`
Search the web via Tavily or Bing.
```json
{ "query": "string" }
```
Returns a JSON array of `{title, url, snippet}` objects (up to 5 results).

### `azure_function`
Call an Azure Function endpoint.
```json
{
  "url": "string",
  "payload": { "optional": "object" },
  "method": "GET | POST"
}
```
Returns the response body as a string.

### `mcp_call`
Invoke a tool on an MCP (Model Context Protocol) server using JSON-RPC.
```json
{
  "server_url": "string",
  "tool_name": "string",
  "arguments": { "optional": "object" }
}
```
Returns the text content blocks from the MCP response.

### `read_file`
Read a local file.
```json
{ "path": "string" }
```
Returns the full text content of the file.

### `write_file`
Write or overwrite a local file (creates parent directories).
```json
{ "path": "string", "content": "string" }
```
Returns a confirmation string with byte count and path.

## Skill context

Every skill in `api/skills/*/SKILL.md` is injected into your system prompt. Skills describe domain-specific workflows and tell you when and how to use available tools for particular problem types. Read them before planning.

## Memory

After each turn, the harness stores a summary of your session state and the last message into a ChromaDB vector collection (`agent_memory`). You cannot query memory directly — it exists to give future sessions context about past work. Write clear, informative final responses that are worth storing.

## Guidelines

- **Follow the plan** — the planner step exists to break the task into manageable steps. Work through them in order unless you discover a reason to deviate.
- **Use tools for facts** — do not fabricate URLs, file contents, or API responses. Use `web_search` or `read_file` instead.
- **One tool at a time** — the harness executes all tool calls in a single turn sequentially. Request only the tools you need for the current step.
- **Be concise in tool inputs** — search queries should be specific; file paths should be absolute or clearly relative to the working directory.
- **Terminate cleanly** — when the task is complete, produce a final text response summarising what was done. Do not call further tools unless the summary itself reveals a gap.
- **Respect iteration limits** — if you are approaching `max_iterations`, produce your best available answer rather than requesting more tool calls.
- **Never invent tool results** — if a tool returns an error, report it honestly and try an alternative approach or explain to the user what is needed to proceed.
