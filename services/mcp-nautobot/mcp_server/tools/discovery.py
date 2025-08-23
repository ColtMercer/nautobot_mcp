"""Discovery tools for finding available locations and providers."""

import logging
from typing import Any, Dict, List

from ..clients.nautobot_graphql import client

logger = logging.getLogger(__name__)


def get_locations_tool() -> Dict[str, Any]:
    """Get all available locations with their hierarchy information."""
    try:
        locations = client.get_locations()
        
        if not locations:
            logger.info("No locations found")
            return {
                "success": True,
                "message": "No locations found in the system",
                "data": [],
                "count": 0
            }

        logger.info("Retrieved locations", count=len(locations))
        return {
            "success": True,
            "message": f"Found {len(locations)} locations",
            "count": len(locations),
            "data": locations
        }
    except Exception as e:
        logger.error("Failed to get locations", error=str(e))
        return {
            "success": False,
            "error": f"Failed to retrieve locations: {e}",
            "data": [],
            "count": 0
        }


def get_providers_tool() -> Dict[str, Any]:
    """Get all available circuit providers."""
    try:
        providers = client.get_providers()
        
        if not providers:
            logger.info("No providers found")
            return {
                "success": True,
                "message": "No providers found in the system",
                "data": [],
                "count": 0
            }

        logger.info("Retrieved providers", count=len(providers))
        return {
            "success": True,
            "message": f"Found {len(providers)} providers",
            "count": len(providers),
            "data": providers
        }
    except Exception as e:
        logger.error("Failed to get providers", error=str(e))
        return {
            "success": False,
            "error": f"Failed to retrieve providers: {e}",
            "data": [],
            "count": 0
        }
