"""Custom exceptions for GOFRNP application.

All exceptions include detailed error messages designed for LLM processing,
enabling intelligent error recovery and decision-making.

Base exceptions are re-exported from gofr_common.exceptions.
Project-specific exceptions (MathError, etc.) are defined locally.
"""

# Re-export common exceptions from gofr_common
from gofr_common.exceptions import (
    GofrError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
    ConfigurationError,
    RegistryError,
)

# Project-specific exceptions
from app.exceptions.base import (  # noqa: E402 - must come after gofr_common imports
    MathError,
    InvalidInputError,
    ComputationError,
)

# Project-specific alias for backward compatibility
GofrNpError = GofrError

__all__ = [
    # Base exceptions (from gofr_common)
    "GofrError",
    "GofrNpError",  # Alias for backward compatibility
    "ValidationError",
    "ResourceNotFoundError",
    "SecurityError",
    "ConfigurationError",
    "RegistryError",
    # Project-specific exceptions
    "MathError",
    "InvalidInputError",
    "ComputationError",
]
