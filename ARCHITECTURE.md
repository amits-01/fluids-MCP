# Architecture Document - Fluids MCP Platform

## 1. System Overview

The Fluids MCP Platform is a multi-tier server architecture that bridges 
AI assistants and domain-specific CFD engineering applications. It allows 
engineers to drive simulation workflows using natural language from a 
chat interface or IDE, without needing to know the internal system topology.

---

## 2. System-Level Diagram

    +---------------------------+
    |      AI Client            |
    |  (Chat UI / IDE Copilot)  |
    +------------+--------------+
                 |
                 | Natural language query
                 | POST /chat
                 v
    +---------------------------+
    |   Top-level Orchestrator  |   Port 8000
    |                           |
    |  - Single entry point     |
    |  - LLM-based routing      |
    |  - Tool discovery         |
    |  - Request tracing        |
    +------------+--------------+
                 |
                 | Routed MCPRequest
                 | POST /execute
                 v
    +---------------------------+
    |  Fluids Sub-orchestrator  |   Port 8001
    |                           |
    |  - Domain gateway         |
    |  - Tool registry          |
    |  - Dynamic registration   |
    |  - Forwards to leaf       |
    +------------+--------------+
                 |
        +--------+--------+
        |                 |
        v                 v
    +----------+     +----------+
    | Generation|     |Validation|
    | Leaf      |     | Leaf     |
    | Port 8002 |     | Port 8003|
    |           |     |          |
    | Single    |     | Single   |
    | capability|     |capability|
    +-----+-----+     +----+-----+
          |                |
          v                v
    +-----------+    +-----------+
    | Groq LLM  |    | Mocked    |
    | API       |    | HTTP API  |
    | (external)|    | Bearer    |
    |           |    | Token Auth|
    +-----------+    +-----------+

---

## 3. Tool/Capability Wiring - Request Flow Diagram

    Engineer types:
    "Generate a UDF for parabolic inlet velocity"
                 |
                 v
    +---------------------------+
    | Top-level Orchestrator    |
    |                           |
    | 1. Receive query          |
    | 2. Assign request_id      |
    | 3. GET /tools from        |
    |    sub-orchestrator       |
    | 4. Send query + tools     |
    |    to Groq LLM            |
    | 5. LLM reads descriptions |
    |    returns "generation"   |
    | 6. POST /execute with     |
    |    tool_type=generation   |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    | Fluids Sub-orchestrator   |
    |                           |
    | 1. Receive routed request |
    | 2. Look up tool_type      |
    |    in local registry      |
    | 3. Find generation leaf   |
    |    endpoint               |
    | 4. Forward POST /execute  |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    | Generation Leaf Server    |
    |                           |
    | 1. Receive request        |
    | 2. Build system prompt    |
    | 3. POST to Groq API       |
    |    with physics query     |
    | 4. Receive UDF C code     |
    | 5. Return MCPResponse     |
    +------------+--------------+
                 |
                 v
    Engineer receives generated UDF C code
    displayed in Chat UI with tool badge

---

## 4. Tier Responsibilities

### Tier 1 - Top-level Orchestrator
- Single unified entry point for all AI clients
- Responsible for LLM-based intent routing only
- Discovers tools dynamically from sub-orchestrators
- Has no knowledge of what tools do internally
- Assigns request_id for end-to-end tracing

### Tier 2 - Domain Sub-orchestrator
- Groups related capabilities under one domain
- Maintains a local tool registry
- Accepts dynamic registration from leaf servers
- Routes requests to correct leaf based on tool_type
- Handles graceful degradation if leaf is unavailable

### Tier 3 - Leaf Servers
- Each owns exactly one bounded capability
- Registers itself with sub-orchestrator on startup
- Talks directly to its backend
- Backend details never leak upward
- Independently deployable and testable

---

## 5. Dynamic Tool Registration Flow

    Leaf Server starts
          |
          v
    Retry loop (5 attempts, 2s delay)
          |
          v
    POST /register to Sub-orchestrator
    {
      tool_name: "udf_generation",
      tool_type: "generation",
      description: "Generates CFD UDF code...",
      endpoint: "http://localhost:8002/execute"
    }
          |
          v
    Sub-orchestrator adds to local registry
          |
          v
    Tool available for routing immediately
    No orchestrator restart needed

---

## 6. LLM Routing Flow

    User query arrives at orchestrator
          |
          v
    GET /tools from sub-orchestrator
    Returns tool manifest:
    [
      {
        tool_name: "udf_generation",
        tool_type: "generation", 
        description: "Generates CFD UDF code..."
      },
      {
        tool_name: "cfd_validation",
        tool_type: "validation",
        description: "Validates CFD setup..."
      }
    ]
          |
          v
    LLM receives: query + tool manifest
    Prompt: "Which tool_type matches this query?
             Respond with tool_type only."
          |
          v
    LLM returns: "generation" or "validation"
          |
          v
    Orchestrator routes accordingly

Key design decision: LLM routing is description-driven.
Adding a new tool requires no routing code changes -
just a good description in the tool registration.

---

## 7. Security Design

    Credential Flow:
    
    .env file (never committed)
         |
         v
    python-dotenv loads at startup
         |
         v
    Environment variables in memory
         |
         v
    Used in HTTP headers only
    Never logged, never returned to client
    
    Controls in place:
    - .env in .gitignore
    - Secrets loaded via os.getenv()
    - Audit logging logs metadata only
    - Bearer token used in validation leaf
      but never exposed upward

---

## 8. Graceful Degradation

    If Generation Leaf is down:
    
    Sub-orchestrator attempts POST /execute
          |
          v
    httpx.TimeoutException caught
          |
          v
    Returns MCPResponse(
      success=False,
      error="Leaf server timed out"
    )
          |
          v
    Orchestrator returns clean error to client
    Other tools remain available

---

## 9. Request Tracing

Every request gets a unique request_id assigned
by the orchestrator and carried through all tiers in this fashion:

    [a3f9b2c1] Orchestrator received: Generate a UDF...
    [a3f9b2c1] LLM routed to: generation
    [a3f9b2c1] Sub-orchestrator forwarding to generation leaf
    [a3f9b2c1] Generation leaf processing request

This allows full end-to-end debugging across
all four services from a single request_id.

---

## 10. Adding a New Domain

To add Structural Analysis domain tomorrow:

    1. Create sub_orchestrators/structural/main.py
       (copy fluids, change service name and port)
    
    2. Create leaf_servers/stress_analysis/main.py
       (implement single capability)
    
    3. Add to config/config.yaml:
       sub_orchestrators:
         structural:
           port: 8004
       leaf_servers:
         stress_analysis:
           port: 8005
    
    4. Add startup commands to startup.bat
    
    Zero changes to top-level orchestrator.
    Zero changes to existing fluids servers.
    New tools appear in routing automatically
    once leaf registers with its sub-orchestrator.