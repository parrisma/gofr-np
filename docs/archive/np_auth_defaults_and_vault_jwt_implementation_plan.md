# Implementation Plan: gofr-np Auth Defaults and Vault JWT Secret

This plan implements docs/np_auth_defaults_and_vault_jwt_spec.md.

Rules:
- No code in this document.
- Each step is small and independently verifiable.

## Step 0 - Baseline (capture current failure)

Action:
- Run: `./docker/start-prod.sh`

Verify:
- It fails complaining JWT secret not set.

Mark: DONE (baseline recorded)

## Step 1 - Mirror gofr-doc start-prod.sh behavior

Action:
- Update `docker/start-prod.sh`:
  - remove the hard requirement for GOFRNP_JWT_SECRET / GOFR_NP_JWT_SECRET
  - keep `--no-auth` flag, which sets GOFR_NP_NO_AUTH=1
  - enforce GOFR_NP_VAULT_PATH_PREFIX=gofr/auth

Verify:
- `./docker/start-prod.sh --no-auth` starts the stack successfully.

Mark: DONE

## Step 2 - Wire Vault env vars and secrets volume in compose.prod.yml

Action:
- Update `docker/compose.prod.yml` to mirror gofr-doc:
  - set GOFR_NP_AUTH_BACKEND=vault
  - set GOFR_NP_VAULT_URL=http://gofr-vault:${GOFR_VAULT_PORT}
  - set GOFR_NP_VAULT_MOUNT=secret
  - set GOFR_NP_VAULT_PATH_PREFIX=gofr/auth
  - mount gofr-secrets volume at /run/gofr-secrets:ro

Verify:
- `docker compose -f docker/compose.prod.yml --project-directory . config` succeeds (with gofr_ports.env sourced).

Mark: DONE

## Step 2.1 - Provision gofr-np AppRole credentials

Action:
- Add gofr-np Vault policy to gofr-common.
- Add config/gofr_approles.json.
- Run gofr-common provisioning to create:
  - /run/gofr-secrets/service_creds/gofr-np.json

Verify:
- /run/gofr-secrets/service_creds/gofr-np.json exists.

Mark: DONE

## Step 3 - Copy AppRole creds in entrypoint-prod.sh

Action:
- Update `docker/entrypoint-prod.sh` to copy AppRole creds:
  - from /run/gofr-secrets/service_creds/gofr-np.json
  - to /run/secrets/vault_creds

Verify:
- In a running container, /run/secrets/vault_creds exists when the source creds file exists.

Mark: DONE

## Step 4 - Fetch JWT signing secret from Vault in Python startup

Action:
- Update gofr-np server startup auth resolution:
  - when auth is required and no JWT secret was provided via args/env, use gofr-common VaultClient + JwtSecretProvider.

Verify:
- `./docker/start-prod.sh` (no flags) starts the stack with no JWT env vars set.
- Logs show auth enabled and do not mention requiring manual JWT secret.

Mark: DONE

## Step 5 - Regression: tests and teardown

Action:
- Run: `./scripts/run_tests.sh`
- Stop prod stack: `./docker/stop-prod.sh`

Verify:
- Full test suite passes.
- Prod stack stops cleanly.

Mark: DONE
