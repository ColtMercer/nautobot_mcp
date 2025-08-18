#!/usr/bin/env python3
"""Initialize Nautobot with default admin user and API token."""

import os
import time
import subprocess
from typing import Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

NAUTOBOT_URL = os.environ.get("NAUTOBOT_URL", "http://nautobot:8080")
ADMIN_USERNAME = os.environ.get("NAUTOBOT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("NAUTOBOT_ADMIN_PASSWORD", "admin")
ADMIN_EMAIL = os.environ.get("NAUTOBOT_ADMIN_EMAIL", "admin@example.com")


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


def create_admin_user():
    """Create the default admin user using Django management command."""
    print(f"Creating admin user: {ADMIN_USERNAME}")
    
    try:
        # Use Django management command to create superuser
        cmd = [
            "nautobot-server", "createsuperuser",
            "--config-path", "/opt/nautobot/nautobot_config.py",
            "--username", ADMIN_USERNAME,
            "--email", ADMIN_EMAIL,
            "--noinput"
        ]
        
        # Set environment variables for the subprocess
        env = os.environ.copy()
        env["DJANGO_SUPERUSER_PASSWORD"] = ADMIN_PASSWORD
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"Admin user {ADMIN_USERNAME} created successfully")
            return True
        else:
            print(f"Failed to create admin user: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False


def create_api_token():
    """Create an API token for the admin user."""
    print("Creating API token for admin user...")
    
    try:
        # Use Django management command to create token
        cmd = [
            "nautobot-server", "shell",
            "--config-path", "/opt/nautobot/nautobot_config.py",
            "-c", f"""
from django.contrib.auth import get_user_model
from nautobot.users.models import Token
User = get_user_model()
user = User.objects.get(username='{ADMIN_USERNAME}')
token, created = Token.objects.get_or_create(
    user=user,
    key='nautobot-mcp-token-1234567890abcdef',
    defaults={{
        'write_enabled': True,
        'description': 'MCP Server API Token'
    }}
)
print(f'Token created: {{token.key}}')
"""
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("API token created successfully")
            return "nautobot-mcp-token-1234567890abcdef"
        else:
            print(f"Failed to create API token: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Error creating API token: {e}")
        return None


def main():
    """Main initialization function."""
    print("Starting Nautobot initialization...")
    
    # Wait for Nautobot to be ready
    wait_for_nautobot()
    
    # Create admin user
    if create_admin_user():
        # Create API token
        token = create_api_token()
        if token:
            print(f"\n=== NAUTOBOT INITIALIZATION COMPLETE ===")
            print(f"Admin Username: {ADMIN_USERNAME}")
            print(f"Admin Password: {ADMIN_PASSWORD}")
            print(f"API Token: {token}")
            print(f"Update your .env file with: NAUTOBOT_TOKEN={token}")
            print("===========================================")
        else:
            print("Failed to create API token")
    else:
        print("Failed to create admin user")


if __name__ == "__main__":
    main()
