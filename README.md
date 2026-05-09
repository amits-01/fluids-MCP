# Fluids MCP - AI Assistant Platform

A multi-tier MCP-based server architecture that bridges AI assistants and 
domain-specific CFD engineering applications. Engineers can drive simulation 
workflows using natural language from inside their IDE or a chat interface.

## Architecture Overview

```
AI Client (Chat UI / IDE)
            ↓
    Top-level Orchestrator (port 8000)  <- LLM-based routing
            ↓
    Fluids Sub-orchestrator (port 8001) <- Domain gateway
            ↓
    +-----------------+     +------------------+
    | Generation Leaf |     | Validation Leaf  |
    | (port 8002)     |     | (port 8003)      |
    | Groq LLM        |     | Mocked HTTP API  |
    | UDF generation  |     | Bearer token auth|
    +-----------------+     +------------------+
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/amits-01/fluids-MCP.git
cd fluids-MCP
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

GROQ_API_KEY=your_groq_api_key_here

VALIDATION_API_TOKEN=mock_token_12345

Get a free Groq API key at: https://console.groq.com

### 5. Start all services

```bash
.\startup.bat
```

This starts all four services in the correct order with proper delays.

### 6. Open the Chat UI

http://localhost:8000

---

## Service Endpoints

| Service | Port | Endpoints |
|---|---|---|
| Top-level Orchestrator | 8000 | `POST /chat`, `GET /tools`, `GET /health`, `GET /` |
| Fluids Sub-orchestrator | 8001 | `POST /execute`, `POST /register`, `GET /tools`, `GET /health` |
| Generation Leaf | 8002 | `POST /execute`, `GET /health` |
| Validation Leaf | 8003 | `POST /execute`, `GET /health` |

---

## Example Queries

**UDF Generation:**

Generate a UDF for parabolic inlet velocity profile
Write C code for temperature dependent viscosity
Create a UDF for turbulent inlet boundary condition

**Setup Validation:**

Validate my k-epsilon turbulence setup for pipe flow
Check my simulation setup for boundary layer resolution
Is my mesh density sufficient for turbulent flow?

---

## How It Works

### 1. Dynamic Tool Registration
Leaf servers register themselves with the sub-orchestrator on startup.
No manual configuration required - add a new leaf server and it
registers automatically.

### 2. LLM-Based Routing
The top-level orchestrator uses Groq's LLaMA model to read the tool
manifest and decide which tool to invoke based on natural language intent.
Routing is purely description-driven - no hardcoded rules.

### 3. Graceful Degradation
If a leaf server is unavailable, the sub-orchestrator returns a clean
error response. The system continues serving other available tools.

### 4. Request Tracing
Every request gets a unique request_id that flows through all tiers.
Visible in logs for end-to-end debugging.

---

## Project Structure

```
fluids_mcp/
├── config/
│   └── config.yaml              # ports, endpoints, LLM config
├── orchestrator/
│   └── main.py                  # top-level orchestrator + chat UI
├── sub_orchestrators/
│   └── fluids/
│       └── main.py              # fluids domain sub-orchestrator
├── leaf_servers/
│   ├── generation/
│   │   └── main.py              # UDF generation via Groq LLM
│   └── validation/
│       └── main.py              # CFD validation (mocked HTTP backend)
├── shared/
│   ├── models.py                # shared Pydantic models
│   └── registry.py              # dynamic tool registry
├── tests/
│   └── test_routing.py          # routing + end-to-end tests
├── ui/
│   └── index.html               # chat UI
├── startup.bat                  # starts all services
└── requirements.txt
```

---

## Running Tests

```bash
venv\Scripts\pytest tests/ -v
```

Expected output: **8 passed**

Tests cover:
- LLM routing correctness for generation queries
- LLM routing correctness for validation queries
- Tool registry registration and discovery
- Tool manifest format validation
- Unknown tool handling
- Multiple tool registration
- End-to-end generation flow
- Graceful degradation when no tools available

---

## Mocks

The validation leaf server uses a **mocked HTTP backend** to simulate
a real CFD validation REST API with bearer token authentication.

In production this would call a real endpoint:
```python
response = await client.post(
    f"{VALIDATION_API_URL}/validate",
    headers={"Authorization": f"Bearer {VALIDATION_API_TOKEN}"},
    json={"setup": setup_description}
)
```

The mock is clearly marked in `leaf_servers/validation/main.py`.

---

## Adding a New Domain

To add a completely new domain (e.g. structural analysis):

1. Create `sub_orchestrators/structural/main.py`
2. Create new leaf servers under `leaf_servers/`
3. Add ports to `config/config.yaml`
4. Add startup commands to `startup.bat`

**No changes required to the top-level orchestrator.**
The new sub-orchestrator registers its tools dynamically.

---

## Configuration

All configuration is in `config/config.yaml`:

```yaml
orchestrator:
  port: 8000

sub_orchestrators:
  fluids:
    port: 8001

leaf_servers:
  generation:
    port: 8002
  validation:
    port: 8003

llm:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  temperature: 0.1
```

Secrets are managed via `.env` - never hardcoded.

