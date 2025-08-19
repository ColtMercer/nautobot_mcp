"""LLM chat tool that can call other MCP tools and emit citations."""

import json
import re
from typing import Any, Dict, List

import structlog

from .prefixes import get_prefixes_by_location

logger = structlog.get_logger(__name__)


def extract_location_name(message: str) -> str:
    """Extract location name from user message using simple heuristics."""
    message_lower = message.lower()
    
    # Common location names to look for (including common typos)
    known_locations = [
        "hq-dallas", "lab-austin", "hq-london", "hq-sydney",
        "branch office 1", "branch office 2", "branch office 3", "branch ofice 3",  # Handle typo
        "data center 1", "data center 2", "campus a", "campus b"
    ]
    
    # First, try to find known location names in the message
    for location in known_locations:
        if location in message_lower:
            # Find the actual case from the original message
            location_pattern = re.compile(re.escape(location), re.IGNORECASE)
            match = location_pattern.search(message)
            if match:
                return match.group(0)
    
    # If no known location found, try to extract using patterns
    # Look for patterns like "at [location]" or "in [location]" or "for [location]"
    patterns = [
        r'(?:at|in|for)\s+([A-Za-z0-9\-\s]+?)(?:\s|$|\.|\?)',  # Multi-word locations
        r'(?:site|office|branch|location)\s+([A-Za-z0-9\-\s]+?)(?:\s|$|\.|\?)',  # After location keywords
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, message, re.IGNORECASE)
        for match in matches:
            location_name = match.strip()
            # Avoid extracting common non-location words
            if location_name.lower() not in ['prefixes', 'prefix', 'what', 'show', 'find', 'me', 'the', 'location']:
                return location_name
    
    # Default location if none found
    return "HQ-Dallas"


def llm_chat(message: str, **kwargs) -> Dict[str, Any]:
    """LLM assistant that can call other MCP tools and records citations.
    
    This tool is designed to be used by an LLM that has access to the full MCP tool catalog.
    The LLM should decide which tools to call based on the user's message.
    
    Args:
        message: The user's message
        
    Returns:
        Dictionary with answer and citations
    """
    logger.info("Processing LLM chat message", message=message[:100] + "..." if len(message) > 100 else message)
    
    citations: List[Dict[str, Any]] = []
    answer = ""
    
    # Simple tool calling logic - in a real implementation, this would be handled by an LLM
    # that has access to the full MCP tool catalog and can make intelligent decisions
    
    if "prefix" in message.lower():
        # Extract location name from message
        location_name = extract_location_name(message)
        
        logger.info("Extracted location name", location_name=location_name, original_message=message)
            
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

1. **Find prefixes by location**: Ask me "What prefixes exist at HQ-Dallas?" or "Show me prefixes at Branch Office 3"
2. **Network information**: I can query Nautobot for network data and provide insights

Just ask me about prefixes at a specific location and I'll look it up for you!"""
    
    else:
        answer = """I'm an AI assistant that can help you with Nautobot network information. 

To get started, try asking me about prefixes at a specific location, such as:
- "What prefixes exist at HQ-Dallas?"
- "Show me prefixes at Branch Office 3"
- "Find prefixes for LAB-Austin"

I can call Nautobot tools to get real network data for you!"""
    
    logger.info("LLM chat response generated", answer_length=len(answer), citations_count=len(citations))
    
    return {
        "answer": answer,
        "citations": citations
    }
