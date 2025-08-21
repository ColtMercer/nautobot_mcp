"""Device tools that return raw JSON data only (formatting/analysis handled by the LLM)."""

from typing import Any, Dict
import structlog

from ..clients.nautobot_graphql import client

logger = structlog.get_logger(__name__)


def get_devices_by_location(location_name: str) -> Dict[str, Any]:
    """Get devices by location name and return raw JSON data.
    
    Args:
        location_name: The name of the location (e.g., "NY Data Center", "Campus A")
        
    Returns:
        Dictionary containing device data in JSON format
    """
    try:
        logger.info("Getting devices by location", location=location_name)
        
        # Get devices from Nautobot
        devices = client.get_devices_by_location(location_name)
        
        if not devices:
            return {
                "success": True,
                "message": f"No devices found at location '{location_name}'",
                "data": [],
                "count": 0
            }
        
        result = {
            "success": True,
            "message": f"Found {len(devices)} devices at location '{location_name}'",
            "count": len(devices),
            "data": devices,
        }

        logger.info("Successfully retrieved devices", location=location_name, count=len(devices))

        return result
        
    except Exception as e:
        logger.error("Failed to get devices for location", 
                    location=location_name, 
                    error=str(e))
        return {
            "success": False,
            "error": f"Failed to get devices for location '{location_name}': {str(e)}",
            "data": [],
            "count": 0,
        }


def get_devices_by_location_and_role(location_name: str, role_name: str) -> Dict[str, Any]:
    """Get devices by location and role, returning raw JSON data.
    
    Args:
        location_name: The name of the location (e.g., "NY Data Center", "Campus A")
        role_name: The name of the device role (e.g., "WAN Router", "Access Switch")
        
    Returns:
        Dictionary containing device data in JSON format
    """
    try:
        logger.info("Getting devices by location and role", location=location_name, role=role_name)
        
        # Get devices from Nautobot
        devices = client.get_devices_by_location_and_role(location_name, role_name)
        
        if not devices:
            return {
                "success": True,
                "message": f"No devices with role '{role_name}' found at location '{location_name}'",
                "data": [],
                "count": 0
            }
        
        result = {
            "success": True,
            "message": f"Found {len(devices)} devices with role '{role_name}' at location '{location_name}'",
            "count": len(devices),
            "data": devices,
        }

        logger.info("Successfully retrieved devices", location=location_name, role=role_name, count=len(devices))

        return result
        
    except Exception as e:
        logger.error("Failed to get devices for location and role", 
                    location=location_name, 
                    role=role_name,
                    error=str(e))
        return {
            "success": False,
            "error": f"Failed to get devices with role '{role_name}' at location '{location_name}': {str(e)}",
            "data": [],
            "count": 0,
        }
