import re
import httpx
from markdownify import markdownify as md_convert
from langchain_core.tools import StructuredTool, tool


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information on a topic.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default 5)
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No search results found for: {query}"

        lines = [f"Search results for: '{query}'\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', 'No title')}")
            lines.append(f"URL: {r.get('href', '')}")
            lines.append(r.get('body', ''))
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def fetch_page(url: str) -> str:
    """
    Fetch the content of a webpage and return it as markdown text.

    Args:
        url: The URL of the webpage to fetch
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = httpx.get(url, timeout=15, follow_redirects=True, headers=headers)
        response.raise_for_status()

        content = md_convert(
            response.text,
            heading_style="ATX",
            strip=["script", "style", "nav", "footer", "header", "aside", "iframe"],
        )

        content = re.sub(r"\n{3,}", "\n\n", content)

        if len(content) > 6000:
            content = content[:6000] + "\n\n...[content truncated]"

        return content
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} error fetching {url}"
    except Exception as e:
        return f"Error fetching page: {str(e)}"


@tool
def think(thought: str) -> str:
    """
    Plan, reflect, and organise your thinking before acting.

    Use this tool to:
    - Identify research gaps and plan next searches
    - Evaluate whether gathered information is sufficient
    - Organise key findings into themes before writing
    - Decide which sources to fetch for more detail

    Args:
        thought: Your analytical thought, plan, or reflection
    """
    return "Thought recorded. Continue with your plan."


def make_write_report_tool(output_format: str, output_path: str) -> StructuredTool:
    """Factory that creates a write_report tool bound to a specific format and path."""
    from .formatters import save_document

    def _write_report(content: str) -> str:
        try:
            save_document(content, output_format, output_path)
            return f"Report successfully saved to: {output_path}"
        except Exception as e:
            return f"Error saving report: {str(e)}"

    return StructuredTool.from_function(
        func=_write_report,
        name="write_report",
        description=(
            "Save the completed enterprise architecture research report to a file. "
            "Call this tool ONCE with the FULL, COMPLETE report in markdown format. "
            "Pass the entire document — all 10 sections — in a single call. "
            "Do not truncate, summarise, or split the content."
        ),
    )
