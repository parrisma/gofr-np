# gofr-np Auth Defaults and Vault JWT Secret (Spec)

## Goal

Follow the same production pattern as gofr-doc:

1. Starting gofr-np production stack must not require manually setting a JWT secret env var.
2. When auth is enabled, the JWT signing secret is sourced from Vault via gofr-common's JwtSecretProvider.
3. A single flag (`--no-auth`) disables auth.

## Current Behavior (Observed)

- `./docker/start-prod.sh` fails unless `GOFRNP_JWT_SECRET` or `GOFR_NP_JWT_SECRET` is set, or `--no-auth` is passed.
- `app/main_mcp.py` and `app/main_web.py` resolve auth config only from CLI args and env vars, with optional ephemeral generation.

## Desired Behavior

### Default behavior (prod compose via docker/start-prod.sh)

- `./docker/start-prod.sh` succeeds without requiring any JWT secret env var.
- Auth is enabled by default (same as gofr-doc), but the JWT signing secret is fetched from Vault.
- `./docker/start-prod.sh --no-auth` disables auth.

### Vault

- Vault addressing uses the Docker service name for Vault (never host.docker.internal for Vault):
  - Vault URL: http://gofr-vault:${GOFR_VAULT_PORT}

### Credentials injection

- Use the shared external Docker volume `gofr-secrets`.
- `docker/compose.prod.yml` mounts it at `/run/gofr-secrets:ro`.
- `docker/entrypoint-prod.sh` copies the AppRole creds file from:
  - `/run/gofr-secrets/service_creds/gofr-np.json`
  to the standard location expected by gofr-common:
  - `/run/secrets/vault_creds`

## Scope

In scope:

- `docker/start-prod.sh` default auth behavior.
- gofr-np server startup auth configuration to support Vault-backed JWT secret resolution when auth is enabled.

Out of scope (explicitly not doing here unless requested):

- Migrating gofr-np token/group storage to Vault.
- Enabling auth by default.
- Changing other services' shared auth behavior.

## Acceptance Criteria

1. `./docker/start-prod.sh` (no flags) starts the stack successfully with no JWT secret env vars configured.
2. `./docker/start-prod.sh --no-auth` starts the stack without Vault auth requirements.
3. With auth enabled (default), the services obtain the JWT signing secret from Vault using gofr-common.
4. GOFR canonical Vault auth path prefix is enforced as `gofr/auth` (to match the shared auth architecture).

## Proposed Design

### docker/start-prod.sh

- Mirror gofr-doc behavior:
  - Remove the hard requirement for `GOFRNP_JWT_SECRET` / `GOFR_NP_JWT_SECRET`.
  - When `--no-auth` is provided, set `GOFR_NP_NO_AUTH=1`.
  - Enforce `GOFR_NP_VAULT_PATH_PREFIX=gofr/auth`.

### docker/compose.prod.yml

- Mirror gofr-doc behavior:
  - Ensure Vault env vars are set for the service prefix:
    - `GOFR_NP_AUTH_BACKEND=vault`
    - `GOFR_NP_VAULT_URL=http://gofr-vault:${GOFR_VAULT_PORT}`
    - `GOFR_NP_VAULT_MOUNT=secret`
    - `GOFR_NP_VAULT_PATH_PREFIX=gofr/auth`
  - Mount `gofr-secrets` volume at `/run/gofr-secrets:ro`.

### docker/entrypoint-prod.sh

- Mirror gofr-doc behavior:
  - Copy `/run/gofr-secrets/service_creds/gofr-np.json` to `/run/secrets/vault_creds`.

### Python startup (JWT secret)

- When auth is required and no JWT secret was provided via args/env:
  - create a VaultClient using `gofr_common.auth.backends.create_vault_client_from_env("GOFR_NP")`
  - use `gofr_common.auth.jwt_secret_provider.JwtSecretProvider` to read the signing secret
  - use that secret for JWT signing/verifying

## Assumptions

1. gofr-np production should follow gofr-doc: auth enabled by default, but JWT secret is fetched from Vault.
2. `--no-auth` provides an immediate escape hatch for dev/test.
3. The JWT signing secret Vault path uses gofr-common default (`gofr/config/jwt-signing-secret`) unless configured otherwise.
