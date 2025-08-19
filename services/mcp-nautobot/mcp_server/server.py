"""FastMCP server for Nautobot integration."""

import os
from typing import Any, Dict, List

import structlog
from fastmcp.server import FastMCP
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import JSONResponse

from .tools.prefixes import get_prefixes_by_location
from .tools.llm_chat import llm_chat

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Create FastMCP server
server = FastMCP(
    name="nautobot-mcp-server",
    instructions="FastMCP server exposing Nautobot utilities as MCP tools",
    version="0.1.0"
)

# Create tools from existing functions
def get_prefixes_tool(location_name: str) -> List[Dict[str, Any]]:
    """Get all prefixes under a Nautobot Location by human-friendly name.
    
    Args:
        location_name: The name of the location (e.g., "HQ-Dallas", "LAB-Austin")
        
    Returns:
        List of prefix objects with prefix, status, role, description, and site information
    """
    return get_prefixes_by_location(location_name)

def llm_chat_tool(message: str) -> Dict[str, Any]:
    """LLM assistant that can call other MCP tools and returns citations.
    
    Args:
        message: The user's message
        
    Returns:
        Dictionary with answer and citations
    """
    return llm_chat(message)

# Create Tool instances
prefixes_tool = Tool.from_function(
    fn=get_prefixes_tool,
    name="get_prefixes_by_location",
    description="""Get all prefixes under a Nautobot Location by human-friendly name.

CRITICAL: When extracting the location name from user queries, NEVER use the word "prefixes" as a location name.

This tool understands various ways users might refer to locations:
- "site" = "location" (e.g., "site Branch Office 3")
- "office" = "location" (e.g., "office HQ-Dallas") 
- "branch" = "location" (e.g., "branch LAB-Austin")

Common location names include:
- HQ-Dallas, LAB-Austin
- Branch Office 1, Branch Office 2, Branch Office 3

EXTRACTION RULES:
1. When a user asks about prefixes at a location, extract ONLY the location name from their query
2. For multi-word locations like "Branch Office 3", use the full name as-is
3. NEVER extract words like "prefix", "prefixes", "what", "show", "find" as location names
4. Look for location names AFTER words like "at", "in", "for", "of"

Examples:
- User: "What prefixes are at site Branch Office 3?" → location_name: "Branch Office 3"
- User: "Show me prefixes at office HQ-Dallas" → location_name: "HQ-Dallas"
- User: "Find prefixes for branch LAB-Austin" → location_name: "LAB-Austin"
- User: "What prefixes are at location Branch Office 3?" → location_name: "Branch Office 3"

WRONG EXAMPLES (DO NOT DO):
- User: "What prefixes are at location Branch Office 3?" → location_name: "prefixes" ❌
- User: "Show me prefixes at Branch Office 3" → location_name: "prefixes" ❌"""
)

llm_chat_tool_instance = Tool.from_function(
    fn=llm_chat_tool,
    name="llm_chat",
    description="LLM assistant that can call other MCP tools and returns citations."
)

# Add tools to the server
server.add_tool(prefixes_tool)
server.add_tool(llm_chat_tool_instance)

# Add custom REST endpoints for chat UI compatibility
@server.custom_route("/tools", methods=["GET"])
async def get_tools(request: Request) -> JSONResponse:
    """Get list of available tools in REST format."""
    tools = []
    tools_dict = await server.get_tools()
    for tool in tools_dict.values():
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
            "output_schema": tool.output_schema
        })
    return JSONResponse({"tools": tools})

@server.custom_route("/tools/invoke", methods=["POST"])
async def invoke_tool(request: Request) -> JSONResponse:
    """Invoke a tool by name with arguments."""
    try:
        # Parse request body
        body = await request.json()
        tool_name = body.get("tool_name")
        args = body.get("args", {})
        
        if not tool_name:
            return JSONResponse({"error": "tool_name is required"}, status_code=400)
        
        # Get the tool
        tool = await server.get_tool(tool_name)
        if not tool:
            return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)
        
        # Call the tool function
        result = tool.fn(**args)
        
        return JSONResponse({"result": result})
    except Exception as e:
        logger.error("Error invoking tool", error=str(e))
        return JSONResponse({"error": str(e)}, status_code=500)

@server.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "nautobot-mcp-server"})

if __name__ == "__main__":
    # Get configuration from environment
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7000"))
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    # Run the FastMCP server
    server.run(
        transport="streamable-http",
        host=host,
        port=port
    )
