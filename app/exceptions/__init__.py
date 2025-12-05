"""Custom exceptions for GOFRNP application.

All exceptions include detailed error messages designed for LLM processing,
enabling intelligent error recovery and decision-making.
"""

from app.exceptions.base import (
    GofrNpError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
    ConfigurationError,
    RegistryError,
    MathError,
    InvalidInputError,
    ComputationError,
)

__all__ = [
    # Base exceptions
    "GofrNpError",
    "ValidationError",
    "ResourceNotFoundError",
    "SecurityError",
    "ConfigurationError",
    "RegistryError",
    "MathError",
    "InvalidInputError",
    "ComputationError",
]
