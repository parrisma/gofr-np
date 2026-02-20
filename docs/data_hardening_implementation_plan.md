# gofr-np Data Hardening Implementation Plan (Inbound + Outbound)

Date: 2026-02-20

This plan implements the proposal in docs/data_hardening_proposal.md.

Constraints / project rules:

- Keep changes minimal and focused.
- Use `./scripts/run_tests.sh` as the only test entry point.
- Do not log secrets; do not add `print()`.
- Prefer centralized enforcement at boundaries (MCP/web) over per-tool patches.

## Definition of Done

All items below must be true:

- All MCP responses are strict JSON (no NaN/Inf; no numpy scalars/arrays leaking).
- Oversized or malformed tool arguments are rejected early with stable error codes.
- Tool argument validation is deterministic and consistent across tools.
- New tests cover the hardening behavior and pass in CI via `./scripts/run_tests.sh`.

## Implementation sequence (step-by-step)

### Step 0: Baseline and safety rails

Goal: lock current behavior so we can validate improvements without regressions.

Actions:

1. Run targeted tests first (fast feedback):
   - `./scripts/run_tests.sh -k "technical_indicators or financial_technicals" -v`
2. Run full suite once before the hardening work begins:
   - `./scripts/run_tests.sh --all`

Acceptance criteria:

- Both commands succeed.


### Step 1 (P0): Centralize outbound JSON sanitization

Goal: a single choke point guarantees strict JSON compatibility for every tool response.

Actions:

1. Add a module `app/mcp_server/serialization.py` with:
   - `sanitize_for_json(obj, *, max_depth, max_items, max_string_len) -> obj`
   - Behavior:
     - Replace NaN/Inf with `None`.
     - Convert numpy scalar types to Python `int/float`.
     - Convert `np.ndarray` to lists.
     - Convert unknown non-JSON types to safe strings (or reject; pick one and be consistent).
     - Enforce recursion depth and max container sizes (fail closed).
2. Update `app/mcp_server/mcp_server.py` so every `_json_text(payload)` call uses sanitized payload:
   - Built-in tools (ping)
   - Registry tool object outputs
   - Registry tool MathResult wrapper outputs
   - Error payloads

Tests to add:

- `test/mcp/test_strict_json_outputs.py`:
  - For a representative set of tools, call the capability handlers directly (unit-level) and ensure:
    - `json.dumps(payload, allow_nan=False)` succeeds for the final payload.
    - No `NaN`/`Infinity` in nested structures.
  - Include at least:
    - Elementwise: `log(-1)` producing NaN
    - Curvefit: a path where AIC could be `-inf` (or force it via unit helper)
    - Financial technicals: SMA warmup

Notes:

- If strict JSON serialization occurs only at the tool layer, regressions will reappear (new tools).
- Prefer enforcing at the MCP boundary before response creation.

Acceptance criteria:

- New strict JSON tests pass.
- Manual smoke: invoking `financial_technical_indicators` returns JSON `null` for warmup values, never `NaN`.


### Step 2 (P0): Standardize error envelopes

Goal: stable machine-readable error codes; no raw exception leakage.

Actions:

1. Add/extend an error mapper for MCP tool calls (either new `app/mcp_server/errors.py` or integrate with `app/errors/mapper.py`):
   - Map common classes to error codes:
     - `InvalidInputError` -> `INVALID_ARGUMENT`
     - Tool not found -> `TOOL_NOT_FOUND`
     - Auth missing -> `AUTH_REQUIRED` (already)
     - Auth invalid -> `AUTH_INVALID` (already)
     - Sanitizer limits exceeded -> `RESPONSE_TOO_LARGE` / `RESPONSE_INVALID`
     - Inbound payload too large -> `PAYLOAD_TOO_LARGE`
     - Unexpected exception -> `EXECUTION_FAILED`
2. Update `_handle_registry_tool()` and `handle_call_tool()` to always return:
   - `{ "error": <CODE>, "detail": <safe>, "recovery": <string> }`
   - Do not include argument values.

Tests to add:

- `test/mcp/test_error_envelopes.py`:
  - Unknown tool returns `TOOL_NOT_FOUND`.
  - Missing required arg returns `INVALID_ARGUMENT`.
  - Force an internal exception path and verify `EXECUTION_FAILED` envelope.

Acceptance criteria:

- Tests confirm codes and response shape.


### Step 3 (P0): Inbound payload limits at MCP boundary

Goal: reject pathological payloads before execution.

Actions:

1. Add `app/mcp_server/inbound_limits.py` with a fast validator:
   - `validate_arguments(arguments) -> None | raises InvalidInputError`
   - Enforce:
     - Max depth
     - Max total items
     - Max string length
     - Optional max numeric array length
2. Call this validator early in `handle_call_tool()` after auth enforcement but before dispatch.
3. Make limits configurable via env vars, with safe defaults:
   - `GOFR_NP_MAX_ARG_DEPTH`
   - `GOFR_NP_MAX_ARG_ITEMS`
   - `GOFR_NP_MAX_STRING_LEN`
   - `GOFR_NP_MAX_ARRAY_LEN`

Tests to add:

- `test/mcp/test_inbound_limits.py`:
  - Too-deep payload gets `PAYLOAD_TOO_LARGE`.
  - Too-many-items payload gets `PAYLOAD_TOO_LARGE`.

Acceptance criteria:

- Limits trigger deterministically; do not start tool execution.


### Step 4 (P1): Schema validation using existing tool schemas

Goal: consistent validation and friendly errors with minimal boilerplate.

Actions:

1. Add dependency (if not present) for JSON Schema validation (prefer `jsonschema`).
2. In tool registry, before handler execution:
   - Validate `arguments` against that tool’s declared `input_schema`.
   - Configure validation to reject unknown fields (recommended) or allow them (decide and document).
3. Map schema failures to `INVALID_ARGUMENT`.

Tests to add:

- `test/mcp/test_schema_validation.py`:
  - Wrong types rejected.
  - Missing required fields rejected.
  - Unknown fields behavior matches chosen policy.

Acceptance criteria:

- Schema failures are handled consistently across tools.


### Step 5 (P1): Per-tool resource guardrails

Goal: bound CPU/memory usage for expensive computations.

Actions:

1. Define a config object (env-driven) for tool limits:
   - curve_fit: `MAX_POINTS`, `MAX_DEGREE`
   - option_price: `MAX_STEPS`
   - technicals: `MAX_SERIES_LEN`
   - elementwise: `MAX_TENSOR_ELEMENTS`
2. Enforce inside tool handlers (closest to the compute):
   - Fail with `INVALID_ARGUMENT` or `PAYLOAD_TOO_LARGE`.

Tests to add:

- `test/mcp/test_tool_limits.py`:
  - Each limit triggers and returns the correct error code.

Acceptance criteria:

- Worst-case request sizes are bounded.


### Step 6 (P1): Logging and redaction hardening

Goal: logs are safe outbound data.

Actions:

1. Remove/replace the `print()` fallback in `app/logger/structured_logger.py` with:
   - A safe `sys.stderr.write(...)` minimal line OR
   - a best-effort logger call (without recursion).
2. Add a reusable redaction helper (token, secret_id, role_id, Authorization header):
   - Used anywhere errors might include sensitive strings.
3. Ensure tool call logging remains key-only (already good).

Tests to add:

- `test/code_quality/test_code_quality.py` update:
  - Assert no `print(` exists in `app/` (if not already enforced).

Acceptance criteria:

- No secrets appear in logs in normal error paths.


### Step 7 (P2): Web server request/response hardening

Goal: baseline HTTP safety even for “stub” endpoints.

Actions:

1. Add basic security headers middleware to the web Starlette/FastAPI app:
   - `X-Content-Type-Options: nosniff`
   - `Cache-Control: no-store` for health endpoints
2. Add request body size limit middleware (if any endpoints accept bodies now or in future).

Tests to add:

- `test/web/test_security_headers.py` (if web tests exist; otherwise add minimal coverage).

Acceptance criteria:

- Headers present; behavior unchanged for existing endpoints.


### Step 8: End-to-end verification

Actions:

1. Run full suite:
   - `./scripts/run_tests.sh --all`
2. Start prod stack and smoke test:
   - `./docker/start-prod.sh --down && ./docker/start-prod.sh --build`
   - Confirm MCP call outputs contain `null` where previously `NaN` appeared.

Acceptance criteria:

- All tests pass.
- No MCP client reports “Response is not valid JSON”.

## Rollout plan

- Land Steps 1-3 first (P0). These are the highest leverage and reduce incident risk immediately.
- Add schema validation (Step 4) next; tune strictness if clients rely on extra fields.
- Add resource guardrails (Step 5) and logging hygiene (Step 6).
- Web hardening (Step 7) last.

## Notes / decisions needed from you

1. Limits: choose defaults for max array length / max items.
2. Schema policy: reject unknown fields vs ignore.
3. Sanitizer behavior for unknown types: stringify vs reject.
