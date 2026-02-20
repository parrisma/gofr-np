import argparse
import os
import sys
import asyncio
from app.logger import Logger, session_logger
import app.startup.validation
from app.auth import create_auth_service, is_auth_disabled

logger: Logger = session_logger

if __name__ == "__main__":
    # Validate data directory structure at startup
    try:
        app.startup.validation.validate_data_directory_structure(logger)
    except RuntimeError as e:
        logger.error("FATAL: Data directory validation failed", error=str(e))
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="GOFRNP MCP Server - NumPy operations via Model Context Protocol"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("GOFRNP_MCP_PORT", "8020")),
        help="Port number to listen on (default: 8020, or GOFRNP_MCP_PORT env var)",
    )
    parser.add_argument(
        "--jwt-secret",
        type=str,
        default=None,
        help="DEPRECATED: JWT secret is sourced from Vault via gofr-common (ignored)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="DEPRECATED: token store is Vault-backed via gofr-common (ignored)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication (WARNING: insecure, for development only)",
    )
    parser.add_argument(
        "--templates-dir",
        type=str,
        default=None,
        help="Path to templates directory (default: app/templates)",
    )
    parser.add_argument(
        "--styles-dir",
        type=str,
        default=None,
        help="Path to styles directory (default: app/styles)",
    )
    parser.add_argument(
        "--web-url",
        type=str,
        default=None,
        help="Web server base URL for proxy mode (default: http://localhost:8022, or GOFRNP_WEB_URL env var)",
    )
    parser.add_argument(
        "--proxy-url-mode",
        type=str,
        choices=["guid", "url"],
        default="url",
        help="Proxy response mode: 'guid' returns only proxy_guid, 'url' returns both proxy_guid and full download_url (default: url)",
    )
    args = parser.parse_args()

    # Create logger for startup messages
    startup_logger: Logger = session_logger

    if args.jwt_secret or args.token_store:
        startup_logger.warning(
            "Deprecated auth args provided; ignored (gofr-common Vault auth is used)",
            has_jwt_secret_arg=bool(args.jwt_secret),
            has_token_store_arg=bool(args.token_store),
        )

    auth_service = None
    if is_auth_disabled(no_auth_flag=args.no_auth):
        startup_logger.warning(
            "Authentication DISABLED - running in no-auth mode (INSECURE)",
            jwt_enabled=False,
        )
    else:
        auth_service = create_auth_service(logger=startup_logger)
        startup_logger.info(
            "Authentication service initialized",
            jwt_enabled=True,
            audience="gofr-api",
            vault_path_prefix=os.environ.get("GOFR_NP_VAULT_PATH_PREFIX", ""),
        )

    # Import and configure mcp_server with auth service
    import app.mcp_server.mcp_server as mcp_server_module

    mcp_server_module.auth_service = auth_service
    mcp_server_module.templates_dir_override = args.templates_dir
    mcp_server_module.styles_dir_override = args.styles_dir
    mcp_server_module.web_url_override = args.web_url
    mcp_server_module.proxy_url_mode = args.proxy_url_mode
    from app.mcp_server.mcp_server import main

    try:
        startup_logger.info("=" * 70)
        startup_logger.info("STARTING GOFRNP MCP SERVER")
        startup_logger.info("=" * 70)
        startup_logger.info(
            "Configuration",
            host=args.host,
            port=args.port,
            transport="HTTP Streamable",
            jwt_enabled=auth_service is not None,
            proxy_mode=args.proxy_url_mode.upper(),
            web_url=args.web_url or "http://localhost:8022",
            templates_dir=args.templates_dir or "(default)",
            styles_dir=args.styles_dir or "(default)",
        )
        startup_logger.info("=" * 70)
        startup_logger.info(f"MCP endpoint: http://{args.host}:{args.port}/mcp")
        startup_logger.info("=" * 70)
        asyncio.run(main(host=args.host, port=args.port))
        startup_logger.info("=" * 70)
        startup_logger.info("MCP server shutdown complete")
        startup_logger.info("=" * 70)
    except KeyboardInterrupt:
        startup_logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        startup_logger.error("Failed to start server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
