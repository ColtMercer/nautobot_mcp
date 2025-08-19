"""MCP client for discovering servers and executing tools."""

import json
import os
from datetime import datetime
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
        self.call_history = []
    
    def get_tools(self) -> Dict[str, Any]:
        """Get the list of available tools from the server."""
        try:
            response = requests.get(
                f"{self.server_url}/tools",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            # Record the API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "GET",
                "endpoint": f"{self.server_url}/tools",
                "request": {"headers": dict(self.headers)},
                "response": result,
                "status_code": response.status_code
            })
            
            return result
        except requests.exceptions.RequestException as e:
            error_result = {"error": str(e)}
            
            # Record the failed API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "GET",
                "endpoint": f"{self.server_url}/tools",
                "request": {"headers": dict(self.headers)},
                "response": error_result,
                "error": str(e)
            })
            
            return error_result
    
    def invoke_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on the server."""
        try:
            request_data = {"tool_name": tool_name, "args": args}
            response = requests.post(
                f"{self.server_url}/tools/invoke",
                json=request_data,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Record the API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "POST",
                "endpoint": f"{self.server_url}/tools/invoke",
                "request": {
                    "headers": dict(self.headers),
                    "body": request_data
                },
                "response": result,
                "status_code": response.status_code
            })
            
            return result
        except requests.exceptions.RequestException as e:
            error_result = {"error": str(e)}
            
            # Record the failed API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "POST",
                "endpoint": f"{self.server_url}/tools/invoke",
                "request": {
                    "headers": dict(self.headers),
                    "body": {"tool_name": tool_name, "args": args}
                },
                "response": error_result,
                "error": str(e)
            })
            
            return error_result
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the server."""
        try:
            response = requests.get(
                f"{self.server_url}/healthz",
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            
            # Record the API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "GET",
                "endpoint": f"{self.server_url}/healthz",
                "request": {"headers": dict(self.headers)},
                "response": result,
                "status_code": response.status_code
            })
            
            return result
        except requests.exceptions.RequestException as e:
            error_result = {"error": str(e)}
            
            # Record the failed API call
            self.call_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "GET",
                "endpoint": f"{self.server_url}/healthz",
                "request": {"headers": dict(self.headers)},
                "response": error_result,
                "error": str(e)
            })
            
            return error_result
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get the API call history."""
        return self.call_history.copy()
    
    def get_context_window(self) -> Dict[str, Any]:
        """Get the context window information (tool catalogs)."""
        try:
            tools_response = requests.get(
                f"{self.server_url}/tools",
                headers=self.headers,
                timeout=10
            )
            tools_response.raise_for_status()
            tools_data = tools_response.json()
            
            return {
                "server_url": self.server_url,
                "timestamp": datetime.now().isoformat(),
                "tools": tools_data.get("tools", []),
                "context_summary": {
                    "total_tools": len(tools_data.get("tools", [])),
                    "tool_names": [tool.get("name", "Unknown") for tool in tools_data.get("tools", [])]
                }
            }
        except requests.exceptions.RequestException as e:
            return {
                "server_url": self.server_url,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "tools": [],
                "context_summary": {
                    "total_tools": 0,
                    "tool_names": []
                }
            }


# Global client instances for tracking
_clients = {}

def get_server_catalogs() -> Dict[str, Any]:
    """Get tool catalogs from all configured MCP servers."""
    catalogs = {}
    
    for server_config in MCP_SERVERS:
        server_name = server_config["name"]
        server_url = server_config["url"]
        
        # Create or get existing client
        if server_name not in _clients:
            _clients[server_name] = MCPClient(server_url)
        
        client = _clients[server_name]
        catalog = client.get_tools()
        catalogs[server_name] = catalog
    
    return catalogs


def invoke_tool_on_server(server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool on a specific server."""
    server_config = next((s for s in MCP_SERVERS if s["name"] == server_name), None)
    
    if not server_config:
        return {"error": f"Server '{server_name}' not found"}
    
    # Create or get existing client
    if server_name not in _clients:
        _clients[server_name] = MCPClient(server_config["url"])
    
    client = _clients[server_name]
    return client.invoke_tool(tool_name, args)


def get_api_call_history(server_name: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get API call history for all servers or a specific server."""
    if server_name:
        if server_name in _clients:
            return {server_name: _clients[server_name].get_call_history()}
        return {}
    
    history = {}
    for name, client in _clients.items():
        history[name] = client.get_call_history()
    return history


def get_context_windows() -> Dict[str, Dict[str, Any]]:
    """Get context window information for all servers."""
    context_windows = {}
    
    for server_config in MCP_SERVERS:
        server_name = server_config["name"]
        server_url = server_config["url"]
        
        # Create or get existing client
        if server_name not in _clients:
            _clients[server_name] = MCPClient(server_url)
        
        client = _clients[server_name]
        context_windows[server_name] = client.get_context_window()
    
    return context_windows
