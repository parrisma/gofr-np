"""Authentication configuration utilities for GOFRNP server.

Re-exports resolve_auth_config from gofr_common.auth.config with
GOFRNP-specific defaults.
"""

from typing import Optional, Tuple

from gofr_common.auth.config import resolve_auth_config as _resolve_auth_config
from gofr_common.logger import Logger

from app.config import Config


def resolve_auth_config(
    jwt_secret_arg: Optional[str],
    token_store_arg: Optional[str],
    require_auth: bool,
    logger: Logger,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve authentication configuration from arguments and environment.

    Priority order:
    1. Command line arguments
    2. Environment variables (GOFRNP_JWT_SECRET, GOFRNP_TOKEN_STORE)
    3. Auto-generation (for JWT secret only)

    Args:
        jwt_secret_arg: JWT secret from command line (--jwt-secret)
        token_store_arg: Token store path from command line (--token-store)
        require_auth: Whether authentication is required
        logger: Logger instance for reporting

    Returns:
        Tuple of (jwt_secret, token_store_path), both None if auth disabled
    """
    # Use default token store path if not provided
    default_token_store = str(Config.get_auth_dir() / "tokens.json")
    effective_token_store = token_store_arg or default_token_store

    jwt_secret, token_store_path, _ = _resolve_auth_config(
        env_prefix="GOFRNP",
        jwt_secret_arg=jwt_secret_arg,
        token_store_arg=effective_token_store,
        require_auth=require_auth,
        allow_auto_secret=True,
        exit_on_missing=False,
        logger=logger,
    )

    # Convert Path to string for backward compatibility
    token_store_str = str(token_store_path) if token_store_path else None
    return jwt_secret, token_store_str
