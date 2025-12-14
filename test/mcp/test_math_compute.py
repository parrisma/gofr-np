"""Test math_compute MCP tool."""

import json
import os
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@pytest.fixture
def mcp_url():
    """MCP server URL."""
    port = os.environ.get("GOFR_NP_MCP_PORT", "8060")
    return f"http://localhost:{port}/mcp"


def extract_text(result) -> str:
    """Extract text from MCP result."""
    if result.content and len(result.content) > 0:
        return result.content[0].text
    return ""


def parse_json(result) -> dict:
    """Parse JSON from MCP result."""
    text = extract_text(result)
    return json.loads(text)


class TestMathListOperations:
    """Tests for math_list_operations tool."""

    @pytest.mark.asyncio
    async def test_list_operations(self, mcp_url):
        """Test listing available operations."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_list_operations", {})
                data = parse_json(result)

                assert "unary" in data
                assert "binary" in data
                assert "exp" in data["unary"]
                assert "add" in data["binary"]


class TestMathComputeUnary:
    """Tests for unary math operations."""

    @pytest.mark.asyncio
    async def test_sqrt(self, mcp_url):
        """Test square root operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "sqrt",
                    "a": [4, 9, 16, 25],
                })
                data = parse_json(result)

                assert data["result"] == [2.0, 3.0, 4.0, 5.0]
                assert data["shape"] == [4]
                assert "float" in data["dtype"]

    @pytest.mark.asyncio
    async def test_exp(self, mcp_url):
        """Test exponential operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "exp",
                    "a": [0, 1],
                })
                data = parse_json(result)

                assert len(data["result"]) == 2
                assert abs(data["result"][0] - 1.0) < 0.001
                assert abs(data["result"][1] - 2.718) < 0.01

    @pytest.mark.asyncio
    async def test_abs(self, mcp_url):
        """Test absolute value operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "abs",
                    "a": [-5, -3, 0, 3, 5],
                })
                data = parse_json(result)

                assert data["result"] == [5.0, 3.0, 0.0, 3.0, 5.0]

    @pytest.mark.asyncio
    async def test_negate(self, mcp_url):
        """Test negation operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "negate",
                    "a": [1, -2, 3],
                })
                data = parse_json(result)

                assert data["result"] == [-1.0, 2.0, -3.0]

    @pytest.mark.asyncio
    async def test_sin_cos(self, mcp_url):
        """Test trigonometric operations."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # sin(0) = 0
                result = await session.call_tool("math_compute", {
                    "operation": "sin",
                    "a": [0],
                })
                data = parse_json(result)
                assert abs(data["result"][0]) < 0.001

                # cos(0) = 1
                result = await session.call_tool("math_compute", {
                    "operation": "cos",
                    "a": [0],
                })
                data = parse_json(result)
                assert abs(data["result"][0] - 1.0) < 0.001


class TestMathComputeBinary:
    """Tests for binary math operations."""

    @pytest.mark.asyncio
    async def test_add(self, mcp_url):
        """Test addition operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "add",
                    "a": [1, 2, 3],
                    "b": [10, 20, 30],
                })
                data = parse_json(result)

                assert data["result"] == [11.0, 22.0, 33.0]

    @pytest.mark.asyncio
    async def test_subtract(self, mcp_url):
        """Test subtraction operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "subtract",
                    "a": [10, 20, 30],
                    "b": [1, 2, 3],
                })
                data = parse_json(result)

                assert data["result"] == [9.0, 18.0, 27.0]

    @pytest.mark.asyncio
    async def test_multiply(self, mcp_url):
        """Test multiplication operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "multiply",
                    "a": [2, 3, 4],
                    "b": [5, 6, 7],
                })
                data = parse_json(result)

                assert data["result"] == [10.0, 18.0, 28.0]

    @pytest.mark.asyncio
    async def test_divide(self, mcp_url):
        """Test division operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "divide",
                    "a": [10, 20, 30],
                    "b": [2, 4, 5],
                })
                data = parse_json(result)

                assert data["result"] == [5.0, 5.0, 6.0]

    @pytest.mark.asyncio
    async def test_power(self, mcp_url):
        """Test power operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "power",
                    "a": [2, 3, 4],
                    "b": 2,
                })
                data = parse_json(result)

                assert data["result"] == [4.0, 9.0, 16.0]


class TestMathComputeBroadcasting:
    """Tests for broadcasting behavior."""

    @pytest.mark.asyncio
    async def test_scalar_broadcast(self, mcp_url):
        """Test scalar broadcasting to array."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "add",
                    "a": [1, 2, 3, 4, 5],
                    "b": 10,
                })
                data = parse_json(result)

                assert data["result"] == [11.0, 12.0, 13.0, 14.0, 15.0]

    @pytest.mark.asyncio
    async def test_2d_broadcast(self, mcp_url):
        """Test 2D array broadcasting."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # [[1, 2], [3, 4]] * [10, 20] -> [[10, 40], [30, 80]]
                result = await session.call_tool("math_compute", {
                    "operation": "multiply",
                    "a": [[1, 2], [3, 4]],
                    "b": [10, 20],
                })
                data = parse_json(result)

                assert data["result"] == [[10.0, 40.0], [30.0, 80.0]]
                assert data["shape"] == [2, 2]


class TestMathComputeErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_unknown_operation(self, mcp_url):
        """Test error for unknown operation."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "unknown_op",
                    "a": [1, 2, 3],
                })

                assert result.isError
                text = extract_text(result)
                assert "unknown_op" in text
                # The error message comes from schema validation, so it might vary slightly
                # but it should mention the invalid value.

    @pytest.mark.asyncio
    async def test_missing_operand_b(self, mcp_url):
        """Test error when binary op missing second operand."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "add",
                    "a": [1, 2, 3],
                    # b is missing
                })
                data = parse_json(result)

                assert "error" in data


class TestMathComputePrecision:
    """Tests for precision options."""

    @pytest.mark.asyncio
    async def test_float32_precision(self, mcp_url):
        """Test float32 precision."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "sqrt",
                    "a": [4, 9],
                    "precision": "float32",
                })
                data = parse_json(result)

                assert data["dtype"] == "float32"
                assert data["result"] == [2.0, 3.0]

    @pytest.mark.asyncio
    async def test_float64_precision(self, mcp_url):
        """Test float64 precision (default)."""
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("math_compute", {
                    "operation": "sqrt",
                    "a": [4, 9],
                    "precision": "float64",
                })
                data = parse_json(result)

                assert data["dtype"] == "float64"
