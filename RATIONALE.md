# Design Rationale — Fluids MCP Platform

## 1. Protocol and Framework Choice

### Inter-tier Communication — HTTP REST via FastAPI

I chose HTTP REST over alternatives like gRPC, message queues, 
or native MCP stdio transport for the following reasons:

**Why FastAPI:**
- Async-first with native asyncio support — essential for handling 
  concurrent requests from multiple engineers without blocking
- Automatic request/response validation via Pydantic models — 
  enforces clean contracts between tiers at runtime
- Built-in OpenAPI docs at /docs — every tier is self-documenting
- Lightweight and fast to iterate on — appropriate for a prototype
  that needs to demonstrate architectural thinking clearly

**Why HTTP over gRPC:**
- Each tier is independently runnable and testable with standard 
  HTTP tooling — curl, Postman, browser
- No schema compilation step — faster iteration during prototyping
- Easier to debug across tiers — standard HTTP logs are readable
- At production scale, gRPC would be worth reconsidering for 
  its performance characteristics and strong schema contracts

**Why not native MCP stdio transport:**
- stdio transport is designed for local same-machine communication
- Our tiers are designed to be independently deployable — 
  potentially on different machines or containers
- HTTP+SSE transport is the correct MCP transport for enterprise 
  remote deployments, which is what this architecture targets

### LLM Provider — Groq with LLaMA 3.3

I chose Groq as the LLM provider because:
- OpenAI-compatible API — satisfies the assignment requirement 
  and allows provider swapping via config with zero code changes
- Free tier available — no access barriers for reviewers running 
  the prototype
- Fast inference — LLaMA 3.3 70B on Groq responds in ~1-2 seconds,
  keeping routing latency acceptable

Provider swap requires only one config change:
```yaml
llm:
  provider: "groq"           # change to "openai" or "azure"
  model: "llama-3.3-70b-versatile"
  api_key: "${GROQ_API_KEY}"
```

---

## 2. How to Add a New Domain Tomorrow

The architecture is designed for zero-orchestrator-change extensibility.
Adding a Structural Analysis domain requires exactly four steps:

**Step 1 — Create the sub-orchestrator:**
Copy `sub_orchestrators/fluids/main.py` to 
`sub_orchestrators/structural/main.py`.
Change the service name and port. No logic changes needed.

**Step 2 — Create leaf servers:**
Create `leaf_servers/stress_analysis/main.py` with a single 
bounded capability. Implement the `register_with_sub_orchestrator` 
startup function pointing to the structural sub-orchestrator.

**Step 3 — Add to config:**
```yaml
sub_orchestrators:
  structural:
    port: 8004

leaf_servers:
  stress_analysis:
    port: 8005
```

**Step 4 — Add to startup script:**
Add two new uvicorn commands to startup.bat.

**What does NOT change:**
- Top-level orchestrator — zero modifications
- Existing fluids servers — completely unaffected
- Routing logic — new tools appear automatically in the 
  tool manifest once the structural leaf registers itself
- LLM routing — description-driven, no hardcoded rules

This extensibility is possible because:
- Tool discovery is dynamic — orchestrator polls sub-orchestrators
- Routing is description-driven — LLM reads tool descriptions
- Each tier has a clean contract — MCPRequest/MCPResponse models

---

## 3. Trade-offs and Production Scale Considerations

### Trade-offs Made in This Prototype

**In-memory tool registry:**
The sub-orchestrator stores registered tools in memory. If it 
restarts, all leaf registrations are lost and leaves must re-register.
This is acceptable for a prototype — in production, a persistent 
registry (Redis or a database) would be used.

**Synchronous LLM routing:**
Every request makes a live LLM call for routing. This adds 1-2 
seconds of latency per request. At production scale I would 
add a routing cache — identical or semantically similar queries 
return cached routing decisions without an LLM call.

**Single sub-orchestrator per domain:**
Currently one sub-orchestrator handles all fluids capabilities. 
At production scale this becomes a single point of failure. 
Horizontal scaling with a load balancer in front of multiple 
sub-orchestrator instances would address this.

**Mocked validation backend:**
The validation leaf uses a mocked HTTP backend. In production 
this would call the real Fluids One validation API. The mock 
is clearly marked in the code and the real implementation 
would require only replacing the mock function body.

**No authentication on orchestrator:**
The chat endpoint is currently open. In production, OAuth2 or 
API key authentication would be added at the orchestrator level, 
with per-tool RBAC enforced at the sub-orchestrator.

### What I Would Do Differently at Production Scale

**1. Persistent Tool Registry**
Replace in-memory registry with Redis. Tool registrations 
survive sub-orchestrator restarts. Leaf servers can also 
deregister on graceful shutdown.

**2. Routing Cache**
Add semantic caching for LLM routing decisions. Similar queries 
return cached tool_type instantly. Reduces latency from ~2s to 
~50ms for repeated query patterns.

**3. Authentication and RBAC**
Add OAuth2 at the orchestrator entry point. Enforce per-tool 
authorization policies at the sub-orchestrator — not every 
engineer should have access to every capability.

**4. Horizontal Scaling**
Each tier is stateless by design — ready for horizontal scaling 
behind a load balancer. The only stateful component is the tool 
registry, which moves to Redis at scale.

**5. Structured Observability**
Replace Python logging with structured JSON logs (structlog). 
Add OpenTelemetry tracing — the request_id foundation is already 
in place. Add Prometheus metrics for request latency, routing 
decisions, and leaf server error rates.

**6. Contract Versioning**
Add version field to MCPRequest and ToolRegistration. 
Orchestrator can route to different leaf versions simultaneously 
during rolling deployments. Prevents breaking changes from 
propagating across the entire system at once.

**7. gRPC for Inter-tier Communication**
At production scale with high throughput, replace HTTP REST 
with gRPC between tiers. Strongly typed contracts via protobuf, 
better performance, and built-in streaming support for long-running 
simulation tasks.

---

## 4. Key Design Decisions Summary

| Decision | Choice | Reason |
|---|---|---|
| Inter-tier protocol | HTTP REST | Simple, debuggable, independently testable |
| Framework | FastAPI | Async, Pydantic validation, self-documenting |
| Tool discovery | Dynamic registration | Zero orchestrator changes for new leaves |
| LLM routing | Description-driven | No hardcoded routing rules |
| LLM provider | Groq (OpenAI-compatible) | Free, fast, swappable via config |
| Credentials | python-dotenv + env vars | Never hardcoded, never logged |
| Tracing | request_id across tiers | Full end-to-end debuggability |
| Degradation | Per-leaf error handling | System stays up if one leaf fails |