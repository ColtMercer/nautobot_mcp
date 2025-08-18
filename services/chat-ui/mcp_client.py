"""MCP client for discovering servers and executing tools."""

import json
import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

MCP_SERVERS = json.loads(os.environ.get("MCP_SERVERS", "[]"))


class MCPClient:
    """Client for interacting with MCP servers."""
    
    def __init__(self, server_url: str, api_key: str = "dev-mcp-key"):
        """Initialize the MCP client."""
        self.server_url = server_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
    
    def get_tools(self) -> Dict[str, Any]:
        """Get the list of available tools from the server."""
        try:
            response = requests.get(
                f"{self.server_url}/tools",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def invoke_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on the server."""
        try:
            response = requests.post(
                f"{self.server_url}/tools/{tool_name}:invoke",
                json=args,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the server."""
        try:
            response = requests.get(
                f"{self.server_url}/healthz",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


def get_server_catalogs() -> Dict[str, Any]:
    """Get tool catalogs from all configured MCP servers."""
    catalogs = {}
    
    for server_config in MCP_SERVERS:
        server_name = server_config["name"]
        server_url = server_config["url"]
        
        client = MCPClient(server_url)
        catalog = client.get_tools()
        catalogs[server_name] = catalog
    
    return catalogs


def invoke_tool_on_server(server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool on a specific server."""
    server_config = next((s for s in MCP_SERVERS if s["name"] == server_name), None)
    
    if not server_config:
        return {"error": f"Server '{server_name}' not found"}
    
    client = MCPClient(server_config["url"])
    return client.invoke_tool(tool_name, args)
