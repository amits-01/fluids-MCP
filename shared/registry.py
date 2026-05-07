import logging
from typing import Dict, List, Optional
from shared.models import ToolRegistration

logger = logging.getLogger(__name__)

class ToolRegistry:
    # register() - leaf server will call this on startup. 
    # get_all_tools() - orchestrator will call this to find all tools.

    def __init__(self):
        self._tools: dict[str, ToolRegistration] = {}

    def register(self, tool: ToolRegistration) -> None:
        self._tools[tool.tool_name] = tool
        logger.info(f"Tool registered: {tool.tool_name} at {tool.endpoint}")

    def get_all_tools(self) -> list[ToolRegistration]:
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> ToolRegistration | None:
        return self._tools.get(tool_name)

    def get_tool_manifest(self) -> list[dict]:
        # LLm will read this to know about tools, which to use and how to use
        return [
            {
                "tool_name": tool.tool_name,
                "tool_type": tool.tool_type,
                "description": tool.description,
                "endpoint": tool.endpoint
            }
            for tool in self._tools.values()
        ]

    def remove(self, tool_name: str) -> None:
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Tool removed: {tool_name}")

registry = ToolRegistry()