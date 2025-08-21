# Nautobot MCP Chat Interface

A self-contained, dockerized demo that exposes a **FastMCP** server for the Nautobot OSS platform, plus a lightweight **chat UI** that can list available MCP tools, call them, and export chat transcripts.

## 🚀 Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Copy environment file and configure
cp .env.example .env

# 3. Create admin user
docker exec -it nautobot_mcp-nautobot-1 nautobot-server createsuperuser --username admin --email admin@example.com

# 4. Get your API token:
#    - Go to http://localhost:8080 and log in with your username and password
#    - Navigate to your User Profile → API Tokens → Add token
#    - Copy the token key and update your .env file: NAUTOBOT_TOKEN=your_api_token_here
#    - Restart the services: docker-compose restart

# 5. Open the chat UI
#    http://localhost:8501
```

## 🎯 What's Included

- **Nautobot** with seeded demo data and GraphQL enabled
- **FastMCP Server** exposing Nautobot utilities as MCP tools
- **Chat UI** for testing MCP tools and exporting conversations
- **Demo Data** including locations, devices, interfaces, and IPAM

## 🔧 Setup Steps

### Step 1: Start Services
```bash
docker-compose up -d
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env file with your OpenAI API key (optional)
```

### Step 3: Create Admin User
```bash
docker exec -it nautobot_mcp-nautobot-1 nautobot-server createsuperuser --username admin --email admin@example.com
```

### Step 4: Get API Token
1. Go to http://localhost:8080 and log in
2. Navigate to **User Profile** → **API Tokens** → **Add token**
3. Copy the token and update your `.env` file:
   ```bash
   NAUTOBOT_TOKEN=your_api_token_here
   ```
4. Restart services:
   ```bash
   docker-compose restart
   ```

### Step 5: Access Chat UI
Open http://localhost:8501 in your browser

## 🛠️ MCP Tools Available

1. **`get_prefixes_by_location_enhanced`** - Query prefixes by location with format options
2. **`get_devices_by_location`** - Get devices at a specific location
3. **`get_devices_by_location_and_role`** - Get devices by location and role
4. **`llm_chat`** - LLM assistant that can call other MCP tools

## 📊 Demo Data Structure

The system includes a comprehensive network topology:

- **Locations**: Regions → Countries → Campuses/Branches/Data Centers
- **Devices**: WAN routers, core routers, access switches, spine/leaf switches
- **Interfaces**: Properly configured with VLANs and IP addressing
- **IPAM**: Prefixes associated with locations and interfaces

## 💬 Example Queries

Try these in the chat UI:
- "What prefixes exist at HQ-Dallas?"
- "Show me all devices at HQ-Dallas"
- "What routers are at HQ-Dallas?"
- "Export the prefixes at HQ-Dallas as a table"

## 📤 Export Chat Transcripts

The chat UI can export conversations in:
- **JSON format** - Complete conversation with tool call metadata
- **Markdown format** - Readable log with tool call details

## 🏗️ Architecture

```
+-------------------+         +-------------------+       +------------------+
|  Chat UI         | <-----> |  MCP Client SDK   | <-->  |  FastMCP Server  |
|  (Flask/HTML)    |         |  (tool catalog)   |       |  (Nautobot tools)|
+-------------------+         +-------------------+       +--------+---------+
                                                                     |
                                                                     v
                                                             +---------------+
                                                             |   Nautobot    |
                                                             | (GraphQL API) |
                                                             +---------------+
```

## 🔍 Troubleshooting

- **Services not starting**: Check `docker-compose logs` for errors
- **Chat UI not loading**: Ensure all services are healthy with `docker-compose ps`
- **API errors**: Verify your `NAUTOBOT_TOKEN` is set correctly in `.env`

## 📝 License

Apache-2.0
