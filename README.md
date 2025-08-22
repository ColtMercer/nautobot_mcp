# Nautobot MCP Chat Interface

A self-contained, dockerized demo that exposes a **FastMCP** server for the Nautobot OSS platform, plus a lightweight **chat UI** that can list available MCP tools, call them, and export chat transcripts.

## 🚀 Version 2.0: Multi-Tool & Recursive Tool Calling

**Version 2.0 introduces advanced capabilities for concurrent tool execution and recursive tool chaining, enabling complex network analysis queries that automatically gather comprehensive data from multiple sources.**

### 📊 Sample Conversation: Complex Network Analysis

Below is a real transcript demonstrating the new capabilities:

---

**User Query:** *"Can you provide prefixes and devices at location BRCN and tell me what interfaces are on those devices. I am specifically looking for the WAN interfaces but want to see them all"*

**System Response:** The LLM automatically executed a complex orchestration of 9 tool calls across 2 rounds:

**Round 1 - Data Gathering:**
1. **`get_prefixes_by_location_enhanced`** → Retrieved 8 network prefixes (0.45s)
2. **`get_devices_by_location`** → Retrieved 6 devices (0.38s)

**Round 2 - Recursive Interface Discovery:**
3. **`get_interfaces_by_device`** → Called 6 times, one for each device found:
   - BRCN-ACC01: 6 interfaces (0.32s)
   - BRCN-ACC02: 0 interfaces (0.28s)
   - BRCN-COR01: 4 interfaces (0.31s)
   - BRCN-COR02: 0 interfaces (0.29s)
   - BRCN-WAN01: 3 interfaces with MPLS circuit (0.33s)
   - BRCN-WAN02: 3 interfaces with Internet circuit (0.30s)

**Total Execution Time:** 3.05 seconds for complete network analysis

**Follow-up Query:** *"Are there any circuits on those interfaces?"*

**System Response:** The LLM intelligently used cached data from the previous query, analyzing circuit information without additional tool calls (0.12s processing time), identifying MPLS and Internet circuits with provider details.

---

### 🔧 Tool Execution Details

**Concurrent Tool Calls:**
- Multiple tools executed in a single query
- Automatic data correlation across different data sources
- Comprehensive analysis combining prefixes, devices, and interfaces

**Recursive Tool Chaining:**
- Results from one tool inform subsequent tool calls
- Automatic iteration through device lists to gather interface details
- Context-aware follow-up queries using previous results

**Enhanced Data Presentation:**
- Markdown-formatted tables for better readability
- Structured data with clear relationships
- Circuit information with provider and type details

### 📈 Version 2.0 Features

✅ **Multi-Tool Execution** - Single queries can trigger multiple tool calls  
✅ **Recursive Tool Chaining** - Tool results inform subsequent tool calls  
✅ **Dynamic Tool Discovery** - Chat UI automatically discovers available tools  
✅ **Enhanced Status Updates** - Real-time progress tracking during complex queries  
✅ **Comprehensive Data Analysis** - Automatic correlation across network data sources  
✅ **Circuit Information** - Detailed circuit data including providers and types  

---

*This demonstrates the power of Version 2.0's advanced tool orchestration capabilities, enabling complex network analysis queries that would previously require multiple manual steps.*

**📄 Full Transcript:** See `exports/transcript_v2_comprehensive.md` for the complete interaction including real-time status updates, tool execution details, and performance metrics.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🎯 What's Included](#-whats-included)
- [🔧 Setup Steps](#-setup-steps)
  - [Step 1: Start Services](#step-1-start-services)
  - [Step 2: Configure Environment](#step-2-configure-environment)
  - [Step 3: Get OpenAI API Key](#step-3-get-openai-api-key)
  - [Step 4: Create Admin User](#step-4-create-admin-user)
  - [Step 5: Get Nautobot API Token](#step-5-get-nautobot-api-token)
  - [Step 6: Access Chat UI](#step-6-access-chat-ui)
- [🛠️ MCP Tools Available](#️-mcp-tools-available)
- [📊 Demo Data Structure](#-demo-data-structure)
- [💬 Example Queries](#-example-queries)
- [📤 Export Chat Transcripts](#-export-chat-transcripts)
- [🏗️ Architecture](#️-architecture)
- [🤝 Contributing New Tools](#-contributing-new-tools)
- [🔍 Troubleshooting](#-troubleshooting)

## 🚀 Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Copy environment file and configure
cp .env.example .env

# 3. Get OpenAI API key (required for chat functionality):
#    - Go to https://platform.openai.com/api-keys
#    - Create a new API key
#    - Add it to your .env file: OPENAI_API_KEY=your_openai_api_key_here

# 4. Create admin user
docker exec -it nautobot_mcp-1-nautobot-1 nautobot-server createsuperuser --username admin --email admin@example.com

# 5. Get your Nautobot API token:
#    - Go to http://localhost:8080 and log in with your username and password
#    - Navigate to your User Profile → API Tokens → Add token
#    - Copy the token key and update your .env file: NAUTOBOT_TOKEN=your_api_token_here
#    - Restart the services: docker-compose restart

# 6. Open the chat UI
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
```

### Step 3: Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add it to your `.env` file:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   **Note**: This is required for chat functionality to work properly.

### Step 4: Create Admin User
```bash
docker exec -it nautobot_mcp-nautobot-1 nautobot-server createsuperuser --username admin --email admin@example.com
```

### Step 5: Get Nautobot API Token
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

### Step 6: Access Chat UI
Open http://localhost:8501 in your browser

## 🛠️ MCP Tools Available

1. **`get_prefixes_by_location_enhanced`** - Query prefixes by location with format options
2. **`get_devices_by_location`** - Get devices at a specific location
3. **`get_devices_by_location_and_role`** - Get devices by location and role
4. **`get_interfaces_by_device`** - Get interfaces, IP addresses, and circuit information for a device
5. **Dynamic Tool Discovery** - Chat UI automatically discovers and presents available tools

## 📊 Demo Data Structure

The system includes a comprehensive network topology:

- **Locations**: Regions → Countries → Campuses/Branches/Data Centers
- **Devices**: WAN routers, core routers, access switches, spine/leaf switches
- **Interfaces**: Properly configured with VLANs and IP addressing
- **IPAM**: Prefixes associated with locations and interfaces

## 💬 Example Queries

Try these in the chat UI:

### **Location Queries (supports both abbreviations and full names):**
- "What prefixes exist at NYDC?" or "What prefixes exist at New York Data Center?"
- "Show me all devices at BRCN" or "Show me all devices at Brazil Campus?"
- "List devices at USBN1" or "List devices at US Branch Network Branch 1"
- "What's at London Data Center?" or "What's at LODC?"

### **Device Role Queries:**
- "Show me all WAN routers at NYDC"
- "List all Spine switches at London Data Center"
- "What Leaf switches are at LODC?"
- "Show me all Branch Access switches at USBN1"
- "List Core routers at Brazil Campus"
- "What Campus Access switches are at DACN?"

### **Combined Queries:**
- "Show me all WAN routers at New York Data Center"
- "List all Spine switches at LODC"
- "What Branch Access devices are at Mexico Branch Network Branch 1?"
- "Show me all Core routers at Korea Campus"

### **Complex Analysis Queries (Version 2.0):**
- "Can you provide prefixes and devices at location BRCN and tell me what interfaces are on those devices?"
- "Show me all devices at NYDC and their interface configurations"
- "What are the WAN interfaces at London Data Center and their circuit information?"
- "Get all devices at USBN1 and show me their interfaces with IP addresses"

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

## 🤝 Contributing New Tools

To add new MCP tools to the server:

### **1. Add Tool Function**
Create your tool function in `services/mcp-nautobot/mcp_server/tools/` directory.

### **2. Register Tool in Server**
Add the tool to `services/mcp-nautobot/mcp_server/server.py`:

```python
# Create Tool instance
my_tool = Tool.from_function(
    fn=my_tool_function,
    name="my_tool_name",
    description="""Detailed description of what the tool does.

        Args:
            param1: Description of parameter 1
            param2: Description of parameter 2

        Returns:
            Description of what the tool returns
        """
)

# Add to server
server.add_tool(my_tool)
```

### **3. Tool Descriptions & LLM Communication**
The `description` field is crucial - it's what the LLM reads to understand:
- **What the tool does**
- **What parameters it accepts**
- **What it returns**
- **Example values and formats**

The LLM uses this description to decide when and how to call your tool. Be specific and include examples!

## 🔍 Troubleshooting

### **General Issues**
- **Services not starting**: Check `docker-compose logs` for errors
- **Chat UI not loading**: Ensure all services are healthy with `docker-compose ps`
- **API errors**: Verify your `NAUTOBOT_TOKEN` is set correctly in `.env`

### **Seed Data Issues**

If you're not seeing data in your queries, the seed container may have failed:

1. **Check seed container logs:**
   ```bash
   docker-compose logs seed-data
   ```

2. **Look for common seed errors:**
   - Connection timeouts to Nautobot
   - Authentication failures
   - Database constraint violations
   - Missing dependencies

3. **Rerun seed container if needed:**
   ```bash
   # Stop and remove the seed container
   docker-compose rm -f seed-data
   
   # Restart it to rerun the seeding process
   docker-compose up -d seed-data
   
   # Check logs again
   docker-compose logs -f seed-data
   ```

4. **Verify data was created:**
   - Go to http://localhost:8080 and log into Nautobot
   - Check that locations, devices, and prefixes exist
   - If no data exists, the seed process failed

5. **Common seed container issues:**
   - **Nautobot not ready**: Seed container starts before Nautobot is fully initialized
   - **Network connectivity**: Container can't reach Nautobot API
   - **Permission issues**: API token doesn't have sufficient permissions
   - **Database locks**: Concurrent operations causing conflicts

## 📝 License

Apache-2.0
