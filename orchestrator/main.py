import os
import logging
import httpx
import yaml
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from shared.models import MCPRequest, MCPResponse, HealthResponse

load_dotenv()

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

logging.basicConfig(level=config["logging"]["level"].upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="Top-level Orchestrator")

MY_PORT = config["orchestrator"]["port"]
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FLUIDS_SUB_ORCHESTRATOR = f"http://localhost:{config['sub_orchestrators']['fluids']['port']}"


# LLM Routing - uses LLM to decide which tool to invoke based on user query and available tools.

async def route_with_llm(query: str, tools: list[dict]) -> str:
    tool_descriptions = json.dumps(tools, indent=2)

    prompt = f"""You are a routing assistant for a CFD engineering platform.
    Given a user query and available tools, decide which tool_type to use.
    Respond with ONLY the tool_type value — nothing else.

    Available tools:
    {tool_descriptions}

    User query: {query}

    Respond with only the tool_type value from the list above."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": config["llm"]["model"],
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            timeout=30.0
        )
        data = response.json()
        tool_type = data["choices"][0]["message"]["content"].strip().lower()
        logger.info(f"LLM routed to: {tool_type}")
        return tool_type


# Tool Discovery - calls sub-orchestrator to get current tool manifest. LLM reads this to make routing decisions.

async def discover_tools() -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FLUIDS_SUB_ORCHESTRATOR}/tools",
                timeout=5.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"Tool discovery failed: {e}")
        return []


# Endpoints - health check, tool listing, main chat endpoint, and a simple UI for testing.

@app.get("/health", response_model=HealthResponse)
async def health():
    sub_status = "unreachable"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{FLUIDS_SUB_ORCHESTRATOR}/health",
                timeout=3.0
            )
            if r.status_code == 200:
                sub_status = "healthy"
    except Exception:
        sub_status = "unreachable"

    return HealthResponse(
        status=f"healthy | sub-orchestrator: {sub_status}",
        service="top-level-orchestrator",
        port=MY_PORT
    )


@app.get("/tools")
async def list_tools():
    return await discover_tools()


# entry point for all AI clients. Accepts natural language, routes to correct tool, returns result.
@app.post("/chat", response_model=MCPResponse)
async def chat(request: MCPRequest):
    logger.info(f"Orchestrator received: {request.query}")

    # Step 1 — Discover available tools
    tools = await discover_tools()

    if not tools:
        return MCPResponse(
            success=False,
            tool_used="none",
            result=None,
            error="No tools available — sub-orchestrator may be down"
        )

    # Step 2 — LLM decides which tool to use
    tool_type = await route_with_llm(request.query, tools)

    # Step 3 — Forward to sub-orchestrator with routing decision
    routed_request = MCPRequest(
        query=request.query,
        tool_type=tool_type,
        parameters=request.parameters
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FLUIDS_SUB_ORCHESTRATOR}/execute",
                json=routed_request.model_dump(),
                timeout=60.0
            )
            return MCPResponse(**response.json())

    except httpx.TimeoutException:
        logger.error("Sub-orchestrator timeout")
        return MCPResponse(
            success=False,
            tool_used="none",
            result=None,
            error="Sub-orchestrator timed out"
        )

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        return MCPResponse(
            success=False,
            tool_used="none",
            result=None,
            error=str(e)
        )


# chat UI - for manual testing. Not meant for production use. 

@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    with open("ui/index.html", "r", encoding="utf-8") as f:
        return f.read()