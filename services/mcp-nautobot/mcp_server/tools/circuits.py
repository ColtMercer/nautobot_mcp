"""Circuit tools that return raw JSON data only (formatting/analysis handled by the LLM)."""

from typing import Any, Dict, List
import structlog

from ..clients.nautobot_graphql import client

logger = structlog.get_logger(__name__)


def get_circuits_by_location(location_names: List[str]) -> Dict[str, Any]:
    """Get circuits by location names and return raw JSON data.

    Args:
        location_names: List of location names (e.g., ["BRCN", "NYDC", "LODC"])

    Returns:
        Dictionary containing circuit data in JSON format
    """
    try:
        logger.info("Getting circuits by location", locations=location_names)

        # Get circuits from Nautobot for each location
        all_circuits = []
        
        for location in location_names:
            circuits = client.get_circuits_by_location(location)
            if circuits:
                all_circuits.extend(circuits)
                logger.info("Retrieved circuits for location", location=location, count=len(circuits))
            else:
                logger.info("No circuits found for location", location=location)

        if not all_circuits:
            logger.info("No circuits found for any location", locations=location_names)
            return {
                "success": True,
                "message": f"No circuits found for locations {location_names}",
                "data": [],
                "count": 0
            }

        logger.info("Retrieved circuits for all locations", locations=location_names, total_count=len(all_circuits))
        return {
            "success": True,
            "message": f"Found {len(all_circuits)} circuits for locations {location_names}",
            "count": len(all_circuits),
            "data": all_circuits
        }
    except Exception as e:
        logger.error("Failed to get circuits by location", locations=location_names, error=str(e))
        return {
            "success": False,
            "error": f"Failed to retrieve circuits for locations {location_names}: {e}",
            "data": [],
            "count": 0
        }
