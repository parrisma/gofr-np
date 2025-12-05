"""Error response mapping for MCP and web interfaces.

Converts structured GofrNpError exceptions into standardized error responses
with machine-readable error codes and recovery strategies.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from app.exceptions import (
    GofrNpError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
)


@dataclass
class ErrorResponse:
    """Structured error response for API consumers."""

    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    recovery_strategy: Optional[str] = None


# Recovery strategy templates for common error types
RECOVERY_STRATEGIES: Dict[str, str] = {
    "REGISTRY_ERROR": "Check that the tool or capability name is valid and exists in the system.",
    "VALIDATION_ERROR": "Review the error message and adjust the request parameters accordingly.",
    "RESOURCE_NOT_FOUND": "Verify the resource ID is correct and the resource exists.",
    "SECURITY_ERROR": "Ensure your authentication token has access to the requested resource.",
    "INVALID_INPUT": "Check the input parameters. Ensure arrays have correct dimensions and values are within valid ranges.",
    "COMPUTATION_ERROR": "The computation failed. This might be due to numerical instability, overflow, or invalid mathematical operations.",
    "MATH_ERROR": "A general math error occurred. Check input values for domain errors (e.g., sqrt of negative number).",
}


def get_recovery_strategy(error_code: str) -> str:
    """Get recovery strategy for an error code.

    Args:
        error_code: The error code

    Returns:
        Recovery strategy string
    """
    return RECOVERY_STRATEGIES.get(
        error_code, "Review the error message, adjust the request, and try again."
    )


def map_exception_to_response(error: Exception) -> ErrorResponse:
    """Convert an exception to a structured ErrorResponse.

    Args:
        error: The exception to convert

    Returns:
        ErrorResponse with structured error information
    """
    if isinstance(error, GofrNpError):
        # Structured GOFRNP error with code, message, details
        return ErrorResponse(
            error_code=error.code,
            message=error.message,
            details=error.details if error.details else None,
            recovery_strategy=get_recovery_strategy(error.code),
        )

    # Handle Pydantic validation errors
    from pydantic import ValidationError as PydanticValidationError

    if isinstance(error, PydanticValidationError):
        errors = error.errors()
        return ErrorResponse(
            error_code="PYDANTIC_VALIDATION_ERROR",
            message=f"Validation failed: {len(errors)} error(s)",
            details={"errors": errors},
            recovery_strategy="Check the error details and provide valid input according to the schema.",
        )

    # Generic exceptions - wrap with minimal structure
    return ErrorResponse(
        error_code="INTERNAL_ERROR",
        message=str(error),
        details={"exception_type": type(error).__name__},
        recovery_strategy="An unexpected error occurred. Please report this issue if it persists.",
    )


def map_error_for_mcp(error: Exception) -> Dict[str, Any]:
    """Map exception to MCP tool response format.

    Args:
        error: The exception to convert

    Returns:
        Dictionary suitable for MCP tool response
    """
    response = map_exception_to_response(error)

    return {
        "status": "error",
        "error_code": response.error_code,
        "message": response.message,
        "details": response.details,
        "recovery_strategy": response.recovery_strategy,
    }


def map_error_for_web(error: Exception, status_code: int = 400) -> Dict[str, Any]:
    """Map exception to web API response format.

    Args:
        error: The exception to convert
        status_code: HTTP status code (default 400)

    Returns:
        Dictionary suitable for FastAPI JSONResponse
    """
    response = map_exception_to_response(error)

    return {
        "status": "error",
        "error": {
            "code": response.error_code,
            "message": response.message,
            "details": response.details,
            "recovery": response.recovery_strategy,
        },
    }


def get_http_status_for_error(error: Exception) -> int:
    """Determine appropriate HTTP status code for an error.

    Args:
        error: The exception

    Returns:
        HTTP status code
    """
    if isinstance(error, ResourceNotFoundError):
        return 404
    elif isinstance(error, SecurityError):
        return 403
    elif isinstance(error, ValidationError):
        return 400
    elif isinstance(error, GofrNpError):
        return 400
    else:
        return 500
