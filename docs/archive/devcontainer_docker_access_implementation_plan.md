# Implementation Plan: Dev Container Docker Host Access

This plan implements docs/devcontainer_docker_access_spec.md.

Rules:
- No code in this document.
- Each step is small and independently verifiable.

## Step 0 - Baseline (current state)

Action:
- From inside the current dev container, run: `./scripts/run_tests.sh --quick`.
- Attempt a full run: `./scripts/run_tests.sh`.

Verify:
- Quick run passes.
- Full run currently fails because Docker CLI/socket access is not available in this container environment.

Mark: DONE (baseline recorded)

## Step 1 - Install Docker CLI in dev image

Action:
- Update docker/Dockerfile.dev to install Docker CLI tooling:
  - docker-ce-cli
  - docker-compose-plugin

Verify:
- Build the dev image.
- Inside a freshly started dev container, `docker version` prints client info.
- Inside the same container, `docker compose version` works.

Mark: TODO

## Step 2 - Mount host docker.sock into dev container

Action:
- Update docker/run-dev.sh to mount `/var/run/docker.sock` into the container.

Verify:
- In the newly started container, `/var/run/docker.sock` exists and is a socket.

Mark: TODO

## Step 3 - Durable permission via dynamic socket GID mapping

Action:
- Update docker/run-dev.sh to detect the socket GID and pass `--group-add <gid>` to `docker run`.

Verify:
- In the newly started container, `id` shows the process is a member of the socket-owning GID.
- As the non-root dev user, `docker ps` works without sudo.

Mark: TODO

## Step 4 - End-to-end validation for test stack

Action:
- In the updated dev container, run the full suite: `./scripts/run_tests.sh`.

Verify:
- The compose-based test environment starts.
- Integration tests that depend on the running test stack pass.

Mark: TODO

## Step 5 - Document developer workflow

Action:
- Update README.md (or a short docs note) describing:
  - How to build/start the dev container.
  - That Docker host access requires mounting docker.sock.
  - The security note: docker.sock access is host-root equivalent.

Verify:
- New instructions are accurate and minimal.

Mark: TODO
