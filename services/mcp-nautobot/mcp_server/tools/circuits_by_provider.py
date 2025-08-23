"""Circuit tools for provider-based queries."""

import logging
from typing import Any, Dict, List

from ..clients.nautobot_graphql import client

logger = logging.getLogger(__name__)


def get_circuits_by_provider_tool(provider_name: str) -> Dict[str, Any]:
    """Get circuits for a specific provider."""
    try:
        circuits = client.get_circuits_by_provider(provider_name)
        
        if not circuits:
            logger.info(f"No circuits found for provider {provider_name}")
            return {
                "success": True,
                "message": f"No circuits found for provider '{provider_name}'",
                "data": [],
                "count": 0
            }

        logger.info(f"Retrieved {len(circuits)} circuits by provider {provider_name}")
        return {
            "success": True,
            "message": f"Found {len(circuits)} circuits for provider '{provider_name}'",
            "count": len(circuits),
            "data": circuits
        }
    except Exception as e:
        logger.error(f"Failed to get circuits by provider {provider_name}: {e}")
        return {
            "success": False,
            "error": f"Failed to retrieve circuits for provider '{provider_name}': {e}",
            "data": [],
            "count": 0
        }
