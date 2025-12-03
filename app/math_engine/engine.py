"""Math Engine - Facade for all mathematical capabilities.

This module provides a unified interface to all math capabilities.
For direct MCP tool handling, use the tool_registry instead.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logger import session_logger as logger
from app.math_engine.base import MathCapability, MathResult
from app.math_engine.capabilities import ElementwiseCapability


class MathEngine:
    """Unified interface to all math engine capabilities.

    This facade provides a simple API for direct programmatic use.
    For MCP tool handling, use the tool_registry module instead.
    """

    def __init__(self):
        """Initialize the math engine with all capabilities."""
        self._capabilities: Dict[str, MathCapability] = {}

        # Initialize all capabilities
        self._register_capability(ElementwiseCapability())

        logger.info(
            "MathEngine initialized",
            capabilities=list(self._capabilities.keys()),
        )

    def _register_capability(self, capability: MathCapability) -> None:
        """Register a capability."""
        self._capabilities[capability.name] = capability

    def get_capability(self, name: str) -> Optional[MathCapability]:
        """Get a capability by name."""
        return self._capabilities.get(name)

    @property
    def elementwise(self) -> ElementwiseCapability:
        """Get the elementwise capability for direct access."""
        cap = self._capabilities.get("elementwise")
        if cap is None:
            raise RuntimeError("ElementwiseCapability not registered")
        return cap  # type: ignore

    def compute(
        self,
        operation: str,
        a: Any,
        b: Any = None,
        precision: str = "float64",
    ) -> MathResult:
        """Convenience method for elementwise compute.

        This maintains backward compatibility with existing code.
        """
        return self.elementwise.compute(
            operation=operation,
            a=a,
            b=b,
            precision=precision,  # type: ignore
        )

    def list_operations(self) -> Dict[str, List[str]]:
        """List all operations from all capabilities."""
        all_ops: Dict[str, List[str]] = {}

        for cap in self._capabilities.values():
            cap_ops = cap.list_operations()
            for category, ops in cap_ops.items():
                key = f"{cap.name}.{category}" if len(self._capabilities) > 1 else category
                all_ops[key] = ops

        return all_ops

    def list_capabilities(self) -> Dict[str, str]:
        """List all registered capabilities."""
        return {
            name: cap.description
            for name, cap in self._capabilities.items()
        }


# Module-level singleton for convenience
_engine: Optional[MathEngine] = None


def get_engine() -> MathEngine:
    """Get or create the singleton MathEngine instance."""
    global _engine
    if _engine is None:
        _engine = MathEngine()
    return _engine
