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

app = FastAPI(title="Generation Leaf Server")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MY_PORT = config["leaf_servers"]["generation"]["port"]
MY_ENDPOINT = f"http://localhost:{MY_PORT}/execute"
FLUIDS_SUB_ORCHESTRATOR = f"http://localhost:{config['sub_orchestrators']['fluids']['port']}"


# Tool Logic - using Groq LLM to generate CFD UDF code from natural language description
async def generate_udf(query: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": config["llm"]["model"],
                "temperature": config["llm"]["temperature"],
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a CFD expert. Generate Fluent UDF C code "
                            "based on the user's physics description. "
                            "Return only the C code with brief comments. "
                            "Code should be ready to compile in Fluent. "
                            "Include necessary headers and function definitions. "
                            "Include comments explaining the physics being implemented. "
                            "No explanation outside the code."
                        )
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            },
            timeout=30.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]



# Endpoints - /health for health checks, /execute for tool execution
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service="generation-leaf",
        port=MY_PORT
    )


@app.post("/execute", response_model=MCPResponse)
async def execute(request: MCPRequest):
    logger.info(f"[{request.request_id}] Generation leaf received: {request.query}")
    try:
        result = await generate_udf(request.query)
        return MCPResponse(
            success=True,
            tool_used="udf_generation",
            result=result
        )
    except Exception as e:
        logger.error(f"[{request.request_id}] Generation failed: {e}")
        return MCPResponse(
            success=False,
            tool_used="udf_generation",
            result=None,
            error=str(e)
        )


# Self registration with sub-orchestrator on startup
@app.on_event("startup")
async def register_with_sub_orchestrator():
    # On startup, this leaf will register itself
    # with the Fluids sub-orchestrator dynamically.
    # No manual config needed in orchestrator.
    
    tool = ToolRegistration(
        tool_name="udf_generation",
        tool_type="generation",
        description=(
            "Generates CFD User Defined Function (UDF) code in C "
            "from a natural language physics description. "
            "Use when user wants to create, write, or generate a UDF "
            "for Fluent simulation."
            "Input should be a description of the physics to implement in the UDF. "
        ),
        endpoint=MY_ENDPOINT
    )

    # Retry registration in case sub-orchestrator isn't up yet
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

    logger.error("Failed to register with sub-orchestrator after 5 attempts")