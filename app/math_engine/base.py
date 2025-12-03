"""Base classes for math engine capabilities.

All capability modules should inherit from MathCapability and implement
the required interface for tool registration and computation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Union


@dataclass
class MathResult:
    """Result of a math computation."""

    result: Union[List[Any], float, int, Dict[str, Any]]
    shape: List[int]
    dtype: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "result": self.result,
            "shape": self.shape,
            "dtype": self.dtype,
        }


@dataclass
class ToolDefinition:
    """Definition of an MCP tool provided by a capability."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler_name: str  # Method name on the capability class


class MathCapability(ABC):
    """Base class for all math engine capabilities.

    Each capability module (elementwise, statistics, linalg, etc.) should:
    1. Inherit from this class
    2. Implement get_tools() to declare its MCP tools
    3. Implement handler methods for each tool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this capability (e.g., 'elementwise', 'statistics')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this capability."""
        pass

    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Return list of tool definitions this capability provides.

        Each tool definition includes:
        - name: Tool name exposed via MCP
        - description: Tool description for LLM
        - input_schema: JSON schema for tool parameters
        - handler_name: Method name to call on this capability

        Returns:
            List of ToolDefinition objects
        """
        pass

    @abstractmethod
    def handle(self, tool_name: str, arguments: Dict[str, Any]) -> MathResult:
        """Handle a tool invocation.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments from MCP

        Returns:
            MathResult with computed values

        Raises:
            ValueError: If tool_name is unknown or arguments are invalid
        """
        pass

    def list_operations(self) -> Dict[str, List[str]]:
        """List operations supported by this capability.

        Override this method to provide categorized operation lists.

        Returns:
            Dictionary mapping category names to lists of operation names
        """
        return {}
