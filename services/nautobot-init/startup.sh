#!/bin/bash

# Wait for Nautobot to be ready
echo "Waiting for Nautobot to be ready..."
until curl -f http://localhost:8080/health/ > /dev/null 2>&1; do
    echo "Waiting for Nautobot..."
    sleep 5
done

echo "Nautobot is ready! Creating admin user..."

# Create admin user with default credentials
nautobot-server createsuperuser --username admin --email admin@example.com --noinput

# Set the password
echo "Setting admin password..."
nautobot-server shell --config-path /opt/nautobot/nautobot_config.py -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='admin')
user.set_password('admin')
user.save()
print('Admin user created successfully with username: admin, password: admin')
"

echo "Admin user setup complete!"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "Please log in to Nautobot at http://localhost:8080 and create an API token."
echo "Then update your .env file with: NAUTOBOT_TOKEN=your_api_token_here"
