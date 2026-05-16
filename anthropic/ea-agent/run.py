"""
Enterprise Architecture Research Agent — CLI entry point.

Local mode (default):
    python run.py "Cloud Migration Strategy"
    python run.py "Zero Trust Security" --format html
    python run.py "API Gateway Selection" --format docx --output report.docx
    python run.py "Kubernetes vs ECS" --model claude-opus-4-7

Managed agents mode (requires setup_agent.py to have been run first):
    python run.py "Cloud Migration Strategy" --mode managed
    python run.py "Zero Trust Security" --mode managed --format html

One-time setup for managed mode:
    python setup_agent.py

Environment variables:
    ANTHROPIC_API_KEY   Required
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow running as a script: `python run.py` or `python anthropic/ea-agent/run.py`
sys.path.insert(0, str(Path(__file__).parent))


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
        prog="ea-agent",
        description="Enterprise Architecture Research Agent (Anthropic SDK).",
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
        help="Output file path (auto-generated under ea-agent/output/ if omitted)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-opus-4-7",
        help="Anthropic model ID (default: claude-opus-4-7)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "managed"],
        default="local",
        help="Execution mode: local tool runner or Anthropic Managed Agents (default: local)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Stream agent message chunks to stdout (managed mode only)",
    )

    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or _auto_output_path(args.topic, args.format)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*62}")
    print("  Enterprise Architecture Research Agent (Anthropic SDK)")
    print(f"{'='*62}")
    print(f"  Topic  : {args.topic}")
    print(f"  Format : {args.format.upper()}")
    print(f"  Mode   : {args.mode}")
    print(f"  Model  : {args.model}")
    print(f"  Output : {output_path}")
    print(f"{'='*62}\n")

    print("Starting research... (this may take several minutes)\n")

    try:
        if args.mode == "local":
            from agent_local import run_local
            run_local(
                topic=args.topic,
                output_format=args.format,
                output_path=output_path,
                model_id=args.model,
            )
        else:
            from agent_managed import run_managed
            run_managed(
                topic=args.topic,
                output_format=args.format,
                output_path=output_path,
                verbose=args.verbose,
            )
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n{e}", file=sys.stderr)
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
