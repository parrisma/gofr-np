"""Element-wise and Broadcasting Operations Capability.

Provides high-performance element-wise mathematical computations
with automatic broadcasting support.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Union

# Suppress TensorFlow logging before import
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import tensorflow as tf  # noqa: E402 - must be after env var is set

# Disable TensorFlow warnings
tf.get_logger().setLevel("ERROR")

from app.logger import session_logger as logger  # noqa: E402 - must be after tf config
from app.logger.decorators import log_execution_time  # noqa: E402
from app.math_engine.base import MathCapability, MathResult, ToolDefinition  # noqa: E402
from app.exceptions import InvalidInputError  # noqa: E402


# Type aliases
ArrayLike = Union[List[Any], float, int]
Precision = Literal["float32", "float64"]

# Supported operations
UNARY_OPS = frozenset({
    "exp", "log", "log10", "log2",
    "sqrt", "square", "abs",
    "sin", "cos", "tan",
    "sinh", "cosh", "tanh",
    "floor", "ceil", "round",
    "negate", "reciprocal",
    "sign", "sigmoid", "relu",
})

BINARY_OPS = frozenset({
    "add", "subtract", "multiply", "divide",
    "power", "mod", "maximum", "minimum",
    "greater", "less", "equal", "not_equal",
    "greater_equal", "less_equal",
    "logical_and", "logical_or", "logical_xor",
})

ALL_OPS = UNARY_OPS | BINARY_OPS


class ElementwiseCapability(MathCapability):
    """Element-wise mathematical operations with broadcasting."""

    @property
    def name(self) -> str:
        return "elementwise"

    @property
    def description(self) -> str:
        return "Element-wise mathematical operations with automatic broadcasting"

    def get_tools(self) -> List[ToolDefinition]:
        """Return list of tool definitions."""
        return [
            ToolDefinition(
                name="math_compute",
                description="Perform element-wise mathematical operations (add, sub, mul, div, exp, log, etc.) on scalars or arrays with broadcasting.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "The mathematical operation to perform.",
                            "enum": sorted(ALL_OPS),
                        },
                        "a": {
                            "description": "First operand (scalar or array).",
                            "anyOf": [
                                {"type": "number"},
                                {"type": "array", "items": {"type": "number"}},
                                {"type": "array", "items": {"type": "array"}},  # Nested arrays
                            ],
                        },
                        "b": {
                            "description": "Second operand for binary operations.",
                            "anyOf": [
                                {"type": "number"},
                                {"type": "array", "items": {"type": "number"}},
                                {"type": "array", "items": {"type": "array"}},
                            ],
                        },
                        "precision": {
                            "type": "string",
                            "description": "Computation precision.",
                            "enum": ["float32", "float64"],
                            "default": "float64",
                        },
                    },
                    "required": ["operation", "a"],
                },
                handler_name="handle",
            ),
            ToolDefinition(
                name="math_list_operations",
                description="List all supported mathematical operations.",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
                handler_name="handle",
            ),
        ]

    def __init__(self):
        """Initialize the elementwise capability."""
        logger.info("ElementwiseCapability initialized")

    @log_execution_time
    def handle(self, tool_name: str, arguments: Dict[str, Any]) -> MathResult:
        """Route tool invocation to appropriate handler."""
        if tool_name == "math_compute":
            operation = arguments.get("operation")
            a = arguments.get("a")
            b = arguments.get("b")
            precision = arguments.get("precision", "float64")

            if not operation:
                raise InvalidInputError("Missing required argument: operation")
            if a is None:
                raise InvalidInputError("Missing required argument: a")

            return self.compute(operation, a, b, precision)
        elif tool_name == "math_list_operations":
            ops = self.list_operations()
            return MathResult(
                result=ops,
                shape=[],
                dtype="object"
            )
        else:
            raise InvalidInputError(f"Unknown tool: {tool_name}")

    def _to_tensor(self, data: ArrayLike, precision: Precision) -> tf.Tensor:
        """Convert input to TensorFlow tensor with specified precision."""
        dtype = tf.float64 if precision == "float64" else tf.float32
        try:
            return tf.convert_to_tensor(data, dtype=dtype)
        except (ValueError, TypeError) as e:
            raise InvalidInputError(f"Failed to convert input to tensor: {str(e)}")

    def _to_result(self, tensor: tf.Tensor) -> MathResult:
        """Convert tensor to MathResult."""
        numpy_result = tensor.numpy()  # type: ignore[union-attr]

        # Convert to nested Python lists for JSON serialization
        if numpy_result.ndim == 0:
            # Scalar
            result_list = float(numpy_result)
        else:
            result_list = numpy_result.tolist()

        shape_list: list[int] = tensor.shape.as_list()  # type: ignore[assignment]
        dtype_name = str(tensor.dtype.name)  # type: ignore[union-attr]

        return MathResult(
            result=result_list,
            shape=shape_list,
            dtype=dtype_name,
        )

    def compute(
        self,
        operation: str,
        a: ArrayLike,
        b: ArrayLike | None = None,
        precision: Precision = "float64",
    ) -> MathResult:
        """
        Perform an element-wise mathematical operation.

        Args:
            operation: The operation to perform (e.g., "add", "exp", "sqrt")
            a: First operand (array or scalar)
            b: Second operand for binary operations (array or scalar)
            precision: Numeric precision ("float32" or "float64")

        Returns:
            MathResult with the computed result, shape, and dtype

        Raises:
            InvalidInputError: If operation is unknown or arguments are invalid
        """
        operation = operation.lower()

        if operation not in ALL_OPS:
            raise InvalidInputError(
                f"Unknown operation: '{operation}'. "
                f"Supported: {sorted(ALL_OPS)}"
            )

        # Convert inputs to tensors
        tensor_a = self._to_tensor(a, precision)

        # Handle unary operations
        if operation in UNARY_OPS:
            result = self._unary_op(operation, tensor_a)

        # Handle binary operations
        elif operation in BINARY_OPS:
            if b is None:
                raise InvalidInputError(
                    f"Operation '{operation}' requires two operands (b is missing)"
                )
            tensor_b = self._to_tensor(b, precision)
            result = self._binary_op(operation, tensor_a, tensor_b)

        else:
            raise InvalidInputError(f"Operation '{operation}' not implemented")

        logger.debug(
            "Math compute completed",
            operation=operation,
            input_shape=tensor_a.shape.as_list(),
            output_shape=result.shape.as_list(),
        )

        return self._to_result(result)

    def _unary_op(self, operation: str, a: tf.Tensor) -> tf.Tensor:
        """Execute a unary operation."""
        ops_map = {
            "exp": tf.exp,
            "log": tf.math.log,
            "log10": lambda x: tf.math.log(x) / tf.math.log(tf.constant(10.0, dtype=x.dtype)),
            "log2": lambda x: tf.math.log(x) / tf.math.log(tf.constant(2.0, dtype=x.dtype)),
            "sqrt": tf.sqrt,
            "square": tf.square,
            "abs": tf.abs,
            "sin": tf.sin,
            "cos": tf.cos,
            "tan": tf.tan,
            "sinh": tf.sinh,
            "cosh": tf.cosh,
            "tanh": tf.tanh,
            "floor": tf.floor,
            "ceil": tf.math.ceil,
            "round": tf.round,
            "negate": tf.negative,
            "reciprocal": tf.math.reciprocal,
            "sign": tf.sign,
            "sigmoid": tf.sigmoid,
            "relu": tf.nn.relu,
        }

        op_func = ops_map.get(operation)
        if op_func is None:
            raise InvalidInputError(f"Unary operation '{operation}' not found")

        return op_func(a)

    def _binary_op(self, operation: str, a: tf.Tensor, b: tf.Tensor) -> tf.Tensor:
        """Execute a binary operation with broadcasting."""
        ops_map = {
            "add": tf.add,
            "subtract": tf.subtract,
            "multiply": tf.multiply,
            "divide": tf.divide,
            "power": tf.pow,
            "mod": tf.math.mod,
            "maximum": tf.maximum,
            "minimum": tf.minimum,
            "greater": tf.greater,
            "less": tf.less,
            "equal": tf.equal,
            "not_equal": tf.not_equal,
            "greater_equal": tf.greater_equal,
            "less_equal": tf.less_equal,
            "logical_and": tf.logical_and,
            "logical_or": tf.logical_or,
            "logical_xor": tf.math.logical_xor,
        }

        op_func = ops_map.get(operation)
        if op_func is None:
            raise InvalidInputError(f"Binary operation '{operation}' not found")

        # Handle logical operations (need boolean tensors)
        if operation.startswith("logical_"):
            a = tf.cast(a, tf.bool)  # type: ignore
            b = tf.cast(b, tf.bool)  # type: ignore

        return op_func(a, b)

    def list_operations(self) -> Dict[str, List[str]]:
        """List all supported operations by category."""
        return {
            "unary": sorted(UNARY_OPS),
            "binary": sorted(BINARY_OPS),
        }

    def list_operations_tool(self) -> Dict[str, List[str]]:
        """Handler for math_list_operations tool."""
        return self.list_operations()
