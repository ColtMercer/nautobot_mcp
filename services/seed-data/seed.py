#!/usr/bin/env python3
"""Comprehensive seed script for Nautobot MCP demo data with proper location hierarchy."""

import os
import time
import requests
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
        "u_height": u_height
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
        "content_types": ["dcim.device"]
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

def create_interface(device_id: str, name: str, interface_type: str = "1000base-t") -> Dict[str, Any]:
    """Create an interface."""
    data = {
        "device": device_id,
        "name": name,
        "type": interface_type,
        "status": "Active"
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/interfaces/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created interface: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Interface {name} already exists")
        # Try to get the existing interface
        get_response = requests.get(
            f"{NAUTOBOT_URL}/api/dcim/interfaces/?device_id={device_id}&name={name}",
            headers=HEADERS
        )
        if get_response.status_code == 200:
            data = get_response.json()
            if data["results"]:
                return data["results"][0]
        return None
    else:
        print(f"Failed to create interface {name}: {response.status_code} - {response.text}")
        return None

def create_ip_address(ip_address: str, interface_id: str, namespace_id: str = None, status: str = "Active") -> Dict[str, Any]:
    """Create an IP address and assign it to an interface."""
    data = {
        "address": ip_address,
        "status": status,
        "assigned_object_type": "dcim.interface",
        "assigned_object_id": interface_id
    }

    if namespace_id:
        data["namespace"] = namespace_id
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/ipam/ip-addresses/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created IP address: {ip_address}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"IP address {ip_address} already exists")
        return response.json()
    else:
        print(f"Failed to create IP address {ip_address}: {response.status_code} - {response.text}")
        return None

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

def seed_data():
    """Seed Nautobot with comprehensive demo data."""
    print("Starting comprehensive Nautobot data seeding...")
    
    # Wait for Nautobot to be ready
    wait_for_nautobot()
    
    # Idempotent run: do NOT delete existing locations; just (re)create/match
    
    # Get location type IDs
    print("\n=== Getting Location Type IDs ===")
    region_type_id = get_location_type_id("Region")
    country_type_id = get_location_type_id("Country")
    campus_type_id = get_location_type_id("Campus")
    dc_type_id = get_location_type_id("Data Center")
    branch_type_id = get_location_type_id("Branch")
    
    if not all([region_type_id, country_type_id, campus_type_id, dc_type_id, branch_type_id]):
        print("ERROR: Failed to get location type IDs")
        return

    # Get Global namespace for IP addressing
    global_ns_id = get_namespace_id("Global")
    if not global_ns_id:
        print("ERROR: Global namespace not found; cannot assign IP addresses")
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
    router_role = get_or_create_device_role("Router")
    switch_role = get_or_create_device_role("Switch")
    
    if not router_role or not switch_role:
        print("ERROR: Failed to create device roles")
        return
    
    # Create location hierarchy
    print("\n=== Creating Location Hierarchy ===")
    
    # Create regions
    north_america = create_location("North America", region_type_id)
    europe = create_location("Europe", region_type_id)
    
    if not north_america or not europe:
        print("ERROR: Failed to create regions")
        return
    
    # Create countries
    usa = create_location("United States", country_type_id, north_america["id"])
    uk = create_location("United Kingdom", country_type_id, europe["id"])
    
    if not usa or not uk:
        print("ERROR: Failed to create countries")
        return
    
    # Create campuses and data centers
    dallas_campus = create_location("Dallas Campus", campus_type_id, usa["id"])
    london_campus = create_location("London Campus", campus_type_id, uk["id"])
    austin_lab = create_location("Austin Lab", campus_type_id, usa["id"])
    
    nyc_dc = create_location("NYC Data Center", dc_type_id, usa["id"])
    lon_dc = create_location("London Data Center", dc_type_id, uk["id"])
    
    if not all([dallas_campus, london_campus, austin_lab, nyc_dc, lon_dc]):
        print("ERROR: Failed to create campuses and data centers")
        return
    
    # Create branch offices
    branch_001 = create_location("Branch Office 1", branch_type_id, usa["id"])
    branch_002 = create_location("Branch Office 2", branch_type_id, usa["id"])
    branch_003 = create_location("Branch Office 3", branch_type_id, uk["id"])
    
    if not all([branch_001, branch_002, branch_003]):
        print("ERROR: Failed to create branch offices")
        return
    
    print(f"Created location hierarchy with {8} locations")
    
    # Create devices at each location
    print("\n=== Creating Devices ===")
    devices = [
        # WAN Routers
        ("WAN-RTR-01", cisco_router["id"], router_role["id"], dallas_campus["id"], ios_xe["id"], "WAN Router at Dallas Campus"),
        ("WAN-RTR-02", cisco_router["id"], router_role["id"], london_campus["id"], ios_xe["id"], "WAN Router at London Campus"),
        ("WAN-RTR-03", juniper_router["id"], router_role["id"], austin_lab["id"], junos["id"], "WAN Router at Austin Lab"),
        
        # Core Routers
        ("CORE-RTR-01", cisco_router["id"], router_role["id"], nyc_dc["id"], ios_xe["id"], "Core Router at NYC Data Center"),
        ("CORE-RTR-02", cisco_router["id"], router_role["id"], lon_dc["id"], ios_xe["id"], "Core Router at London Data Center"),
        
        # Access Switches
        ("ACC-SW-01", cisco_switch["id"], switch_role["id"], dallas_campus["id"], nx_os["id"], "Access Switch at Dallas Campus"),
        ("ACC-SW-02", cisco_switch["id"], switch_role["id"], london_campus["id"], nx_os["id"], "Access Switch at London Campus"),
        ("ACC-SW-03", cisco_switch["id"], switch_role["id"], austin_lab["id"], nx_os["id"], "Access Switch at Austin Lab"),
        
        # Spine/Leaf Switches
        ("SPINE-01", arista_switch["id"], switch_role["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("SPINE-02", arista_switch["id"], switch_role["id"], nyc_dc["id"], eos["id"], "Spine Switch at NYC Data Center"),
        ("LEAF-01", arista_switch["id"], switch_role["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        ("LEAF-02", arista_switch["id"], switch_role["id"], nyc_dc["id"], eos["id"], "Leaf Switch at NYC Data Center"),
        
        # Branch Devices
        ("BR-SW-01", cisco_switch["id"], switch_role["id"], branch_001["id"], nx_os["id"], "Branch Switch at Branch Office 1"),
        ("BR-SW-02", cisco_switch["id"], switch_role["id"], branch_002["id"], nx_os["id"], "Branch Switch at Branch Office 2"),
        ("BR-SW-03", cisco_switch["id"], switch_role["id"], branch_003["id"], nx_os["id"], "Branch Switch at Branch Office 3")
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
    
    # Create interfaces and IP addresses
    print("\n=== Creating Interfaces and IP Addresses ===")
    interface_configs = [
        # WAN Router interfaces
        ("WAN-RTR-01", "GigabitEthernet0/0/0", "10.1.1.1/24"),
        ("WAN-RTR-01", "GigabitEthernet0/0/1", "10.1.2.1/24"),
        ("WAN-RTR-02", "GigabitEthernet0/0/0", "10.2.1.1/24"),
        ("WAN-RTR-02", "GigabitEthernet0/0/1", "10.2.2.1/24"),
        ("WAN-RTR-03", "ge-0/0/0", "10.3.1.1/24"),
        ("WAN-RTR-03", "ge-0/0/1", "10.3.2.1/24"),
        
        # Core Router interfaces
        ("CORE-RTR-01", "GigabitEthernet0/0/0", "10.10.1.1/24"),
        ("CORE-RTR-01", "GigabitEthernet0/0/1", "10.10.2.1/24"),
        ("CORE-RTR-02", "GigabitEthernet0/0/0", "10.20.1.1/24"),
        ("CORE-RTR-02", "GigabitEthernet0/0/1", "10.20.2.1/24"),
        
        # Access Switch interfaces
        ("ACC-SW-01", "Ethernet1/1", "10.1.10.1/24"),
        ("ACC-SW-01", "Ethernet1/2", "10.1.11.1/24"),
        ("ACC-SW-02", "Ethernet1/1", "10.2.10.1/24"),
        ("ACC-SW-02", "Ethernet1/2", "10.2.11.1/24"),
        ("ACC-SW-03", "Ethernet1/1", "10.3.10.1/24"),
        ("ACC-SW-03", "Ethernet1/2", "10.3.11.1/24"),
        
        # Spine/Leaf interfaces
        ("SPINE-01", "Ethernet1", "10.10.100.1/24"),
        ("SPINE-02", "Ethernet1", "10.10.100.2/24"),
        ("LEAF-01", "Ethernet1", "10.10.101.1/24"),
        ("LEAF-02", "Ethernet1", "10.10.101.2/24"),
        
        # Branch Switch interfaces
        ("BR-SW-01", "Ethernet1/1", "10.100.1.1/24"),
        ("BR-SW-02", "Ethernet1/1", "10.100.2.1/24"),
        ("BR-SW-03", "Ethernet1/1", "10.100.3.1/24")
    ]
    
    interface_count = 0
    ip_count = 0
    for device_name, interface_name, ip_address in interface_configs:
        if device_name in device_ids:
            # Ensure interface exists or fetch it
            interface = create_interface(device_ids[device_name], interface_name)
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
                if create_ip_address(ip_address, interface["id"], global_ns_id):
                    ip_count += 1
    
    print(f"Created {interface_count} interfaces (created or matched) and {ip_count} IP addresses")
    
    # Create prefixes for each location
    print("\n=== Creating Prefixes ===")
    prefix_configs = [
        (dallas_campus["id"], "10.1.0.0/16", "Main network for Dallas Campus"),
        (london_campus["id"], "10.2.0.0/16", "Main network for London Campus"),
        (austin_lab["id"], "10.3.0.0/16", "Lab network for Austin"),
        (nyc_dc["id"], "10.10.0.0/16", "Data center network for NYC"),
        (lon_dc["id"], "10.20.0.0/16", "Data center network for London"),
        (branch_001["id"], "10.100.1.0/24", "Branch office network 1"),
        (branch_002["id"], "10.100.2.0/24", "Branch office network 2"),
        (branch_003["id"], "10.100.3.0/24", "Branch office network 3")
    ]
    
    prefix_count = 0
    for location_id, prefix, description in prefix_configs:
        if create_prefix(prefix, location_id, description, global_ns_id):
            prefix_count += 1
            
            # Create some subnets for each location
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
    
    print(f"Created {prefix_count} prefixes")
    
    # Update existing prefixes with location associations
    print("\n=== Updating Existing Prefixes with Location Associations ===")
    update_count = 0
    for location_id, prefix, description in prefix_configs:
        existing_prefix = get_prefix_by_network(prefix)
        if existing_prefix and not existing_prefix.get("location"):
            if update_prefix_location(existing_prefix["id"], location_id):
                update_count += 1
            
            # Also update subnets
            base_prefix = prefix.split('/')[0]
            base_parts = base_prefix.split('.')
            if prefix.endswith("/16"):
                # For /16 networks, update /24 subnets
                for i in range(3):
                    third_octet = int(base_parts[2]) + (i * 50)
                    subnet = f"{base_parts[0]}.{base_parts[1]}.{third_octet}.0/24"
                    existing_subnet = get_prefix_by_network(subnet)
                    if existing_subnet and not existing_subnet.get("location"):
                        if update_prefix_location(existing_subnet["id"], location_id):
                            update_count += 1
            else:
                # For /24 networks, update smaller subnets
                for i in range(3):
                    fourth_octet = int(base_parts[3]) + (i * 10)
                    subnet = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{fourth_octet}/26"
                    existing_subnet = get_prefix_by_network(subnet)
                    if existing_subnet and not existing_subnet.get("location"):
                        if update_prefix_location(existing_subnet["id"], location_id):
                            update_count += 1
    
    print(f"Updated {update_count} existing prefixes with location associations")
    
    print("\n=== Data seeding completed successfully! ===")
    print(f"Created {len(devices)} devices across {8} locations")
    print(f"Created {interface_count} interfaces with IP addresses")
    print(f"Created {prefix_count} prefixes")
    print("Network topology includes WAN routers, core routers, access switches, and spine/leaf switches")
    print("Proper location hierarchy: Region -> Country -> Campus/Data Center/Branch")
    print("All devices are properly associated with their respective locations")

if __name__ == "__main__":
    seed_data()
