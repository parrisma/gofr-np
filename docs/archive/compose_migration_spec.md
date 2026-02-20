# gofr-np Compose Migration - Specification

Date: 2026-02-18

## Purpose

Migrate gofr-np to the same operational model used by gofr-doc:

- Production runs as a docker compose stack with separate containers for:
  - MCP service
  - MCPO proxy
  - Web service
- Tests that require live services run against an ephemeral docker compose test stack (not local nohup processes).
- Start/stop scripts use compose and centralized configuration from gofr-common.

## Background (current state)

- Dev uses a long-lived dev container started via docker/run-dev.sh (docker run).
- Production uses a single container that starts MCP, MCPO, and Web via supervisor.
- scripts/run_tests.sh starts servers locally using nohup for integration tests.
- Port configuration is split (gofr-np currently has gofr_ports.sh; gofr-doc uses gofr_ports.env).

## Desired End State

1. Central configuration
   - Ports are defined in one place: lib/gofr-common/config/gofr_ports.env
   - Compose files and start scripts consume this env file via env_file
   - Any repo-local port config duplicates are removed

2. Production
   - docker/compose.prod.yml exists and is the supported production runtime
   - The production image does not use supervisor; each container runs one process
   - docker/start-prod.sh builds (if needed) and starts the compose stack
   - docker/stop-prod.sh stops the compose stack (wrapper to start-prod.sh --down)

3. Test
   - docker/compose.dev.yml exists as an ephemeral test stack
   - scripts/start-test-env.sh manages the test stack lifecycle and health checks
   - scripts/run_tests.sh uses the test compose stack for integration tests

4. Cleanup
   - Legacy redundant prod lifecycle scripts are deleted or converted to wrappers
   - Redundant, unused placeholder implementations are removed if not referenced

## Non-Goals

- Redesigning application runtime behavior beyond what is required to run under compose
- Changing math/financial tool behavior
- Introducing new UX, APIs, or endpoints
- Enabling Vault-based auth parity unless explicitly requested as a follow-on

## Constraints and Standards

- Centralized config: ports must come from gofr-common gofr_ports.env
- No localhost usage in documentation and scripts; use 127.0.0.1 and host.docker.internal when needed
- UV only: no pip-based workflow added
- ASCII only in code and output
- Tests must be run via ./scripts/run_tests.sh (baseline and acceptance)

## Assumptions (must be confirmed)

A1. gofr-common submodule can be updated so that lib/gofr-common/config/gofr_ports.env is available in gofr-np.
A2. Production can move from a single supervisor container to three compose services without changing external API semantics.
A3. For initial migration, test stack can run with auth disabled (GOFR_NP_NO_AUTH=1) and keep existing JWT secret + token store behavior for pytest fixtures.
A4. It is acceptable to delete docker/run-prod.sh after compose start/stop is working.
A5. It is acceptable to delete app/web_server.py if it is not referenced (keeping app/web_server/web_server.py).

## Acceptance Criteria

- Production:
  - ./docker/start-prod.sh --build brings up mcp, mcpo, web via compose
  - ./docker/stop-prod.sh stops the stack

- Tests:
  - ./scripts/start-test-env.sh --build starts a healthy ephemeral test stack
  - ./scripts/run_tests.sh --integration uses the compose stack and passes
  - ./scripts/run_tests.sh full suite passes before and after the migration

- Configuration:
  - All compose files and start scripts read ports from lib/gofr-common/config/gofr_ports.env

## Rollback Plan

- Keep changes on a branch / as incremental commits.
- If compose migration fails, temporarily revert to prior behavior:
  - restore supervisor-based prod image and docker/run-prod.sh usage
  - restore nohup-based server startup in scripts/run_tests.sh

## Open Questions

Q1. Should the prod compose stack join gofr-net only, or also join gofr-test-net for convenience?
A1. prod compose stack joins gofr-net ONLY
Q2. Should MCPO in prod use the mcpo binary directly (recommended) or the app/main_mcpo.py wrapper?
A2. Same as GoFr-doc does 
Q3. For tests, do you want host mode only (127.0.0.1 + published test ports) or also docker-network mode (dev container talks to service hostnames on gofr-test-net)?
A3. you are running in a container so tests need to use docker hostnames, I cam run tests on host by hand as needed
