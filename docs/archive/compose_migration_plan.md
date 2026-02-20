# gofr-np Compose Migration (Small-Step Implementation Plan)

This document is a small-step implementation plan to migrate gofr-np from:

- Dev: a long-lived dev container launched with `docker run`
- Prod: a single container running multiple processes under supervisor
- Tests: local `nohup`-started servers

to a compose-driven layout aligned with gofr-doc:

- Prod: docker/compose.prod.yml runs 3 services (mcp, mcpo, web) from one image
- Tests: docker/compose.dev.yml runs an ephemeral test stack
- Scripts: start/stop/build wrappers that match gofr-doc ergonomics

Notes:

- ASCII-only: keep punctuation and output ASCII.
- No local hostnames: use 127.0.0.1 for host checks, and host.docker.internal for cross-container-to-host when needed.

---

## Conventions (do this first)

### Step 00.1 - Baseline: confirm tools are available

Action:

- Confirm `docker` and `docker compose` work.

Verify:

- `docker info` succeeds
- `docker compose version` succeeds

Status: DONE

### Step 00.2 - Baseline: capture test status before changes

Action:

- Run the full suite once: `./scripts/run_tests.sh`

Verify:

- Exit code is 0

Status: DONE

---

## Step 01 - Centralize config (hard requirement)

### Step 01.1 - Ensure centralized ports env exists in gofr-common

Goal:

- Use lib/gofr-common/config/gofr_ports.env as the single source of truth.

Action:

- Update the gofr-common submodule until lib/gofr-common/config/gofr_ports.env exists in this repo.

Verify:

- File exists: lib/gofr-common/config/gofr_ports.env
- It contains GOFR_NP_MCP_PORT, GOFR_NP_MCPO_PORT, GOFR_NP_WEB_PORT
- It contains *_TEST variants (GOFR_NP_MCP_PORT_TEST, etc.)

Status: DONE

### Step 01.2 - Remove any repo-local fallback ports file

Action:

- If docker/gofr_ports.env exists as a fallback, delete it.

Verify:

- The only ports env used by compose/scripts is lib/gofr-common/config/gofr_ports.env

Status: DONE

---

## Step 02 - Make the prod image single-process (compose-friendly)

### Step 02.1 - Refactor docker/Dockerfile.prod to remove supervisor

Action:

- Remove supervisor installation and any supervisor assumptions.
- Keep uv, venv creation, editable installs (gofr-common + project), and mcpo install.

Verify:

- `./docker/build-prod.sh` succeeds
- Image can run one service per container with a normal command

Status: DONE

### Step 02.2 - Replace docker/entrypoint-prod.sh to be "exec the command"

Action:

- Implement a gofr-doc style entrypoint:
  - create data/logs dirs
  - fix ownership
  - if GOFR_NP_NO_AUTH=1, add `--no-auth` for python services
  - drop privileges (run as the app user)
  - exec the command passed by compose

Verify:

- Running the image with `python -m app.main_mcp ...` starts and stays in the foreground
- No supervisor is invoked

Status: DONE

---

## Step 03 - Add production compose stack

### Step 03.1 - Add docker/compose.prod.yml

Action:

- Create docker/compose.prod.yml based on gofr-doc with services:
  - mcp
  - mcpo (depends_on mcp healthy)
  - web

Requirements:

- Use env_file: ../lib/gofr-common/config/gofr_ports.env
- Use external network: gofr-net
- Use one image tag for all 3 services (gofr-np-prod:latest)
- Use entrypoint-prod.sh for python services (mcp, web)
- For healthchecks, avoid local hostnames in docs/scripts; in compose healthchecks use container-local access (127.0.0.1) where needed

Verify:

- `docker compose -f docker/compose.prod.yml config` succeeds

Status: DONE

### Step 03.2 - Add docker/start-prod.sh

Action:

- Implement a compose-based launcher modeled after gofr-doc/docker/start-prod.sh:
  - flags: --build, --down, --no-auth
  - sources lib/gofr-common/config/gofr_ports.env
  - creates gofr-net if missing
  - builds image if missing or --build
  - runs `docker compose up -d`

Verify:

- `./docker/start-prod.sh --build` brings up mcp/mcpo/web

Status: DONE

### Step 03.3 - Make docker/stop-prod.sh a wrapper

Action:

- Replace docker/stop-prod.sh logic with a wrapper that calls `./docker/start-prod.sh --down`.

Verify:

- `./docker/stop-prod.sh` stops the compose stack

Status: DONE

---

## Step 04 - Add ephemeral compose test stack

### Step 04.1 - Add docker/compose.dev.yml (ephemeral test stack)

Action:

- Create docker/compose.dev.yml similar to gofr-doc/docker/compose.dev.yml but without Vault initially.

Requirements:

- name: gofr-np-test
- external network: gofr-test-net
- env_file: lib/gofr-common/config/gofr_ports.env
- containers listen on internal prod ports
- host publishes *_TEST ports
- set GOFR_NP_ENV=TEST
- set GOFR_NP_NO_AUTH=1 initially
- ensure GOFRNP_JWT_SECRET and GOFRNP_TOKEN_STORE are set consistently with pytest fixtures

Verify:

- `docker compose -f docker/compose.dev.yml --project-directory . up -d` succeeds
- From host: `curl -sf http://127.0.0.1:${GOFR_NP_MCP_PORT_TEST}/mcp` connects

Status: DONE

### Step 04.2 - Add scripts/start-test-env.sh

Action:

- Implement scripts/start-test-env.sh modeled after gofr-doc/scripts/start-test-env.sh:
  - flags: --build, --down
  - sources ports env
  - creates gofr-test-net
  - builds gofr-np-prod:latest if needed
  - runs compose.dev.yml up -d
  - polls container healthchecks (mcp, mcpo, web)

Verify:

- `./scripts/start-test-env.sh --build` results in all services healthy
- `./scripts/start-test-env.sh --down` removes containers

Status: DONE

---

## Step 05 - Migrate scripts/run_tests.sh to use the test compose stack

### Step 05.1 - Replace nohup-based server management

Action:

- Update scripts/run_tests.sh so integration tests do not start local processes.
- For integration tests:
  - call `./scripts/start-test-env.sh --build`
  - ensure teardown uses a trap and calls `./scripts/start-test-env.sh --down`

Verify:

- `./scripts/run_tests.sh --integration` starts the test stack and runs integration tests

Status: DONE

### Step 05.2 - Isolate legacy GOFRNP_* mapping to one place

Action:

- Compose files and docker scripts must use GOFR_NP_* (canonical).
- If Python/tests still read GOFRNP_* for now, keep mapping only inside scripts/run_tests.sh.

Verify:

- docker/compose.*.yml contains no GOFRNP_* references

Status: DONE

---

## Step 06 - Minimal test fix for hostname parameterization

### Step 06.1 - Remove hard-coded host in integration test

Action:

- Update test/mcp/test_math_compute.py to use GOFR_NP_MCP_HOST (default 127.0.0.1) instead of hard-coded local hostnames.

Verify:

- `./scripts/run_tests.sh --integration` passes

Status: DONE

---

## Step 07 - Delete redundant files (cleanup)

Do not delete until the new compose flows work.

### Step 07.1 - Remove redundant prod lifecycle scripts

Action:

- Delete docker/run-prod.sh (replaced by docker/start-prod.sh) [DONE]
- Delete docker/run-prod.sh.bak if present

Verify:

- Only docker/start-prod.sh and docker/stop-prod.sh are the supported prod lifecycle scripts

Status: DONE

### Step 07.2 - Remove unused web server placeholder (if unused)

Action:

- If nothing imports app/web_server.py, delete it (the actual stub server is app/web_server/web_server.py).

Verify:

- Web server still starts in compose

Status: DONE

---

## Step 08 - Final verification (acceptance)

### Step 08.1 - Prod stack smoke

Action:

- `./docker/start-prod.sh --build`

Verify:

- Endpoints are reachable from host at 127.0.0.1: published prod ports

Status: DONE

### Step 08.2 - Test stack smoke

Action:

- `./scripts/start-test-env.sh --build`

Verify:

- Test ports respond on 127.0.0.1

Status: DONE

### Step 08.3 - Full test suite

Action:

- Run `./scripts/run_tests.sh`

Verify:

- Exit code is 0

Status: DONE
