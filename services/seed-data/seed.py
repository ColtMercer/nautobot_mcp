#!/usr/bin/env python3
"""Comprehensive seed script for Nautobot MCP demo data with proper location hierarchy."""

import os
import time
import requests
import random
import string
from typing import Dict, Any, List

# Configuration
NAUTOBOT_URL = os.environ.get("NAUTOBOT_URL", "http://nautobot:8080")
NAUTOBOT_TOKEN = os.environ.get("NAUTOBOT_TOKEN", "nautobot-mcp-token-1234567890abcdef")

HEADERS = {
    "Authorization": f"Token {NAUTOBOT_TOKEN}",
    "Content-Type": "application/json"
}

def wait_for_nautobot():
    """Wait for Nautobot to be ready."""
    print("Waiting for Nautobot to be ready...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(f"{NAUTOBOT_URL}/health/", timeout=5)
            if response.status_code == 200:
                print("Nautobot is ready!")
                return
        except requests.exceptions.RequestException:
            pass
        
        retry_count += 1
        time.sleep(2)
    
    raise Exception("Nautobot did not become ready in time")

def cleanup_existing_locations():
    """Clean up existing locations to start fresh."""
    print("Cleaning up existing locations...")
    
    # Get all existing locations
    response = requests.get(
        f"{NAUTOBOT_URL}/api/dcim/locations/",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        locations = response.json()["results"]
        for location in locations:
            print(f"Deleting location: {location['name']}")
            delete_response = requests.delete(
                f"{NAUTOBOT_URL}/api/dcim/locations/{location['id']}/",
                headers=HEADERS
            )
            if delete_response.status_code == 204:
                print(f"Deleted location: {location['name']}")
            else:
                print(f"Failed to delete location {location['name']}: {delete_response.status_code}")
    
    print("Location cleanup completed")

def cleanup_existing_interfaces():
    """Clean up existing interfaces to start fresh."""
    print("Cleaning up existing interfaces...")
    
    # Get all existing interfaces
    response = requests.get(
        f"{NAUTOBOT_URL}/api/dcim/interfaces/",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        interfaces = response.json()["results"]
        deleted_count = 0
        for interface in interfaces:
            print(f"Deleting interface: {interface['name']} on device {interface.get('device', {}).get('name', 'Unknown')}")
            delete_response = requests.delete(
                f"{NAUTOBOT_URL}/api/dcim/interfaces/{interface['id']}/",
                headers=HEADERS
            )
            if delete_response.status_code == 204:
                deleted_count += 1
                print(f"Deleted interface: {interface['name']}")
            else:
                print(f"Failed to delete interface {interface['name']}: {delete_response.status_code}")
        
        print(f"Interface cleanup completed. Deleted {deleted_count} interfaces.")
    else:
        print(f"Failed to get interfaces: {response.status_code}")

def create_manufacturer(name: str, slug: str) -> Dict[str, Any]:
    """Create a manufacturer."""
    data = {
        "name": name,
        "slug": slug
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/manufacturers/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created manufacturer: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Manufacturer {name} already exists")
        # Try to get the existing manufacturer
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/manufacturers/?name={name}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create manufacturer {name}: {response.status_code} - {response.text}")
        return None

def get_or_create_device_type(manufacturer_id: str, model: str, slug: str, u_height: int = 1) -> Dict[str, Any]:
    """Get existing device type or create a new one."""
    # First try to get existing device type
    get_response = requests.get(
        f"{NAUTOBOT_URL}/api/dcim/device-types/?model={model}",
        headers=HEADERS
    )
    
    if get_response.status_code == 200:
        data = get_response.json()
        if data["results"]:
            existing_device_type = data["results"][0]
            print(f"Found existing device type: {model}")
            
            # Update the manufacturer if it's not set
            if not existing_device_type.get("manufacturer"):
                update_data = {
                    "manufacturer": manufacturer_id
                }
                update_response = requests.patch(
                    f"{NAUTOBOT_URL}/api/dcim/device-types/{existing_device_type['id']}/",
                    json=update_data,
                    headers=HEADERS
                )
                if update_response.status_code == 200:
                    print(f"Updated manufacturer for device type: {model}")
                    return update_response.json()
            
            return existing_device_type
    
    # Create new device type if it doesn't exist
    data = {
        "manufacturer": manufacturer_id,
        "model": model,
        "slug": slug,
        "u_height": u_height,
        "status": "Active"
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/device-types/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created device type: {model}")
        return response.json()
    else:
        print(f"Failed to create device type {model}: {response.status_code} - {response.text}")
        return None

def create_platform(name: str, slug: str) -> Dict[str, Any]:
    """Create a platform."""
    data = {
        "name": name,
        "slug": slug
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/platforms/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created platform: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Platform {name} already exists")
        # Try to get the existing platform
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/platforms/?name={name}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create platform {name}: {response.status_code} - {response.text}")
        return None

def get_or_create_device_role(name: str) -> Dict[str, Any]:
    """Get existing device role or create a new one."""
    # First try to get existing device role
    response = requests.get(
        f"{NAUTOBOT_URL}/api/extras/roles/?name={name}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            existing_role = data["results"][0]
            print(f"Found existing device role: {name}")
            return existing_role
    
    # Create new device role if it doesn't exist
    data = {
        "name": name,
        "content_types": ["dcim.device"],
        "status": "Active"
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/extras/roles/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created device role: {name}")
        return response.json()
    else:
        print(f"Failed to create device role {name}: {response.status_code} - {response.text}")
        return None

def create_location(name: str, location_type: str, parent: str = None) -> Dict[str, Any]:
    """Create a location (idempotent). If it exists, return the existing one by name and optional parent."""
    data = {
        "name": name,
        "location_type": location_type,
        "status": "Active"
    }
    
    if parent:
        data["parent"] = parent
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/locations/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created location: {name}")
        return response.json()
    
    # On any 400, try to fetch existing by name and optional parent
    if response.status_code == 400:
        params = {"name": name}
        if parent:
            params["parent"] = parent
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/locations/",
            params=params,
            headers=HEADERS
        )
        if get_response.status_code == 200:
            payload = get_response.json()
            if payload.get("results"):
                print(f"Location {name} already exists")
                return payload["results"][0]
        # Secondary lookup by name only
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/locations/",
            params={"name": name},
        headers=HEADERS
    )
        if get_response.status_code == 200:
            payload = get_response.json()
            if payload.get("results"):
                print(f"Location {name} already exists (matched by name)")
                return payload["results"][0]
    
    print(f"Failed to create location {name}: {response.status_code} - {response.text}")
    return None

def create_device(name: str, device_type_id: str, role_id: str, location_id: str, platform_id: str = None, description: str = None) -> Dict[str, Any]:
    """Create a device."""
    data = {
        "name": name,
        "device_type": device_type_id,
        "role": role_id,
        "location": location_id,
        "status": "Active"
    }
    
    if platform_id:
        data["platform"] = platform_id
    
    if description:
        data["description"] = description
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/devices/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created device: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Device {name} already exists")
        # Try to get the existing device
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/devices/?name={name}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create device {name}: {response.status_code} - {response.text}")
        return None

def create_interface(device_id: str, name: str, interface_type: str = "1000base-t", description: str = None) -> Dict[str, Any]:
    """Create an interface."""
    # First check if interface already exists
    get_response = requests.get(
        f"{NAUTOBOT_URL}/api/dcim/interfaces/?device_id={device_id}&name={name}",
        headers=HEADERS
    )
    
    if get_response.status_code == 200:
        data = get_response.json()
        if data["results"]:
            print(f"Interface {name} already exists, skipping creation")
            return data["results"][0]
    
    print(f"DEBUG: Attempting to create interface {name} for device {device_id}")
    data = {
        "device": device_id,
        "name": name,
        "type": interface_type,
        "status": "Active"
    }
    
    if description:
        data["description"] = description
    
    print(f"DEBUG: Interface data: {data}")
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/interfaces/",
        json=data,
        headers=HEADERS
    )
    
    print(f"DEBUG: Interface creation response status: {response.status_code}")
    if response.status_code == 201:
        print(f"Created interface: {name}")
        return response.json()
    else:
        print(f"Failed to create interface {name}: {response.status_code} - {response.text}")
        return None

def create_ip_address(ip_address: str, namespace_id: str = None, status_id: str = None) -> Dict[str, Any]:
    """Create an IP address."""
    print(f"DEBUG: Creating IP address {ip_address}")
    
    data = {
        "address": ip_address
    }

    if namespace_id:
        data["namespace"] = namespace_id
    
    if status_id:
        data["status"] = status_id
    
    print(f"DEBUG: IP address data: {data}")
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/ipam/ip-addresses/",
        json=data,
        headers=HEADERS
    )
    
    print(f"DEBUG: IP address creation response status: {response.status_code}")
    print(f"DEBUG: IP address creation response: {response.text}")
    
    if response.status_code == 201:
        print(f"Created IP address: {ip_address}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"IP address {ip_address} already exists")
        # Try to get the existing IP address
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/ipam/ip-addresses/?address={ip_address}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            existing_ips = get_response.json().get("results", [])
            if existing_ips:
                print(f"Found existing IP address: {ip_address}")
                return existing_ips[0]
            else:
                print(f"WARNING: IP address {ip_address} said to exist but not found in API")
                # Try creating it again without the parent prefix
                data_without_parent = {
                    "address": ip_address
                }
                if namespace_id:
                    data_without_parent["namespace"] = namespace_id
                if status_id:
                    data_without_parent["status"] = status_id
                
                retry_response = requests.post(
                    f"{NAUTOBOT_URL}/api/ipam/ip-addresses/",
                    json=data_without_parent,
                    headers=HEADERS
                )
                if retry_response.status_code == 201:
                    print(f"Successfully created IP address {ip_address} on retry")
                    return retry_response.json()
                else:
                    print(f"Failed to create IP address {ip_address} on retry: {retry_response.status_code} - {retry_response.text}")
        return None
    else:
        print(f"Failed to create IP address {ip_address}: {response.status_code} - {response.text}")
        return None

def assign_ip_to_interface(ip_address_id: str, interface_id: str) -> bool:
    """Assign an IP address to an interface using the ip-address-to-interface endpoint."""
    print(f"DEBUG: Assigning IP address {ip_address_id} to interface {interface_id}")
    
    data = {
        "ip_address": ip_address_id,
        "interface": interface_id,
        "is_source": True,
        "is_destination": True,
        "is_default": True,
        "is_preferred": True,
        "is_primary": True,
        "is_secondary": False,
        "is_standby": False
    }
    
    print(f"DEBUG: IP-to-interface assignment data: {data}")
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/ipam/ip-address-to-interface/",
        json=data,
        headers=HEADERS
    )
    
    print(f"DEBUG: IP-to-interface assignment response status: {response.status_code}")
    print(f"DEBUG: IP-to-interface assignment response: {response.text}")
    
    if response.status_code == 201:
        print(f"Successfully assigned IP address {ip_address_id} to interface {interface_id}")
        return True
    else:
        print(f"Failed to assign IP address {ip_address_id} to interface {interface_id}: {response.status_code} - {response.text}")
        return False

def create_prefix(prefix: str, location_id: str = None, description: str = None, namespace_id: str = None) -> Dict[str, Any]:
    """Create a prefix."""
    data = {
        "prefix": prefix,
        "status": "Active"
    }
    
    if location_id:
        data["location"] = location_id
    
    if namespace_id:
        data["namespace"] = namespace_id
    
    if description:
        data["description"] = description
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/ipam/prefixes/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created prefix: {prefix}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Prefix {prefix} already exists")
        return response.json()
    else:
        print(f"Failed to create prefix {prefix}: {response.status_code} - {response.text}")
        return None

def update_prefix_location(prefix_id: str, location_id: str) -> bool:
    """Update an existing prefix with a location association."""
    data = {
        "location": location_id
    }
    
    response = requests.patch(
        f"{NAUTOBOT_URL}/api/ipam/prefixes/{prefix_id}/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 200:
        print(f"Updated prefix {prefix_id} with location")
        return True
    else:
        print(f"Failed to update prefix {prefix_id}: {response.status_code} - {response.text}")
        return False


def get_prefix_by_network(network: str) -> Dict[str, Any]:
    """Get prefix by network address."""
    response = requests.get(
        f"{NAUTOBOT_URL}/api/ipam/prefixes/?prefix={network}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]
    
    return None

def get_location_type_id(name: str) -> str:
    """Get location type ID by name."""
    response = requests.get(
        f"{NAUTOBOT_URL}/api/dcim/location-types/?name={name}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]["id"]
    
    print(f"ERROR: Location type '{name}' not found")
    return None

def create_location_type(name: str, slug: str, description: str = "", parent_type: str = None, content_types: list = None) -> Dict[str, Any]:
    """Create a location type."""
    data = {
        "name": name,
        "slug": slug,
        "description": description
    }
    
    if parent_type:
        data["parent"] = parent_type
    
    if content_types:
        data["content_types"] = content_types
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/location-types/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created location type: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Location type {name} already exists")
        # Try to get the existing location type
        location_type_id = get_location_type_id(name)
        if location_type_id:
            return {"id": location_type_id}
        return None
    else:
        print(f"Failed to create location type {name}: {response.status_code} - {response.text}")
        return None

def update_location_type(location_type_id: str, content_types: list = None, parent_type: str = None) -> bool:
    """Update an existing location type with new content types and parent."""
    data = {}
    
    if content_types:
        data["content_types"] = content_types
    
    if parent_type:
        data["parent"] = parent_type
    
    if not data:
        return True  # Nothing to update
    
    response = requests.patch(
        f"{NAUTOBOT_URL}/api/dcim/location-types/{location_type_id}/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 200:
        print(f"Updated location type with ID {location_type_id}")
        return True
    else:
        print(f"Failed to update location type {location_type_id}: {response.status_code} - {response.text}")
        return False

def get_or_create_location_type(name: str, slug: str, description: str = "", parent_type: str = None, content_types: list = None) -> str:
    """Get location type ID by name, create if it doesn't exist."""
    # First try to get existing location type
    location_type_id = get_location_type_id(name)
    if location_type_id:
        # Update existing location type with new content types and parent if provided
        if content_types or parent_type:
            update_location_type(location_type_id, content_types, parent_type)
        return location_type_id
    
    # If not found, create it
    location_type = create_location_type(name, slug, description, parent_type, content_types)
    if location_type:
        return location_type["id"]
    
    return None

def get_namespace_id(name: str) -> str:
    """Get IP namespace ID by name."""
    response = requests.get(
        f"{NAUTOBOT_URL}/api/ipam/namespaces/?name={name}",
        headers=HEADERS
    )
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]["id"]
    print(f"ERROR: Namespace '{name}' not found")
    return None

def get_status_id(name: str) -> str:
    """Get status ID by name."""
    response = requests.get(
        f"{NAUTOBOT_URL}/api/extras/statuses/?name={name}",
        headers=HEADERS
    )
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]["id"]
    print(f"ERROR: Status '{name}' not found")
    return None

def create_circuit_type(name: str, slug: str, description: str = "") -> Dict[str, Any]:
    """Create a circuit type."""
    data = {
        "name": name,
        "slug": slug,
        "description": description
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/circuits/circuit-types/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created circuit type: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Circuit type {name} already exists")
        # Try to get the existing circuit type
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/circuits/circuit-types/?name={name}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create circuit type {name}: {response.status_code} - {response.text}")
        return None

def create_provider(name: str, slug: str, description: str = "") -> Dict[str, Any]:
    """Create a provider."""
    data = {
        "name": name,
        "slug": slug,
        "description": description
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/circuits/providers/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created provider: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Provider {name} already exists")
        # Try to get the existing provider
        existing_provider = get_provider_by_name(name)
        if existing_provider:
            print(f"Found existing provider: {name} with ID {existing_provider['id']}")
            return existing_provider
        else:
            print(f"Provider {name} exists but could not be retrieved")
            print(f"Debug: Checking all providers to see what's available...")
            # Debug: List all providers to see what's actually there
            debug_response = requests.get(f"{NAUTOBOT_URL}/api/circuits/providers/", headers=HEADERS)
            if debug_response.status_code == 200:
                debug_data = debug_response.json()
                print(f"Available providers: {[p['name'] for p in debug_data['results']]}")
            return None
    else:
        print(f"Failed to create provider {name}: {response.status_code} - {response.text}")
        return None

def get_provider_by_name(name: str) -> Dict[str, Any]:
    """Get provider by name."""
    # Try exact name match first
    response = requests.get(
        f"{NAUTOBOT_URL}/api/circuits/providers/?name={name}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]
    
    # If not found, try case-insensitive search
    response = requests.get(
        f"{NAUTOBOT_URL}/api/circuits/providers/",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        for provider in data["results"]:
            if provider["name"].lower() == name.lower():
                return provider
    
    return None

def generate_circuit_id() -> str:
    """Generate a random circuit ID for carrier circuits."""
    # Format: CKT-XXXX-XXXX (where X is alphanumeric)
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choice(chars) for _ in range(4))
    part2 = ''.join(random.choice(chars) for _ in range(4))
    return f"CKT-{part1}-{part2}"

def create_circuit(cid: str, circuit_type_id: str, provider_id: str, location_id: str, 
                  status: str = "Active", description: str = "") -> Dict[str, Any]:
    """Create a circuit."""
    data = {
        "cid": cid,
        "circuit_type": circuit_type_id,
        "provider": provider_id,
        "status": status
    }
    
    if location_id:
        data["location"] = location_id
    
    if description:
        data["description"] = description
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/circuits/circuits/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created circuit: {cid}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Circuit {cid} already exists")
        # Try to get the existing circuit
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/circuits/circuits/?cid={cid}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create circuit {cid}: {response.status_code} - {response.text}")
        return None

def create_circuit_termination(circuit_id: str, location_id: str, term_side: str = "A", port_speed: int = 1000) -> Dict[str, Any]:
    """Create a circuit termination."""
    data = {
        "circuit": circuit_id,
        "term_side": term_side,
        "port_speed": port_speed,
        "status": "Active"
    }
    
    if location_id:
        data["location"] = location_id
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/circuits/circuit-terminations/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created circuit termination: {term_side} side for circuit {circuit_id}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Circuit termination {term_side} side for circuit {circuit_id} already exists")
        # Try to get the existing termination
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/circuits/circuit-terminations/?circuit_id={circuit_id}&term_side={term_side}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create circuit termination {term_side} side for circuit {circuit_id}: {response.status_code} - {response.text}")
        return None

def create_cable_connection(termination_a_type: str, termination_a_id: str, termination_b_type: str, termination_b_id: str) -> Dict[str, Any]:
    """Create a cable to connect two terminations."""
    # Get the Connected status ID for cables
    connected_status_id = get_status_id("Connected")
    
    data = {
        "termination_a_type": termination_a_type,
        "termination_a_id": termination_a_id,
        "termination_b_type": termination_b_type,
        "termination_b_id": termination_b_id,
        "type": "cat6"
    }
    
    if connected_status_id:
        data["status"] = connected_status_id
    else:
        # If we can't get the status ID, try using the name
        data["status"] = "Connected"
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/cables/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created cable connection between {termination_a_type} {termination_a_id} and {termination_b_type} {termination_b_id}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Cable connection already exists between {termination_a_type} {termination_a_id} and {termination_b_type} {termination_b_id}")
        return None
    else:
        print(f"Failed to create cable connection: {response.status_code} - {response.text}")
        return None

def seed_data():
    """Seed Nautobot with comprehensive demo data."""
    print("Starting comprehensive Nautobot data seeding...")
    
    # Wait for Nautobot to be ready
    wait_for_nautobot()
    
    # Idempotent run: do NOT delete existing locations; just (re)create/match
    
    # Create location types with proper hierarchy
    print("\n=== Creating Location Types with Hierarchy ===")
    
    # First create Region (no parent)
    region_type_id = get_or_create_location_type("Region", "region", "Geographic region")
    
    # Then create Country with Region as parent
    country_type_id = get_or_create_location_type("Country", "country", "Country within a region", region_type_id)
    
    # Then create Campus, Data Center, and Branch with proper content types and parentage
    campus_type_id = get_or_create_location_type("Campus", "campus", "Campus location within a country", country_type_id, ["dcim.device", "ipam.prefix", "circuits.circuittermination"])
    dc_type_id = get_or_create_location_type("Data Center", "data-center", "Data center within a country", country_type_id, ["dcim.device", "ipam.prefix", "circuits.circuittermination"])
    branch_type_id = get_or_create_location_type("Branch", "branch", "Branch office within a country", country_type_id, ["dcim.device", "ipam.prefix", "circuits.circuittermination"])
    
    if not all([region_type_id, country_type_id, campus_type_id, dc_type_id, branch_type_id]):
        print("ERROR: Failed to create location type hierarchy")
        return

    # Get Global namespace for IP addressing
    global_ns_id = get_namespace_id("Global")
    if not global_ns_id:
        print("ERROR: Global namespace not found; cannot assign IP addresses")
        return
    
    # Get Active status ID for IP addressing
    active_status_id = get_status_id("Active")
    print(f"DEBUG: Retrieved Active status ID: {active_status_id}")
    if not active_status_id:
        print("ERROR: Active status not found; cannot assign IP addresses")
        return
    
    # Create manufacturers
    print("\n=== Creating Manufacturers ===")
    cisco = create_manufacturer("Cisco Systems", "cisco")
    juniper = create_manufacturer("Juniper Networks", "juniper")
    arista = create_manufacturer("Arista Networks", "arista")
    
    if not cisco or not juniper or not arista:
        print("ERROR: Failed to create manufacturers")
        return
    
    # Create device types
    print("\n=== Creating Device Types ===")
    cisco_router = get_or_create_device_type(cisco["id"], "ISR 4321", "isr-4321", 1)
    cisco_switch = get_or_create_device_type(cisco["id"], "Catalyst 9300", "catalyst-9300", 1)
    juniper_router = get_or_create_device_type(juniper["id"], "MX204", "mx204", 1)
    arista_switch = get_or_create_device_type(arista["id"], "DCS-7050SX3", "dcs-7050sx3", 1)
    
    if not cisco_router or not cisco_switch or not juniper_router or not arista_switch:
        print("ERROR: Failed to create device types")
        return
    
    # Create platforms
    print("\n=== Creating Platforms ===")
    ios_xe = create_platform("IOS-XE", "ios-xe")
    nx_os = create_platform("NX-OS", "nx-os")
    junos = create_platform("Junos", "junos")
    eos = create_platform("EOS", "eos")
    
    if not ios_xe or not nx_os or not junos or not eos:
        print("ERROR: Failed to create platforms")
        return
    
    # Create device roles
    print("\n=== Creating Device Roles ===")
    wan_router = get_or_create_device_role("WAN")
    core_switch = get_or_create_device_role("Core")
    spine_switch = get_or_create_device_role("Spine")
    leaf_switch = get_or_create_device_role("Leaf")
    branch_switch = get_or_create_device_role("Branch Access")
    campus_switch = get_or_create_device_role("Campus Access")
    
    if not wan_router or not core_switch or not spine_switch or not leaf_switch or not branch_switch or not campus_switch:
        print("ERROR: Failed to create device roles")
        return
    
    # Create location hierarchy
    print("\n=== Creating Location Hierarchy ===")
    
    # Create regions
    north_america = create_location("NAM", region_type_id)
    europe = create_location("EMEA", region_type_id)
    asia = create_location("APAC", region_type_id)
    latam = create_location("LATAM", region_type_id)
    
    if not north_america or not europe:
        print("ERROR: Failed to create regions")
        return
    
    # Create countries with their respective region parents
    usa = create_location("United States", country_type_id, north_america["id"])
    uk = create_location("United Kingdom", country_type_id, europe["id"])
    korea = create_location("Republic of Korea", country_type_id, asia["id"])
    brazil = create_location("Brazil", country_type_id, latam["id"])
    mexico = create_location("Mexico", country_type_id, north_america["id"])
    
    if not usa or not uk or not korea or not brazil or not mexico:
        print("ERROR: Failed to create countries")
        return
    
    # Create campuses and data centers with proper parentage
    dallas_campus = create_location("DACN", campus_type_id, usa["id"])
    london_campus = create_location("LOCN", campus_type_id, uk["id"])
    korea_campus = create_location("KOCN", campus_type_id, korea["id"])
    brazil_campus = create_location("BRCN", campus_type_id, brazil["id"])
    mexico_campus = create_location("MXCN", campus_type_id, mexico["id"])
    
    nyc_dc = create_location("NYDC", dc_type_id, usa["id"])
    lon_dc = create_location("LODC", dc_type_id, uk["id"])
    
    if not all([dallas_campus, london_campus, korea_campus, brazil_campus, mexico_campus, nyc_dc, lon_dc]):
        print("ERROR: Failed to create campuses and data centers")
        return
    
    # Create branch offices with their respective country parents
    branch_001 = create_location("USBN1", branch_type_id, usa["id"])
    branch_002 = create_location("MXBN1", branch_type_id, mexico["id"])
    branch_003 = create_location("UKBN1", branch_type_id, uk["id"])
    branch_004 = create_location("BRBN1", branch_type_id, brazil["id"])
    branch_005 = create_location("USBN2", branch_type_id, usa["id"])
    branch_006 = create_location("MXBN2", branch_type_id, mexico["id"])
    branch_007 = create_location("UKBN2", branch_type_id, uk["id"])
    branch_008 = create_location("BRBN2", branch_type_id, brazil["id"])
    
    if not all([branch_001, branch_002, branch_003, branch_004, branch_005, branch_006, branch_007, branch_008]):
        print("ERROR: Failed to create branch offices")
        return
    
    print(f"Created location hierarchy with {8} locations")
    
    # Create devices at each location
    print("\n=== Creating Devices ===")
    devices = [
        # WAN Routers
        ("DALCN-WAN01", cisco_router["id"], wan_router["id"], dallas_campus["id"], ios_xe["id"], "WAN Router at Dallas Campus"),
        ("DALCN-WAN02", cisco_router["id"], wan_router["id"], dallas_campus["id"], ios_xe["id"], "WAN Router at Dallas Campus"),
        ("LOCN-WAN01", cisco_router["id"], wan_router["id"], london_campus["id"], ios_xe["id"], "WAN Router at London Campus"),
        ("LOCN-WAN02", cisco_router["id"], wan_router["id"], london_campus["id"], ios_xe["id"], "WAN Router at London Campus"),
        ("KOCN-WAN01", cisco_router["id"], wan_router["id"], korea_campus["id"], ios_xe["id"], "WAN Router at Korea Campus"),
        ("KOCN-WAN02", cisco_router["id"], wan_router["id"], korea_campus["id"], ios_xe["id"], "WAN Router at Korea Campus"),
        ("BRCN-WAN01", cisco_router["id"], wan_router["id"], brazil_campus["id"], ios_xe["id"], "WAN Router at Brazil Campus"),
        ("BRCN-WAN02", cisco_router["id"], wan_router["id"], brazil_campus["id"], ios_xe["id"], "WAN Router at Brazil Campus"),
        ("MXCN-WAN01", cisco_router["id"], wan_router["id"], mexico_campus["id"], ios_xe["id"], "WAN Router at Mexico Campus"),
        ("MXCN-WAN02", cisco_router["id"], wan_router["id"], mexico_campus["id"], ios_xe["id"], "WAN Router at Mexico Campus"),
        
        # Core Routers
        ("DALCN-COR01", cisco_router["id"], core_switch["id"], nyc_dc["id"], ios_xe["id"], "Core Router at NYC Data Center"),
        ("DALCN-COR02", cisco_router["id"], core_switch["id"], nyc_dc["id"], ios_xe["id"], "Core Router at NYC Data Center"),
        ("LOCN-COR01", cisco_router["id"], core_switch["id"], lon_dc["id"], ios_xe["id"], "Core Router at London Data Center"),
        ("LOCN-COR02", cisco_router["id"], core_switch["id"], lon_dc["id"], ios_xe["id"], "Core Router at London Data Center"),
        ("KOCN-COR01", cisco_router["id"], core_switch["id"], korea_campus["id"], ios_xe["id"], "Core Router at Korea Campus"),
        ("KOCN-COR02", cisco_router["id"], core_switch["id"], korea_campus["id"], ios_xe["id"], "Core Router at Korea Campus"),
        ("BRCN-COR01", cisco_router["id"], core_switch["id"], brazil_campus["id"], ios_xe["id"], "Core Router at Brazil Campus"),
        ("BRCN-COR02", cisco_router["id"], core_switch["id"], brazil_campus["id"], ios_xe["id"], "Core Router at Brazil Campus"),
        ("MXCN-COR01", cisco_router["id"], core_switch["id"], mexico_campus["id"], ios_xe["id"], "Core Router at Mexico Campus"),
        
        # Access Switches
        ("DALCN-ACC01", cisco_switch["id"], campus_switch["id"], dallas_campus["id"], nx_os["id"], "Access Switch at Dallas Campus"),
        ("DALCN-ACC02", cisco_switch["id"], campus_switch["id"], dallas_campus["id"], nx_os["id"], "Access Switch at Dallas Campus"),
        ("LOCN-ACC01", cisco_switch["id"], campus_switch["id"], london_campus["id"], nx_os["id"], "Access Switch at London Campus"),
        ("LOCN-ACC02", cisco_switch["id"], campus_switch["id"], london_campus["id"], nx_os["id"], "Access Switch at London Campus"),
        ("KOCN-ACC01", cisco_switch["id"], campus_switch["id"], korea_campus["id"], nx_os["id"], "Access Switch at Korea Campus"),
        ("KOCN-ACC02", cisco_switch["id"], campus_switch["id"], korea_campus["id"], nx_os["id"], "Access Switch at Korea Campus"),
        ("BRCN-ACC01", cisco_switch["id"], campus_switch["id"], brazil_campus["id"], nx_os["id"], "Access Switch at Brazil Campus"),
        ("BRCN-ACC02", cisco_switch["id"], campus_switch["id"], brazil_campus["id"], nx_os["id"], "Access Switch at Brazil Campus"),
        ("MXCN-ACC01", cisco_switch["id"], campus_switch["id"], mexico_campus["id"], nx_os["id"], "Access Switch at Mexico Campus"),
        
        # Spine/Leaf Switches
        ("NYDC-SPN1000", arista_switch["id"], spine_switch["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("NYDC-SPN1001", arista_switch["id"], spine_switch["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("NYDC-SPN1002", arista_switch["id"], spine_switch["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("NYDC-SPN1003", arista_switch["id"], spine_switch["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("LODC-SPN1000", arista_switch["id"], spine_switch["id"], lon_dc["id"], eos["id"], "Spine Switch at London Data Center"),
        ("LODC-SPN1001", arista_switch["id"], spine_switch["id"], lon_dc["id"], eos["id"], "Spine Switch at London Data Center"),
        ("LODC-SPN1002", arista_switch["id"], spine_switch["id"], lon_dc["id"], eos["id"], "Spine Switch at London Data Center"),
        ("LODC-SPN1003", arista_switch["id"], spine_switch["id"], lon_dc["id"], eos["id"], "Spine Switch at London Data Center"),
        
        ("NYDC-LEAF1000", arista_switch["id"], leaf_switch["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        ("NYDC-LEAF1001", arista_switch["id"], leaf_switch["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        ("NYDC-LEAF1002", arista_switch["id"], leaf_switch["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        ("NYDC-LEAF1003", arista_switch["id"], leaf_switch["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        ("LODC-LEAF1000", arista_switch["id"], leaf_switch["id"], lon_dc["id"], eos["id"], "Leaf Switch at London Data Center"),
        ("LODC-LEAF1001", arista_switch["id"], leaf_switch["id"], lon_dc["id"], eos["id"], "Leaf Switch at London Data Center"),
        ("LODC-LEAF1002", arista_switch["id"], leaf_switch["id"], lon_dc["id"], eos["id"], "Leaf Switch at London Data Center"),
        ("LODC-LEAF1003", arista_switch["id"], leaf_switch["id"], lon_dc["id"], eos["id"], "Leaf Switch at London Data Center"),
        
        # Branch Devices
        ("USBN1-SW01", cisco_switch["id"], branch_switch["id"], branch_001["id"], nx_os["id"], "Branch Switch at Branch Office 1"),
        ("USBN1-SW02", cisco_switch["id"], branch_switch["id"], branch_001["id"], nx_os["id"], "Branch Switch at Branch Office 1"),
        ("USBN1-WAN01", cisco_router["id"], wan_router["id"], branch_001["id"], ios_xe["id"], "WAN Router at Branch Office 1"),
        ("USBN1-WAN02", cisco_router["id"], wan_router["id"], branch_001["id"], ios_xe["id"], "WAN Router at Branch Office 1"),
        
        ("MXBN1-SW01", cisco_switch["id"], branch_switch["id"], branch_002["id"], nx_os["id"], "Branch Switch at Branch Office 2"),
        ("MXBN1-SW02", cisco_switch["id"], branch_switch["id"], branch_002["id"], nx_os["id"], "Branch Switch at Branch Office 2"),
        ("MXBN1-WAN01", cisco_router["id"], wan_router["id"], branch_002["id"], ios_xe["id"], "WAN Router at Branch Office 2"),
        ("MXBN1-WAN02", cisco_router["id"], wan_router["id"], branch_002["id"], ios_xe["id"], "WAN Router at Branch Office 2"),
        
        ("UKBN1-SW01", cisco_switch["id"], branch_switch["id"], branch_003["id"], nx_os["id"], "Branch Switch at Branch Office 3"),
        ("UKBN1-SW02", cisco_switch["id"], branch_switch["id"], branch_003["id"], nx_os["id"], "Branch Switch at Branch Office 3"),
        ("UKBN1-WAN01", cisco_router["id"], wan_router["id"], branch_003["id"], ios_xe["id"], "WAN Router at Branch Office 3"),
        ("UKBN1-WAN02", cisco_router["id"], wan_router["id"], branch_003["id"], ios_xe["id"], "WAN Router at Branch Office 3"),
        
        ("BRBN1-SW01", cisco_switch["id"], branch_switch["id"], branch_004["id"], nx_os["id"], "Branch Switch at Branch Office 4"),
        ("BRBN1-SW02", cisco_switch["id"], branch_switch["id"], branch_004["id"], nx_os["id"], "Branch Switch at Branch Office 4"),
        ("BRBN1-WAN01", cisco_router["id"], wan_router["id"], branch_004["id"], ios_xe["id"], "WAN Router at Branch Office 4"),
        ("BRBN1-WAN02", cisco_router["id"], wan_router["id"], branch_004["id"], ios_xe["id"], "WAN Router at Branch Office 4"),
        
        ("USBN2-SW01", cisco_switch["id"], branch_switch["id"], branch_005["id"], nx_os["id"], "Branch Switch at Branch Office 5"),
        ("USBN2-SW02", cisco_switch["id"], branch_switch["id"], branch_005["id"], nx_os["id"], "Branch Switch at Branch Office 5"),
        ("USBN2-WAN01", cisco_router["id"], wan_router["id"], branch_005["id"], ios_xe["id"], "WAN Router at Branch Office 5"),
        ("USBN2-WAN02", cisco_router["id"], wan_router["id"], branch_005["id"], ios_xe["id"], "WAN Router at Branch Office 5"),
        
        ("MXBN2-SW01", cisco_switch["id"], branch_switch["id"], branch_006["id"], nx_os["id"], "Branch Switch at Branch Office 6"),
        ("MXBN2-SW02", cisco_switch["id"], branch_switch["id"], branch_006["id"], nx_os["id"], "Branch Switch at Branch Office 6"),
        ("MXBN2-WAN01", cisco_router["id"], wan_router["id"], branch_006["id"], ios_xe["id"], "WAN Router at Branch Office 6"),
        ("MXBN2-WAN02", cisco_router["id"], wan_router["id"], branch_006["id"], ios_xe["id"], "WAN Router at Branch Office 6"),
        
        ("UKBN2-SW01", cisco_switch["id"], branch_switch["id"], branch_007["id"], nx_os["id"], "Branch Switch at Branch Office 7"),
        ("UKBN2-SW02", cisco_switch["id"], branch_switch["id"], branch_007["id"], nx_os["id"], "Branch Switch at Branch Office 7"),
        ("UKBN2-WAN01", cisco_router["id"], wan_router["id"], branch_007["id"], ios_xe["id"], "WAN Router at Branch Office 7"),
        ("UKBN2-WAN02", cisco_router["id"], wan_router["id"], branch_007["id"], ios_xe["id"], "WAN Router at Branch Office 7"),
        
        ("BRBN2-SW01", cisco_switch["id"], branch_switch["id"], branch_008["id"], nx_os["id"], "Branch Switch at Branch Office 8"),
        ("BRBN2-SW02", cisco_switch["id"], branch_switch["id"], branch_008["id"], nx_os["id"], "Branch Switch at Branch Office 8"),
        ("BRBN2-WAN01", cisco_router["id"], wan_router["id"], branch_008["id"], ios_xe["id"], "WAN Router at Branch Office 8"),
        ("BRBN2-WAN02", cisco_router["id"], wan_router["id"], branch_008["id"], ios_xe["id"], "WAN Router at Branch Office 8"),
    ]
    
    device_ids = {}
    for name, device_type_id, role_id, location_id, platform_id, description in devices:
        device = create_device(name, device_type_id, role_id, location_id, platform_id, description)
        if device:
            device_ids[name] = device["id"]
        else:
            # Try to look up existing device by name if creation failed
            get_response = requests.get(
                f"{NAUTOBOT_URL}/api/dcim/devices/",
                params={"name": name},
                headers=HEADERS
            )
            if get_response.status_code == 200 and get_response.json().get("results"):
                device_ids[name] = get_response.json()["results"][0]["id"]
            else:
                print(f"ERROR: Failed to create or find device {name}")
                return
    
    print(f"Created {len(device_ids)} devices")
    
    # Create prefixes for each location first
    print("\n=== Creating Prefixes ===")
    prefix_configs = [
        (dallas_campus["id"], "10.1.0.0/16", "Main network for Dallas Campus"),
        (london_campus["id"], "10.2.0.0/16", "Main network for London Campus"),
        (korea_campus["id"], "10.3.0.0/16", "Main network for Korea Campus"),
        (brazil_campus["id"], "10.4.0.0/16", "Main network for Brazil Campus"),
        (mexico_campus["id"], "10.5.0.0/16", "Main network for Mexico Campus"),
        (nyc_dc["id"], "10.10.0.0/16", "Data center network for NYC"),
        (lon_dc["id"], "10.20.0.0/16", "Data center network for London"),
        (korea_campus["id"], "10.30.0.0/16", "Core network for Korea Campus"),
        (brazil_campus["id"], "10.40.0.0/16", "Core network for Brazil Campus"),
        (mexico_campus["id"], "10.50.0.0/16", "Core network for Mexico Campus"),
        (branch_001["id"], "10.100.1.0/24", "Branch office network 1"),
        (branch_002["id"], "10.100.2.0/24", "Branch office network 2"),
        (branch_003["id"], "10.100.3.0/24", "Branch office network 3"),
        (branch_004["id"], "10.100.4.0/24", "Branch office network 4"),
        (branch_005["id"], "10.100.5.0/24", "Branch office network 5"),
        (branch_006["id"], "10.100.6.0/24", "Branch office network 6"),
        (branch_007["id"], "10.100.7.0/24", "Branch office network 7"),
        (branch_008["id"], "10.100.8.0/24", "Branch office network 8"),
        (None, "203.0.113.0/24", "WAN network for branch offices")
    ]
    
    prefix_count = 0
    for location_id, prefix, description in prefix_configs:
        if create_prefix(prefix, location_id, description, global_ns_id):
            prefix_count += 1
            
            # Create some subnets for each location (skip for WAN networks)
            if location_id:
                for i in range(3):
                    base_prefix = prefix.split('/')[0]
                    base_parts = base_prefix.split('.')
                    if prefix.endswith("/16"):
                        # For /16 networks, create /24 subnets
                        third_octet = int(base_parts[2]) + (i * 50)
                        subnet = f"{base_parts[0]}.{base_parts[1]}.{third_octet}.0/24"
                    else:
                        # For /24 networks, create smaller subnets
                        fourth_octet = int(base_parts[3]) + (i * 10)
                        subnet = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{fourth_octet}/26"
                    if create_prefix(subnet, location_id, f"Subnet {i+1} for location", global_ns_id):
                        prefix_count += 1
    
    # Create /31 prefixes for spine/leaf connections
    print("\n=== Creating /31 Prefixes for Spine/Leaf Connections ===")
    spine_leaf_prefixes = [
        # NYC Data Center Spine/Leaf /31 prefixes
        (nyc_dc["id"], "10.10.100.0/31", "NYDC Spine-Leaf connection 1"),
        (nyc_dc["id"], "10.10.100.2/31", "NYDC Spine-Leaf connection 2"),
        (nyc_dc["id"], "10.10.100.4/31", "NYDC Spine-Leaf connection 3"),
        (nyc_dc["id"], "10.10.100.6/31", "NYDC Spine-Leaf connection 4"),
        (nyc_dc["id"], "10.10.100.8/31", "NYDC Spine-Leaf connection 5"),
        (nyc_dc["id"], "10.10.100.10/31", "NYDC Spine-Leaf connection 6"),
        (nyc_dc["id"], "10.10.100.12/31", "NYDC Spine-Leaf connection 7"),
        (nyc_dc["id"], "10.10.100.14/31", "NYDC Spine-Leaf connection 8"),
        (nyc_dc["id"], "10.10.100.16/31", "NYDC Spine-Leaf connection 9"),
        (nyc_dc["id"], "10.10.100.18/31", "NYDC Spine-Leaf connection 10"),
        (nyc_dc["id"], "10.10.100.20/31", "NYDC Spine-Leaf connection 11"),
        (nyc_dc["id"], "10.10.100.22/31", "NYDC Spine-Leaf connection 12"),
        (nyc_dc["id"], "10.10.100.24/31", "NYDC Spine-Leaf connection 13"),
        (nyc_dc["id"], "10.10.100.26/31", "NYDC Spine-Leaf connection 14"),
        (nyc_dc["id"], "10.10.100.28/31", "NYDC Spine-Leaf connection 15"),
        (nyc_dc["id"], "10.10.100.30/31", "NYDC Spine-Leaf connection 16"),
        (nyc_dc["id"], "10.10.100.32/31", "NYDC Spine-Leaf connection 17"),
        (nyc_dc["id"], "10.10.100.34/31", "NYDC Spine-Leaf connection 18"),
        (nyc_dc["id"], "10.10.100.36/31", "NYDC Spine-Leaf connection 19"),
        (nyc_dc["id"], "10.10.100.38/31", "NYDC Spine-Leaf connection 20"),
        (nyc_dc["id"], "10.10.100.40/31", "NYDC Spine-Leaf connection 21"),
        (nyc_dc["id"], "10.10.100.42/31", "NYDC Spine-Leaf connection 22"),
        (nyc_dc["id"], "10.10.100.44/31", "NYDC Spine-Leaf connection 23"),
        (nyc_dc["id"], "10.10.100.46/31", "NYDC Spine-Leaf connection 24"),
        (nyc_dc["id"], "10.10.100.48/31", "NYDC Spine-Leaf connection 25"),
        (nyc_dc["id"], "10.10.100.50/31", "NYDC Spine-Leaf connection 26"),
        (nyc_dc["id"], "10.10.100.52/31", "NYDC Spine-Leaf connection 27"),
        (nyc_dc["id"], "10.10.100.54/31", "NYDC Spine-Leaf connection 28"),
        (nyc_dc["id"], "10.10.100.56/31", "NYDC Spine-Leaf connection 29"),
        (nyc_dc["id"], "10.10.100.58/31", "NYDC Spine-Leaf connection 30"),
        (nyc_dc["id"], "10.10.100.60/31", "NYDC Spine-Leaf connection 31"),
        (nyc_dc["id"], "10.10.100.62/31", "NYDC Spine-Leaf connection 32"),
        (nyc_dc["id"], "10.10.100.64/31", "NYDC Spine-Leaf connection 33"),
        (nyc_dc["id"], "10.10.100.66/31", "NYDC Spine-Leaf connection 34"),
        (nyc_dc["id"], "10.10.100.68/31", "NYDC Spine-Leaf connection 35"),
        (nyc_dc["id"], "10.10.100.70/31", "NYDC Spine-Leaf connection 36"),
        (nyc_dc["id"], "10.10.100.72/31", "NYDC Spine-Leaf connection 37"),
        (nyc_dc["id"], "10.10.100.74/31", "NYDC Spine-Leaf connection 38"),
        (nyc_dc["id"], "10.10.100.76/31", "NYDC Spine-Leaf connection 39"),
        (nyc_dc["id"], "10.10.100.78/31", "NYDC Spine-Leaf connection 40"),
        (nyc_dc["id"], "10.10.100.80/31", "NYDC Spine-Leaf connection 41"),
        (nyc_dc["id"], "10.10.100.82/31", "NYDC Spine-Leaf connection 42"),
        (nyc_dc["id"], "10.10.100.84/31", "NYDC Spine-Leaf connection 43"),
        (nyc_dc["id"], "10.10.100.86/31", "NYDC Spine-Leaf connection 44"),
        (nyc_dc["id"], "10.10.100.88/31", "NYDC Spine-Leaf connection 45"),
        (nyc_dc["id"], "10.10.100.90/31", "NYDC Spine-Leaf connection 46"),
        (nyc_dc["id"], "10.10.100.92/31", "NYDC Spine-Leaf connection 47"),
        (nyc_dc["id"], "10.10.100.94/31", "NYDC Spine-Leaf connection 48"),
        (nyc_dc["id"], "10.10.100.96/31", "NYDC Spine-Leaf connection 49"),
        (nyc_dc["id"], "10.10.100.98/31", "NYDC Spine-Leaf connection 50"),
        (nyc_dc["id"], "10.10.100.100/31", "NYDC Spine-Leaf connection 51"),
        (nyc_dc["id"], "10.10.100.102/31", "NYDC Spine-Leaf connection 52"),
        (nyc_dc["id"], "10.10.100.104/31", "NYDC Spine-Leaf connection 53"),
        (nyc_dc["id"], "10.10.100.106/31", "NYDC Spine-Leaf connection 54"),
        
        # London Data Center Spine/Leaf /31 prefixes
        (lon_dc["id"], "10.30.100.0/31", "LODC Spine-Leaf connection 1"),
        (lon_dc["id"], "10.30.100.2/31", "LODC Spine-Leaf connection 2"),
        (lon_dc["id"], "10.30.100.4/31", "LODC Spine-Leaf connection 3"),
        (lon_dc["id"], "10.30.100.6/31", "LODC Spine-Leaf connection 4"),
        (lon_dc["id"], "10.30.100.8/31", "LODC Spine-Leaf connection 5"),
        (lon_dc["id"], "10.30.100.10/31", "LODC Spine-Leaf connection 6"),
        (lon_dc["id"], "10.30.100.12/31", "LODC Spine-Leaf connection 7"),
        (lon_dc["id"], "10.30.100.14/31", "LODC Spine-Leaf connection 8"),
        (lon_dc["id"], "10.30.100.16/31", "LODC Spine-Leaf connection 9"),
        (lon_dc["id"], "10.30.100.18/31", "LODC Spine-Leaf connection 10"),
        (lon_dc["id"], "10.30.100.20/31", "LODC Spine-Leaf connection 11"),
        (lon_dc["id"], "10.30.100.22/31", "LODC Spine-Leaf connection 12"),
        (lon_dc["id"], "10.30.100.24/31", "LODC Spine-Leaf connection 13"),
        (lon_dc["id"], "10.30.100.26/31", "LODC Spine-Leaf connection 14"),
        (lon_dc["id"], "10.30.100.28/31", "LODC Spine-Leaf connection 15"),
        (lon_dc["id"], "10.30.100.30/31", "LODC Spine-Leaf connection 16"),
        (lon_dc["id"], "10.30.100.32/31", "LODC Spine-Leaf connection 17"),
        (lon_dc["id"], "10.30.100.34/31", "LODC Spine-Leaf connection 18"),
        (lon_dc["id"], "10.30.100.36/31", "LODC Spine-Leaf connection 19"),
        (lon_dc["id"], "10.30.100.38/31", "LODC Spine-Leaf connection 20"),
        (lon_dc["id"], "10.30.100.40/31", "LODC Spine-Leaf connection 21"),
        (lon_dc["id"], "10.30.100.42/31", "LODC Spine-Leaf connection 22"),
        (lon_dc["id"], "10.30.100.44/31", "LODC Spine-Leaf connection 23"),
        (lon_dc["id"], "10.30.100.46/31", "LODC Spine-Leaf connection 24"),
        (lon_dc["id"], "10.30.100.48/31", "LODC Spine-Leaf connection 25"),
        (lon_dc["id"], "10.30.100.50/31", "LODC Spine-Leaf connection 26"),
        (lon_dc["id"], "10.30.100.52/31", "LODC Spine-Leaf connection 27"),
        (lon_dc["id"], "10.30.100.54/31", "LODC Spine-Leaf connection 28"),
        (lon_dc["id"], "10.30.100.56/31", "LODC Spine-Leaf connection 29"),
        (lon_dc["id"], "10.30.100.58/31", "LODC Spine-Leaf connection 30"),
        (lon_dc["id"], "10.30.100.60/31", "LODC Spine-Leaf connection 31"),
        (lon_dc["id"], "10.30.100.62/31", "LODC Spine-Leaf connection 32"),
        (lon_dc["id"], "10.30.100.64/31", "LODC Spine-Leaf connection 33"),
        (lon_dc["id"], "10.30.100.66/31", "LODC Spine-Leaf connection 34"),
        (lon_dc["id"], "10.30.100.68/31", "LODC Spine-Leaf connection 35"),
        (lon_dc["id"], "10.30.100.70/31", "LODC Spine-Leaf connection 36"),
        (lon_dc["id"], "10.30.100.72/31", "LODC Spine-Leaf connection 37"),
        (lon_dc["id"], "10.30.100.74/31", "LODC Spine-Leaf connection 38"),
        (lon_dc["id"], "10.30.100.76/31", "LODC Spine-Leaf connection 39"),
        (lon_dc["id"], "10.30.100.78/31", "LODC Spine-Leaf connection 40"),
        (lon_dc["id"], "10.30.100.80/31", "LODC Spine-Leaf connection 41"),
        (lon_dc["id"], "10.30.100.82/31", "LODC Spine-Leaf connection 42"),
        (lon_dc["id"], "10.30.100.84/31", "LODC Spine-Leaf connection 43"),
        (lon_dc["id"], "10.30.100.86/31", "LODC Spine-Leaf connection 44"),
        (lon_dc["id"], "10.30.100.88/31", "LODC Spine-Leaf connection 45"),
        (lon_dc["id"], "10.30.100.90/31", "LODC Spine-Leaf connection 46"),
        (lon_dc["id"], "10.30.100.92/31", "LODC Spine-Leaf connection 47"),
        (lon_dc["id"], "10.30.100.94/31", "LODC Spine-Leaf connection 48"),
        (lon_dc["id"], "10.30.100.96/31", "LODC Spine-Leaf connection 49"),
        (lon_dc["id"], "10.30.100.98/31", "LODC Spine-Leaf connection 50"),
        (lon_dc["id"], "10.30.100.100/31", "LODC Spine-Leaf connection 51"),
        (lon_dc["id"], "10.30.100.102/31", "LODC Spine-Leaf connection 52"),
        (lon_dc["id"], "10.30.100.104/31", "LODC Spine-Leaf connection 53"),
        (lon_dc["id"], "10.30.100.106/31", "LODC Spine-Leaf connection 54"),
        (lon_dc["id"], "10.30.100.108/31", "LODC Spine-Leaf connection 55"),
        (lon_dc["id"], "10.30.100.110/31", "LODC Spine-Leaf connection 56"),
        (lon_dc["id"], "10.30.100.112/31", "LODC Spine-Leaf connection 57"),
        (lon_dc["id"], "10.30.100.114/31", "LODC Spine-Leaf connection 58"),
        (lon_dc["id"], "10.30.100.116/31", "LODC Spine-Leaf connection 59"),
        (lon_dc["id"], "10.30.100.118/31", "LODC Spine-Leaf connection 60"),
        (lon_dc["id"], "10.30.100.120/31", "LODC Spine-Leaf connection 61"),
        (lon_dc["id"], "10.30.100.122/31", "LODC Spine-Leaf connection 62"),
        (lon_dc["id"], "10.30.100.124/31", "LODC Spine-Leaf connection 63"),
        (lon_dc["id"], "10.30.100.126/31", "LODC Spine-Leaf connection 64"),
        
        # London Data Center Leaf Compute /31 prefixes
        (lon_dc["id"], "10.30.200.0/31", "LODC Leaf-Compute connection 1"),
        (lon_dc["id"], "10.30.200.2/31", "LODC Leaf-Compute connection 2"),
        (lon_dc["id"], "10.30.200.4/31", "LODC Leaf-Compute connection 3"),
        (lon_dc["id"], "10.30.200.6/31", "LODC Leaf-Compute connection 4"),
        (lon_dc["id"], "10.30.200.8/31", "LODC Leaf-Compute connection 5"),
        (lon_dc["id"], "10.30.200.10/31", "LODC Leaf-Compute connection 6"),
        (lon_dc["id"], "10.30.200.12/31", "LODC Leaf-Compute connection 7"),
        (lon_dc["id"], "10.30.200.14/31", "LODC Leaf-Compute connection 8"),
        (lon_dc["id"], "10.30.200.16/31", "LODC Leaf-Compute connection 9"),
        (lon_dc["id"], "10.30.200.18/31", "LODC Leaf-Compute connection 10"),
        (lon_dc["id"], "10.30.200.20/31", "LODC Leaf-Compute connection 11"),
        (lon_dc["id"], "10.30.200.22/31", "LODC Leaf-Compute connection 12"),
        (lon_dc["id"], "10.30.200.24/31", "LODC Leaf-Compute connection 13"),
        (lon_dc["id"], "10.30.200.26/31", "LODC Leaf-Compute connection 14"),
        (lon_dc["id"], "10.30.200.28/31", "LODC Leaf-Compute connection 15"),
        (lon_dc["id"], "10.30.200.30/31", "LODC Leaf-Compute connection 16"),
        (lon_dc["id"], "10.30.200.32/31", "LODC Leaf-Compute connection 17"),
        (lon_dc["id"], "10.30.200.34/31", "LODC Leaf-Compute connection 18"),
        (lon_dc["id"], "10.30.200.36/31", "LODC Leaf-Compute connection 19"),
        (lon_dc["id"], "10.30.200.38/31", "LODC Leaf-Compute connection 20"),
        (lon_dc["id"], "10.30.200.40/31", "LODC Leaf-Compute connection 21"),
        (lon_dc["id"], "10.30.200.42/31", "LODC Leaf-Compute connection 22"),
        (lon_dc["id"], "10.30.200.44/31", "LODC Leaf-Compute connection 23"),
        (lon_dc["id"], "10.30.200.46/31", "LODC Leaf-Compute connection 24"),
        (lon_dc["id"], "10.30.200.48/31", "LODC Leaf-Compute connection 25"),
        (lon_dc["id"], "10.30.200.50/31", "LODC Leaf-Compute connection 26"),
        (lon_dc["id"], "10.30.200.52/31", "LODC Leaf-Compute connection 27"),
        (lon_dc["id"], "10.30.200.54/31", "LODC Leaf-Compute connection 28"),
        (lon_dc["id"], "10.30.200.56/31", "LODC Leaf-Compute connection 29"),
        (lon_dc["id"], "10.30.200.58/31", "LODC Leaf-Compute connection 30"),
        (lon_dc["id"], "10.30.200.60/31", "LODC Leaf-Compute connection 31"),
        (lon_dc["id"], "10.30.200.62/31", "LODC Leaf-Compute connection 32"),
    ]
    
    for location_id, prefix, description in spine_leaf_prefixes:
        if create_prefix(prefix, location_id, description, global_ns_id):
            prefix_count += 1
    
    print(f"Created {prefix_count} prefixes total")
    
    # Create interfaces and IP addresses (skip cleanup to preserve existing assignments)
    print("\n=== Creating Interfaces and IP Addresses ===")
    interface_configs = [
        # WAN Router interfaces
        ("DALCN-WAN01", "GigabitEthernet0/0/0", "10.1.1.1/24", "WAN uplink to MPLS"),
        ("DALCN-WAN01", "GigabitEthernet0/0/1", "10.1.2.1/24", "Link to COR01"),
        ("DALCN-WAN01", "GigabitEthernet0/0/2", "10.1.3.1/24", "Link to COR02"),
        ("DALCN-WAN02", "GigabitEthernet0/0/0", "10.1.4.1/24", "WAN uplink to Internet"),
        ("DALCN-WAN02", "GigabitEthernet0/0/1", "10.1.5.1/24", "Link to COR01"),
        ("DALCN-WAN02", "GigabitEthernet0/0/2", "10.1.6.1/24", "Link to COR02"),
        ("LOCN-WAN01", "GigabitEthernet0/0/0", "10.2.1.1/24", "WAN uplink to MPLS"),
        ("LOCN-WAN01", "GigabitEthernet0/0/1", "10.2.2.1/24", "Link to COR01"),
        ("LOCN-WAN01", "GigabitEthernet0/0/2", "10.2.3.1/24", "Link to COR02"),
        ("LOCN-WAN02", "GigabitEthernet0/0/0", "10.2.4.1/24", "WAN uplink to Internet"),
        ("LOCN-WAN02", "GigabitEthernet0/0/1", "10.2.5.1/24", "Link to COR01"),
        ("LOCN-WAN02", "GigabitEthernet0/0/2", "10.2.6.1/24", "Link to COR02"),
        ("KOCN-WAN01", "GigabitEthernet0/0/0", "10.3.1.1/24", "WAN uplink to MPLS"),
        ("KOCN-WAN01", "GigabitEthernet0/0/1", "10.3.2.1/24", "Link to COR01"),
        ("KOCN-WAN01", "GigabitEthernet0/0/2", "10.3.3.1/24", "Link to COR02"),
        ("KOCN-WAN02", "GigabitEthernet0/0/0", "10.3.4.1/24", "WAN uplink to Internet"),
        ("KOCN-WAN02", "GigabitEthernet0/0/1", "10.3.5.1/24", "Link to COR01"),
        ("KOCN-WAN02", "GigabitEthernet0/0/2", "10.3.6.1/24", "Link to COR02"),
        ("BRCN-WAN01", "GigabitEthernet0/0/0", "10.4.1.1/24", "WAN uplink to MPLS"),
        ("BRCN-WAN01", "GigabitEthernet0/0/1", "10.4.2.1/24", "Link to COR01"),
        ("BRCN-WAN01", "GigabitEthernet0/0/2", "10.4.3.1/24", "Link to COR02"),
        ("BRCN-WAN02", "GigabitEthernet0/0/0", "10.4.4.1/24", "WAN uplink to Internet"),
        ("BRCN-WAN02", "GigabitEthernet0/0/1", "10.4.5.1/24", "Link to COR01"),
        ("BRCN-WAN02", "GigabitEthernet0/0/2", "10.4.6.1/24", "Link to COR02"),
        ("MXCN-WAN01", "GigabitEthernet0/0/0", "10.5.1.1/24", "WAN uplink to MPLS"),
        ("MXCN-WAN01", "GigabitEthernet0/0/1", "10.5.2.1/24", "Link to COR01"),
        ("MXCN-WAN01", "GigabitEthernet0/0/2", "10.5.3.1/24", "Link to COR02"),
        ("MXCN-WAN02", "GigabitEthernet0/0/0", "10.5.4.1/24", "WAN uplink to Internet"),
        ("MXCN-WAN02", "GigabitEthernet0/0/1", "10.5.5.1/24", "Link to COR01"),
        ("MXCN-WAN02", "GigabitEthernet0/0/2", "10.5.6.1/24", "Link to COR02"),
        
        # Core Router interfaces
        ("DALCN-COR01", "GigabitEthernet0/0/0", "10.10.1.1/24", "Core network uplink to WAN01"),
        ("DALCN-COR01", "GigabitEthernet0/0/1", "10.10.2.1/24", "Core network uplink to WAN02"),
        ("DALCN-COR01", "GigabitEthernet0/0/2", "10.10.3.1/24", "network link to ACC01"),
        ("DALCN-COR01", "GigabitEthernet0/0/3", "10.10.4.1/24", "network link to ACC02"),
        ("LOCN-COR01", "GigabitEthernet0/0/0", "10.20.1.1/24", "Core network uplink to WAN01"),
        ("LOCN-COR01", "GigabitEthernet0/0/1", "10.20.2.1/24", "Core network uplink to WAN02"),
        ("LOCN-COR01", "GigabitEthernet0/0/2", "10.20.3.1/24", "network link to ACC01"),
        ("LOCN-COR01", "GigabitEthernet0/0/3", "10.20.4.1/24", "network link to ACC02"),
        ("KOCN-COR01", "GigabitEthernet0/0/0", "10.30.1.1/24", "Core network uplink to WAN01"),
        ("KOCN-COR01", "GigabitEthernet0/0/1", "10.30.2.1/24", "Core network uplink to WAN02"),
        ("KOCN-COR01", "GigabitEthernet0/0/2", "10.30.3.1/24", "network link to ACC01"),
        ("KOCN-COR01", "GigabitEthernet0/0/3", "10.30.4.1/24", "network link to ACC02"),
        ("BRCN-COR01", "GigabitEthernet0/0/0", "10.40.1.1/24", "Core network uplink to WAN01"),
        ("BRCN-COR01", "GigabitEthernet0/0/1", "10.40.2.1/24", "Core network uplink to WAN02"),
        ("BRCN-COR01", "GigabitEthernet0/0/2", "10.40.3.1/24", "network link to ACC01"),
        ("BRCN-COR01", "GigabitEthernet0/0/3", "10.40.4.1/24", "network link to ACC02"),
        ("MXCN-COR01", "GigabitEthernet0/0/0", "10.50.1.1/24", "Core network uplink to WAN01"),
        ("MXCN-COR01", "GigabitEthernet0/0/1", "10.50.2.1/24", "Core network uplink to WAN02"),
        ("MXCN-COR01", "GigabitEthernet0/0/2", "10.50.3.1/24", "network link to ACC01"),
        ("MXCN-COR01", "GigabitEthernet0/0/3", "10.50.4.1/24", "network link to ACC02"),
        
        # Access Switch interfaces
        ("DALCN-ACC01", "Ethernet1/1", "10.1.10.1/24", "Uplink to COR01"),
        ("DALCN-ACC01", "Ethernet1/2", "10.1.11.1/24", "Uplink to COR02"),
        ("DALCN-ACC01", "Ethernet1/3", "no_ip", "User Access Port"),
        ("DALCN-ACC01", "Ethernet1/4", "no_ip", "User Access Port"),
        ("DALCN-ACC01", "Ethernet1/5", "no_ip", "User Access Port"),
        ("DALCN-ACC01", "Ethernet1/6", "no_ip", "User Access Port"),
        ("LOCN-ACC01", "Ethernet1/1", "10.2.10.1/24", "Uplink to COR01"),
        ("LOCN-ACC01", "Ethernet1/2", "10.2.11.1/24", "Uplink to COR02"),
        ("LOCN-ACC01", "Ethernet1/3", "no_ip", "User Access Port"),
        ("LOCN-ACC01", "Ethernet1/4", "no_ip", "User Access Port"),
        ("LOCN-ACC01", "Ethernet1/5", "no_ip", "User Access Port"),
        ("LOCN-ACC01", "Ethernet1/6", "no_ip", "User Access Port"),
        ("KOCN-ACC01", "Ethernet1/1", "10.3.10.1/24", "Uplink to COR01"),
        ("KOCN-ACC01", "Ethernet1/2", "10.3.11.1/24", "Uplink to COR02"),
        ("KOCN-ACC01", "Ethernet1/3", "no_ip", "User Access Port"),
        ("KOCN-ACC01", "Ethernet1/4", "no_ip", "User Access Port"),
        ("KOCN-ACC01", "Ethernet1/5", "no_ip", "User Access Port"),
        ("KOCN-ACC01", "Ethernet1/6", "no_ip", "User Access Port"),
        ("BRCN-ACC01", "Ethernet1/1", "10.4.10.1/24", "Uplink to COR01"),
        ("BRCN-ACC01", "Ethernet1/2", "10.4.11.1/24", "Uplink to COR02"),
        ("BRCN-ACC01", "Ethernet1/3", "no_ip", "User Access Port"),
        ("BRCN-ACC01", "Ethernet1/4", "no_ip", "User Access Port"),
        ("BRCN-ACC01", "Ethernet1/5", "no_ip", "User Access Port"),
        ("BRCN-ACC01", "Ethernet1/6", "no_ip", "User Access Port"),
        ("MXCN-ACC01", "Ethernet1/1", "10.5.10.1/24", "Uplink to COR01"),
        ("MXCN-ACC01", "Ethernet1/2", "10.5.11.1/24", "Uplink to COR02"),
        ("MXCN-ACC01", "Ethernet1/3", "no_ip", "User Access Port"),
        ("MXCN-ACC01", "Ethernet1/4", "no_ip", "User Access Port"),
        ("MXCN-ACC01", "Ethernet1/5", "no_ip", "User Access Port"),
        ("MXCN-ACC01", "Ethernet1/6", "no_ip", "User Access Port"),
        
        # Spine/Leaf Interfaces
        ("NYDC-SPN1000", "Ethernet1", "10.10.100.1/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet2", "10.10.100.3/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet3", "10.10.100.5/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet4", "10.10.100.7/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet5", "10.10.100.9/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet6", "10.10.100.11/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet7", "10.10.100.13/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet8", "10.10.100.15/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet9", "10.10.100.17/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet10", "10.10.100.19/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet11", "10.10.100.21/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet12", "10.10.100.23/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet13", "10.10.100.25/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet14", "10.10.100.27/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet15", "10.10.100.29/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1000", "Ethernet16", "10.10.100.31/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet1", "10.10.100.11/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet2", "10.10.100.13/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet3", "10.10.100.15/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet4", "10.10.100.17/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet5", "10.10.100.19/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet6", "10.10.100.21/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet7", "10.10.100.23/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet8", "10.10.100.25/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet9", "10.10.100.27/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet10", "10.10.100.29/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet11", "10.10.100.31/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet12", "10.10.100.33/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet13", "10.10.100.35/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet14", "10.10.100.37/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet15", "10.10.100.39/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1001", "Ethernet16", "10.10.100.41/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet1", "10.10.100.43/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet2", "10.10.100.45/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet3", "10.10.100.47/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet4", "10.10.100.49/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet5", "10.10.100.51/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet6", "10.10.100.53/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet7", "10.10.100.55/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet8", "10.10.100.57/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet9", "10.10.100.59/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet10", "10.10.100.61/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet11", "10.10.100.63/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet12", "10.10.100.65/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet13", "10.10.100.67/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet14", "10.10.100.69/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet15", "10.10.100.71/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1002", "Ethernet16", "10.10.100.73/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet1", "10.10.100.75/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet2", "10.10.100.77/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet3", "10.10.100.79/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet4", "10.10.100.81/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet5", "10.10.100.83/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet6", "10.10.100.85/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet7", "10.10.100.87/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet8", "10.10.100.89/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet9", "10.10.100.91/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet10", "10.10.100.93/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet11", "10.10.100.95/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet12", "10.10.100.97/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet13", "10.10.100.99/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet14", "10.10.100.101/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet15", "10.10.100.103/31", "Spine to Leaf uplink"),
        ("NYDC-SPN1003", "Ethernet16", "10.10.100.105/31", "Spine to Leaf uplink"),
        
        ("NYDC-LEAF1000", "Ethernet1", "10.20.100.2/31", "Uplink to SPN1000"),
        ("NYDC-LEAF1000", "Ethernet2", "10.20.100.4/31", "Uplink to SPN1001"),
        ("NYDC-LEAF1000", "Ethernet3", "10.20.100.6/31", "Uplink to SPN1002"),
        ("NYDC-LEAF1000", "Ethernet4", "10.20.100.8/31", "Uplink to SPN1003"),
        ("NYDC-LEAF1000", "Ethernet5", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1000", "Ethernet6", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1000", "Ethernet7", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1000", "Ethernet8", "no_ip", "Compute Interface"),

        ("NYDC-LEAF1001", "Ethernet1", "10.20.100.10/31", "Uplink to SPN1000"),
        ("NYDC-LEAF1001", "Ethernet2", "10.20.100.12/31", "Uplink to SPN1001"),
        ("NYDC-LEAF1001", "Ethernet3", "10.20.100.14/31", "Uplink to SPN1002"),
        ("NYDC-LEAF1001", "Ethernet4", "10.20.100.16/31", "Uplink to SPN1003"),
        ("NYDC-LEAF1001", "Ethernet5", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1001", "Ethernet6", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1001", "Ethernet7", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1001", "Ethernet8", "no_ip", "Compute Interface"),

        ("NYDC-LEAF1002", "Ethernet1", "10.20.100.18/31", "Uplink to SPN1000"),
        ("NYDC-LEAF1002", "Ethernet2", "10.20.100.20/31", "Uplink to SPN1001"),
        ("NYDC-LEAF1002", "Ethernet3", "10.20.100.22/31", "Uplink to SPN1002"),
        ("NYDC-LEAF1002", "Ethernet4", "10.20.100.24/31", "Uplink to SPN1003"),
        ("NYDC-LEAF1002", "Ethernet5", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1002", "Ethernet6", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1002", "Ethernet7", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1002", "Ethernet8", "no_ip", "Compute Interface"),

        ("NYDC-LEAF1003", "Ethernet1", "10.20.100.26/31", "Uplink to SPN1000"),
        ("NYDC-LEAF1003", "Ethernet2", "10.20.100.28/31", "Uplink to SPN1001"),
        ("NYDC-LEAF1003", "Ethernet3", "10.20.100.30/31", "Uplink to SPN1002"),
        ("NYDC-LEAF1003", "Ethernet4", "10.20.100.32/31", "Uplink to SPN1003"),
        ("NYDC-LEAF1003", "Ethernet5", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1003", "Ethernet6", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1003", "Ethernet7", "no_ip", "Compute Interface"),
        ("NYDC-LEAF1003", "Ethernet8", "no_ip", "Compute Interface"),


        ("LODC-SPN1000", "Ethernet1", "10.30.100.0/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet2", "10.30.100.2/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet3", "10.30.100.4/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet4", "10.30.100.6/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet5", "10.30.100.8/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet6", "10.30.100.10/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet7", "10.30.100.12/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet8", "10.30.100.14/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet9", "10.30.100.16/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet10", "10.30.100.18/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet11", "10.30.100.20/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet12", "10.30.100.22/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet13", "10.30.100.24/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet14", "10.30.100.26/31", "Core network backup"),
        ("LODC-SPN1000", "Ethernet15", "10.30.100.28/31", "Core network uplink"),
        ("LODC-SPN1000", "Ethernet16", "10.30.100.30/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet1", "10.30.100.32/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet2", "10.30.100.34/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet3", "10.30.100.36/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet4", "10.30.100.38/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet5", "10.30.100.40/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet6", "10.30.100.42/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet7", "10.30.100.44/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet8", "10.30.100.46/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet9", "10.30.100.48/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet10", "10.30.100.50/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet11", "10.30.100.52/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet12", "10.30.100.54/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet13", "10.30.100.56/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet14", "10.30.100.58/31", "Core network backup"),
        ("LODC-SPN1001", "Ethernet15", "10.30.100.60/31", "Core network uplink"),
        ("LODC-SPN1001", "Ethernet16", "10.30.100.62/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet1", "10.30.100.64/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet2", "10.30.100.66/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet3", "10.30.100.68/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet4", "10.30.100.70/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet5", "10.30.100.72/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet6", "10.30.100.74/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet7", "10.30.100.76/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet8", "10.30.100.78/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet9", "10.30.100.80/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet10", "10.30.100.82/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet11", "10.30.100.84/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet12", "10.30.100.86/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet13", "10.30.100.88/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet14", "10.30.100.90/31", "Core network backup"),
        ("LODC-SPN1002", "Ethernet15", "10.30.100.92/31", "Core network uplink"),
        ("LODC-SPN1002", "Ethernet16", "10.30.100.94/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet1", "10.30.100.96/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet2", "10.30.100.98/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet3", "10.30.100.100/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet4", "10.30.100.102/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet5", "10.30.100.104/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet6", "10.30.100.106/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet7", "10.30.100.108/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet8", "10.30.100.110/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet9", "10.30.100.112/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet10", "10.30.100.114/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet11", "10.30.100.116/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet12", "10.30.100.118/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet13", "10.30.100.120/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet14", "10.30.100.122/31", "Core network backup"),
        ("LODC-SPN1003", "Ethernet15", "10.30.100.124/31", "Core network uplink"),
        ("LODC-SPN1003", "Ethernet16", "10.30.100.126/31", "Core network backup"),

        # LODC Leaf interfaces - Uplinks to Spines
        ("LODC-LEAF1000", "Ethernet1", "10.30.200.1/31", "Uplink to Spine 1"),
        ("LODC-LEAF1000", "Ethernet2", "10.30.200.3/31", "Uplink to Spine 2"), 
        ("LODC-LEAF1000", "Ethernet3", "10.30.200.5/31", "Uplink to Spine 3"),
        ("LODC-LEAF1000", "Ethernet4", "10.30.200.7/31", "Uplink to Spine 4"),
        ("LODC-LEAF1000", "Ethernet5", "10.30.200.9/31", "Compute Server 1"),
        ("LODC-LEAF1000", "Ethernet6", "10.30.200.11/31", "Compute Server 2"),
        ("LODC-LEAF1000", "Ethernet7", "10.30.200.13/31", "Compute Server 3"),
        ("LODC-LEAF1000", "Ethernet8", "10.30.200.15/31", "Compute Server 4"),

        ("LODC-LEAF1001", "Ethernet1", "10.30.200.17/31", "Uplink to Spine 1"),
        ("LODC-LEAF1001", "Ethernet2", "10.30.200.19/31", "Uplink to Spine 2"),
        ("LODC-LEAF1001", "Ethernet3", "10.30.200.21/31", "Uplink to Spine 3"),
        ("LODC-LEAF1001", "Ethernet4", "10.30.200.23/31", "Uplink to Spine 4"),
        ("LODC-LEAF1001", "Ethernet5", "10.30.200.25/31", "Compute Server 1"),
        ("LODC-LEAF1001", "Ethernet6", "10.30.200.27/31", "Compute Server 2"),
        ("LODC-LEAF1001", "Ethernet7", "10.30.200.29/31", "Compute Server 3"),
        ("LODC-LEAF1001", "Ethernet8", "10.30.200.31/31", "Compute Server 4"),

        ("LODC-LEAF1002", "Ethernet1", "10.30.200.33/31", "Uplink to Spine 1"),
        ("LODC-LEAF1002", "Ethernet2", "10.30.200.35/31", "Uplink to Spine 2"),
        ("LODC-LEAF1002", "Ethernet3", "10.30.200.37/31", "Uplink to Spine 3"),
        ("LODC-LEAF1002", "Ethernet4", "10.30.200.39/31", "Uplink to Spine 4"),
        ("LODC-LEAF1002", "Ethernet5", "10.30.200.41/31", "Compute Server 1"),
        ("LODC-LEAF1002", "Ethernet6", "10.30.200.43/31", "Compute Server 2"),
        ("LODC-LEAF1002", "Ethernet7", "10.30.200.45/31", "Compute Server 3"),
        ("LODC-LEAF1002", "Ethernet8", "10.30.200.47/31", "Compute Server 4"),

        ("LODC-LEAF1003", "Ethernet1", "10.30.200.49/31", "Uplink to Spine 1"),
        ("LODC-LEAF1003", "Ethernet2", "10.30.200.51/31", "Uplink to Spine 2"),
        ("LODC-LEAF1003", "Ethernet3", "10.30.200.53/31", "Uplink to Spine 3"),
        ("LODC-LEAF1003", "Ethernet4", "10.30.200.55/31", "Uplink to Spine 4"),
        ("LODC-LEAF1003", "Ethernet5", "10.30.200.57/31", "Compute Server 1"),
        ("LODC-LEAF1003", "Ethernet6", "10.30.200.59/31", "Compute Server 2"),
        ("LODC-LEAF1003", "Ethernet7", "10.30.200.61/31", "Compute Server 3"),
        ("LODC-LEAF1003", "Ethernet8", "10.30.200.63/31", "Compute Server 4"),
        
        # WAN Router interfaces
        ("USBN1-WAN01", "Ethernet0/0", "203.0.113.1/24", "Internet WAN"),
        ("USBN1-WAN01", "Ethernet0/1", "10.100.1.0/31", "Link to SW01"),
        ("USBN1-WAN02", "Ethernet0/2", "10.100.1.2/31", "Link to SW02"),
        ("USBN1-SW01", "Ethernet1/1", "10.100.1.1/31", "Uplink to WAN01"),
        ("USBN1-SW01", "Vlan101", "10.100.1.129/24", "User Data VLAN"),
        ("USBN1-SW02", "Ethernet1/1", "10.100.1.3/31", "Uplink to WAN02"),
        ("USBN1-SW02", "Vlan101", "10.100.1.130/24", "User Data VLAN"),

        ("MXBN1-WAN01", "Ethernet0/0", "203.0.113.2/24", "Internet WAN"),
        ("MXBN1-WAN01", "Ethernet0/1", "10.100.2.0/31", "Link to SW01"),
        ("MXBN1-WAN02", "Ethernet0/2", "10.100.2.2/31", "Link to SW02"),
        ("MXBN1-SW01", "Ethernet1/1", "10.100.2.1/31", "Uplink to WAN01"),
        ("MXBN1-SW01", "Vlan101", "10.100.2.129/24", "User Data VLAN"),
        ("MXBN1-SW02", "Ethernet1/1", "10.100.2.3/31", "Uplink to WAN02"),
        ("MXBN1-SW02", "Vlan101", "10.100.2.130/24", "User Data VLAN"),

        ("UKBN1-WAN01", "Ethernet0/0", "203.0.113.3/24", "Internet WAN"), 
        ("UKBN1-WAN01", "Ethernet0/1", "10.100.3.0/31", "Link to SW01"),
        ("UKBN1-WAN02", "Ethernet0/2", "10.100.3.2/31", "Link to SW02"),
        ("UKBN1-SW01", "Ethernet1/1", "10.100.3.1/31", "Uplink to WAN01"),
        ("UKBN1-SW01", "Vlan101", "10.100.3.129/24", "User Data VLAN"),
        ("UKBN1-SW02", "Ethernet1/1", "10.100.3.3/31", "Uplink to WAN02"),
        ("UKBN1-SW02", "Vlan101", "10.100.3.130/24", "User Data VLAN"),

        ("BRBN1-WAN01", "Ethernet0/0", "203.0.113.4/24", "Internet WAN"),
        ("BRBN1-WAN01", "Ethernet0/1", "10.100.4.0/31", "Link to SW01"), 
        ("BRBN1-WAN02", "Ethernet0/2", "10.100.4.2/31", "Link to SW02"),
        ("BRBN1-SW01", "Ethernet1/1", "10.100.4.1/31", "Uplink to WAN01"),
        ("BRBN1-SW01", "Vlan101", "10.100.4.129/24", "User Data VLAN"),
        ("BRBN1-SW02", "Ethernet1/1", "10.100.4.3/31", "Uplink to WAN02"),
        ("BRBN1-SW02", "Vlan101", "10.100.4.130/24", "User Data VLAN"),

        ("USBN2-WAN01", "Ethernet0/0", "203.0.113.5/24", "Internet WAN"),
        ("USBN2-WAN01", "Ethernet0/1", "10.100.5.0/31", "Link to SW01"),
        ("USBN2-WAN02", "Ethernet0/2", "10.100.5.2/31", "Link to SW02"), 
        ("USBN2-SW01", "Ethernet1/1", "10.100.5.1/31", "Uplink to WAN01"),
        ("USBN2-SW01", "Vlan101", "10.100.5.129/24", "User Data VLAN"),
        ("USBN2-SW02", "Ethernet1/1", "10.100.5.3/31", "Uplink to WAN02"),
        ("USBN2-SW02", "Vlan101", "10.100.5.130/24", "User Data VLAN"),

        ("MXBN2-WAN01", "Ethernet0/0", "203.0.113.6/24", "Internet WAN"),
        ("MXBN2-WAN01", "Ethernet0/1", "10.100.6.0/31", "Link to SW01"),
        ("MXBN2-WAN02", "Ethernet0/2", "10.100.6.2/31", "Link to SW02"),
        ("MXBN2-SW01", "Ethernet1/1", "10.100.6.1/31", "Uplink to WAN01"),
        ("MXBN2-SW01", "Vlan101", "10.100.6.129/24", "User Data VLAN"),
        ("MXBN2-SW02", "Ethernet1/1", "10.100.6.3/31", "Uplink to WAN02"),
        ("MXBN2-SW02", "Vlan101", "10.100.6.130/24", "User Data VLAN"),

        ("UKBN2-WAN01", "Ethernet0/0", "203.0.113.7/24", "Internet WAN"),
        ("UKBN2-WAN01", "Ethernet0/1", "10.100.7.0/31", "Link to SW01"),
        ("UKBN2-WAN02", "Ethernet0/2", "10.100.7.2/31", "Link to SW02"),
        ("UKBN2-SW01", "Ethernet1/1", "10.100.7.1/31", "Uplink to WAN01"),
        ("UKBN2-SW01", "Vlan101", "10.100.7.129/24", "User Data VLAN"),
        ("UKBN2-SW02", "Ethernet1/1", "10.100.7.3/31", "Uplink to WAN02"),
        ("UKBN2-SW02", "Vlan101", "10.100.7.130/24", "User Data VLAN"),

        ("BRBN2-WAN01", "Ethernet0/0", "203.0.113.8/24", "Internet WAN"),
        ("BRBN2-WAN01", "Ethernet0/1", "10.100.8.0/31", "Link to SW01"),
        ("BRBN2-WAN02", "Ethernet0/2", "10.100.8.2/31", "Link to SW02"),
        ("BRBN2-SW01", "Ethernet1/1", "10.100.8.1/31", "Uplink to WAN01"),
        ("BRBN2-SW01", "Vlan101", "10.100.8.129/24", "User Data VLAN"),
        ("BRBN2-SW02", "Ethernet1/1", "10.100.8.3/31", "Uplink to WAN02"),
        ("BRBN2-SW02", "Vlan101", "10.100.8.130/24", "User Data VLAN"),

        # Branch Switch Access Ports
        ("USBN1-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("USBN1-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("MXBN1-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("MXBN1-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("UKBN1-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("UKBN1-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("BRBN1-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("BRBN1-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("USBN2-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("USBN2-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("MXBN2-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("MXBN2-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("UKBN2-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("UKBN2-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
        ("BRBN2-SW01", "Ethernet1/3", "no_ip", "Branch Access Port"),
        ("BRBN2-SW01", "Ethernet1/4", "no_ip", "Branch Access Port"),
    ]
    
    interface_count = 0
    ip_count = 0
    print(f"Starting interface creation for {len(interface_configs)} interface configurations")
    print(f"Available devices: {list(device_ids.keys())}")
    
    for device_name, interface_name, ip_address, description in interface_configs:
        if device_name in device_ids:
            print(f"Creating interface {interface_name} for device {device_name}")
            # Ensure interface exists or fetch it
            interface = create_interface(device_ids[device_name], interface_name, description=description)
            if not interface:
                # Try to fetch existing interface
                get_if = requests.get(
                    f"{NAUTOBOT_URL}/api/dcim/interfaces/",
                    params={"device_id": device_ids[device_name], "name": interface_name},
                    headers=HEADERS
                )
                if get_if.status_code == 200 and get_if.json().get("results"):
                    interface = get_if.json()["results"][0]
            if interface:
                interface_count += 1
                # Only create IP address if it's not "no_ip"
                if ip_address != "no_ip":
                    print(f"Creating IP address {ip_address} for interface {interface_name}")
                    # First create the IP address (without assignment)
                    ip_result = create_ip_address(ip_address, global_ns_id, active_status_id)
                    if ip_result:
                        # Then assign it to the interface by updating the IP address
                        if assign_ip_to_interface(ip_result["id"], interface["id"]):
                            ip_count += 1
                            print(f"Successfully created and assigned IP {ip_address} to interface {interface_name}")
                        else:
                            print(f"Failed to assign IP {ip_address} to interface {interface_name}")
                    else:
                        print(f"Failed to create IP {ip_address} for interface {interface_name}")
                else:
                    print(f"Skipping IP creation for interface {interface_name} (no_ip)")
        else:
            print(f"WARNING: Device {device_name} not found in device_ids")
    
    print(f"Created {interface_count} interfaces (created or matched) and {ip_count} IP addresses")
    

    
    # Create circuit types and providers
    print("\n=== Creating Circuit Types and Providers ===")
    mpls_type = create_circuit_type("MPLS", "mpls", "Multiprotocol Label Switching circuit")
    internet_type = create_circuit_type("Internet WAN", "internet-wan", "Internet WAN circuit")
    
    if not mpls_type or not internet_type:
        print("ERROR: Failed to create circuit types")
        return
    
    # Create providers
    providers = [
        ("AT&T", "att", "AT&T Communications"),
        ("AT&T-MEX", "att-mex", "AT&T Communications Mexico"),
        ("Verizon", "verizon", "Verizon Business"),
        ("Comcast", "comcast", "Comcast Business"),
        ("Comcast-MEX", "comcast-mex", "Comcast Business Mexico"),
        ("CenturyLink", "centurylink", "CenturyLink"),
        ("Cogent", "cogent", "Cogent Communications"),
        ("Level 3", "level3", "Level 3 Communications"),
        ("Zayo", "zayo", "Zayo Group"),
        ("Windstream", "windstream", "Windstream Communications")
    ]
    
    provider_ids = {}
    for name, slug, description in providers:
        provider = create_provider(name, slug, description)
        if provider:
            provider_ids[name] = provider["id"]
        else:
            print(f"ERROR: Failed to create provider {name}")
            return
    
    # Create circuits for campuses and branches
    print("\n=== Creating Circuits ===")
    

    
    # Clean up existing circuit terminations and cables first
    print("\n=== Cleaning up existing circuit terminations and cables ===")
    
    # Delete existing cables
    cables_response = requests.get(f"{NAUTOBOT_URL}/api/dcim/cables/", headers=HEADERS)
    if cables_response.status_code == 200:
        existing_cables = cables_response.json().get("results", [])
        for cable in existing_cables:
            delete_response = requests.delete(f"{NAUTOBOT_URL}/api/dcim/cables/{cable['id']}/", headers=HEADERS)
            if delete_response.status_code == 204:
                print(f"Deleted cable {cable['id']}")
    
    # Delete existing circuit terminations
    terminations_response = requests.get(f"{NAUTOBOT_URL}/api/circuits/circuit-terminations/", headers=HEADERS)
    if terminations_response.status_code == 200:
        existing_terminations = terminations_response.json().get("results", [])
        for termination in existing_terminations:
            delete_response = requests.delete(f"{NAUTOBOT_URL}/api/circuits/circuit-terminations/{termination['id']}/", headers=HEADERS)
            if delete_response.status_code == 204:
                print(f"Deleted circuit termination {termination['id']}")
    
    # Delete ALL existing circuits (complete cleanup)
    print("Deleting ALL existing circuits...")
    circuits_response = requests.get(f"{NAUTOBOT_URL}/api/circuits/circuits/", headers=HEADERS)
    if circuits_response.status_code == 200:
        existing_circuits = circuits_response.json().get("results", [])
        print(f"Found {len(existing_circuits)} existing circuits to delete")
        for circuit in existing_circuits:
            delete_response = requests.delete(f"{NAUTOBOT_URL}/api/circuits/circuits/{circuit['id']}/", headers=HEADERS)
            if delete_response.status_code == 204:
                print(f"Deleted circuit {circuit['id']} with CID {circuit.get('cid', 'unknown')}")
            else:
                print(f"Failed to delete circuit {circuit['id']}: {delete_response.status_code}")
    else:
        print(f"Failed to get circuits: {circuits_response.status_code}")
    
    # Add a small delay to ensure API has processed all deletions
    print("Waiting for API to process deletions...")
    import time
    time.sleep(5)
    
    # Verify that all circuits have been deleted
    print("Verifying circuit deletion...")
    verify_response = requests.get(f"{NAUTOBOT_URL}/api/circuits/circuits/", headers=HEADERS)
    if verify_response.status_code == 200:
        remaining_circuits = verify_response.json().get("results", [])
        if remaining_circuits:
            print(f"WARNING: {len(remaining_circuits)} circuits still exist after deletion")
            for circuit in remaining_circuits:
                print(f"  - Circuit {circuit['id']} with CID {circuit.get('cid', 'unknown')}")
            # Try to delete them again
            print("Attempting to delete remaining circuits...")
            for circuit in remaining_circuits:
                delete_response = requests.delete(f"{NAUTOBOT_URL}/api/circuits/circuits/{circuit['id']}/", headers=HEADERS)
                if delete_response.status_code == 204:
                    print(f"  Deleted remaining circuit {circuit['id']}")
                else:
                    print(f"  Failed to delete remaining circuit {circuit['id']}: {delete_response.status_code}")
            # Wait a bit more
            time.sleep(3)
        else:
            print("All circuits successfully deleted")
    else:
        print(f"Failed to verify circuit deletion: {verify_response.status_code}")
    
    # Create all circuits with hardcoded carrier circuit IDs
    circuit_ids = {}
    circuit_configs = [
        # Campus MPLS circuits
        ("DALCN-MPLS-01", "CKT-DAL-MPLS-001", mpls_type["id"], "AT&T", dallas_campus["id"], "MPLS circuit for Dallas Campus"),
        ("LOCN-MPLS-01", "CKT-LON-MPLS-001", mpls_type["id"], "Verizon", london_campus["id"], "MPLS circuit for London Campus"),
        ("KOCN-MPLS-01", "CKT-KOR-MPLS-001", mpls_type["id"], "Cogent", korea_campus["id"], "MPLS circuit for Korea Campus"),
        ("BRCN-MPLS-01", "CKT-BRA-MPLS-001", mpls_type["id"], "Zayo", brazil_campus["id"], "MPLS circuit for Brazil Campus"),
        ("MXCN-MPLS-01", "CKT-MEX-MPLS-001", mpls_type["id"], "AT&T-MEX", mexico_campus["id"], "MPLS circuit for Mexico Campus"),
        
        # Campus Internet WAN circuits
        ("DALCN-INT-01", "CKT-DAL-INT-001", internet_type["id"], "Comcast", dallas_campus["id"], "Internet WAN for Dallas Campus"),
        ("LOCN-INT-01", "CKT-LON-INT-001", internet_type["id"], "CenturyLink", london_campus["id"], "Internet WAN for London Campus"),
        ("KOCN-INT-01", "CKT-KOR-INT-001", internet_type["id"], "Level 3", korea_campus["id"], "Internet WAN for Korea Campus"),
        ("BRCN-INT-01", "CKT-BRA-INT-001", internet_type["id"], "Windstream", brazil_campus["id"], "Internet WAN for Brazil Campus"),
        ("MXCN-INT-01", "CKT-MEX-INT-001", internet_type["id"], "Comcast-MEX", mexico_campus["id"], "Internet WAN for Mexico Campus"),
        
        # Branch Internet WAN circuits (primary)
        ("USBN1-INT-01", "CKT-USB1-INT-001", internet_type["id"], "Verizon", branch_001["id"], "Internet WAN for Branch Office 1"),
        ("USBN2-INT-01", "CKT-USB2-INT-001", internet_type["id"], "Comcast", branch_002["id"], "Internet WAN for Branch Office 2"),
        ("UKBN1-INT-01", "CKT-UKB1-INT-001", internet_type["id"], "Cogent", branch_003["id"], "Internet WAN for Branch Office 3"),
        ("BRBN1-INT-01", "CKT-BRB1-INT-001", internet_type["id"], "Zayo", branch_004["id"], "Internet WAN for Branch Office 4"),
        ("USBN3-INT-01", "CKT-USB3-INT-001", internet_type["id"], "Verizon", branch_005["id"], "Internet WAN for Branch Office 5"),
        ("MXBN1-INT-01", "CKT-MXB1-INT-001", internet_type["id"], "Comcast", branch_006["id"], "Internet WAN for Branch Office 6"),
        ("UKBN2-INT-01", "CKT-UKB2-INT-001", internet_type["id"], "Cogent", branch_007["id"], "Internet WAN for Branch Office 7"),
        ("BRBN2-INT-01", "CKT-BRB2-INT-001", internet_type["id"], "Zayo", branch_008["id"], "Internet WAN for Branch Office 8"),
        
        # Branch Internet WAN circuits (backup)
        ("USBN1-INT-02", "CKT-USB1-INT-002", internet_type["id"], "CenturyLink", branch_001["id"], "Backup Internet WAN for Branch Office 1"),
        ("USBN2-INT-02", "CKT-USB2-INT-002", internet_type["id"], "AT&T", branch_002["id"], "Backup Internet WAN for Branch Office 2"),
        ("UKBN1-INT-02", "CKT-UKB1-INT-002", internet_type["id"], "Level 3", branch_003["id"], "Backup Internet WAN for Branch Office 3"),
        ("BRBN1-INT-02", "CKT-BRB1-INT-002", internet_type["id"], "Windstream", branch_004["id"], "Backup Internet WAN for Branch Office 4"),
        ("USBN3-INT-02", "CKT-USB3-INT-002", internet_type["id"], "CenturyLink", branch_005["id"], "Backup Internet WAN for Branch Office 5"),
        ("MXBN1-INT-02", "CKT-MXB1-INT-002", internet_type["id"], "AT&T", branch_006["id"], "Backup Internet WAN for Branch Office 6"),
        ("UKBN2-INT-02", "CKT-UKB2-INT-002", internet_type["id"], "Level 3", branch_007["id"], "Backup Internet WAN for Branch Office 7"),
        ("BRBN2-INT-02", "CKT-BRB2-INT-002", internet_type["id"], "Windstream", branch_008["id"], "Backup Internet WAN for Branch Office 8"),
    ]
    
    for cid, carrier_cid, circuit_type_id, provider_name, location_id, description in circuit_configs:
        circuit = create_circuit(carrier_cid, circuit_type_id, provider_ids[provider_name], location_id, description=description)
        if circuit:
            circuit_ids[cid] = circuit["id"]
        else:
            print(f"ERROR: Failed to create circuit {cid}")
            return
    
    print(f"Created {len(circuit_ids)} circuits")
    
    # Create circuit terminations and connect to interfaces
    print("\n=== Creating Circuit Terminations ===")
    
    # Map circuits to their corresponding WAN interfaces
    # Format: (circuit_id, device_name, interface_name, location_id)
    circuit_interface_mapping = [
        # Campus MPLS circuits - connect to GigabitEthernet0/0/0 (WAN uplink to MPLS)
        ("DALCN-MPLS-01", "DALCN-WAN01", "GigabitEthernet0/0/0", dallas_campus["id"]),
        ("LOCN-MPLS-01", "LOCN-WAN01", "GigabitEthernet0/0/0", london_campus["id"]),
        ("KOCN-MPLS-01", "KOCN-WAN01", "GigabitEthernet0/0/0", korea_campus["id"]),
        ("BRCN-MPLS-01", "BRCN-WAN01", "GigabitEthernet0/0/0", brazil_campus["id"]),
        ("MXCN-MPLS-01", "MXCN-WAN01", "GigabitEthernet0/0/0", mexico_campus["id"]),
        
        # Campus Internet WAN circuits - connect to GigabitEthernet0/0/0 (WAN uplink to Internet)
        ("DALCN-INT-01", "DALCN-WAN01", "GigabitEthernet0/0/0", dallas_campus["id"]),
        ("LOCN-INT-01", "LOCN-WAN01", "GigabitEthernet0/0/0", london_campus["id"]),
        ("KOCN-INT-01", "KOCN-WAN01", "GigabitEthernet0/0/0", korea_campus["id"]),
        ("BRCN-INT-01", "BRCN-WAN01", "GigabitEthernet0/0/0", brazil_campus["id"]),
        ("MXCN-INT-01", "MXCN-WAN01", "GigabitEthernet0/0/0", mexico_campus["id"]),
        
        # Branch Internet WAN circuits (primary) - connect to Ethernet0/0 (Internet WAN)
        ("USBN1-INT-01", "USBN1-WAN01", "Ethernet0/0", branch_001["id"]),
        ("USBN2-INT-01", "USBN2-WAN01", "Ethernet0/0", branch_002["id"]),
        ("UKBN1-INT-01", "UKBN1-WAN01", "Ethernet0/0", branch_003["id"]),
        ("BRBN1-INT-01", "BRBN1-WAN01", "Ethernet0/0", branch_004["id"]),
        ("USBN3-INT-01", "USBN3-WAN01", "Ethernet0/0", branch_005["id"]),
        ("MXBN1-INT-01", "MXBN1-WAN01", "Ethernet0/0", branch_006["id"]),
        ("UKBN2-INT-01", "UKBN2-WAN01", "Ethernet0/0", branch_007["id"]),
        ("BRBN2-INT-01", "BRBN2-WAN01", "Ethernet0/0", branch_008["id"]),
        
        # Branch Internet WAN circuits (backup) - connect to Ethernet0/0 (Internet WAN)
        # For branches, we'll use the same interface since they only have one WAN interface
        ("USBN1-INT-02", "USBN1-WAN01", "Ethernet0/0", branch_001["id"]),
        ("USBN2-INT-02", "USBN2-WAN01", "Ethernet0/0", branch_002["id"]),
        ("UKBN1-INT-02", "UKBN1-WAN01", "Ethernet0/0", branch_003["id"]),
        ("BRBN1-INT-02", "BRBN1-WAN01", "Ethernet0/0", branch_004["id"]),
        ("USBN3-INT-02", "USBN3-WAN01", "Ethernet0/0", branch_005["id"]),
        ("MXBN1-INT-02", "MXBN1-WAN01", "Ethernet0/0", branch_006["id"]),
        ("UKBN2-INT-02", "UKBN2-WAN01", "Ethernet0/0", branch_007["id"]),
        ("BRBN2-INT-02", "BRBN2-WAN01", "Ethernet0/0", branch_008["id"]),
    ]
    
    termination_count = 0
    cable_count = 0
    for circuit_cid, device_name, interface_name, location_id in circuit_interface_mapping:
        if circuit_cid in circuit_ids and device_name in device_ids:
            # Find the interface ID
            interface_response = requests.get(
                f"{NAUTOBOT_URL}/api/dcim/interfaces/",
                params={"device": device_ids[device_name], "name": interface_name},
                headers=HEADERS
            )
            if interface_response.status_code == 200 and interface_response.json().get("results"):
                interface_id = interface_response.json()["results"][0]["id"]
                
                # Step 1: Create circuit termination
                termination = create_circuit_termination(
                    circuit_ids[circuit_cid], 
                    location_id,  # Use the specific location
                    "A",  # A-side termination
                    1000  # 1Gbps port speed
                )
                if termination:
                    termination_count += 1
                    print(f"Successfully created termination for circuit {circuit_cid} on {device_name} {interface_name}")
                    
                    # Step 2: Create cable connection between circuit termination and interface
                    cable = create_cable_connection(
                        "circuits.circuittermination",  # termination_a_type
                        termination["id"],              # termination_a_id
                        "dcim.interface",               # termination_b_type
                        interface_id                    # termination_b_id
                    )
                    if cable:
                        cable_count += 1
                        print(f"Successfully created cable connection for circuit {circuit_cid} on {device_name} {interface_name}")
                    else:
                        print(f"Failed to create cable connection for circuit {circuit_cid} on {device_name} {interface_name}")
                else:
                    print(f"Failed to create termination for circuit {circuit_cid} on {device_name} {interface_name}")
            else:
                print(f"Interface {interface_name} not found on device {device_name}")
        else:
            if circuit_cid not in circuit_ids:
                print(f"Circuit {circuit_cid} not found")
            if device_name not in device_ids:
                print(f"Device {device_name} not found")
    
    print(f"Created {termination_count} circuit terminations with {cable_count} cable connections")
    
    print("\n=== Data seeding completed successfully! ===")
    print(f"Created {len(devices)} devices across {8} locations")
    print(f"Created {interface_count} interfaces with IP addresses")
    print(f"Created {prefix_count} prefixes")
    print(f"Created {len(circuit_ids)} circuits with {termination_count} terminations")
    print("Network topology includes WAN routers, core routers, access switches, and spine/leaf switches")
    print("Proper location hierarchy: Region -> Country -> Campus/Data Center/Branch")
    print("All devices are properly associated with their respective locations")
    print("Circuits include MPLS for campuses and dual Internet WAN for branches")

if __name__ == "__main__":
    seed_data()