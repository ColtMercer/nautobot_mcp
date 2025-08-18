#!/usr/bin/env python3
"""Seed script to populate Nautobot with demo data."""

import os
import time
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv

load_dotenv()

NAUTOBOT_URL = os.environ.get("NAUTOBOT_URL", "http://nautobot:8080")
NAUTOBOT_TOKEN = os.environ.get("NAUTOBOT_TOKEN", "changeme")

HEADERS = {"Authorization": f"Token {NAUTOBOT_TOKEN}"} if NAUTOBOT_TOKEN else {}


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
                return True
        except requests.exceptions.RequestException:
            pass
        
        retry_count += 1
        print(f"Retry {retry_count}/{max_retries}...")
        time.sleep(10)
    
    raise RuntimeError("Nautobot did not become ready in time")


def create_location_type(name: str, description: str) -> Dict[str, Any]:
    """Create a location type."""
    data = {
        "name": name,
        "description": description
    }
    
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
        return response.json()
    else:
        print(f"Failed to create location type {name}: {response.status_code} - {response.text}")
        return None


def create_location(name: str, location_type: str, parent: str = None) -> Dict[str, Any]:
    """Create a location."""
    data = {
        "name": name,
        "location_type": location_type
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
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Location {name} already exists")
        return response.json()
    else:
        print(f"Failed to create location {name}: {response.status_code} - {response.text}")
        return None


def create_device_role(name: str, color: str = "9e9e9e") -> Dict[str, Any]:
    """Create a device role."""
    data = {
        "name": name,
        "color": color
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/device-roles/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created device role: {name}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Device role {name} already exists")
        return response.json()
    else:
        print(f"Failed to create device role {name}: {response.status_code} - {response.text}")
        return None


def create_device(name: str, device_role: str, location: str, device_type: str = "Generic Device") -> Dict[str, Any]:
    """Create a device."""
    data = {
        "name": name,
        "device_role": device_role,
        "location": location,
        "device_type": device_type
    }
    
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
        return response.json()
    else:
        print(f"Failed to create device {name}: {response.status_code} - {response.text}")
        return None


def create_interface(device: str, name: str, interface_type: str = "1000base-t") -> Dict[str, Any]:
    """Create an interface."""
    data = {
        "device": device,
        "name": name,
        "type": interface_type
    }
    
    response = requests.post(
        f"{NAUTOBOT_URL}/api/dcim/interfaces/",
        json=data,
        headers=HEADERS
    )
    
    if response.status_code == 201:
        print(f"Created interface: {name} on {device}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        print(f"Interface {name} on {device} already exists")
        return response.json()
    else:
        print(f"Failed to create interface {name} on {device}: {response.status_code} - {response.text}")
        return None


def create_prefix(prefix: str, location: str, role: str = None, description: str = None) -> Dict[str, Any]:
    """Create a prefix."""
    data = {
        "prefix": prefix,
        "location": location
    }
    
    if role:
        data["role"] = role
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


def seed_data():
    """Seed Nautobot with demo data."""
    print("Starting Nautobot data seeding...")
    
    # Wait for Nautobot to be ready
    wait_for_nautobot()
    
    # Create location types
    location_types = [
        ("Region", "Geographic regions"),
        ("Country", "Countries within regions"),
        ("Campus", "Campus locations"),
        ("Data Center", "Data center facilities"),
        ("Branch", "Branch office locations")
    ]
    
    for name, description in location_types:
        create_location_type(name, description)
    
    # Create device roles
    device_roles = [
        ("wan-router", "ff5722"),  # Deep Orange
        ("core-router", "2196f3"),  # Blue
        ("access-switch", "4caf50"),  # Green
        ("spine-switch", "9c27b0"),  # Purple
        ("leaf-switch", "ff9800"),  # Orange
    ]
    
    for name, color in device_roles:
        create_device_role(name, color)
    
    # Create regions
    regions = ["NAM", "ASPAC", "EMEA", "LATAM"]
    region_locations = {}
    
    for region in regions:
        location = create_location(region, "Region")
        if location:
            region_locations[region] = location["id"]
    
    # Create countries (top 5 per region)
    countries_data = {
        "NAM": ["USA", "Canada", "Mexico", "Brazil", "Argentina"],
        "ASPAC": ["China", "Japan", "India", "Australia", "South Korea"],
        "EMEA": ["Germany", "UK", "France", "Italy", "Spain"],
        "LATAM": ["Brazil", "Mexico", "Argentina", "Colombia", "Chile"]
    }
    
    country_locations = {}
    
    for region, countries in countries_data.items():
        if region in region_locations:
            for country in countries:
                location = create_location(country, "Country", region_locations[region])
                if location:
                    country_locations[country] = location["id"]
    
    # Create campuses (5-character alphanumeric codes, 2 per country)
    campus_locations = {}
    campus_counter = 1
    
    for country in country_locations:
        for i in range(2):
            campus_code = f"{country[:2].upper()}{campus_counter:03d}"
            campus_name = f"{campus_code}-Campus"
            location = create_location(campus_name, "Campus", country_locations[country])
            if location:
                campus_locations[campus_code] = location["id"]
            campus_counter += 1
    
    # Create data centers (2 per region)
    dc_locations = {}
    dc_counter = 1
    
    for region in regions:
        for i in range(2):
            dc_code = f"{region}{dc_counter:02d}"
            dc_name = f"{dc_code}-DC"
            location = create_location(dc_name, "Data Center", region_locations[region])
            if location:
                dc_locations[dc_code] = location["id"]
            dc_counter += 1
    
    # Create branches (10 per country)
    branch_locations = {}
    branch_counter = 1
    
    for country in country_locations:
        for i in range(10):
            branch_code = f"{country[:2].upper()}{branch_counter:03d}"
            branch_name = f"{branch_code}-Branch"
            location = create_location(branch_name, "Branch", country_locations[country])
            if location:
                branch_locations[branch_code] = location["id"]
            branch_counter += 1
    
    # Create devices for campuses
    device_counter = 1
    
    for campus_code, location_id in campus_locations.items():
        # 2 WAN routers
        for i in range(2):
            device_name = f"{campus_code}-wan{i+1:03d}"
            create_device(device_name, "wan-router", location_id)
        
        # 1 Core router
        core_name = f"{campus_code}-cor001"
        create_device(core_name, "core-router", location_id)
        
        # 5 Access switches
        for i in range(5):
            acc_name = f"{campus_code}-acc{i+1:03d}"
            create_device(acc_name, "access-switch", location_id)
    
    # Create devices for data centers
    for dc_code, location_id in dc_locations.items():
        # 4 Spine switches
        for i in range(4):
            spine_name = f"{dc_code}-spn{i+1:03d}"
            create_device(spine_name, "spine-switch", location_id)
        
        # 20 Leaf switches
        for i in range(20):
            leaf_name = f"{dc_code}-lea{i+1001:04d}"
            create_device(leaf_name, "leaf-switch", location_id)
    
    # Create prefixes for demo locations
    demo_locations = {
        "HQ-Dallas": "10.1.0.0/16",
        "HQ-London": "10.2.0.0/16", 
        "LAB-Austin": "10.3.0.0/16",
        "DC-NYC01": "10.10.0.0/16",
        "DC-LON01": "10.20.0.0/16"
    }
    
    for location_name, prefix in demo_locations.items():
        create_prefix(prefix, location_name, "Network", f"Demo network for {location_name}")
        
        # Create some subnets
        for i in range(5):
            subnet = f"{prefix[:-3]}{i*50}.0/24"
            create_prefix(subnet, location_name, "Network", f"Subnet {i+1} for {location_name}")
    
    print("Data seeding completed successfully!")


if __name__ == "__main__":
    seed_data()
