# gofr-np Inbound/Outbound Data Hardening Proposal

Date: 2026-02-20

## Scope

This proposal covers hardening of:

- Inbound data: all external inputs entering gofr-np (MCP tool arguments, HTTP headers, and the stub web server endpoints).
- Outbound data: all outputs emitted to clients (MCP tool responses, web responses), plus logs as a secondary outbound channel.

Non-goals (for this document):

- New product features.
- A full threat model of the entire GOFR platform.

## Why this matters (observed symptom)

A recent failure showed `financial_technical_indicators` returning `NaN` values in the response payload. Strict JSON parsers reject `NaN/Infinity` (RFC 8259), which caused clients to treat the response as invalid JSON.

This is a representative class of issues: inbound/outbound validation and serialization are not uniformly enforced at a single boundary, so a single tool can break client compatibility.

Related sources already present in the codebase:

- Element-wise math can legitimately produce `NaN` (e.g., `log(-1)`), and those results flow through `MathResult` unchanged.
- Curve fitting code contains `-inf` sentinels (e.g., `aic = -np.inf`) in some candidate selection paths.

These make it important that strict JSON sanitization happens at a single shared choke point, not only inside individual tools.

## Current state (quick review)

### Inbound

- MCP calls are handled by `app/mcp_server/mcp_server.py` and dispatched to capability handlers via a registry.
- Auth enforcement is centralized in `_enforce_auth()`.
- Tool argument validation is mostly implemented inside each tool handler (type checks and length/window checks), not centrally.
- There are no global limits for payload size, array lengths, nesting depth, or overall compute cost per request.

### Outbound

- MCP responses are constructed via `_json_text()` which delegates to `gofr_common.web.json_text`.
- `MathResult.to_dict()` is a thin wrapper that does not sanitize values for strict JSON compatibility.
- Errors are returned as `{ "error": "..." }` today, and some exceptions are stringified directly.
- Logging is structured but may still emit sensitive details if exception messages include inputs; and there is at least one `print()` in the logger implementation (see `app/logger/structured_logger.py`).

## Hardening goals

1. Strict JSON correctness for all outbound responses (no `NaN`, `Infinity`, unserializable objects).
2. Predictable, validated inputs at the boundary (schema adherence, size and type constraints).
3. Fail-closed behavior: reject malformed/oversized inputs early with safe, consistent errors.
4. Avoid leaking secrets or sensitive inputs via responses or logs.
5. Bounded resource usage: prevent denial-of-service via huge arrays, deep nesting, or expensive operations.

## Proposal summary (prioritized)

### P0: Centralize strict JSON sanitization at the response boundary

Problem:
- Returning Python/NumPy values that are not valid JSON (NaN/Inf, numpy scalar types, numpy arrays, bytes, etc.) will intermittently break clients.

Proposal:
- Introduce a single “response sanitizer” function used for all outbound payloads before serialization.
- Enforce strict JSON encoding (`allow_nan=false`) at the final serialization step.

Implementation sketch:
- Add `app/mcp_server/serialization.py` with `sanitize_for_json(obj) -> obj`:
  - Convert `NaN`/`Inf` to `None`.
  - Convert NumPy scalar types to Python `int/float`.
  - Convert `np.ndarray` to `.tolist()`.
  - Convert `datetime/uuid/Decimal` (if present) to safe string/float forms.
  - Enforce recursion limits (depth) and maximum container size.
- In `app/mcp_server/mcp_server.py`, wrap `_json_text(...)` calls so they always serialize sanitized payloads.
- Optionally, harden in `gofr_common.web.json_text` as well (platform-wide benefit), but gofr-np should protect itself regardless.

Acceptance criteria:
- Every MCP tool response is strict JSON; a regression test asserts no output contains `NaN`, `Infinity`, or non-JSON types.

### P0: Enforce consistent error envelopes (safe + machine-readable)

Problem:
- Stringifying raw exceptions can leak implementation details and/or user-supplied content.

Proposal:
- Standardize outbound error objects to:

  - `error`: stable code (e.g. `INVALID_ARGUMENT`, `AUTH_REQUIRED`, `AUTH_INVALID`, `TOOL_NOT_FOUND`, `EXECUTION_FAILED`)
  - `detail`: safe message (no secrets, no raw payload dumps)
  - `recovery`: actionable next step
  - `request_id` (optional): correlation id for logs

Implementation sketch:
- Add a small mapper (similar to `app/errors/mapper.py`) for tool execution errors.
- In `handle_call_tool()` and `_handle_registry_tool()`, catch known exceptions and map them to stable codes.

Acceptance criteria:
- Clients can rely on `error` codes and do not need to parse human text.

### P0: Hard input limits (size, depth, arrays) at the MCP boundary

Problem:
- A client can send extremely large arrays or deep nested structures, causing memory and CPU blowups.

Proposal:
- Apply generic limits before dispatching any tool:
  - Maximum argument JSON size (bytes).
  - Maximum nesting depth.
  - Maximum total scalar count in arrays.
  - Maximum string length.

Implementation sketch:
- Implement `validate_inbound_payload(arguments)` that:
  - Traverses the dict and counts depth/size.
  - Rejects payloads exceeding limits with `PAYLOAD_TOO_LARGE`.
- Add configuration via env vars (prefixed with `GOFR_NP_`), with safe defaults.

Acceptance criteria:
- Oversized requests are rejected quickly and do not cause worker instability.

### P1: Schema enforcement at tool boundary

Problem:
- Tool handlers currently do ad-hoc validation; mismatches can slip through and cause unexpected behavior.

Proposal:
- Validate `arguments` against the tool’s `input_schema` before invoking handler.

Implementation sketch options:
- Option A (low dependency): Use `jsonschema` (already common in Python ecosystems) to validate input.
- Option B (strong typing): Define Pydantic models per tool.

Given gofr-np’s simplicity, Option A is likely the best fit.

Acceptance criteria:
- Incorrect types/missing required fields produce deterministic `INVALID_ARGUMENT` errors.

### P1: Bounded compute for expensive tools

Problem:
- Some operations can scale poorly (curve fitting, large convolution windows, long time series).

Proposal:
- Add guardrails per tool:
  - Max points for curve fit.
  - Max polynomial degree.
  - Max time series length for technical indicators.
  - Max steps for option pricing.

Implementation sketch:
- Define a per-tool limits config (env-driven) and enforce in handlers.

Acceptance criteria:
- Worst-case compute time is bounded; load tests demonstrate stability.

### P1: Log hygiene and secret redaction

Problem:
- Logs are outbound data; they must not contain tokens, secrets, or raw payloads.

Proposal:
- Keep current good practice of logging only argument keys (not values).
- Add a redaction helper for any future logs that include values.
- Remove `print()` in logger code (replace with `StructuredLogger.error` or safe fallback).

Acceptance criteria:
- No auth tokens or Vault creds ever appear in logs.

### P2: Web server hardening (even if “stub”)

Problem:
- Stub endpoints can become production dependencies over time.

Proposal:
- Add:
  - Standard security headers.
  - Request size limits.
  - Health endpoints do not leak configuration secrets.

Acceptance criteria:
- Baseline HTTP hardening present without changing product behavior.

## Proposed implementation plan (high level)

1. Add response sanitizer and wire into MCP output path.
2. Switch JSON serialization to strict mode (no NaN) and add regression tests.
3. Add inbound payload limiter at MCP boundary.
4. Add tool schema validation using the existing tool input schemas.
5. Add per-tool compute guardrails and env config.
6. Clean up logging fallback (`print` removal) and add redaction utilities.

## Regression tests to add

- A test that calls every tool with minimal valid inputs and asserts:
  - Output is strict JSON (round-trip `json.loads(json.dumps(..., allow_nan=False))`).
  - No `NaN`/`Infinity` appear.
- A test that sends oversized payloads and expects `PAYLOAD_TOO_LARGE`.
- A test that sends wrong types and expects `INVALID_ARGUMENT`.

## Open questions

1. What are acceptable default limits for payload size and series lengths in your expected workloads?
2. Do you want strict schema validation to reject unknown extra fields, or ignore them?
3. Should the MCPO OpenAPI proxy enforce the same payload limits (recommended)?
