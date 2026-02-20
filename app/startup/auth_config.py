"""Authentication configuration utilities for gofr-np.

gofr-common previously provided resolve_auth_config() for resolving JWT secrets
from CLI args and environment variables. That helper has been removed upstream
in favor of Vault-backed JwtSecretProvider.

gofr-np still supports local/dev and test workflows that do not require Vault,
so we provide a small local resolver here.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from gofr_common.auth.backends import create_vault_client_from_env
from gofr_common.auth.jwt_secret_provider import JwtSecretProvider
from gofr_common.logger import Logger

from app.config import Config


def resolve_auth_config(
    jwt_secret_arg: Optional[str],
    token_store_arg: Optional[str],
    require_auth: bool,
    logger: Logger,
) -> Tuple[Optional[str], str]:
    """
    Resolve authentication configuration from arguments and environment.

    Priority order:
    1. Command line arguments
    2. Environment variables (legacy GOFRNP_* or canonical GOFR_NP_*)
    3. Auto-generation (for JWT secret only, when require_auth=True)

    Args:
        jwt_secret_arg: JWT secret from command line (--jwt-secret)
        token_store_arg: Token store path from command line (--token-store)
        require_auth: Whether authentication is required
        logger: Logger instance for reporting

    Returns:
        Tuple of (jwt_secret, token_store_path).

        jwt_secret is None when auth is disabled.
        token_store_path is always returned as a string.
    """
    auth_dir = Config.get_auth_dir()
    try:
        auth_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Directory creation failure should not crash no-auth flows.
        pass

    default_token_store = str(auth_dir / "tokens.json")

    # Token store: CLI arg -> env -> default
    token_store_env = (
        os.environ.get("GOFRNP_TOKEN_STORE")
        or os.environ.get("GOFR_NP_TOKEN_STORE")
    )
    effective_token_store = token_store_arg or token_store_env or default_token_store

    if not require_auth:
        logger.info(
            "Authentication disabled by configuration",
            require_auth=False,
            token_store=effective_token_store,
        )
        return None, effective_token_store

    # JWT secret: CLI arg -> env -> Vault (preferred) -> fail
    jwt_secret = (
        jwt_secret_arg
        or os.environ.get("GOFRNP_JWT_SECRET")
        or os.environ.get("GOFR_NP_JWT_SECRET")
    )

    if not jwt_secret:
        vault_prefix = "GOFR_NP"
        resolved_vault_path = os.environ.get(
            "GOFR_NP_JWT_SECRET_VAULT_PATH",
            "gofr/config/jwt-signing-secret",
        )

        try:
            vault_client = create_vault_client_from_env(vault_prefix, logger=logger)
            provider = JwtSecretProvider(
                vault_client=vault_client,
                vault_path=resolved_vault_path,
                logger=logger,
            )
            jwt_secret = provider.get()
            logger.info(
                "JWT secret loaded from Vault",
                require_auth=True,
                vault_prefix=vault_prefix,
                vault_path=resolved_vault_path,
                fingerprint=provider.fingerprint,
            )
        except Exception as exc:
            logger.error(
                "JWT secret resolution failed (Vault)",
                require_auth=True,
                vault_prefix=vault_prefix,
                vault_path=resolved_vault_path,
                error_type=type(exc).__name__,
                error=str(exc),
                recovery="Provide GOFR_NP_JWT_SECRET or run with GOFR_NP_NO_AUTH=1 / --no-auth, or ensure Vault creds at /run/secrets/vault_creds",
            )
            raise RuntimeError(
                "JWT secret not provided and could not be loaded from Vault. "
                "Set GOFR_NP_JWT_SECRET, or run with --no-auth, or configure Vault credentials."
            ) from exc

    return jwt_secret, effective_token_store
