#!/bin/bash
# Run GOFR-NP development container
# Uses gofr-np-dev:latest image (built from gofr-base:latest)
# Runs as the host UID/GID so bind-mounted files have correct ownership.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect host user's UID/GID.
GOFR_UID=$(id -u)
GOFR_GID=$(id -g)

# Container and image names
CONTAINER_NAME="gofr-np-dev"
IMAGE_NAME="gofr-np-dev:latest"

# Defaults from environment or hardcoded (gofr-np uses 8020-8022)
MCP_PORT="${GOFRNP_MCP_PORT:-8020}"
MCPO_PORT="${GOFRNP_MCPO_PORT:-8021}"
WEB_PORT="${GOFRNP_WEB_PORT:-8022}"
DOCKER_NETWORK="${GOFRNP_DOCKER_NETWORK:-gofr-net}"

# Host user's home directory (for container mount destination paths).
HOST_HOME="${HOST_HOME:-}"

usage() {
        cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --mcp-port PORT      Host port to map to container MCP (default: $MCP_PORT)
    --mcpo-port PORT     Host port to map to container MCPO (default: $MCPO_PORT)
    --web-port PORT      Host port to map to container Web UI (default: $WEB_PORT)
    --network NAME       Docker network (default: $DOCKER_NETWORK)
    --host-home DIR      Host home directory used to construct container mount paths
    -h, --help           Show this help

Env:
    HOST_HOME            Same as --host-home
    GOFRNP_DOCKER_NETWORK  Same as --network
EOF
}

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --mcp-port)
            MCP_PORT="$2"
            shift 2
            ;;
        --mcpo-port)
            MCPO_PORT="$2"
            shift 2
            ;;
        --web-port)
            WEB_PORT="$2"
            shift 2
            ;;
        --network)
            DOCKER_NETWORK="$2"
            shift 2
            ;;
        --host-home)
            HOST_HOME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$HOST_HOME" ]; then
    host_user="${SUDO_USER:-$(id -un)}"
    host_home_from_passwd="$(getent passwd "$host_user" | cut -d: -f6 || true)"
    if [ -n "$host_home_from_passwd" ]; then
        HOST_HOME="$host_home_from_passwd"
    else
        HOST_HOME="${HOME:-/home/$host_user}"
    fi
fi

if [ ! -d "$HOST_HOME" ]; then
    echo "ERROR: host home directory does not exist: $HOST_HOME" >&2
    echo "  Provide a valid path via --host-home DIR" >&2
    exit 1
fi

CONTAINER_PROJECT_DIR="${HOST_HOME}/devroot/gofr-np"
CONTAINER_DOC_DIR="${HOST_HOME}/devroot/gofr-doc"

echo "======================================================================="
echo "Starting GOFR-NP Development Container"
echo "======================================================================="
echo "Host user: $(id -un) (UID=${GOFR_UID}, GID=${GOFR_GID})"
echo "Host home: $HOST_HOME"
echo "Container will run with --user ${GOFR_UID}:${GOFR_GID}"
echo "Ports: MCP=$MCP_PORT, MCPO=$MCPO_PORT, Web=$WEB_PORT"
echo "Network: $DOCKER_NETWORK"
echo "======================================================================="

# Create docker network if it doesn't exist
if ! docker network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
    echo "Creating network: $DOCKER_NETWORK"
    docker network create "$DOCKER_NETWORK"
fi

# Create docker volume for persistent data
VOLUME_NAME="gofr-np-data-dev"
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "Creating volume: $VOLUME_NAME"
    docker volume create "$VOLUME_NAME"
fi

# Docker host access (docker-outside-of-docker)
DOCKER_SOCK="/var/run/docker.sock"
DOCKER_GID_ARGS=""
DOCKER_SOCK_MOUNT=""
if [ -S "$DOCKER_SOCK" ]; then
    DOCKER_SOCK_GID=$(stat -c '%g' "$DOCKER_SOCK")
    DOCKER_GID_ARGS="--group-add $DOCKER_SOCK_GID"
    DOCKER_SOCK_MOUNT="-v /var/run/docker.sock:/var/run/docker.sock"
    echo "Docker socket detected: $DOCKER_SOCK (gid=$DOCKER_SOCK_GID)"
else
    echo "ERROR: Docker socket not found on host at $DOCKER_SOCK"
    echo "This dev container requires docker-outside-of-docker access."
    echo "Start Docker on the host and re-run this script."
    exit 1
fi

# Stop and remove existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Run container
docker run -d \
    --name "$CONTAINER_NAME" \
    --network "$DOCKER_NETWORK" \
    --user "${GOFR_UID}:${GOFR_GID}" \
    -w "${CONTAINER_PROJECT_DIR}" \
    $DOCKER_GID_ARGS \
    -p ${MCP_PORT}:8020 \
    -p ${MCPO_PORT}:8021 \
    -p ${WEB_PORT}:8022 \
    $DOCKER_SOCK_MOUNT \
    -v "$PROJECT_ROOT:${CONTAINER_PROJECT_DIR}:rw" \
    -v "${VOLUME_NAME}:${CONTAINER_PROJECT_DIR}/data:rw" \
    -v "$PROJECT_ROOT/../gofr-doc:${CONTAINER_DOC_DIR}:ro" \
    -e GOFR_NP_PROJECT_DIR="${CONTAINER_PROJECT_DIR}" \
    -e GOFRNP_ENV=development \
    -e GOFRNP_DEBUG=true \
    -e GOFRNP_LOG_LEVEL=DEBUG \
    "$IMAGE_NAME"

echo ""
echo "======================================================================="
echo "Container started: $CONTAINER_NAME"
echo "======================================================================="
echo ""
echo "Ports:"
echo "  - $MCP_PORT: MCP server"
echo "  - $MCPO_PORT: MCPO proxy"
echo "  - $WEB_PORT: Web interface"
echo ""
echo "Useful commands:"
echo "  docker logs -f $CONTAINER_NAME          # Follow logs"
echo "  docker exec -it $CONTAINER_NAME bash    # Shell access"
echo "  docker stop $CONTAINER_NAME             # Stop container"
