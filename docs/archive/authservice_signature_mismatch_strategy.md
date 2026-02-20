# Issue Strategy: AuthService signature mismatch (pyright failures)

Date: 2026-02-18

## Symptom

./scripts/run_tests.sh fails in code quality:

- pyright reports errors in app/main_mcp.py, app/main_web.py, test/conftest.py
- AuthService(...) is called with secret_key= and token_store_path=, but the constructor now expects different parameters:
  - token_store
  - group_registry
  - secret_provider

## Likely Root Cause

The gofr-common submodule (and/or gofr-np's AuthService wrapper) has evolved:

- JWT secrets are intended to be resolved via a secret provider (Vault-backed)
- Token storage and group registry are now explicit dependencies

gofr-np's code and tests still use the older AuthService constructor.

## Constraints

- Must restore zero-tolerance type checking (pyright) and keep runtime behavior.
- Must not introduce Vault dependency as a requirement for local tests.
- Must keep ./scripts/run_tests.sh as the only supported test runner.

## Plan of Attack

1. Inspect app/auth/AuthService implementation and its expected dependencies.
2. Identify gofr-common helpers for:
   - token store implementation
   - group registry implementation
   - secret provider implementation (non-Vault fallback)
3. Update app/main_mcp.py and app/main_web.py to construct AuthService with the new signature.
4. Update pytest fixtures in test/conftest.py to construct AuthService the same way.
5. Rerun ./scripts/run_tests.sh to confirm:
   - code quality (pyright) passes
   - unit and integration tests still pass

## Validation

- pyright reports 0 errors
- ./scripts/run_tests.sh exits 0

## Rollback

- Revert gofr-np AuthService construction changes; tests will remain blocked until gofr-np is updated to match gofr-common.
