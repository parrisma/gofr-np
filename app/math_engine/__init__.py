"""Math Engine - High-performance mathematical operations.

This module provides a clean abstraction over numerical computing backends.
The implementation details (TensorFlow, NumPy, etc.) are hidden from consumers.
"""

from app.math_engine.base import MathCapability, MathResult, ToolDefinition
from app.math_engine.engine import MathEngine, get_engine

__all__ = [
    "MathCapability",
    "MathResult",
    "ToolDefinition",
    "MathEngine",
    "get_engine",
]
