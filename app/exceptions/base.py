"""Project-specific exception classes for GOFRNP application.

Base exceptions (GofrError, ValidationError, etc.) are provided by gofr_common.
This module contains only GOFRNP-specific exceptions.
"""

from typing import Dict, Optional, Any

# Import base from gofr_common
from gofr_common.exceptions import GofrError

# Backward compatibility alias
GofrNpError = GofrError


class MathError(GofrError):
    """Base for all math engine errors."""
    pass


class InvalidInputError(MathError):
    """Raised when input parameters are invalid (wrong type, shape, or value)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="INVALID_INPUT", message=message, details=details)


class ComputationError(MathError):
    """Raised when a computation fails (overflow, singular matrix, etc.)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="COMPUTATION_ERROR", message=message, details=details)

