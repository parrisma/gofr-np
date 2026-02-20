#!/bin/bash
# =============================================================================
# gofr-np Production Stack - compose-based launcher
# =============================================================================
# Usage:
#   ./docker/start-prod.sh               # Start stack
#   ./docker/start-prod.sh --build       # Force rebuild image first
#   ./docker/start-prod.sh --down        # Stop and remove all services
#   ./docker/start-prod.sh --no-auth     # Disable JWT authentication
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILE="$SCRIPT_DIR/compose.prod.yml"
DOCKERFILE="$SCRIPT_DIR/Dockerfile.prod"
IMAGE_NAME="gofr-np-prod:latest"
NETWORK_NAME="gofr-net"
PORTS_ENV="$PROJECT_ROOT/lib/gofr-common/config/gofr_ports.env"

FORCE_BUILD=false
NO_AUTH=false
DO_DOWN=false

while [ $# -gt 0 ]; do
    case "$1" in
        --build)   FORCE_BUILD=true; shift ;;
        --no-auth) NO_AUTH=true; shift ;;
        --down)    DO_DOWN=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--build] [--down] [--no-auth]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== gofr-np Production Stack ==="

if [ -f "$PORTS_ENV" ]; then
    set -a && source "$PORTS_ENV" && set +a
    echo "Ports loaded from gofr_ports.env"
else
    echo "ERROR: Port config not found: $PORTS_ENV"
    exit 1
fi

MCP_PORT="${GOFR_NP_MCP_PORT:-8060}"
MCPO_PORT="${GOFR_NP_MCPO_PORT:-8061}"
WEB_PORT="${GOFR_NP_WEB_PORT:-8062}"

if [ "$DO_DOWN" = true ]; then
    echo "Stopping gofr-np production stack..."
    docker compose -f "$COMPOSE_FILE" --project-directory "$PROJECT_ROOT" down
    echo "Stack stopped."
    exit 0
fi

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
    echo "Creating network: ${NETWORK_NAME}"
    docker network create "${NETWORK_NAME}"
fi

if [ "$NO_AUTH" = true ]; then
    export GOFR_NP_NO_AUTH=1
    echo "Authentication DISABLED (--no-auth)"
fi

# ---- Vault auth path prefix hardening ----------------------------------------
# All GOFR services share one canonical auth path prefix: gofr/auth.
CANONICAL_VAULT_AUTH_PREFIX="gofr/auth"
if [ "${GOFR_NP_VAULT_PATH_PREFIX:-}" != "${CANONICAL_VAULT_AUTH_PREFIX}" ]; then
    if [ -n "${GOFR_NP_VAULT_PATH_PREFIX:-}" ]; then
        echo "WARNING: GOFR_NP_VAULT_PATH_PREFIX was '${GOFR_NP_VAULT_PATH_PREFIX}'; overriding to '${CANONICAL_VAULT_AUTH_PREFIX}'"
    fi
    export GOFR_NP_VAULT_PATH_PREFIX="${CANONICAL_VAULT_AUTH_PREFIX}"
fi

if [ "$FORCE_BUILD" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building production image..."
    "$PROJECT_ROOT/docker/build-prod.sh"
fi

echo ""
echo "Starting compose stack..."
echo "  MCP Port:  ${MCP_PORT}"
echo "  MCPO Port: ${MCPO_PORT}"
echo "  Web Port:  ${WEB_PORT}"
echo ""

docker compose -f "$COMPOSE_FILE" --project-directory "$PROJECT_ROOT" up -d

echo ""
echo "Waiting for services..."
sleep 5

HEALTHY=true
for svc in mcp mcpo web; do
    cname="gofr-np-${svc}"
    if docker ps -q -f name="${cname}" | grep -q .; then
        echo "  [OK]  ${cname} running"
    else
        echo "  [ERR] ${cname} NOT running"
        HEALTHY=false
    fi
done

echo ""
if [ "$HEALTHY" = true ]; then
    echo "=== Stack Started Successfully ==="
    echo "MCP Server:  http://host.docker.internal:${MCP_PORT}/mcp"
    echo "MCPO Server: http://host.docker.internal:${MCPO_PORT}"
    echo "Web Server:  http://host.docker.internal:${WEB_PORT}"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker compose -f ${COMPOSE_FILE} --project-directory ${PROJECT_ROOT} logs -f"
    echo "  Stop:   ./docker/start-prod.sh --down"
    echo "  Status: docker compose -f ${COMPOSE_FILE} --project-directory ${PROJECT_ROOT} ps"
else
    echo "ERROR: Some services failed to start"
    docker compose -f "$COMPOSE_FILE" --project-directory "$PROJECT_ROOT" logs
    exit 1
fi
