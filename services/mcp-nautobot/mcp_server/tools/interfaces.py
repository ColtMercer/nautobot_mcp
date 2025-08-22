"""Interface tools that return raw JSON data only (formatting/analysis handled by the LLM)."""

from typing import Any, Dict
import structlog

from ..clients.nautobot_graphql import client

logger = structlog.get_logger(__name__)


def get_interfaces_by_device(device_name: str) -> Dict[str, Any]:
    """Get interfaces for a specific device and return raw JSON data.
    
    Args:
        device_name: The name of the device (e.g., "BRCN-SW-01", "NYDC-RTR-01")
        
    Returns:
        Dictionary containing interface data in JSON format
    """
    try:
        logger.info("Getting interfaces by device", device=device_name)
        
        # Get interfaces from Nautobot
        interfaces = client.get_interfaces_by_device(device_name)
        
        if not interfaces:
            return {
                "success": True,
                "message": f"No interfaces found for device '{device_name}'",
                "data": [],
                "count": 0
            }
        
        result = {
            "success": True,
            "message": f"Found {len(interfaces)} interfaces for device '{device_name}'",
            "count": len(interfaces),
            "data": interfaces,
        }

        logger.info("Successfully retrieved interfaces", device=device_name, count=len(interfaces))

        return result
        
    except Exception as e:
        logger.error("Failed to get interfaces for device", 
                    device=device_name, 
                    error=str(e))
        return {
            "success": False,
            "error": f"Failed to get interfaces for device '{device_name}': {str(e)}",
            "data": [],
            "count": 0,
        }
