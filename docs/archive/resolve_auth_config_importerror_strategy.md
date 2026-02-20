# Issue Strategy: resolve_auth_config ImportError

Date: 2026-02-18

## Symptom

Running ./scripts/run_tests.sh fails when starting the MCP server:

- ImportError: cannot import name resolve_auth_config from gofr_common.auth.config

## Likely Root Cause

The gofr-common submodule's gofr_common/auth/config.py no longer exports resolve_auth_config.
It now indicates JWT secrets must be resolved via JwtSecretProvider (Vault-backed).

gofr-np still imports and depends on the removed function via app/startup/auth_config.py.

## Constraints

- Must keep current gofr-np behavior working without introducing Vault as a new dependency.
- Must keep tests runnable via ./scripts/run_tests.sh.

## Plan of Attack

1. Inspect gofr_common/auth/config.py to confirm removal and intended replacement.
2. Update gofr-np's app/startup/auth_config.py so it no longer imports the removed gofr-common function.
3. Implement a minimal, local resolve_auth_config() that preserves existing behavior:
   - Priority: CLI args -> env vars -> auto-generate (when auth required)
   - Support both legacy env prefix (GOFRNP_*) and canonical prefix (GOFR_NP_*)
   - Default token store path remains under Config.get_auth_dir()/tokens.json
4. Rerun ./scripts/run_tests.sh to restore baseline.

## Validation

- ./scripts/run_tests.sh succeeds (exit code 0)
- MCP and Web servers start in test runner

## Rollback

- Revert app/startup/auth_config.py to prior state (but tests will remain broken until gofr-common restores the API).
