from typing import Optional

from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

from .prompts import EA_ORCHESTRATOR_PROMPT, EA_RESEARCHER_PROMPT
from .tools import web_search, fetch_page, think, make_write_report_tool

DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"


def create_ea_agent(
    output_format: str = "md",
    output_path: Optional[str] = None,
    model_id: str = DEFAULT_MODEL,
):
    """
    Create an Enterprise Architect research agent.

    Args:
        output_format: 'md', 'html', or 'docx'
        output_path: Path to save the output file
        model_id: LangChain model identifier, e.g. 'anthropic:claude-sonnet-4-6'

    Returns:
        Compiled LangGraph agent ready to invoke
    """
    model = init_chat_model(model_id, temperature=0.1)
    write_report = make_write_report_tool(output_format, output_path)

    researcher = {
        "name": "researcher",
        "description": (
            "Specialist research analyst. Searches the web and fetches pages to gather "
            "detailed, multi-source information on any topic. Returns structured findings "
            "covering key facts, industry trends, vendor landscape, standards, risks, and sources."
        ),
        "system_prompt": EA_RESEARCHER_PROMPT,
        "tools": [web_search, fetch_page, think],
    }

    agent = create_deep_agent(
        model=model,
        tools=[think, write_report],
        system_prompt=EA_ORCHESTRATOR_PROMPT,
        subagents=[researcher],
    )

    return agent
