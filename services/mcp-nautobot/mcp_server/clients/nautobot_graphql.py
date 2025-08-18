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
  prefixes(filter: { site: { name: $name } }) {
    edges {
      node {
        prefix
        status {
          value
        }
        role {
          name
        }
        description
        site {
          name
        }
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

    def get_prefixes_by_location(self, location_name: str) -> List[Dict[str, Any]]:
        """Get all prefixes for a given location name."""
        try:
            data = self.query(PREFIXES_QUERY, {"name": location_name})
            edges = data["data"]["prefixes"]["edges"]
            
            prefixes = []
            for edge in edges:
                node = edge["node"]
                prefix_data = {
                    "prefix": node["prefix"],
                    "status": (node["status"] or {}).get("value"),
                    "role": (node["role"] or {}).get("name"),
                    "description": node.get("description"),
                    "site": (node["site"] or {}).get("name"),
                }
                prefixes.append(prefix_data)
            
            logger.info("Retrieved prefixes", location=location_name, count=len(prefixes))
            return prefixes
            
        except Exception as e:
            logger.error("Failed to get prefixes by location", location=location_name, error=str(e))
            raise


# Global client instance
client = NautobotGraphQLClient()
