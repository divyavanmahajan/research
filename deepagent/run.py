"""
Enterprise Architecture Research Agent — CLI entry point.

Usage:
    python -m deepagent.run "Cloud Migration Strategy" --format html
    python -m deepagent.run "Zero Trust Security Architecture" --format docx
    python -m deepagent.run "API Gateway Selection" --format md --output report.md
    python -m deepagent.run "Kubernetes vs ECS" --model anthropic:claude-opus-4-7

Environment variables:
    ANTHROPIC_API_KEY   Required for Anthropic models (default)
    OPENAI_API_KEY      Required for OpenAI models
"""

import argparse
import os
import sys
import re
from datetime import datetime
from pathlib import Path


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug[:60].strip("_")


def _auto_output_path(topic: str, fmt: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    slug = _slugify(topic)
    ext = fmt.lstrip(".")
    return str(Path(__file__).parent / "output" / f"{slug}_{timestamp}.{ext}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deepagent",
        description="Enterprise Architecture Research Agent — research a topic and produce an EA document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("topic", help="Topic to research (e.g. 'Cloud Migration Strategy')")
    parser.add_argument(
        "--format", "-f",
        choices=["md", "html", "docx"],
        default="md",
        help="Output document format (default: md)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (auto-generated under deepagent/output/ if omitted)",
    )
    parser.add_argument(
        "--model", "-m",
        default="anthropic:claude-sonnet-4-6",
        help="LangChain model ID (default: anthropic:claude-sonnet-4-6)",
    )

    args = parser.parse_args()

    output_path = args.output or _auto_output_path(args.topic, args.format)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Guard: check API key before wasting time
    if "anthropic" in args.model.lower() and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if "openai" in args.model.lower() and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*62}")
    print("  Enterprise Architecture Research Agent")
    print(f"{'='*62}")
    print(f"  Topic  : {args.topic}")
    print(f"  Format : {args.format.upper()}")
    print(f"  Output : {output_path}")
    print(f"  Model  : {args.model}")
    print(f"{'='*62}\n")

    from langchain_core.messages import HumanMessage
    from .agent import create_ea_agent

    agent = create_ea_agent(
        output_format=args.format,
        output_path=output_path,
        model_id=args.model,
    )

    prompt = (
        f"Research the following topic and produce a comprehensive Enterprise Architecture document.\n\n"
        f"TOPIC: {args.topic}\n\n"
        f"Steps:\n"
        f"1. Use the think tool to plan 4–6 research angles for this topic\n"
        f"2. Delegate research tasks to the researcher sub-agent — gather broad and deep coverage\n"
        f"3. Synthesise all findings into a complete EA document with all 10 required sections\n"
        f"4. Call write_report with the FULL document content (do not truncate or omit sections)\n\n"
        f"Output file: {output_path}"
    )

    print("Starting research... (this may take several minutes)\n")

    try:
        agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAgent error: {e}", file=sys.stderr)
        sys.exit(1)

    output = Path(output_path)
    if output.exists():
        size = output.stat().st_size
        print(f"\n{'='*62}")
        print(f"  Report complete!")
        print(f"  File : {output_path}")
        print(f"  Size : {size:,} bytes  ({size // 1024} KB)")
        print(f"{'='*62}\n")
    else:
        print(f"\nWarning: output file not found at {output_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
