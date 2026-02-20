# gofr-np -> gofr-common Auth Migration (Implementation Plan)

Date: 2026-02-20

This plan implements the target state from docs/commons_auth_migration_spec.md.
Constraint from stakeholders: production and tests MUST run with auth enabled.
Auth infra (Vault, JWT secret, token/group stores) must be present and wired,
even if no current callers depend on it.

## Scope

- Replace gofr-np local file-backed JWT AuthService with gofr-common AuthService.
- Use Vault-backed JWT signing secret (JwtSecretProvider) and Vault-backed token/group stores.
- Enforce auth for MCP tool calls when auth is enabled, with a small set of token-optional tools.
- Ensure tests and ephemeral test stack run with auth enabled and do not depend on local JSON token store.

Non-goals are unchanged from the spec.

## Definitions

- Env prefix: GOFR_NP
- JWT audience: gofr-api
- Canonical Vault auth path prefix: gofr/auth
- JWT signing secret logical path: gofr/config/jwt-signing-secret (stored under secret/ KV v2)

## Required decisions (must be locked before implementation)

1) TOKEN_OPTIONAL_TOOLS
   - Default: ping, math_list_operations
   - Decide whether math_compute is auth-required (recommended: yes).

2) Effective group selection
   - gofr-common tokens are multi-group; gofr-np tool args expect a single group.
   - Decision: choose one deterministic effective group and document it.
     Recommended rule:
       - if token has any non-public group, select the first non-public group (stable order from token)
       - else select public

3) Web server enforcement
   - Default: keep web server as a stub and do not enforce auth on its endpoints.
   - MCP enforcement is mandatory per spec.

## Pre-requisites (must be automated for tests)

All environments that run auth-enabled services must have:

- Production: a running Vault container reachable as gofr-vault on gofr-net.
- Tests: an isolated Vault container (gofr-np-vault-test) started by the ephemeral test stack.
- Vault initialized and unsealed.
- KV v2 enabled at secret/.
- JWT signing secret present at secret/gofr/config/jwt-signing-secret with key "value".
- Auth stores present at secret/gofr/auth/{groups,tokens}.
- Service AppRole credentials for gofr-np available to the runtime container at:
  - /run/gofr-secrets/service_creds/gofr-np.json (copied by entrypoint-prod.sh to /run/secrets/vault_creds)

Production bootstrap tooling lives in lib/gofr-common:

- Vault lifecycle + bootstrap:
  - lib/gofr-common/scripts/manage_vault.sh bootstrap
- AppRole provisioning (writes service creds):
  - uv run lib/gofr-common/scripts/setup_approle.py --project-root . --config config/gofr_approles.test.json

Note: setup_approle.py discovers Vault bootstrap artifacts from:
  - /run/gofr-secrets
  - ./secrets
  - ./lib/gofr-common/secrets

For tests, scripts/start-test-env.sh bootstraps an isolated Vault instance and provisions the required
AppRole credentials and GOFR_NP_TEST_TOKEN.

## Phase 1 - Code migration to gofr-common AuthService (no enforcement yet)

Goal: switch wiring to gofr-common AuthService in entrypoints without changing tool behavior.

Steps:

1. Add an auth wiring module
   - Create app/auth/factory.py with:
     - is_auth_disabled(args, env) -> bool
       - For this project: always false in prod/tests; keep flag parsing only for local dev parity.
     - create_auth_service(logger) -> gofr_common.auth.AuthService
       - create_vault_client_from_env("GOFR_NP")
       - secret_provider = JwtSecretProvider(vault_client, vault_path=GOFR_NP_JWT_SECRET_VAULT_PATH or default)
       - token_store, group_store = create_stores_from_env("GOFR_NP", vault_client=vault_client)
       - group_registry = GroupRegistry(store=group_store, auto_bootstrap=False)
       - return AuthService(token_store=token_store, group_registry=group_registry, secret_provider=secret_provider,
                           env_prefix="GOFR_NP", audience="gofr-api")

2. Convert app/auth to a thin re-export layer
   - Update app/auth/__init__.py to re-export gofr_common.auth.AuthService and TokenInfo.
   - Remove or quarantine the local file-backed implementation in app/auth/service.py.
   - Ensure imports in app/main_mcp.py, app/main_web.py, app/web_server/web_server.py still resolve.

3. Update entrypoints to use the factory
   - app/main_mcp.py
     - Stop calling app.startup.auth_config.resolve_auth_config.
     - Always create gofr-common AuthService via app/auth/factory.py.
     - Keep --no-auth for local development only; do not use it in prod/tests.
   - app/main_web.py
     - Same wiring (create auth service) so web health response reports auth enabled consistently.

4. Switch MCP Starlette app to propagate Authorization header
   - app/mcp_server/mcp_server.py
     - create_mcp_starlette_app(..., include_auth_middleware=True)

Validation:
- Start MCP service in prod compose: should start cleanly, no local token store files created.
- Verify that Authorization header context propagation works (can be validated later in Phase 2).

## Phase 2 - Enforce auth on MCP tool calls

Goal: mirror gofr-doc behavior: auth is required for non-discovery tools.

Steps:

1. Define token optional tools
   - Add TOKEN_OPTIONAL_TOOLS = {"ping", "math_list_operations"} near tool routing.

2. Implement token extraction
   - In app/mcp_server/mcp_server.py implement helper get_auth_token(arguments) with priority:
     1) arguments["auth_token"]
     2) arguments["token"]
     3) Authorization header from gofr_common.web.get_auth_header_from_context()
        - parse "Bearer <token>"

3. Implement verify_auth(name, arguments) -> (effective_group, token_info)
   - If tool in TOKEN_OPTIONAL_TOOLS:
     - If no token provided: return (None, None) and proceed.
     - If token provided: verify and return group.
   - Else:
     - If token missing: return an AUTH_REQUIRED error response.
     - Verify token via auth_service.verify_token.

4. Inject group into tool arguments
   - Select effective group per the decision rule.
   - Set arguments["group"] = effective_group (override caller input).
   - Continue to existing registry routing.

5. Normalize error responses
   - Missing token -> {"error": "AUTH_REQUIRED", "recovery": "Provide auth_token/token/Authorization"}
   - Invalid/expired/revoked -> {"error": "AUTH_INVALID", ...}
   - Do not leak token values or secrets into logs.

Validation:
- With auth enabled:
  - ping succeeds without token.
  - math_list_operations succeeds without token.
  - math_compute fails without token with AUTH_REQUIRED.
  - math_compute succeeds with a valid token.

## Phase 3 - Make the ephemeral test stack auth-enabled (Vault-backed)

Goal: tests and test compose stack run auth enabled and use the same Vault-backed stores as prod.

Steps:

1. Update docker/compose.dev.yml
   - Ensure auth is enabled (no GOFR_NP_NO_AUTH=1) and no local GOFR_NP_JWT_SECRET / GOFR_NP_TOKEN_STORE are used.
   - Run an isolated Vault for tests inside the stack:
    - service name: gofr-np-vault-test
     - exposed on a host test port only for local debugging
   - Point gofr-np services at the isolated test Vault:
     - GOFR_NP_AUTH_BACKEND=vault
    - GOFR_NP_VAULT_URL=http://gofr-np-vault-test:8201
     - GOFR_NP_VAULT_PATH_PREFIX=gofr/auth
     - GOFR_NP_VAULT_MOUNT=secret
   - Mount a dedicated test secrets volume at /run/gofr-secrets:ro:
     - gofr-secrets-test contains /run/gofr-secrets/service_creds/gofr-np.json
     - entrypoint-prod.sh copies it to /run/secrets/vault_creds

2. Update scripts/start-test-env.sh
   - Before starting gofr-np services:
     - Build the gofr-vault image if missing.
     - Start the vault service from docker/compose.dev.yml.
     - Wait for the Vault API to be reachable.
     - Initialize + unseal the test Vault (store artifacts under ./secrets/).
     - Enable KV v2 at secret/ and enable approle auth.
     - Ensure JWT signing secret exists at secret/gofr/config/jwt-signing-secret (key: value).

   - Provision AppRole creds for gofr-np:
     - Run: uv run lib/gofr-common/scripts/setup_approle.py --project-root . --config config/gofr_approles.test.json
     - Validate ./secrets/service_creds/gofr-np.json exists.
     - Stream that JSON into the docker volume gofr-secrets-test as:
       /run/gofr-secrets/service_creds/gofr-np.json

   - Mint a test token for integration tests:
     - Run scripts/ensure_test_tokens.py to create/ensure a Vault-backed token and write:
       ./secrets/test_tokens.env (exported as GOFR_NP_TEST_TOKEN)

   - Keep health polling for gofr-np services.

3. Update scripts/run_tests.sh
   - Export canonical GOFR_NP_* env vars required by gofr-common backends.
   - For integration/all modes:
     - Start the ephemeral stack via scripts/start-test-env.sh
     - Source ./secrets/test_tokens.env so pytest can read GOFR_NP_TEST_TOKEN.

Validation:
- ./scripts/run_tests.sh --all passes with auth enabled.
- Test stack starts without GOFR_NP_NO_AUTH.

## Phase 4 - Update test fixtures to use gofr-common auth (no local store)

Goal: tests pass auth to MCP routing without a local JSON token store.

Steps:

1. Update test/conftest.py
   - Remove file-backed token store assumptions.
   - Use GOFR_NP_TEST_TOKEN from the environment (minted by scripts/start-test-env.sh).
   - Provide a helper fixture for MCP tool calls (preferred):
     - mcp_auth_args -> {"auth_token": GOFR_NP_TEST_TOKEN}

2. Ensure token is passed for non-optional tools
   - Any test that calls math_compute (or other non-optional tools) must pass token as:
     - arguments.auth_token (preferred) or
     - Authorization: Bearer header

Validation:
- Targeted run of a representative MCP test module that calls math_compute.
- Full ./scripts/run_tests.sh.

## Rollback / Safety

- Phase 1 can be rolled back by restoring the local AuthService module and the old resolve_auth_config wiring.
- Phases 2-4 are feature-gated only by GOFR_NP_NO_AUTH/--no-auth, but prod/tests will not use the bypass.
- Do not commit any Vault tokens or credential artifacts.

## Deliverables checklist

- Code:
  - app/auth/factory.py
  - app/auth/__init__.py and removal of local file-backed auth
  - app/main_mcp.py and app/main_web.py updated wiring
  - app/mcp_server/mcp_server.py auth propagation + enforcement

- Infra/scripts:
  - docker/compose.dev.yml auth enabled with Vault
  - scripts/start-test-env.sh bootstraps Vault and provisions AppRole
  - scripts/run_tests.sh uses GOFR_NP_* (no legacy GOFRNP_* auth)
  - config/gofr_approles.test.json for AppRole provisioning in tests
  - scripts/ensure_test_tokens.py to mint GOFR_NP_TEST_TOKEN for integration tests

- Tests:
  - test/conftest.py updated fixtures
  - Any MCP tests updated to include token when calling non-optional tools
