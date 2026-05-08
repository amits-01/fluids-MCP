import logging
import httpx
import yaml
import asyncio
from fastapi import FastAPI
from shared.models import MCPRequest, MCPResponse, ToolRegistration, HealthResponse
from shared.registry import ToolRegistry

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

logging.basicConfig(level=config["logging"]["level"].upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="Fluids Sub-orchestrator")

MY_PORT = config["sub_orchestrators"]["fluids"]["port"]

# Local registry for this sub-orchestrator
# Leaf servers register here on startup
registry = ToolRegistry()


# Endpoints

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service="fluids-sub-orchestrator",
        port=MY_PORT
    )


# leaf servers will call this to register themselves on startup
@app.post("/register")
async def register_tool(tool: ToolRegistration):
    registry.register(tool)
    logger.info(f"Leaf registered: {tool.tool_name} at {tool.endpoint}")
    return {"status": "registered", "tool_name": tool.tool_name}


# returns a list of all registered tools with their details. 
# This is used by the top-level orchestrator to know what tools are available in this sub-orchestrator.
@app.get("/tools")
async def list_tools():
    return registry.get_tool_manifest()


# Receives routed request from top-level orchestrator.
# Finds correct leaf server and forwards request.
@app.post("/execute", response_model=MCPResponse)
async def execute(request: MCPRequest):
    logger.info(f"[{request.request_id}] Sub-orchestrator received: {request.query}, tool: {request.tool_type}")

    # Find the right leaf based on tool_type
    tools = registry.get_all_tools()
    target_tool = None

    for tool in tools:
        if tool.tool_type == request.tool_type:
            target_tool = tool
            break

    # Graceful degradation if tool not found
    if not target_tool:
        logger.warning(f"No tool found for type: {request.tool_type}")
        return MCPResponse(
            success=False,
            tool_used="none",
            result=None,
            error=f"No tool available for type: {request.tool_type}"
        )

    # Forward request to correct leaf server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_tool.endpoint,
                json=request.model_dump(),
                timeout=30.0
            )
            return MCPResponse(**response.json())

    except httpx.TimeoutException:
        logger.error(f"Leaf server timeout: {target_tool.endpoint}")
        return MCPResponse(
            success=False,
            tool_used=target_tool.tool_name,
            result=None,
            error="Leaf server timed out"
        )

    except Exception as e:
        logger.error(f"Leaf server error: {e}")
        return MCPResponse(
            success=False,
            tool_used=target_tool.tool_name,
            result=None,
            error=str(e)
        )