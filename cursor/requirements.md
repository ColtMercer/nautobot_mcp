# Nautobot FastMCP Server + Streamlit Chat — Requirements

> **Goal**: Ship a self‑contained, dockerized reference project that exposes a **FastMCP** server for the Nautobot OSS platform, plus a lightweight **LLM chat UI** that can (a) list available MCP tools per‑server, (b) call them, and (c) **export chat transcripts** for use as proof in PRs. The stack seeds Nautobot with **fake demo data** so anyone can `docker compose up` and try it.

---

## 1) Scope & Success Criteria

**In scope**

- An **MCP server** implemented with **FastMCP** exposing Nautobot utilities.
- Two exemplar MCP tools:
  1. `get_prefixes_by_location(location_name: string)` → returns Prefix objects for a given site/region.
  2. `llm_chat(query: string, …)` → LLM assistant that can **call any MCP tool** and cite the tool calls it used.
- A **Chat UI** (assume **Streamlit**) that:
  - Lists **all registered MCP servers** and their **tool catalogs**.
  - Executes tools, shows inputs/outputs, and tool call traces.
  - **Exports** the entire chat (JSON + Markdown) with tool call metadata.
- **Dockerized env**: Nautobot + Postgres/Redis (or required deps), FastMCP server, Streamlit UI, and **init containers** that seed demo data.
- Dev/ops quality: tests, linting, typed code, structured logging, metrics, basic security/auth, docs.

**Out of scope** (for v1)

- Extra MCP servers (beyond placeholders for discovery).
- Full RBAC/SSO—keep a minimal token-based approach for local dev.

**Definition of Done (DoD)**

- `docker compose up` brings up:
  - Nautobot with seeded data and GraphQL enabled.
  - FastMCP server healthy and discoverable.
  - Streamlit chat UI reachable at `http://localhost:8501` (configurable).
- Demo flow works end-to-end: ask LLM for prefixes at a location → tool executed → results returned and attributed.
- “Export Chat” produces **both** `transcript.json` and `transcript.md` capturing user turns, AI turns, and per‑turn tool call artifacts.
- CI passes: unit tests, type checks, lint, formatting.

---

## 2) High-Level Architecture

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

- **Streamlit Chat**: thin UI + session manager, calls MCP client to fetch tool catalogs and execute tools.
- **MCP Client SDK**: small utility that discovers MCP servers (from config), lists tools, dispatches calls, returns structured traces.
- **FastMCP Server**: hosts tool handlers; talks to Nautobot via GraphQL.
- **Nautobot**: running with demo data, GraphQL enabled.

---

## 3) MCP Server (FastMCP)

**Language**: Python 3.11+

**Key requirements**

- Use **FastMCP** to define and register tools with JSONSchemas.
- Tool discovery endpoint (per MCP spec) exposes name, description, params/returns.
- Structured logging for each call with correlation id and duration.
- Config via env vars: NAUTOBOT\_URL, NAUTOBOT\_TOKEN, GRAPHQL\_PATH, LOG\_LEVEL, etc.
- Health endpoint `/healthz` returns 200 w/ build SHA.

**Tools**

1. `get_prefixes_by_location(location_name: str)`

   - **Description**: Return all prefixes under a Nautobot Location (site/region/campus) by human‑friendly name.
   - **Input schema**:
     ```json
     {"type":"object","properties":{"location_name":{"type":"string"}},"required":["location_name"]}
     ```
   - **Output schema** (array of prefixes):
     ```json
     {"type":"array","items":{"type":"object","properties":{"prefix":{"type":"string"},"status":{"type":"string"},"role":{"type":"string"},"description":{"type":"string"}}}}
     ```
   - **GraphQL** (example):
     ```graphql
     query PrefixesByLocation($name: String!) {
       prefixes(filter: { site: { name: $name } }) {
         edges {
           node { prefix status { value } role { name } description }
         }
       }
     }
     ```
   - **Acceptance**: returns ≥1 item for demo locations (e.g., "HQ-Dallas").

2. `llm_chat(message: string, context?: object)`

   - **Description**: An LLM tool that can **call other MCP tools** as needed and **records citations** of tools used.
   - **Behavior**:
     - Use ReAct-style planning: think → choose tool(s) → observe → answer.
     - When tool called, persist `{tool, args, result_summary}` in the turn metadata.
     - Return final answer + citations array (list of tool call ids).

**Error handling**

- Map Nautobot GraphQL errors to MCP error objects with `code`, `message`, `details`.
- Timeouts: 10s default for downstream GraphQL.

**Observability**

- Logs to stdout in JSON (level, ts, component, correlation\_id, latency\_ms).
- Metrics: simple `/metrics` (Prometheus) with counters for tool calls, errors, durations.

---

## 4) Chat UI (Streamlit)

**Why Streamlit**: quick to ship, zero-ops, easy Dockerize. (If a different UI is later preferred, keep the MCP client layer UI‑agnostic.)

**Features**

- **Left sidebar**: MCP server list → select one or many; show tool catalog per server.
- **Main pane**: chat transcript; each AI turn shows any tool calls as expandable accordions (request/response preview).
- **Controls**:
  - Model selector (env‑driven default).
  - Temperature/top‑p sliders.
  - **Export** buttons: `Export JSON`, `Export Markdown`.
  - `Clear chat`.
- **Persistence**: Session state in local storage; optional bind mount volume for exports at `/exports`.

**Export formats**

- `transcript.json`: array of turns with `{role, text, tool_calls:[{server,tool,args,summary}], timestamps}`.
- `transcript.md`: readable log with fenced blocks for tool calls.

---

## 5) Data Seeding (Init Containers)

- A one‑shot container runs after Nautobot becomes healthy.
- Creates demo **Locations** (e.g., `HQ-Dallas`, `HQ-London`, `LAB-Austin`).
- Inserts varied **Prefixes** with different roles/status values.
- Validates via a small script that GraphQL queries return items.

---

## 6) Docker Compose (Top-Level)

**Services (baseline)**

- `nautobot` (and `db`, `redis` if required by distro image)
- `mcp-nautobot` (FastMCP server)
- `chat-ui` (Streamlit)
- `seed-data` (depends\_on: nautobot healthy)
- `otel-collector` (optional, can be a stub)

**Env & networking**

- All services on a shared `devnet` network.
- `.env` file for secrets and configuration.
- Named volume for Nautobot DB data; bind mount for exports.

**Compose snippet (illustrative)**

```yaml
version: "3.9"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: nautobot
      POSTGRES_USER: nautobot
      POSTGRES_PASSWORD: nautobot
    volumes:
      - dbdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL","pg_isready -U nautobot"]
      interval: 5s
      timeout: 5s
      retries: 20

  redis:
    image: redis:7-alpine

  nautobot:
    image: networktocode/nautobot:stable
    environment:
      NAUTOBOT_DB_HOST: db
      NAUTOBOT_DB_NAME: nautobot
      NAUTOBOT_DB_USER: nautobot
      NAUTOBOT_DB_PASSWORD: nautobot
      NAUTOBOT_ALLOWED_HOSTS: "*"
      # ensure GraphQL is enabled by default in this image/config
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    ports: ["8080:8080"]

  mcp-nautobot:
    build: ./services/mcp-nautobot
    environment:
      NAUTOBOT_URL: http://nautobot:8080
      NAUTOBOT_TOKEN: changeme
      GRAPHQL_PATH: /graphql
      LOG_LEVEL: info
    depends_on:
      nautobot:
        condition: service_started
    ports: ["7000:7000"]

  chat-ui:
    build: ./services/chat-ui
    environment:
      MCP_SERVERS: |
        [
          {"name":"nautobot","url":"http://mcp-nautobot:7000"}
        ]
      DEFAULT_MODEL: gpt-4o-mini
    volumes:
      - ./exports:/app/exports
    ports: ["8501:8501"]

  seed-data:
    build: ./services/seed-data
    environment:
      NAUTOBOT_URL: http://nautobot:8080
      NAUTOBOT_TOKEN: changeme
    depends_on:
      nautobot:
        condition: service_started

volumes:
  dbdata: {}
```

---

## 7) Project Structure (for Cursor)

```
/ (repo root)
├─ docker-compose.yml
├─ .env.example
├─ Makefile
├─ README.md
├─ exports/                # chat exports (gitignored)
├─ services/
│  ├─ mcp-nautobot/
│  │  ├─ Dockerfile
│  │  ├─ pyproject.toml
│  │  ├─ mcp_server/
│  │  │  ├─ __init__.py
│  │  │  ├─ server.py      # FastMCP bootstrap, routes
│  │  │  ├─ tools/
│  │  │  │  ├─ prefixes.py # get_prefixes_by_location
│  │  │  │  └─ llm_chat.py # tool-aware assistant
│  │  │  └─ clients/
│  │  │     └─ nautobot_graphql.py
│  │  └─ tests/
│  │     ├─ test_prefixes.py
│  │     └─ test_schemas.py
│  ├─ chat-ui/
│  │  ├─ Dockerfile
│  │  ├─ app.py            # Streamlit UI
│  │  ├─ mcp_client.py     # discovery + tool exec
│  │  └─ exporters.py      # json/md
│  └─ seed-data/
│     ├─ Dockerfile
│     └─ seed.py
└─ ci/
   ├─ pre-commit-config.yaml
   └─ github-actions.yml
```

---

## 8) Implementation Notes

### 8.1 FastMCP server bootstrap (Python sketch)

```python
# server.py
from fastmcp import MCPApp
from tools.prefixes import get_prefixes_by_location
from tools.llm_chat import llm_chat

app = MCPApp(name="nautobot", version="0.1.0")

app.register_tool(
    name="get_prefixes_by_location",
    description="Return Nautobot prefixes for a given location name.",
    input_schema={"type":"object","properties":{"location_name":{"type":"string"}},"required":["location_name"]},
    output_schema={"type":"array","items":{"type":"object","properties":{"prefix":{"type":"string"},"status":{"type":"string"},"role":{"type":"string"},"description":{"type":"string"}}}},
    handler=get_prefixes_by_location,
)

app.register_tool(
    name="llm_chat",
    description="LLM chat that may call other MCP tools and returns citations.",
    input_schema={"type":"object","properties":{"message":{"type":"string"}},"required":["message"]},
    output_schema={"type":"object","properties":{"answer":{"type":"string"},"citations":{"type":"array","items":{"type":"object"}}}},
    handler=llm_chat,
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
```

### 8.2 Nautobot GraphQL client (Python sketch)

```python
# clients/nautobot_graphql.py
import os, requests

BASE = os.environ.get("NAUTOBOT_URL", "http://nautobot:8080")
PATH = os.environ.get("GRAPHQL_PATH", "/graphql")
TOKEN = os.environ.get("NAUTOBOT_TOKEN")

HEADERS = {"Authorization": f"Token {TOKEN}"} if TOKEN else {}

PREFIXES_QUERY = """
query PrefixesByLocation($name: String!) {
  prefixes(filter: { site: { name: $name } }) {
    edges { node { prefix status { value } role { name } description } }
  }
}
"""

def prefixes_by_location(name: str):
    r = requests.post(f"{BASE}{PATH}", json={"query": PREFIXES_QUERY, "variables": {"name": name}}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    edges = data["data"]["prefixes"]["edges"]
    return [
        {
            "prefix": n["node"]["prefix"],
            "status": (n["node"]["status"] or {}).get("value"),
            "role": (n["node"]["role"] or {}).get("name"),
            "description": n["node"].get("description"),
        }
        for n in edges
    ]
```

### 8.3 Tool handler (Python sketch)

```python
# tools/prefixes.py
from clients.nautobot_graphql import prefixes_by_location

def get_prefixes_by_location(location_name: str):
    return prefixes_by_location(location_name)
```

### 8.4 LLM tool (minimal, calls back into MCP tools)

```python
# tools/llm_chat.py
import json
from typing import Dict, Any, List

# placeholder: in v1, simply call the prefixes tool when user asks for prefixes
# future: add a planning layer (ReAct) + tool registry lookup

def llm_chat(message: str, **kwargs) -> Dict[str, Any]:
    citations: List[Dict[str, Any]] = []
    answer = ""
    if "prefix" in message.lower() and "location" in message.lower():
        from .prefixes import get_prefixes_by_location
        # naive parse of location
        loc = message.split("location")[-1].strip().strip(": ?.") or "HQ-Dallas"
        res = get_prefixes_by_location(loc)
        citations.append({"tool": "get_prefixes_by_location", "args": {"location_name": loc}, "result_count": len(res)})
        if res:
            answer = f"Found {len(res)} prefixes at {loc}. First: {res[0]['prefix']}"
        else:
            answer = f"No prefixes found at {loc}."
    else:
        answer = "I can help with Nautobot prefixes by location. Ask me for prefixes at a given location."
    return {"answer": answer, "citations": citations}
```

---

## 9) Chat UI (Streamlit) sketch

```python
# services/chat-ui/app.py
import os, json, requests, streamlit as st

MCP_SERVERS = json.loads(os.environ.get("MCP_SERVERS", "[]"))

st.set_page_config(page_title="MCP Chat", layout="wide")
st.sidebar.title("MCP Servers")

selected = st.sidebar.multiselect(
    "Select servers", options=[s["name"] for s in MCP_SERVERS], default=[s["name"] for s in MCP_SERVERS]
)

# toy catalog fetch (assume GET /tools returns tool specs)
@st.cache_data
def fetch_catalog(server):
    try:
        return requests.get(server["url"] + "/tools", timeout=5).json()
    except Exception as e:
        return {"error": str(e)}

catalogs = {s["name"]: fetch_catalog(s) for s in MCP_SERVERS if s["name"] in selected}

with st.sidebar:
    for name, cat in catalogs.items():
        st.subheader(name)
        if "tools" in cat:
            for t in cat["tools"]:
                st.text(f"• {t['name']}: {t.get('description','')}")
        else:
            st.error(cat.get("error", "No tools"))

st.title("MCP Chat")
if "chat" not in st.session_state:
    st.session_state.chat = []

for turn in st.session_state.chat:
    with st.chat_message(turn["role"]):
        st.markdown(turn["text"])
        for c in turn.get("citations", []):
            with st.expander(f"Tool: {c['tool']}"):
                st.json(c)

msg = st.chat_input("Ask something (e.g., prefixes at HQ-Dallas)")
if msg:
    st.session_state.chat.append({"role": "user", "text": msg})
    with st.chat_message("assistant"):
        # naive route to llm_chat on the first server
        server = MCP_SERVERS[0]
        r = requests.post(server["url"] + "/tools/llm_chat:invoke", json={"message": msg})
        data = r.json()
        st.session_state.chat.append({"role": "assistant", "text": data.get("answer","(no answer)"), "citations": data.get("citations", [])})
        st.markdown(data.get("answer","(no answer)"))

col1, col2 = st.columns(2)
with col1:
    if st.button("Export JSON"):
        p = "exports/transcript.json"
        os.makedirs("exports", exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(st.session_state.chat, f, indent=2)
        st.success(f"Saved {p}")
with col2:
    if st.button("Export Markdown"):
        p = "exports/transcript.md"
        os.makedirs("exports", exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for t in st.session_state.chat:
                f.write(f"**{t['role'].upper()}**: {t['text']}\n\n")
                for c in t.get("citations", []):
                    f.write(f"> Tool {c['tool']} args={c.get('args')} result_count={c.get('result_count')}\n\n")
        st.success(f"Saved {p}")
```

---

## 10) Security & Config

- Local dev token for Nautobot via `.env` → **never** check real tokens into git.
- CORS allowlist: restrict to chat UI host.
- Rate limiting: simple token bucket per IP or per API key (optional for v1).
- Healthz hidden behind no‑auth; tool invocations require an **MCP API key** (static for local).

**.env.example**

```
NAUTOBOT_URL=http://nautobot:8080
NAUTOBOT_TOKEN=changeme
GRAPHQL_PATH=/graphql
MCP_API_KEY=dev-mcp-key
DEFAULT_MODEL=gpt-4o-mini
```

---

## 11) Testing Strategy

- **Unit tests**: tool handlers, GraphQL client error paths.
- **Contract tests**: tool schemas validate with JSONSchema; discovery returns expected shapes.
- **Integration tests**: dockerized `pytest -m integration` spins minimal Nautobot + server and asserts real GraphQL results.
- **Golden tests**: sample chat inputs produce deterministic markdown exports (snapshot compare, allow small diffs).

**Makefile targets**

```
make format      # ruff/black/isort
make lint        # ruff
make typecheck   # mypy/pyright
make test        # pytest
make up          # docker compose up -d --build
make down        # docker compose down -v
```

---

## 12) Observability

- **Logging**: JSON to stdout; include `trace_id`, `tool`, `latency_ms`, `status`.
- **Metrics**: Prometheus /metrics endpoint (counters, histograms for tool latency).
- **Tracing**: optional OpenTelemetry stubs; env flags to enable.

---

## 13) Developer Experience (Cursor)

- Provide this file + `ROADMAP.md` as context. Cursor should:
  - Scaffold folders/files above.
  - Add pre-commit hooks for format/lint.
  - Generate unit/integration test skeletons.
  - Keep containerized dev workflow only (no local venv assumptions).
  - On each step, **update **`` with progress and next steps.

**Cursor Kickoff Prompt (paste into Cursor)**

> Use the attached requirements to scaffold the repo. Create Dockerfiles, compose, seed script, FastMCP server, Streamlit UI, tests, and CI. Keep all dev/testing in containers. After each milestone, update ROADMAP.md and run `make up` smoke tests. Ensure `Export JSON/Markdown` works and that `get_prefixes_by_location` returns data for demo locations.

---

## 14) Roadmap (initial)

1. Repo & CI scaffolding (pre-commit, lint/type/test).
2. Nautobot + DB/Redis compose, health checks.
3. Seed container + fake data script; validate GraphQL.
4. FastMCP server skeleton with discovery + healthz.
5. Implement `get_prefixes_by_location` tool + tests.
6. Minimal `llm_chat` tool that can call other tools and emit citations.
7. Streamlit chat UI: server list, catalog view, chat, export.
8. Observability: metrics + structured logs.
9. Security polish: API key guard on tool invocations.
10. Docs + examples + sample exports.

---

## 15) Acceptance Tests (manual)

- **AT-1**: From the chat UI, list tools for the `nautobot` MCP server.
- **AT-2**: Ask: “What prefixes exist at HQ-Dallas?” → returns ≥1 with example.
- **AT-3**: The response shows a **tool call trace** with `get_prefixes_by_location`.
- **AT-4**: Export JSON + MD; files appear under `./exports` with expected content.
- **AT-5**: Kill/restart `mcp-nautobot`; healthz shows build SHA; chat resumes.

---

## 16) Future Enhancements

- Multi-location queries; pagination handling.
- Additional Nautobot tools (devices by role, interfaces by site, VLANs by location, etc.).
- Richer planner for `llm_chat` (ReAct/Toolformer), multi‑tool chaining, retries.
- Auth integration with Nautobot users; scoped tokens / RBAC.
- Switchable frontend (FastAPI+HTMX) while keeping MCP client layer.

---

## 17) Licensing & Community

- License: Apache-2.0 (friendly for enterprises).
- PR template asks contributors to attach a **chat export** demonstrating new tool behavior under varied prompts.
- Code of Conduct + contribution guide.

---

## 18) Risks & Mitigations

- **GraphQL schema differences**: pin Nautobot version in compose; document tested versions.
- **LLM determinism**: use temperature 0 for golden tests; mock tool calls when snapshotting.
- **Secrets leakage**: `.env` only; mount not committed.

---

## 19) Quickstart

```bash
cp .env.example .env
# set NAUTOBOT_TOKEN in .env if needed
make up
# open http://localhost:8501 and ask: "Show prefixes at HQ-Dallas"
```

---

*Assumption note*: “Streamline app” interpreted as **Streamlit** UI. If a different framework is intended, we can swap the UI service while keeping the MCP client layer unchanged.

