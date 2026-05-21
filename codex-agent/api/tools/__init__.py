from agent_framework import ToolRouter

from .azure_function import call_azure_function
from .file_rw import read_file, write_file
from .mcp_client import mcp_call
from .web_search import web_search


def build_tool_router() -> ToolRouter:
    router = ToolRouter()

    router.register(
        web_search,
        description="Search the web for information.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    )
    router.register(
        call_azure_function,
        name="azure_function",
        description="Call an Azure Function by URL with an optional JSON payload.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "payload": {"type": "object"},
                "method": {"type": "string", "enum": ["GET", "POST"], "default": "POST"},
            },
            "required": ["url"],
        },
    )
    router.register(
        mcp_call,
        name="mcp_call",
        description="Invoke a tool on an MCP server.",
        input_schema={
            "type": "object",
            "properties": {
                "server_url": {"type": "string"},
                "tool_name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["server_url", "tool_name"],
        },
    )
    router.register(
        read_file,
        description="Read the contents of a local file.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    router.register(
        write_file,
        description="Write content to a local file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    )

    return router
