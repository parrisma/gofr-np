# Dev Container Docker Host Access Spec (docker-outside-of-docker)

## Goal

Make the repo's dev container (started via `docker/run-dev.sh`) able to run `docker` and `docker compose` immediately (first start) and durably (across rebuilds), using the host Docker daemon via a mounted Unix socket at `/var/run/docker.sock`.

This is docker-outside-of-docker (DooD), not Docker-in-Docker (DinD).

## Non-goals

- Do not run a Docker daemon inside the dev container.
- Do not set `DOCKER_HOST` to TCP unless explicitly required.
- Do not require manual post-start steps.

## Success Criteria

Inside the dev container, as the normal (non-root) dev user:

- `/var/run/docker.sock` exists.
- `docker version` works.
- `docker ps` works.
- `docker compose version` works.
- No `sudo` is required to run `docker`.
- The dev user belongs to the group that owns `/var/run/docker.sock` (matching socket GID).

## Constraints

- The developer machine has Docker installed and running.
- The devcontainer runtime supports bind-mounting the host Docker socket.
- Access to `docker.sock` is effectively root-equivalent on the host; this is only for trusted developer environments.
- Repo rules:
  - ASCII-only output.
  - Use UV (`uv run`, `uv sync`, `uv add`). Avoid pip workflows.

## Proposed Approach

This repo will follow a simple, direct pattern:

1. Install Docker CLI tooling in the dev image

- Update `docker/Dockerfile.dev` to install:
  - `docker-ce-cli`
  - `docker-compose-plugin`

2. Mount the host Docker socket into the dev container

- Update `docker/run-dev.sh` to include:
  - `-v /var/run/docker.sock:/var/run/docker.sock`

3. Make it durable across machines via socket GID mapping

- Update `docker/run-dev.sh` to detect the socket GID at runtime and pass:
  - `--group-add <gid-from-docker.sock>`

This avoids hardcoding a docker group GID, which differs per host.

4. Validate access

- Inside the container, as the non-root dev user:
  - `docker version`
  - `docker ps`
  - `docker compose version`

## Assumptions (explicit)

1. Developer machine has Docker installed and running.
2. The dev container runtime supports bind-mounting `/var/run/docker.sock` from the host.
3. The host docker socket group ID may vary across machines.
4. The desired behavior is docker-outside-of-docker using the host daemon (no DinD).

## Open Questions

None. This change targets `docker/Dockerfile.dev` and `docker/run-dev.sh` only.
