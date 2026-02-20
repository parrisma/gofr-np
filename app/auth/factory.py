"""Auth wiring for gofr-np.

gofr-np uses gofr-common auth with Vault-backed stores.
This module centralizes construction so entrypoints and tests share
the same wiring.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional

from gofr_common.auth import AuthService, GroupRegistry, JwtSecretProvider
from gofr_common.auth.backends import create_stores_from_env, create_vault_client_from_env
from gofr_common.logger import Logger


DEFAULT_ENV_PREFIX = "GOFR_NP"
DEFAULT_AUDIENCE = "gofr-api"


def is_auth_disabled(*, no_auth_flag: bool = False, env: Optional[Mapping[str, str]] = None) -> bool:
    """Return True if auth should be disabled.

    Note: prod and tests are expected to run with auth enabled.
    This exists for local development parity only.
    """

    env_map = env or os.environ
    if no_auth_flag:
        return True
    return env_map.get("GOFR_NP_NO_AUTH", "").strip() == "1"


def create_auth_service(
    *,
    env_prefix: str = DEFAULT_ENV_PREFIX,
    audience: str = DEFAULT_AUDIENCE,
    logger: Logger,
) -> AuthService:
    """Create a Vault-backed gofr-common AuthService for gofr-np."""

    vault_client = create_vault_client_from_env(env_prefix, logger=logger)

    vault_path = os.environ.get(
        f"{env_prefix}_JWT_SECRET_VAULT_PATH",
        "gofr/config/jwt-signing-secret",
    )
    secret_provider = JwtSecretProvider(
        vault_client=vault_client,
        vault_path=vault_path,
        logger=logger,
    )

    token_store, group_store = create_stores_from_env(env_prefix, vault_client=vault_client, logger=logger)

    # Runtime services should not bootstrap groups; groups/tokens are seeded by platform bootstrap.
    group_registry = GroupRegistry(store=group_store, logger=logger, auto_bootstrap=False)

    return AuthService(
        token_store=token_store,
        group_registry=group_registry,
        secret_provider=secret_provider,
        env_prefix=env_prefix,
        audience=audience,
        logger=logger,
    )
