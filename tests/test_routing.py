import os
import sys
import pytest
import httpx
from unittest.mock import AsyncMock, patch

# project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import MCPRequest, MCPResponse, ToolRegistration


# Unit Tests, Routing Logic - tests that LLM routing returns correct tool_type for different natural language queries.

class TestLLMRouting:

    @pytest.mark.asyncio
    async def test_generation_query_routes_correctly(self):
        mock_tools = [
            {
                "tool_name": "udf_generation",
                "tool_type": "generation",
                "description": "Generates CFD UDF code from natural language",
                "endpoint": "http://localhost:8002/execute"
            },
            {
                "tool_name": "cfd_validation",
                "tool_type": "validation",
                "description": "Validates CFD simulation setup",
                "endpoint": "http://localhost:8003/execute"
            }
        ]

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": "generation"
                }
            }]
        })

        with patch("orchestrator.main.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            from orchestrator.main import route_with_llm
            result = await route_with_llm(
                "Generate a UDF for inlet velocity profile",
                mock_tools
            )

        assert result == "generation"

    @pytest.mark.asyncio
    async def test_validation_query_routes_correctly(self):
        mock_tools = [
            {
                "tool_name": "udf_generation",
                "tool_type": "generation",
                "description": "Generates CFD UDF code from natural language",
                "endpoint": "http://localhost:8002/execute"
            },
            {
                "tool_name": "cfd_validation",
                "tool_type": "validation",
                "description": "Validates CFD simulation setup",
                "endpoint": "http://localhost:8003/execute"
            }
        ]

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": "validation"
                }
            }]
        })

        with patch("orchestrator.main.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            from orchestrator.main import route_with_llm
            result = await route_with_llm(
                "Validate my k-epsilon turbulence setup",
                mock_tools
            )

        assert result == "validation"
    

# Unit Tests, Tool Registry - tests that tools can be registered, retrieved, and listed correctly. 
# Also tests edge cases like unknown tools and multiple registrations.

class TestToolRegistry:

    def test_tool_registration(self):
        from shared.registry import ToolRegistry
        registry = ToolRegistry()

        tool = ToolRegistration(
            tool_name="udf_generation",
            tool_type="generation",
            description="Generates UDF code",
            endpoint="http://localhost:8002/execute"
        )

        registry.register(tool)
        assert registry.get_tool("udf_generation") is not None

    def test_tool_manifest_format(self):
        from shared.registry import ToolRegistry
        registry = ToolRegistry()

        tool = ToolRegistration(
            tool_name="cfd_validation",
            tool_type="validation",
            description="Validates CFD setup",
            endpoint="http://localhost:8003/execute"
        )

        registry.register(tool)
        manifest = registry.get_tool_manifest()

        assert len(manifest) == 1
        assert manifest[0]["tool_name"] == "cfd_validation"
        assert manifest[0]["tool_type"] == "validation"
        assert "description" in manifest[0]
        assert "endpoint" in manifest[0]

    def test_unknown_tool_returns_none(self):
        from shared.registry import ToolRegistry
        registry = ToolRegistry()

        result = registry.get_tool("nonexistent_tool")
        assert result is None

    def test_multiple_tools_registered(self):
        from shared.registry import ToolRegistry
        registry = ToolRegistry()

        tools = [
            ToolRegistration(
                tool_name="udf_generation",
                tool_type="generation",
                description="Generates UDF",
                endpoint="http://localhost:8002/execute"
            ),
            ToolRegistration(
                tool_name="cfd_validation",
                tool_type="validation",
                description="Validates setup",
                endpoint="http://localhost:8003/execute"
            )
        ]

        for tool in tools:
            registry.register(tool)

        assert len(registry.get_all_tools()) == 2


# Integration Test, end-to-end Flow - tests full request flow from orchestrator to leaf. 
# Uses mocked sub-orchestrator response. Also tests graceful degradation when no tools are available.

class TestEndToEnd:

    @pytest.mark.asyncio
    async def test_full_generation_flow(self):

        from fastapi.testclient import TestClient
        from orchestrator.main import app

        # Mock discover_tools
        mock_tools = [
            {
                "tool_name": "udf_generation",
                "tool_type": "generation",
                "description": "Generates CFD UDF code",
                "endpoint": "http://localhost:8002/execute"
            }
        ]

        # Mock sub-orchestrator response
        mock_response_data = {
            "success": True,
            "tool_used": "udf_generation",
            "result": "/* Generated UDF code */\nDEFINE_PROFILE(inlet, t, i) {}",
            "error": None
        }

        with patch("orchestrator.main.discover_tools", return_value=mock_tools), \
             patch("orchestrator.main.route_with_llm", return_value="generation"), \
             patch("orchestrator.main.httpx.AsyncClient") as mock_client:

            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )

            client = TestClient(app)
            response = client.post(
                "/chat",
                json={"query": "Generate a UDF for inlet velocity"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool_used"] == "udf_generation"
        assert data["result"] is not None

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_tools(self):

        from fastapi.testclient import TestClient
        from orchestrator.main import app

        with patch("orchestrator.main.discover_tools", return_value=[]):
            client = TestClient(app)
            response = client.post(
                "/chat",
                json={"query": "Generate a UDF"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No tools available" in data["error"]