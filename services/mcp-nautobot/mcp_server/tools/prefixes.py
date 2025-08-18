"""Tool for getting prefixes by location."""

from typing import Any, Dict, List

import structlog

from ..clients.nautobot_graphql import client

logger = structlog.get_logger(__name__)


def get_prefixes_by_location(location_name: str) -> List[Dict[str, Any]]:
    """Get all prefixes under a Nautobot Location by human-friendly name.
    
    Args:
        location_name: The name of the location (e.g., "HQ-Dallas", "LAB-Austin")
        
    Returns:
        List of prefix objects with prefix, status, role, description, and site information
    """
    logger.info("Getting prefixes by location", location=location_name)
    
    try:
        prefixes = client.get_prefixes_by_location(location_name)
        logger.info("Successfully retrieved prefixes", location=location_name, count=len(prefixes))
        return prefixes
    except Exception as e:
        logger.error("Failed to get prefixes by location", location=location_name, error=str(e))
        raise RuntimeError(f"Failed to get prefixes for location '{location_name}': {e}")
