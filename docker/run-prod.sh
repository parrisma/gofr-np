#!/bin/bash
# Run gofr-np production container with proper volumes and networking
set -e

CONTAINER_NAME="gofr-np-prod"
IMAGE_NAME="gofr-np-prod:latest"
NETWORK_NAME="gofr-net"

# Port assignments for gofr-np
MCP_PORT="${GOFR_NP_MCP_PORT:-8060}"
MCPO_PORT="${GOFR_NP_MCPO_PORT:-8061}"
WEB_PORT="${GOFR_NP_WEB_PORT:-8062}"

# JWT Secret (required)
JWT_SECRET="${GOFR_NP_JWT_SECRET:-}"

if [ -z "$JWT_SECRET" ]; then
    echo "ERROR: GOFR_NP_JWT_SECRET environment variable is required"
    echo "Usage: GOFR_NP_JWT_SECRET=your-secret ./run-prod.sh"
    exit 1
fi

echo "=== gofr-np Production Container ==="

# Create network if it doesn't exist
if ! docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo "Creating network: ${NETWORK_NAME}"
    docker network create ${NETWORK_NAME}
fi

# Create volumes if they don't exist
for vol in gofr-np-data gofr-np-logs; do
    if ! docker volume inspect ${vol} >/dev/null 2>&1; then
        echo "Creating volume: ${vol}"
        docker volume create ${vol}
    fi
done

# Stop existing container if running
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Stopping existing container..."
    docker stop ${CONTAINER_NAME}
fi

# Remove existing container if exists
if docker ps -aq -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Removing existing container..."
    docker rm ${CONTAINER_NAME}
fi

echo "Starting ${CONTAINER_NAME}..."
echo "  MCP Port:  ${MCP_PORT}"
echo "  MCPO Port: ${MCPO_PORT}"
echo "  Web Port:  ${WEB_PORT}"

docker run -d \
    --name ${CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    -v gofr-np-data:/home/gofr-np/data \
    -v gofr-np-logs:/home/gofr-np/logs \
    -p ${MCP_PORT}:8060 \
    -p ${MCPO_PORT}:8061 \
    -p ${WEB_PORT}:8062 \
    -e JWT_SECRET="${JWT_SECRET}" \
    -e MCP_PORT=8060 \
    -e MCPO_PORT=8061 \
    -e WEB_PORT=8062 \
    ${IMAGE_NAME}

# Wait for container to start
sleep 2

if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo ""
    echo "=== Container Started Successfully ==="
    echo "MCP Server:  http://localhost:${MCP_PORT}/mcp"
    echo "MCPO Server: http://localhost:${MCPO_PORT}"
    echo "Web Server:  http://localhost:${WEB_PORT}"
    echo ""
    echo "Volumes:"
    echo "  Data: gofr-np-data"
    echo "  Logs: gofr-np-logs"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:   ./stop-prod.sh"
    echo "  Shell:  docker exec -it ${CONTAINER_NAME} bash"
else
    echo "ERROR: Container failed to start"
    docker logs ${CONTAINER_NAME}
    exit 1
fi
