"""FastMCP server for Nautobot integration."""

import os
from typing import Any, Dict

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

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

# Create FastAPI app
app = FastAPI(
    title="Nautobot MCP Server",
    description="FastMCP server exposing Nautobot utilities as MCP tools",
    version="0.1.0"
)

# Metrics (disabled for now due to conflicts)
# tool_calls_total = Counter('nautobot_mcp_tool_calls_total', 'Total number of MCP tool calls', ['tool_name', 'status'])
# tool_call_duration = Histogram('nautobot_mcp_tool_call_duration_seconds', 'Duration of MCP tool calls', ['tool_name'])

# API key for tool invocations
MCP_API_KEY = os.environ.get("MCP_API_KEY", "dev-mcp-key")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with correlation ID."""
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    logger.info("Request started", 
                method=request.method, 
                url=str(request.url), 
                correlation_id=correlation_id)
    
    response = await call_next(request)
    
    logger.info("Request completed", 
                method=request.method, 
                url=str(request.url), 
                status_code=response.status_code,
                correlation_id=correlation_id)
    
    return response


def require_api_key(request: Request):
    """Check for valid API key in request headers."""
    api_key = request.headers.get("X-API-Key")
    if api_key != MCP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "build_sha": os.environ.get("BUILD_SHA", "dev")
    }


@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    tools = [
        {
            "name": "get_prefixes_by_location",
            "description": "Return all prefixes under a Nautobot Location by human-friendly name.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location_name": {"type": "string"}
                },
                "required": ["location_name"]
            },
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "prefix": {"type": "string"},
                        "status": {"type": "string"},
                        "role": {"type": "string"},
                        "description": {"type": "string"},
                        "site": {"type": "string"}
                    }
                }
            }
        },
        {
            "name": "llm_chat",
            "description": "LLM assistant that can call other MCP tools and returns citations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                }
            }
        }
    ]
    
    return {"tools": tools}


@app.post("/tools/get_prefixes_by_location:invoke")
async def invoke_get_prefixes_by_location(request: Request):
    """Invoke the get_prefixes_by_location tool."""
    require_api_key(request)
    
    try:
        body = await request.json()
        location_name = body.get("location_name")
        
        if not location_name:
            raise HTTPException(status_code=400, detail="location_name is required")
        
        result = get_prefixes_by_location(location_name)
        return {"result": result}
        
    except Exception as e:
        logger.error("Tool invocation failed", tool="get_prefixes_by_location", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/llm_chat:invoke")
async def invoke_llm_chat(request: Request):
    """Invoke the llm_chat tool."""
    require_api_key(request)
    
    try:
        body = await request.json()
        message = body.get("message")
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        result = llm_chat(message)
        return {"result": result}
        
    except Exception as e:
        logger.error("Tool invocation failed", tool="llm_chat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return {"message": "Metrics disabled for now"}


if __name__ == "__main__":
    import uvicorn
    
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    uvicorn.run(
        "mcp_server.server:app",
        host="0.0.0.0",
        port=7000,
        log_level=log_level,
        access_log=True
    )
