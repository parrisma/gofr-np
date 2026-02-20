#!/usr/bin/env python3
"""Create (or reuse) a long-lived test token in Vault-backed auth stores.

This is intended for local/CI test harness usage where:
- Vault is running and unsealed
- JWT signing secret exists in Vault at gofr/config/jwt-signing-secret
- Token/group stores exist at gofr/auth

The script writes a small env file containing a bearer token used by pytest.
It does not print the JWT signing secret.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gofr_common.auth import AuthService, GroupRegistry, JwtSecretProvider
from gofr_common.auth.backends import VaultClient, VaultConfig, VaultGroupStore, VaultTokenStore
from gofr_common.logger import create_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure GOFR-NP test tokens exist")
    parser.add_argument("--vault-url", required=True)
    parser.add_argument("--vault-token", required=True)
    parser.add_argument("--vault-path-prefix", default="gofr/auth")
    parser.add_argument("--jwt-secret-path", default="gofr/config/jwt-signing-secret")
    parser.add_argument("--audience", default="gofr-api")
    parser.add_argument("--group", default="public")
    parser.add_argument("--expires-in-seconds", type=int, default=10 * 365 * 24 * 60 * 60)
    parser.add_argument("--out", required=True, help="Path to write env file")
    args = parser.parse_args()

    logger = create_logger("gofr-np-test-tokens")

    client = VaultClient(VaultConfig(url=args.vault_url, token=args.vault_token))
    secret_provider = JwtSecretProvider(vault_client=client, vault_path=args.jwt_secret_path, logger=logger)

    token_store = VaultTokenStore(client=client, path_prefix=args.vault_path_prefix, logger=logger)
    group_store = VaultGroupStore(client=client, path_prefix=args.vault_path_prefix, logger=logger)

    # Use bootstrap mode here; this script runs under an admin/root token.
    group_registry = GroupRegistry(store=group_store, logger=logger, auto_bootstrap=True)

    auth = AuthService(
        token_store=token_store,
        group_registry=group_registry,
        secret_provider=secret_provider,
        env_prefix="GOFR_NP",
        audience=args.audience,
        logger=logger,
    )

    token = auth.create_token(groups=[args.group], expires_in_seconds=args.expires_in_seconds, name="gofr-np-test")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f"GOFR_NP_TEST_TOKEN={token}\n", encoding="utf-8")

    logger.info("Wrote test token env file", out=str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
