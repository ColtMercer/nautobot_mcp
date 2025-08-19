#!/usr/bin/env python3
"""Script to create a token in Nautobot."""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nautobot.core.settings')
django.setup()

from nautobot.users.models import User
from nautobot.users.models import Token

def create_token():
    """Create a token for the first user."""
    try:
        # Get the first user (usually admin)
        user = User.objects.first()
        if not user:
            print("No users found in the database")
            return None
        
        # Create the token
        token_key = 'nautobot-mcp-token-1234567890abcdef'
        token, created = Token.objects.get_or_create(
            key=token_key,
            defaults={'user': user}
        )
        
        if created:
            print(f"Token created successfully: {token.key}")
        else:
            print(f"Token already exists: {token.key}")
        
        return token.key
        
    except Exception as e:
        print(f"Error creating token: {e}")
        return None

if __name__ == "__main__":
    create_token()
