import os
import logging
import httpx
import yaml
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
from shared.models import MCPRequest, MCPResponse, ToolRegistration, HealthResponse

load_dotenv()

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

logging.basicConfig(level=config["logging"]["level"].upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="Validation Leaf Server")

MY_PORT = config["leaf_servers"]["validation"]["port"]
MY_ENDPOINT = f"http://localhost:{MY_PORT}/execute"
FLUIDS_SUB_ORCHESTRATOR = f"http://localhost:{config['sub_orchestrators']['fluids']['port']}"

# Mocked backend config
VALIDATION_API_URL = config["backends"]["validation_api"]["base_url"]
VALIDATION_API_TOKEN = os.getenv("VALIDATION_API_TOKEN")


# Mocked External HTTP Backend
# In production this would call a real validation service
# Marked as mock as per assignment instructions

async def call_validation_backend(setup_description: str) -> dict:

    logger.info(f"Calling validation backend at {VALIDATION_API_URL}")
    logger.info("Authorization: Bearer token used — not logged for security")

    # Simulate HTTP call with bearer token auth
    # In production this would be:
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"{VALIDATION_API_URL}/validate",
    #         headers={"Authorization": f"Bearer {VALIDATION_API_TOKEN}"},
    #         json={"setup": setup_description}
    #     )
    #     return response.json()

    # Mock response simulating what real API would return
    return {
        "status": "valid",
        "warnings": [
            "Mesh density may be insufficient near boundary layer",
            "Consider refining near wall regions for k-epsilon model"
        ],
        "errors": [],
        "recommendation": (
            "Setup is valid for simulation. "
            "Review warnings before running full solver."
        )
    }


# Tool Logic - validates CFD simulation setup by calling external validation backend

async def validate_cfd_setup(query: str) -> dict:
    result = await call_validation_backend(query)
    return result


# Endpoints - /health for health checks, /execute for tool execution

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service="validation-leaf",
        port=MY_PORT
    )


@app.post("/execute", response_model=MCPResponse)
async def execute(request: MCPRequest):
    logger.info(f"Validation leaf received: {request.query}")
    try:
        result = await validate_cfd_setup(request.query)
        return MCPResponse(
            success=True,
            tool_used="cfd_validation",
            result=result
        )
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return MCPResponse(
            success=False,
            tool_used="cfd_validation",
            result=None,
            error=str(e)
        )


# Self Registration with sub-orchestrator on startup

@app.on_event("startup")
async def register_with_sub_orchestrator():
    tool = ToolRegistration(
        tool_name="cfd_validation",
        tool_type="validation",
        description=(
            "Validates a CFD simulation setup against Fluent best practices. "
            "Checks boundary conditions, mesh quality, solver settings. "
            "Use when user wants to validate, check, or verify a simulation setup."
        ),
        endpoint=MY_ENDPOINT
    )
    for attempt in range(5):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FLUIDS_SUB_ORCHESTRATOR}/register",
                    json=tool.model_dump(),
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info("Successfully registered with Fluids sub-orchestrator")
                    return
        except Exception as e:
            logger.warning(f"Registration attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)

    logger.error("Failed to register after 5 attempts")