"""LLM chat tool that can call other MCP tools and emit citations."""

import json
import re
from typing import Any, Dict, List

import structlog

from .prefixes import get_prefixes_by_location

logger = structlog.get_logger(__name__)


def llm_chat(message: str, **kwargs) -> Dict[str, Any]:
    """LLM assistant that can call other MCP tools and records citations.
    
    Args:
        message: The user's message
        **kwargs: Additional parameters
        
    Returns:
        Dictionary with answer and citations
    """
    logger.info("Processing LLM chat message", message=message[:100] + "..." if len(message) > 100 else message)
    
    citations: List[Dict[str, Any]] = []
    answer = ""
    
    # Simple keyword-based routing for now
    # In a real implementation, this would use an actual LLM for planning
    
    if "prefix" in message.lower() and "location" in message.lower():
        # Extract location name from message
        location_match = re.search(r'(?:at|in|for)\s+([A-Za-z0-9\-]+)', message, re.IGNORECASE)
        if location_match:
            location_name = location_match.group(1)
        else:
            # Default location if none found
            location_name = "HQ-Dallas"
            
        try:
            # Call the prefixes tool
            prefixes = get_prefixes_by_location(location_name)
            
            # Record the citation
            citations.append({
                "tool": "get_prefixes_by_location",
                "args": {"location_name": location_name},
                "result_count": len(prefixes),
                "result_summary": f"Found {len(prefixes)} prefixes"
            })
            
            # Generate response
            if prefixes:
                prefix_list = [p["prefix"] for p in prefixes[:5]]  # Show first 5
                answer = f"Found {len(prefixes)} prefixes at {location_name}. "
                if len(prefixes) <= 5:
                    answer += f"All prefixes: {', '.join(prefix_list)}"
                else:
                    answer += f"First 5 prefixes: {', '.join(prefix_list)}... (and {len(prefixes) - 5} more)"
            else:
                answer = f"No prefixes found at {location_name}."
                
        except Exception as e:
            logger.error("Failed to get prefixes in LLM chat", location=location_name, error=str(e))
            answer = f"Sorry, I encountered an error while looking up prefixes for {location_name}: {e}"
            citations.append({
                "tool": "get_prefixes_by_location",
                "args": {"location_name": location_name},
                "error": str(e)
            })
    
    elif "help" in message.lower() or "what can you do" in message.lower():
        answer = """I can help you with Nautobot network information! Here are some things I can do:

1. **Find prefixes by location**: Ask me "What prefixes exist at HQ-Dallas?" or "Show me prefixes at LAB-Austin"
2. **Network information**: I can query Nautobot for network data and provide insights

Just ask me about prefixes at a specific location and I'll look it up for you!"""
    
    else:
        answer = """I'm an AI assistant that can help you with Nautobot network information. 

To get started, try asking me about prefixes at a specific location, such as:
- "What prefixes exist at HQ-Dallas?"
- "Show me prefixes at LAB-Austin"
- "Find prefixes for HQ-London"

I can call Nautobot tools to get real network data for you!"""
    
    logger.info("LLM chat response generated", answer_length=len(answer), citations_count=len(citations))
    
    return {
        "answer": answer,
        "citations": citations
    }
