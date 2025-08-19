"""Prefix tools that return raw JSON data only (formatting/analysis handled by the LLM)."""

from typing import Any, Dict
import structlog

from ..clients.nautobot_graphql import client

logger = structlog.get_logger(__name__)


def get_prefixes_by_location(location_name: str, format: str = "json") -> Dict[str, Any]:
    """Get prefixes by location name and return raw JSON data.

    Note: The 'format' argument is accepted for backward compatibility but ignored. The
    MCP server always returns JSON, leaving all formatting/analysis to the caller/LLM.
    """
    try:
        logger.info("Getting prefixes by location", location=location_name)
        
        # Get prefixes from Nautobot
        prefixes = client.get_prefixes_by_location(location_name)
        
        if not prefixes:
            return {
                "success": True,
                "message": f"No prefixes found at location '{location_name}'",
                "data": [],
                "count": 0
            }
        result = {
            "success": True,
            "message": f"Found {len(prefixes)} prefixes at location '{location_name}'",
            "count": len(prefixes),
            "data": prefixes,
        }

        logger.info("Successfully retrieved prefixes", location=location_name, count=len(prefixes))

        return result
        
    except Exception as e:
        logger.error("Failed to get prefixes for location", 
                    location=location_name, 
                    error=str(e))
        return {
            "success": False,
            "error": f"Failed to get prefixes for location '{location_name}': {str(e)}",
            "data": [],
            "count": 0,
        }
