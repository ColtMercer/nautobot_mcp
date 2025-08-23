"""Nautobot GraphQL client for making queries."""

import os
from typing import Any, Dict, List, Optional

import requests
import structlog

logger = structlog.get_logger(__name__)

BASE_URL = os.environ.get("NAUTOBOT_URL", "http://nautobot:8080")
GRAPHQL_PATH = os.environ.get("GRAPHQL_PATH", "/graphql/")
TOKEN = os.environ.get("NAUTOBOT_TOKEN")

HEADERS = {"Authorization": f"Token {TOKEN}"} if TOKEN else {}

PREFIXES_QUERY = """
query PrefixesByLocation($name: String!) {
  prefixes(locations: [$name]) {
    prefix
    status {
      name
    }
    role {
      name
    }
    description
    locations {
      name
    }
  }
}
"""

DEVICES_QUERY = """
query DevicesByLocation($name: String!) {
  devices(location: [$name]) {
    name
    status {
      name
    }
    role {
      name
    }
    device_type {
      model
      manufacturer {
        name
      }
    }
    platform {
      name
    }
    primary_ip4 {
      address
    }
    location {
      name
    }
  }
}
"""

DEVICES_BY_LOCATION_AND_ROLE_QUERY = """
query DevicesByLocationAndRole($location: String!, $role: String!) {
  devices(location: [$location], role: [$role]) {
    name
    status {
      name
    }
    role {
      name
    }
    device_type {
      model
      manufacturer {
        name
      }
    }
    platform {
      name
    }
    primary_ip4 {
      address
    }
    location {
      name
    }
  }
}
"""

INTERFACES_BY_DEVICE_QUERY = """
query InterfacesByDevice($device: String!) {
  interfaces(device: [$device]) {
    name
    description
    status {
      name
    }
    ip_addresses {
      address
    }
    device {
      name
    }
    connected_circuit_termination {
      circuit {
        cid
        provider {
          name
        }
        circuit_type {
          name
        }
      }
    }
  }
}
"""

CIRCUITS_BY_LOCATION_QUERY = """
query CircuitsByLocation($location: String!) {
  circuit_terminations(location: [$location]) {
    term_side
    location {
      name
    }
    connected_interface {
      name
      device {
        name
        role {
          name
        }
      }
    }
    circuit {
      cid
      provider {
        name
      }
      circuit_type {
        name
      }
    }
  }
}
"""


class NautobotGraphQLClient:
    """Client for making GraphQL queries to Nautobot."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """Initialize the client."""
        self.base_url = base_url or BASE_URL
        self.token = token or TOKEN
        self.headers = {"Authorization": f"Token {self.token}"} if self.token else {}
        self.graphql_url = f"{self.base_url}{GRAPHQL_PATH}"

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.info("Executing GraphQL query", query=query[:100] + "..." if len(query) > 100 else query)
        
        try:
            response = requests.post(
                self.graphql_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error("GraphQL errors", errors=data["errors"])
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
                
            return data
        except requests.exceptions.RequestException as e:
            logger.error("GraphQL request failed", error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_all_prefixes(self) -> List[Dict[str, Any]]:
        """Get all prefixes."""
        try:
            data = self.query("query { prefixes { prefix status { name } role { name } description } }")
            prefixes_data = data["data"]["prefixes"]
            
            prefixes = []
            for prefix in prefixes_data:
                prefix_data = {
                    "prefix": prefix["prefix"],
                    "status": (prefix["status"] or {}).get("name"),
                    "role": (prefix["role"] or {}).get("name"),
                    "description": prefix.get("description"),
                }
                prefixes.append(prefix_data)
            
            logger.info("Retrieved all prefixes", count=len(prefixes))
            return prefixes
        except Exception as e:
            logger.error("Failed to get all prefixes", error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_prefixes_by_location(self, location_name: str) -> List[Dict[str, Any]]:
        """Get all prefixes for a given location name."""
        try:
            data = self.query(PREFIXES_QUERY, {"name": location_name})
            prefixes_data = data["data"]["prefixes"]
            
            prefixes = []
            for prefix in prefixes_data:
                # Get location names from the locations array
                location_names = [loc["name"] for loc in (prefix.get("locations") or [])]
                
                prefix_data = {
                    "prefix": prefix["prefix"],
                    "status": (prefix["status"] or {}).get("name"),
                    "role": (prefix["role"] or {}).get("name"),
                    "description": prefix.get("description"),
                    "locations": location_names
                }
                prefixes.append(prefix_data)
            
            logger.info("Retrieved prefixes by location", location=location_name, count=len(prefixes))
            return prefixes
        except Exception as e:
            logger.error("Failed to get prefixes by location", location=location_name, error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_devices_by_location(self, location_name: str) -> List[Dict[str, Any]]:
        """Get all devices for a given location name."""
        try:
            data = self.query(DEVICES_QUERY, {"name": location_name})
            devices_data = data["data"]["devices"]
            
            devices = []
            for device in devices_data:
                device_data = {
                    "name": device["name"],
                    "status": (device["status"] or {}).get("name"),
                    "role": (device["role"] or {}).get("name"),
                    "device_type": {
                        "model": (device["device_type"] or {}).get("model"),
                        "manufacturer": (device["device_type"] or {}).get("manufacturer", {}).get("name")
                    },
                    "platform": (device["platform"] or {}).get("name"),
                    "primary_ip4": (device["primary_ip4"] or {}).get("address"),
                    "location": (device["location"] or {}).get("name"),
                }
                devices.append(device_data)
            
            logger.info("Retrieved devices by location", location=location_name, count=len(devices))
            return devices
        except Exception as e:
            logger.error("Failed to get devices by location", location=location_name, error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_devices_by_location_and_role(self, location_name: str, role_name: str) -> List[Dict[str, Any]]:
        """Get devices for a given location and role."""
        try:
            data = self.query(DEVICES_BY_LOCATION_AND_ROLE_QUERY, {"location": location_name, "role": role_name})
            devices_data = data["data"]["devices"]
            
            devices = []
            for device in devices_data:
                device_data = {
                    "name": device["name"],
                    "status": (device["status"] or {}).get("name"),
                    "role": (device["role"] or {}).get("name"),
                    "device_type": {
                        "model": (device["device_type"] or {}).get("model"),
                        "manufacturer": (device["device_type"] or {}).get("manufacturer", {}).get("name")
                    },
                    "platform": (device["platform"] or {}).get("name"),
                    "primary_ip4": (device["primary_ip4"] or {}).get("address"),
                    "location": (device["location"] or {}).get("name"),
                }
                devices.append(device_data)
            
            logger.info("Retrieved devices by location and role", location=location_name, role=role_name, count=len(devices))
            return devices
        except Exception as e:
            logger.error("Failed to get devices by location and role", location=location_name, role=role_name, error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_interfaces_by_device(self, device_name: str) -> List[Dict[str, Any]]:
        """Get interfaces for a given device name."""
        try:
            data = self.query(INTERFACES_BY_DEVICE_QUERY, {"device": device_name})
            interfaces_data = data["data"]["interfaces"]
            
            interfaces = []
            for interface in interfaces_data:
                # Extract IP addresses
                ip_addresses = []
                for ip in (interface.get("ip_addresses") or []):
                    ip_addresses.append({
                        "address": ip.get("address"),
                        "status": (ip.get("status") or {}).get("name")
                    })
                
                interface_data = {
                    "name": interface["name"],
                    "description": interface.get("description"),
                    "status": (interface["status"] or {}).get("name"),
                    "ip_addresses": ip_addresses,
                    "device": (interface["device"] or {}).get("name"),
                }
                
                # Add circuit information if available
                if interface.get("connected_circuit_termination"):
                    circuit_info = interface["connected_circuit_termination"].get("circuit", {})
                    interface_data["circuit"] = {
                        "cid": circuit_info.get("cid"),
                        "provider": (circuit_info.get("provider") or {}).get("name"),
                        "circuit_type": (circuit_info.get("circuit_type") or {}).get("name")
                    }
                interfaces.append(interface_data)
            
            logger.info("Retrieved interfaces by device", device=device_name, count=len(interfaces))
            return interfaces
        except Exception as e:
            logger.error("Failed to get interfaces by device", device=device_name, error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")

    def get_circuits_by_location(self, location_name: str) -> List[Dict[str, Any]]:
        """Get circuits for a given location name."""
        try:
            data = self.query(CIRCUITS_BY_LOCATION_QUERY, {"location": location_name})
            circuit_terminations_data = data["data"]["circuit_terminations"]
            
            circuits = []
            for termination in circuit_terminations_data:
                circuit_data = {
                    "term_side": termination.get("term_side"),
                    "location": (termination.get("location") or {}).get("name"),
                    "connected_interface": {
                        "name": (termination.get("connected_interface") or {}).get("name"),
                        "device": {
                            "name": (termination.get("connected_interface") or {}).get("device", {}).get("name"),
                            "role": (termination.get("connected_interface") or {}).get("device", {}).get("role", {}).get("name")
                        }
                    },
                    "circuit": {
                        "cid": (termination.get("circuit") or {}).get("cid"),
                        "provider": (termination.get("circuit") or {}).get("provider", {}).get("name"),
                        "circuit_type": (termination.get("circuit") or {}).get("circuit_type", {}).get("name")
                    }
                }
                circuits.append(circuit_data)
            
            logger.info("Retrieved circuits by location", location=location_name, count=len(circuits))
            return circuits
        except Exception as e:
            logger.error("Failed to get circuits by location", location=location_name, error=str(e))
            raise RuntimeError(f"GraphQL request failed: {e}")


# Global client instance
client = NautobotGraphQLClient()
