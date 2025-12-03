"""Tool Registry for MCP Server.

Central registry that collects tools from all math engine capabilities
and provides them to the MCP server.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mcp.types import Tool

from app.logger import session_logger as logger
from app.math_engine.base import MathCapability, MathResult, ToolDefinition

if TYPE_CHECKING:
    pass


class ToolRegistry:
    """Registry for MCP tools from math engine capabilities.

    Collects tool definitions from capability modules and provides:
    - MCP Tool objects for list_tools()
    - Routing of tool calls to appropriate capability handlers
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._capabilities: Dict[str, MathCapability] = {}
        self._tool_to_capability: Dict[str, str] = {}
        self._tools: Dict[str, ToolDefinition] = {}
        logger.info("ToolRegistry initialized")

    def register_capability(self, capability: MathCapability) -> None:
        """Register a capability and its tools.

        Args:
            capability: The capability instance to register

        Raises:
            ValueError: If capability name conflicts or tool names conflict
        """
        cap_name = capability.name

        if cap_name in self._capabilities:
            raise ValueError(f"Capability '{cap_name}' already registered")

        # Register capability
        self._capabilities[cap_name] = capability

        # Register all tools from this capability
        for tool_def in capability.get_tools():
            if tool_def.name in self._tools:
                existing_cap = self._tool_to_capability[tool_def.name]
                raise ValueError(
                    f"Tool '{tool_def.name}' already registered by capability '{existing_cap}'"
                )

            self._tools[tool_def.name] = tool_def
            self._tool_to_capability[tool_def.name] = cap_name

        logger.info(
            "Capability registered",
            capability=cap_name,
            tools=[t.name for t in capability.get_tools()],
        )

    def get_mcp_tools(self) -> List[Tool]:
        """Get all registered tools as MCP Tool objects.

        Returns:
            List of MCP Tool objects ready for list_tools() response
        """
        mcp_tools = []

        for tool_def in self._tools.values():
            mcp_tools.append(
                Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema=tool_def.input_schema,
                )
            )

        return mcp_tools

    def get_tool_names(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

    def handle_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MathResult:
        """Route a tool call to the appropriate capability.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments from MCP

        Returns:
            MathResult from the capability handler

        Raises:
            ValueError: If tool is not registered
        """
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: '{tool_name}'")

        cap_name = self._tool_to_capability[tool_name]
        capability = self._capabilities[cap_name]

        logger.debug(
            "Routing tool call",
            tool=tool_name,
            capability=cap_name,
        )

        return capability.handle(tool_name, arguments)

    def list_capabilities(self) -> Dict[str, str]:
        """List all registered capabilities.

        Returns:
            Dict mapping capability names to descriptions
        """
        return {
            name: cap.description
            for name, cap in self._capabilities.items()
        }

    def get_capability(self, name: str) -> Optional[MathCapability]:
        """Get a capability by name."""
        return self._capabilities.get(name)


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def initialize_registry() -> ToolRegistry:
    """Initialize the registry with all available capabilities.

    Call this at server startup to register all capabilities.

    Returns:
        The initialized ToolRegistry
    """
    from app.math_engine.capabilities import (
        ElementwiseCapability,
        CurveFitCapability,
        FinancialCapability,
    )

    registry = get_registry()

    # Register all capabilities
    # Add new capabilities here as they are implemented
    registry.register_capability(ElementwiseCapability())
    registry.register_capability(CurveFitCapability())
    registry.register_capability(FinancialCapability())

    logger.info(
        "Registry initialized",
        capabilities=list(registry.list_capabilities().keys()),
        tools=registry.get_tool_names(),
    )

    return registry
