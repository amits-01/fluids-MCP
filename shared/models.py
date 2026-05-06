from pydantic import BaseModel
from typing import Any, Optional
from enum import Enum


class ToolType(str, Enum):
    GENERATION = "generation"
    VALIDATION = "validation"


# Request that flows top to bottom through all tiers
class MCPRequest(BaseModel):
    query: str                                  # natural language from user
    tool_type: Optional[ToolType] = None        # filled by orchestrator after routing
    parameters: Optional[dict] = None           # additional parameters


# Response that flows bottom to top through all tiers
class MCPResponse(BaseModel):
    success: bool
    tool_used: str
    result: Any
    error: Optional[str] = None


# How each leaf server registers itself with sub-orchestrator
class ToolRegistration(BaseModel):
    tool_name: str                      # unique name
    tool_type: ToolType                 # generation or validation
    description: str                    # what this tool does - LLM reads this
    endpoint: str                       # where to send requests
    version: str = "1.0.0"


# Health check response
class HealthResponse(BaseModel):
    status: str
    service: str
    port: int