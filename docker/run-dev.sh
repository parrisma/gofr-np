#!/bin/bash
# Run GOFR-NP development container
# Uses gofr-np-dev:latest image (built from gofr-base:latest)
# Standard user: gofr (UID 1000, GID 1000)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# gofr-common is now a git submodule at lib/gofr-common, no separate mount needed

# Standard GOFR user - all projects use same user
GOFR_USER="gofr"
GOFR_UID=1000
GOFR_GID=1000

# Container and image names
CONTAINER_NAME="gofr-np-dev"
IMAGE_NAME="gofr-np-dev:latest"

# Defaults from environment or hardcoded (gofr-np uses 8020-8022)
MCP_PORT="${GOFRNP_MCP_PORT:-8020}"
MCPO_PORT="${GOFRNP_MCPO_PORT:-8021}"
WEB_PORT="${GOFRNP_WEB_PORT:-8022}"
DOCKER_NETWORK="${GOFRNP_DOCKER_NETWORK:-gofr-net}"

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--mcp-port PORT] [--mcpo-port PORT] [--web-port PORT] [--network NAME]"
            exit 1
            ;;
    esac
done

echo "======================================================================="
echo "Starting GOFR-NP Development Container"
echo "======================================================================="
echo "User: ${GOFR_USER} (UID=${GOFR_UID}, GID=${GOFR_GID})"
echo "Ports: MCP=$MCP_PORT, MCPO=$MCPO_PORT, Web=$WEB_PORT"
echo "Network: $DOCKER_NETWORK"
echo "======================================================================="

# Create docker network if it doesn't exist
if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
    echo "Creating network: $DOCKER_NETWORK"
    docker network create $DOCKER_NETWORK
fi

# Create docker volume for persistent data
VOLUME_NAME="gofr-np-data-dev"
if ! docker volume inspect $VOLUME_NAME >/dev/null 2>&1; then
    echo "Creating volume: $VOLUME_NAME"
    docker volume create $VOLUME_NAME
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
    $DOCKER_GID_ARGS \
    -p ${MCP_PORT}:8020 \
    -p ${MCPO_PORT}:8021 \
    -p ${WEB_PORT}:8022 \
    $DOCKER_SOCK_MOUNT \
    -v "$PROJECT_ROOT:/home/gofr/devroot/gofr-np:rw" \
    -v ${VOLUME_NAME}:/home/gofr/devroot/gofr-np/data:rw \
    -v "$PROJECT_ROOT/../gofr-doc:/home/gofr/devroot/gofr-doc:ro" \
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
