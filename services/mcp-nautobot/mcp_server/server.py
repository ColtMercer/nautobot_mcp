"""FastMCP server for Nautobot integration."""

import os
from typing import Any, Dict, List

import structlog
from fastmcp.server import FastMCP
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import JSONResponse

from .tools.prefixes import (
    get_prefixes_by_location,
)
from .tools.devices import (
    get_devices_by_location,
    get_devices_by_location_and_role,
)

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
    instructions="FastMCP server exposing Nautobot GraphQL API as MCP tools",
    version="0.1.0"
)

# Create tools from existing functions
def get_prefixes_tool(location_name: str, format: str = "json") -> Dict[str, Any]:
    """Get prefixes by location name with multiple output formats.
    
    Args:
        location_name: The name of the location (e.g., "HQ-Dallas", "LAB-Austin")
        format: Output format - "json", "table", "dataframe", or "csv"
        
    Returns:
        Dictionary containing prefixes data in the requested format
    """
    return get_prefixes_by_location(location_name, format)

def get_devices_by_location_tool(location_name: str) -> Dict[str, Any]:
    """Get devices by location name.
    
    Args:
        location_name: The name of the location (e.g., "NY Data Center", "Campus A")
        
    Returns:
        Dictionary containing device data in JSON format
    """
    return get_devices_by_location(location_name)

def get_devices_by_location_and_role_tool(location_name: str, role_name: str) -> Dict[str, Any]:
    """Get devices by location and role.
    
    Args:
        location_name: The name of the location (e.g., "NY Data Center", "Campus A")
        role_name: The name of the device role (e.g., "WAN Router", "Access Switch")
        
    Returns:
        Dictionary containing device data in JSON format
    """
    return get_devices_by_location_and_role(location_name, role_name)

# Create Tool instances
prefixes_tool = Tool.from_function(
    fn=get_prefixes_tool,
    name="get_prefixes_by_location_enhanced",
    description="""Get prefixes by location. Returns raw JSON only (LLM handles formatting/analysis).

        Args:
            location_name: Name of the location (e.g., "Branch Office 3", "HQ-Dallas")
            format: Ignored. Always returns JSON.

        Returns:
            JSON object with fields: success, message, count, data (list of prefixes)
        """
)

devices_by_location_tool = Tool.from_function(
    fn=get_devices_by_location_tool,
    name="get_devices_by_location",
    description="""Get devices by location. Returns raw JSON only (LLM handles formatting/analysis).

        Args:
            location_name: Name of the location (e.g., "NY Data Center", "Campus A", "Branch Office 3")

        Returns:
            JSON object with fields: success, message, count, data (list of devices with name, status, role, device_type, platform, primary_ip4, location, description)
        """
)

devices_by_location_and_role_tool = Tool.from_function(
    fn=get_devices_by_location_and_role_tool,
    name="get_devices_by_location_and_role",
    description="""Get devices by location and role. Returns raw JSON only (LLM handles formatting/analysis).

        Args:
            location_name: Name of the location (e.g., "NY Data Center", "Campus A", "Branch Office 3")
            role_name: Name of the device role (e.g., "WAN Router", "Access Switch", "Core Switch", "Firewall")

        Returns:
            JSON object with fields: success, message, count, data (list of devices with name, status, role, device_type, platform, primary_ip4, location, description)
        """
)

# Add tools to the server
server.add_tool(prefixes_tool)
server.add_tool(devices_by_location_tool)
server.add_tool(devices_by_location_and_role_tool)

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
    port = int(os.environ.get("PORT", "7001"))
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    # Run the FastMCP server
    server.run(
        transport="streamable-http",
        host=host,
        port=port
    )
