#!/usr/bin/env python3
"""GOFRNP MCP Server - Math Operations Service.

This module provides the MCP server implementation with tool routing
handled by the centralized tool registry.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool

from gofr_common.mcp import json_text, error_response

from app.auth import AuthService
from app.logger import session_logger as logger
from app.mcp_server.tool_registry import get_registry, initialize_registry

# Module-level configuration (set by main_mcp.py before starting server)
auth_service: Optional[AuthService] = None
templates_dir_override: Optional[str] = None
styles_dir_override: Optional[str] = None
web_url_override: Optional[str] = None
proxy_url_mode: Optional[str] = None

app = Server("gofr-np-service")


def _json_text(data: Dict[str, Any]) -> TextContent:
    """Create JSON text content - uses gofr_common."""
    return json_text(data)


# Built-in tools (not from math engine)
BUILTIN_TOOLS = [
    Tool(
        name="ping",
        description="Health check - returns server status",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    # Get tools from registry (math capabilities)
    registry = get_registry()
    math_tools = registry.get_mcp_tools()

    # Combine built-in tools with registered tools
    return BUILTIN_TOOLS + math_tools


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocations."""
    logger.info("Tool called", tool=name, args=arguments)

    # Handle built-in tools
    if name == "ping":
        return [_json_text({"status": "ok", "service": "gofr-np"})]

    # Route to registry for math tools
    registry = get_registry()
    if registry.has_tool(name):
        return await _handle_registry_tool(name, arguments)

    return [_json_text({"error": f"Unknown tool: {name}"})]


async def _handle_registry_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocation via registry."""
    try:
        registry = get_registry()
        result = registry.handle_tool(name, arguments)

        # Handle special case where result is the operations list
        if result.dtype == "object":
            return [_json_text(result.result)]  # type: ignore

        return [_json_text(result.to_dict())]

    except ValueError as e:
        return [_json_text({"error": str(e)})]
    except Exception as e:
        logger.error("Tool execution failed", tool=name, error=str(e))
        return [_json_text({"error": f"Execution failed: {str(e)}"})]


async def initialize_server() -> None:
    """Initialize server components."""
    # Initialize the tool registry with all capabilities
    initialize_registry()
    logger.info("GOFRNP server initialized")


# Streamable HTTP setup
session_manager_http = StreamableHTTPSessionManager(
    app=app,
    event_store=None,
    json_response=False,
    stateless=False,
)


async def handle_streamable_http(scope, receive, send) -> None:
    """Handle HTTP requests."""
    await session_manager_http.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(starlette_app) -> AsyncIterator[None]:
    """Manage server lifecycle."""
    logger.info("Starting GOFRNP server")
    await initialize_server()
    async with session_manager_http.run():
        yield


from starlette.applications import Starlette  # noqa: E402 - after async defs
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.routing import Mount  # noqa: E402

starlette_app = Starlette(
    debug=False,
    routes=[Mount("/mcp/", app=handle_streamable_http)],
    lifespan=lifespan,
)

starlette_app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    expose_headers=["Mcp-Session-Id"],
)


async def main(host: str = "0.0.0.0", port: int = 8020) -> None:
    """Run the server."""
    import uvicorn

    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
