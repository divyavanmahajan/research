#!/usr/bin/env python3
"""
run_tests.py — Agentic SQL generation benchmark.

Architecture:
  1. SQL Generator Agent  — has a `get_table_documentation` tool; autonomously
     fetches the table .md files it needs, then generates SQL.
  2. Judge Agent          — receives (question, expected_sql, generated_sql)
     and returns {"match": true/false, "reason": "..."}.
  3. Agentic loop (max N attempts): if judge says no-match, the generator gets
     the judge's reason as feedback and tries again.

Observability: arize-phoenix via OpenTelemetry.
  • Start Phoenix locally:  python -m phoenix.server.main serve
  • Or set PHOENIX_API_KEY  for Phoenix Cloud.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import yaml
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import SimpleSpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from phoenix.otel import register
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Token tracking — a thin span exporter that maps trace IDs → per-test tokens
# ─────────────────────────────────────────────────────────────────────────────

_token_data: dict[str, dict[str, int]] = {}   # test_id → {prompt, completion}
_trace_test_map: dict[str, str] = {}           # trace_id (hex) → test_id


class _TokenCollector(SpanExporter):
    """Collects LLM token counts from OpenInference spans for per-test summaries."""

    def export(self, spans) -> SpanExportResult:
        for span in spans:
            attrs = dict(span.attributes or {})
            prompt_tokens = int(attrs.get("llm.token_count.prompt", 0) or 0)
            completion_tokens = int(attrs.get("llm.token_count.completion", 0) or 0)
            if not (prompt_tokens + completion_tokens):
                continue
            trace_hex = f"{span.context.trace_id:032x}"
            test_id = _trace_test_map.get(trace_hex)
            if test_id:
                bucket = _token_data.setdefault(test_id, {"prompt": 0, "completion": 0})
                bucket["prompt"] += prompt_tokens
                bucket["completion"] += completion_tokens
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    category: str
    difficulty: str
    question: str
    expected_sql: str
    tables_needed: list[str]


@dataclass
class TestResult:
    test: TestCase
    passed: bool
    attempts: int
    generated_sql: str = ""
    final_reason: str = ""
    error: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Config loading
# ─────────────────────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_tests(config: dict, config_dir: Path) -> list[TestCase]:
    tests_path = config_dir / config["paths"]["test_definitions"]
    with open(tests_path) as f:
        raw = yaml.safe_load(f)
    return [
        TestCase(
            id=t["id"],
            category=t["category"],
            difficulty=t["difficulty"],
            question=t["question"],
            expected_sql=t["expected_sql"].strip(),
            tables_needed=t.get("tables_needed", []),
        )
        for t in raw["tests"]
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Agent client factory
# ─────────────────────────────────────────────────────────────────────────────

def _make_client(provider: str, provider_cfg: dict):
    """Return the appropriate agent-framework chat client for the given provider."""
    if provider == "openai":
        try:
            from agent_framework.openai import OpenAIChatCompletionClient
        except ImportError:
            sys.exit("Run: pip install agent-framework-openai")
        return OpenAIChatCompletionClient(
            model=provider_cfg.get("model", "gpt-4o-mini"),
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    elif provider == "azure_openai":
        try:
            from agent_framework.openai import OpenAIChatCompletionClient
            from azure.identity import AzureCliCredential, DefaultAzureCredential
        except ImportError:
            sys.exit("Run: pip install agent-framework-openai azure-identity")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        kwargs: dict[str, Any] = dict(
            model=provider_cfg.get("model", "gpt-4o-mini"),
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=provider_cfg.get("api_version", os.environ.get("AZURE_OPENAI_API_VERSION")),
        )
        if api_key:
            kwargs["api_key"] = api_key
        else:
            kwargs["credential"] = AzureCliCredential()
        return OpenAIChatCompletionClient(**kwargs)

    elif provider == "anthropic":
        try:
            from agent_framework.anthropic import AnthropicClient
        except ImportError:
            sys.exit("Run: pip install agent-framework-anthropic")
        return AnthropicClient(
            model=provider_cfg.get("model", "claude-haiku-4-5-20251001"),
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

    elif provider == "ollama":
        try:
            from agent_framework.ollama import OllamaChatClient
        except ImportError:
            sys.exit("Run: pip install agent-framework-ollama")
        return OllamaChatClient(
            model=provider_cfg.get("model", "llama3.2"),
            host=provider_cfg.get("host", "http://localhost:11434"),
        )

    else:
        sys.exit(f"Unknown provider: {provider!r}. Choose from: openai, azure_openai, anthropic, ollama")


# ─────────────────────────────────────────────────────────────────────────────
# Tool: table documentation retrieval (given to the SQL Generator agent)
# ─────────────────────────────────────────────────────────────────────────────

def make_table_doc_tool(tables_dir: Path):
    """Create a tool closure that reads table .md files from the model directory."""
    from typing import Annotated
    from agent_framework import tool

    @tool
    def get_table_documentation(
        table_full_name: Annotated[str, "Full table name in catalog.schema.table format, e.g. main.sales.orders"]
    ) -> str:
        """
        Get complete column-level documentation for a specific table.
        Call this for each table you plan to use before writing the SQL.
        Returns markdown with columns, types, descriptions, and join examples.
        """
        parts = table_full_name.strip().split(".")
        if len(parts) != 3:
            return f"Error: expected catalog.schema.table, got {table_full_name!r}"
        _, schema, table = parts
        md_path = tables_dir / schema / f"{table}.md"
        if not md_path.exists():
            return f"Error: no documentation found for {table_full_name}. Check the catalog index."
        return md_path.read_text()

    return get_table_documentation


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────────────────────────────────

def build_generator_system(catalog_index_text: str) -> str:
    return f"""You are an expert Databricks SQL engineer. You generate precise Spark SQL queries
based on natural language questions.

RULES:
- Always use the full catalog.schema.table name (e.g. main.sales.orders), never bare table names.
- Use ANSI SQL compatible with Databricks / Spark SQL.
- Before writing SQL, call get_table_documentation for EACH table you plan to use.
- Output ONLY the SQL query — no explanation, no markdown fences, no preamble.
- For date arithmetic use ADD_MONTHS, DATE_ADD, or INTERVAL syntax.
- For window functions use standard OVER(...) syntax.

CATALOG OVERVIEW (use this to identify relevant tables):
{catalog_index_text}"""


def build_generator_prompt(question: str, feedback: str | None) -> str:
    prompt = f"Question: {question}\n\nFetch documentation for the tables you need, then write the SQL query."
    if feedback:
        prompt += f"\n\nPrevious attempt was incorrect. Judge feedback: {feedback}\n\nPlease fix the SQL and try again."
    return prompt


JUDGE_SYSTEM = """You are a SQL correctness judge. You compare a generated SQL query against
an expected (reference) SQL query for semantic equivalence.

Two queries are a MATCH if they would produce the same result set (allow for:
- different column aliases
- different but equivalent JOIN styles (explicit vs implicit)
- different but equivalent WHERE/HAVING clauses
- different but equivalent ORDER BY when result is deterministic either way
- minor whitespace/formatting differences)

Two queries are NOT a MATCH if they:
- query different tables
- apply wrong filters or miss required filters
- use wrong aggregation logic
- return structurally different columns
- miss a required JOIN

Respond with ONLY valid JSON: {"match": true, "reason": "brief explanation"}"""


def build_judge_prompt(question: str, expected_sql: str, generated_sql: str) -> str:
    return (
        f"Question: {question}\n\n"
        f"Expected SQL:\n{expected_sql}\n\n"
        f"Generated SQL:\n{generated_sql}\n\n"
        "Are these semantically equivalent? Reply with JSON only."
    )


# ─────────────────────────────────────────────────────────────────────────────
# SQL extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_sql(text: str) -> str:
    """Strip markdown fences and extraneous text; return the SQL portion."""
    text = text.strip()
    # Remove ```sql ... ``` or ``` ... ``` fences
    fenced = re.search(r"```(?:sql)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    # If it starts with SELECT/WITH/INSERT, take from there
    match = re.search(r"((?:WITH|SELECT|INSERT|UPDATE|DELETE)\b.*)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def parse_judgment(text: str) -> dict:
    """Extract the JSON judgment from the judge's response."""
    text = text.strip()
    # Try to find JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    # Fallback: look for yes/no keywords
    lower = text.lower()
    if "\"match\": true" in lower or "match: true" in lower:
        return {"match": True, "reason": text}
    if "\"match\": false" in lower or "match: false" in lower:
        return {"match": False, "reason": text}
    # Last resort
    return {"match": False, "reason": f"Could not parse judgment: {text[:200]}"}


# ─────────────────────────────────────────────────────────────────────────────
# Core: run one test case
# ─────────────────────────────────────────────────────────────────────────────

async def run_test(
    test: TestCase,
    sql_agent,
    judge_agent,
    tracer,
    max_attempts: int,
) -> TestResult:
    with tracer.start_as_current_span(
        f"test.{test.id}",
        attributes={
            "test.id": test.id,
            "test.category": test.category,
            "test.difficulty": test.difficulty,
            "test.question": test.question,
        },
    ) as root_span:
        # Register this trace so the token collector can map spans to this test
        trace_hex = f"{root_span.context.trace_id:032x}"
        _trace_test_map[trace_hex] = test.id

        generated_sql = ""
        feedback: str | None = None

        for attempt in range(1, max_attempts + 1):
            # ── SQL Generation ──────────────────────────────────────────────
            with tracer.start_as_current_span(
                "generate_sql",
                attributes={"test.id": test.id, "attempt": attempt},
            ) as gen_span:
                try:
                    prompt = build_generator_prompt(test.question, feedback)
                    result = await sql_agent.run(prompt)
                    generated_sql = extract_sql(result.text if hasattr(result, "text") else str(result))
                    gen_span.set_attribute("generated_sql", generated_sql)
                except Exception as exc:
                    gen_span.set_attribute("error", str(exc))
                    return TestResult(
                        test=test,
                        passed=False,
                        attempts=attempt,
                        error=str(exc),
                    )

            # ── Judge ───────────────────────────────────────────────────────
            with tracer.start_as_current_span(
                "judge_sql",
                attributes={"test.id": test.id, "attempt": attempt},
            ) as judge_span:
                try:
                    judge_prompt = build_judge_prompt(test.question, test.expected_sql, generated_sql)
                    judge_result = await judge_agent.run(judge_prompt)
                    judgment = parse_judgment(
                        judge_result.text if hasattr(judge_result, "text") else str(judge_result)
                    )
                    judge_span.set_attribute("match", bool(judgment.get("match", False)))
                    judge_span.set_attribute("reason", judgment.get("reason", ""))
                except Exception as exc:
                    judge_span.set_attribute("error", str(exc))
                    judgment = {"match": False, "reason": f"Judge error: {exc}"}

            if judgment.get("match"):
                root_span.set_attribute("result", "pass")
                root_span.set_attribute("attempts", attempt)
                return TestResult(
                    test=test,
                    passed=True,
                    attempts=attempt,
                    generated_sql=generated_sql,
                    final_reason=judgment.get("reason", ""),
                )

            # Feed the judge's reason back into the next generation attempt
            feedback = judgment.get("reason", "The query was incorrect.")

        root_span.set_attribute("result", "fail")
        root_span.set_attribute("attempts", max_attempts)
        return TestResult(
            test=test,
            passed=False,
            attempts=max_attempts,
            generated_sql=generated_sql,
            final_reason=feedback or "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Summary printing
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: list[TestResult]) -> None:
    # Per-category aggregation
    cat_totals: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "passed": 0,
        "prompt_tokens": 0, "completion_tokens": 0,
    })
    for r in results:
        cat = r.test.category
        cat_totals[cat]["total"] += 1
        if r.passed:
            cat_totals[cat]["passed"] += 1
        tokens = _token_data.get(r.test.id, {})
        cat_totals[cat]["prompt_tokens"] += tokens.get("prompt", 0)
        cat_totals[cat]["completion_tokens"] += tokens.get("completion", 0)

    # Category table
    console.print("\n")
    table = Table(title="Test Results by Category", show_lines=True)
    table.add_column("Category", style="bold cyan")
    table.add_column("Pass / Total", justify="center")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")

    grand = {"total": 0, "passed": 0, "prompt": 0, "completion": 0}
    for cat in sorted(cat_totals):
        d = cat_totals[cat]
        rate = d["passed"] / d["total"] * 100 if d["total"] else 0
        style = "green" if rate == 100 else "yellow" if rate >= 50 else "red"
        total_tok = d["prompt_tokens"] + d["completion_tokens"]
        table.add_row(
            cat,
            f"{d['passed']} / {d['total']}",
            f"[{style}]{rate:.0f}%[/{style}]",
            f"{d['prompt_tokens']:,}",
            f"{d['completion_tokens']:,}",
            f"{total_tok:,}",
        )
        grand["total"] += d["total"]
        grand["passed"] += d["passed"]
        grand["prompt"] += d["prompt_tokens"]
        grand["completion"] += d["completion_tokens"]

    overall_rate = grand["passed"] / grand["total"] * 100 if grand["total"] else 0
    style = "green" if overall_rate >= 80 else "yellow" if overall_rate >= 50 else "red"
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{grand['passed']} / {grand['total']}[/bold]",
        f"[bold][{style}]{overall_rate:.0f}%[/{style}][/bold]",
        f"[bold]{grand['prompt']:,}[/bold]",
        f"[bold]{grand['completion']:,}[/bold]",
        f"[bold]{grand['prompt'] + grand['completion']:,}[/bold]",
    )
    console.print(table)

    # Failed tests detail
    failed = [r for r in results if not r.passed]
    if failed:
        console.print(f"\n[red]Failed tests ({len(failed)}):[/red]")
        for r in failed:
            console.print(f"  [dim]{r.test.id}[/dim] [{r.test.category}] {r.test.question[:80]}")
            if r.error:
                console.print(f"    [red]Error:[/red] {r.error}")
            elif r.final_reason:
                console.print(f"    [yellow]Judge:[/yellow] {r.final_reason[:120]}")


def save_results(results: list[TestResult], output_path: Path) -> None:
    data = []
    for r in results:
        tokens = _token_data.get(r.test.id, {})
        data.append({
            "id": r.test.id,
            "category": r.test.category,
            "difficulty": r.test.difficulty,
            "question": r.test.question,
            "passed": r.passed,
            "attempts": r.attempts,
            "generated_sql": r.generated_sql,
            "expected_sql": r.test.expected_sql,
            "final_reason": r.final_reason,
            "error": r.error,
            "tokens": tokens,
        })
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(f"\nDetailed results saved to [bold]{output_path}[/bold]")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--config", default="config.yaml", type=click.Path(exists=True),
              help="Path to config.yaml")
@click.option("--provider", default=None,
              help="Override provider from config (openai|azure_openai|anthropic|ollama)")
@click.option("--model", default=None,
              help="Override model name from config")
@click.option("--category", "category_filter", multiple=True,
              help="Run only these categories (repeat for multiple)")
@click.option("--test-id", "test_id_filter", multiple=True,
              help="Run only these test IDs (e.g. ss_001 jn_003)")
@click.option("--max-attempts", default=None, type=int,
              help="Override max retry attempts from config")
@click.option("--no-phoenix", is_flag=True,
              help="Disable Phoenix OTEL (useful for quick local runs)")
def main(
    config: str,
    provider: str | None,
    model: str | None,
    category_filter: tuple,
    test_id_filter: tuple,
    max_attempts: int | None,
    no_phoenix: bool,
) -> None:
    """Run SQL generation tests against a semantic model using the Microsoft Agent Framework."""
    asyncio.run(_run(config, provider, model, category_filter, test_id_filter, max_attempts, no_phoenix))


async def _run(
    config_path: str,
    provider_override: str | None,
    model_override: str | None,
    category_filter: tuple,
    test_id_filter: tuple,
    max_attempts_override: int | None,
    no_phoenix: bool,
) -> None:
    cfg_path = Path(config_path).resolve()
    cfg = load_config(cfg_path)
    cfg_dir = cfg_path.parent

    # ── Apply overrides ───────────────────────────────────────────────────────
    active_provider = provider_override or cfg.get("provider", "openai")
    max_attempts = max_attempts_override or cfg.get("max_attempts", 3)

    provider_cfg = cfg.get("providers", {}).get(active_provider, {})
    if model_override:
        provider_cfg = dict(provider_cfg)
        provider_cfg["model"] = model_override

    judge_cfg_raw = cfg.get("judge", {})
    judge_provider = judge_cfg_raw.get("provider", active_provider)
    judge_provider_cfg = cfg.get("providers", {}).get(judge_provider, {})
    if judge_cfg_raw.get("model"):
        judge_provider_cfg = dict(judge_provider_cfg)
        judge_provider_cfg["model"] = judge_cfg_raw["model"]

    # ── Phoenix / OTEL setup ──────────────────────────────────────────────────
    token_collector = _TokenCollector()
    if no_phoenix:
        from opentelemetry.sdk.trace import TracerProvider as _TP
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor as _SSP
        tp = _TP()
        tp.add_span_processor(_SSP(token_collector))
        trace.set_tracer_provider(tp)
        console.print("[dim]Phoenix OTEL disabled.[/dim]")
    else:
        phoenix_cfg = cfg.get("phoenix", {})
        tp = register(
            project_name=phoenix_cfg.get("project_name", "sql-semantic-model-test"),
            endpoint=phoenix_cfg.get("endpoint", "http://localhost:6006") + "/v1/traces",
            auto_instrument=True,
            batch=True,
        )
        # Add our token collector alongside the Phoenix exporter
        tp.add_span_processor(SimpleSpanProcessor(token_collector))
        console.print(
            f"[dim]Phoenix OTEL: {phoenix_cfg.get('endpoint', 'http://localhost:6006')} "
            f"project={phoenix_cfg.get('project_name', 'sql-semantic-model-test')}[/dim]"
        )
    tracer = trace.get_tracer("sql-test-runner")

    # ── Load catalog index ────────────────────────────────────────────────────
    catalog_index_path = cfg_dir / cfg["paths"]["catalog_index"]
    tables_dir = (cfg_dir / cfg["paths"]["tables_dir"]).resolve()
    catalog_index_text = catalog_index_path.read_text()

    # ── Load and filter tests ─────────────────────────────────────────────────
    all_tests = load_tests(cfg, cfg_dir)
    active_categories = list(category_filter) or cfg.get("categories") or []
    if active_categories:
        all_tests = [t for t in all_tests if t.category in active_categories]
    if test_id_filter:
        all_tests = [t for t in all_tests if t.id in test_id_filter]

    if not all_tests:
        console.print("[red]No tests matched the filter.[/red]")
        return

    # ── Build agents ──────────────────────────────────────────────────────────
    console.print(f"\n[bold]SQL Semantic Model Test Runner[/bold]")
    console.print(f"Provider : [cyan]{active_provider}[/cyan]  "
                  f"Model: [cyan]{provider_cfg.get('model', '?')}[/cyan]")
    console.print(f"Tests    : [cyan]{len(all_tests)}[/cyan]  "
                  f"Max attempts: [cyan]{max_attempts}[/cyan]")
    console.print(f"Judge    : [cyan]{judge_provider}/{judge_provider_cfg.get('model', '?')}[/cyan]\n")

    table_doc_tool = make_table_doc_tool(tables_dir)

    sql_client = _make_client(active_provider, provider_cfg)
    sql_agent = sql_client.as_agent(
        name="SQLGenerator",
        instructions=build_generator_system(catalog_index_text),
        tools=table_doc_tool,
    )

    judge_client = _make_client(judge_provider, judge_provider_cfg)
    judge_agent = judge_client.as_agent(
        name="SQLJudge",
        instructions=JUDGE_SYSTEM,
    )

    # ── Run tests ─────────────────────────────────────────────────────────────
    results: list[TestResult] = []
    verbose = cfg.get("output", {}).get("verbose", True)

    with tracer.start_as_current_span("test_suite"):
        for i, test in enumerate(all_tests, 1):
            status_prefix = f"[{i:02}/{len(all_tests):02}] [{test.category}/{test.difficulty}] {test.id}"
            if verbose:
                console.print(f"{status_prefix} … ", end="")

            result = await run_test(test, sql_agent, judge_agent, tracer, max_attempts)
            results.append(result)

            if verbose:
                if result.passed:
                    attempts_str = f"(attempt {result.attempts})" if result.attempts > 1 else ""
                    console.print(f"[green]PASS[/green] {attempts_str}")
                elif result.error:
                    console.print(f"[red]ERROR[/red] {result.error[:60]}")
                else:
                    console.print(f"[red]FAIL[/red] {result.final_reason[:80]}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(results)

    # ── Save results ──────────────────────────────────────────────────────────
    output_cfg = cfg.get("output", {})
    if output_cfg.get("results_file"):
        save_results(results, cfg_dir / output_cfg["results_file"])


if __name__ == "__main__":
    main()
