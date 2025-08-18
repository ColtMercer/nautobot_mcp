# Nautobot FastMCP Server + Streamlit Chat

A self-contained, dockerized reference project that exposes a **FastMCP** server for the Nautobot OSS platform, plus a lightweight **LLM chat UI** that can list available MCP tools, call them, and export chat transcripts.

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd nautobot_mcp

# Copy environment file and configure
cp .env.example .env

# Start all services
make up

# Get your Nautobot API token:
# 1. Create admin user: docker compose exec nautobot nautobot-server createsuperuser --username <user_name> --email admin@example.com
# 2. Go to http://localhost:8080 and log in with your username and password
# 3. Navigate to your User Profile → API Tokens → Add token
# 4. Copy the token key and update your .env file: NAUTOBOT_TOKEN=your_api_token_here
# 5. Restart the services: make restart

# Open the chat UI
# http://localhost:8501
```

## What's Included

- **Nautobot** with seeded demo data and GraphQL enabled
- **FastMCP Server** exposing Nautobot utilities as MCP tools
- **Streamlit Chat UI** for testing MCP tools and exporting conversations
- **Demo Data** including locations, devices, interfaces, and IPAM

## Default Credentials

- **Nautobot Admin**: You'll create your own username and password during setup
- **API Token**: You'll need to create this manually (see Manual Setup)

## Manual Setup (Required)

After starting the services, you need to manually create the admin user and API token:

1. **Create admin user** (run this command):
   ```bash
   docker compose exec nautobot nautobot-server createsuperuser --username <user_name> --email admin@example.com
   ```
   - Enter your desired username when prompted
   - Enter your desired password when prompted
   - Confirm the password when prompted

2. **Get your API token**:
   - Go to http://localhost:8080 and log in with your username and password
   - Navigate to your **User Profile** (click your username in the top right)
   - Go to the **API Tokens** tab
   - Click **Add token** and create a new token
   - Copy the token key and update your `.env` file:
     ```bash
     NAUTOBOT_TOKEN=your_api_token_here
     ```
   - Restart the services: `make restart`

## MCP Tools Available

1. **`get_prefixes_by_location`** - Returns all prefixes under a Nautobot Location
2. **`llm_chat`** - LLM assistant that can call other MCP tools and cite usage

## Demo Data Structure

The system includes a comprehensive network topology:

- **Locations**: Regions → Countries → Campuses/Branches/Data Centers
- **Devices**: WAN routers, core routers, access switches, spine/leaf switches
- **Interfaces**: Properly configured with VLANs and IP addressing
- **IPAM**: Prefixes associated with locations and interfaces

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Type check
make typecheck
```

## Export Chat Transcripts

The chat UI can export conversations in:
- **JSON format** - Complete conversation with tool call metadata
- **Markdown format** - Readable log with tool call details

## Architecture

```
+-------------------+         +-------------------+       +------------------+
|  Streamlit Chat   | <-----> |  MCP Client SDK   | <-->  |  FastMCP Server  |
|  (LLM front-end)  |         |  (tool catalog)   |       |  (Nautobot tools)|
+-------------------+         +-------------------+       +--------+---------+
                                                                     |
                                                                     v
                                                             +---------------+
                                                             |   Nautobot    |
                                                             | (GraphQL API) |
                                                             +---------------+
```

## License

Apache-2.0
