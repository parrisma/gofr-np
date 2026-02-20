# gofr-np -> gofr-common Auth Migration (Spec)

## Goal

Migrate gofr-np from its local JWT AuthService implementation to gofr-common auth,
following the same patterns used by gofr-doc:

- Token + group storage backed by Vault (shared auth architecture)
- JWT signing secret sourced from Vault via JwtSecretProvider
- Optional auth disable flag --no-auth / GOFR_NP_NO_AUTH=1
- Enforce authentication for MCP tool calls when auth is enabled
- Propagate Authorization header into MCP handlers via gofr-common AuthHeaderMiddleware
- Inject authenticated group into tool arguments (auth group overrides any caller-provided group)

## Non-goals

- Do not change the shared auth architecture (Vault paths, reserved groups, audience).
- Do not introduce a new UI or management API in gofr-np for groups/tokens.
- Do not migrate gofr-np tests to require live token issuance unless explicitly requested.

## Current State (gofr-np)

- JWT signing secret:
  - When auth is enabled and no secret provided via args/env, gofr-np reads the secret from Vault using gofr-common JwtSecretProvider.

- Token validation + token store:
  - gofr-np uses a local file-backed AuthService implementation in app/auth/service.py.
  - gofr-common AuthService is not used, and Vault token/group stores are not used.

- MCP server:
  - Starlette app is created via gofr_common.web.create_mcp_starlette_app.
  - include_auth_middleware is currently false, so Authorization header is not propagated into MCP handlers.
  - MCP tool calls are not authenticated/authorized today.

## Reference: How gofr-doc solves this

gofr-doc implements commons auth integration with these concrete patterns:

1. app/auth is a thin re-export layer
  - app/auth/__init__.py re-exports gofr_common.auth symbols for backward compatibility.

2. main_mcp/main_web create AuthService directly from gofr-common
  - Build a Vault client using gofr-common helpers and the GOFR_DOC env prefix.
  - Create a JWT secret provider that reads the signing secret from Vault.
  - Create token and group stores backed by Vault.
  - Create a GroupRegistry backed by the Vault group store.
  - Create an AuthService configured with env prefix GOFR_DOC and audience gofr-api.

3. MCP auth enforcement happens in routing
  - routing dispatch calls verify_auth(), which:
    - prefers arguments.auth_token (gofr-dig convention)
    - falls back to arguments.token (legacy)
    - falls back to Authorization header context (AuthHeaderMiddleware)
  - Some tools are token-optional (discovery tools); others require auth.
  - The authenticated group is injected into the tool call arguments as the group value.

4. Authorization header propagation is enabled for MCP
  - The MCP server enables the auth header middleware so Authorization is available to tool dispatch.

## Target State

### Auth data plane

- Use gofr-common AuthService (same as gofr-doc):
  - Build a Vault client using gofr-common helpers and the GOFR_NP env prefix.
  - Create a JWT secret provider that reads the signing secret from Vault.
  - Create token and group stores backed by Vault.
  - Create a GroupRegistry backed by the Vault group store.
  - Create an AuthService configured with env prefix GOFR_NP and audience gofr-api.

### Auth enforcement

- MCP tool calls (mirror gofr-doc):
  - If auth is disabled (GOFR_NP_NO_AUTH=1), allow anonymous tool calls.
  - If auth is enabled:
    - require auth token for non-discovery tools
    - accept token from (in priority order): arguments.auth_token, arguments.token, Authorization header
    - validate token via gofr-common AuthService.verify_token
    - inject authenticated group into the tool call arguments as the group value

### Vault wiring

- Production compose provides:
  - AppRole creds mounted from gofr-secrets volume and copied to /run/secrets/vault_creds by entrypoint.
  - GOFR_NP_AUTH_BACKEND set to vault.
  - GOFR_NP_VAULT_URL points at the gofr-vault service on the configured Vault port.
  - GOFR_NP_VAULT_MOUNT set to secret.
  - GOFR_NP_VAULT_PATH_PREFIX set to gofr/auth (canonical).

## Required Design Decisions / Assumptions (must confirm)

1. Token-optional tools
  - Assumption: gofr-np defines TOKEN_OPTIONAL_TOOLS similar to gofr-doc.
  - Proposed initial set:
    - ping
    - math_list_operations (discovery)

2. Group usage
  - Assumption: gofr-np injects group into arguments for parity with gofr-doc.
  - gofr-np does not currently isolate data by group (math operations are stateless), so the group is primarily for auditing/parity.

3. Token store location
  - Assumption: gofr-np will stop using the local JSON token store for production. Vault is the source of truth.

4. Backwards compatibility
  - Assumption: Keep GOFRNP_* env var fallback for a limited time in server startup only, but all compose/scripts remain GOFR_NP_*.

## Acceptance Criteria

1. Production:
  - Starting the production stack with docker/start-prod.sh in build mode starts with auth enabled using Vault-backed secret and Vault-backed token/group stores.
  - For a tool that is not token-optional:
    - with no auth_token/token/Authorization header, it fails with AUTH_REQUIRED.
    - with a valid token, it succeeds.

2. No-auth mode:
  - Starting the production stack with docker/start-prod.sh in build mode with --no-auth starts and all MCP tools work without auth.

3. Tests:
  - Running scripts/run_tests.sh still passes (tests currently run with auth disabled).

## Migration Notes

- gofr-doc does not rely on gofr-common FastAPI middleware for MCP.
  It enforces auth in MCP routing using Authorization header context (AuthHeaderMiddleware).

- Auth header propagation is done via gofr_common.web.middleware.AuthHeaderMiddleware
  enabled by turning on the include_auth_middleware option for the MCP Starlette app.

## Open Questions

1. Token-optional tool set: should math_compute require auth, or do you want to allow anonymous math_compute like discovery tools?
2. Should gofr-np web server remain a stub without auth, or should it enforce auth like gofr-doc web?
3. Token management stays in gofr-common tooling (auth_manager.sh), not in gofr-np. Confirm.
