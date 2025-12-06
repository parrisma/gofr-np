#!/bin/sh

# Usage: ./run-dev.sh [options]
# Options:
#   --mcp-port PORT    MCP server port (default: 8020 or GOFRNP_MCP_PORT)
#   --mcpo-port PORT   MCPO proxy port (default: 8021 or GOFRNP_MCPO_PORT)
#   --web-port PORT    Web server port (default: 8022 or GOFRNP_WEB_PORT)
#   --network NAME     Docker network (default: gofr-net or GOFRNP_DOCKER_NETWORK)
#
# Environment variables can also be set: GOFRNP_MCP_PORT, GOFRNP_MCPO_PORT, GOFRNP_WEB_PORT, GOFRNP_DOCKER_NETWORK

# Defaults from environment or hardcoded
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

# Create docker network if it doesn't exist
echo "Checking for $DOCKER_NETWORK network..."
if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
    echo "Creating $DOCKER_NETWORK network..."
    docker network create $DOCKER_NETWORK
else
    echo "Network $DOCKER_NETWORK already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gofrnp_data_dev volume..."
if ! docker volume inspect gofrnp_data_dev >/dev/null 2>&1; then
    echo "Creating gofrnp_data_dev volume..."
    docker volume create gofrnp_data_dev
    VOLUME_CREATED=true
else
    echo "Volume gofrnp_data_dev already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofrnp_dev container..."
docker stop gofrnp_dev 2>/dev/null || true

echo "Removing existing gofrnp_dev container..."
docker rm gofrnp_dev 2>/dev/null || true

echo "Starting new gofrnp_dev container..."
echo "Mounting $HOME/devroot/gofr-np to /home/gofr-np/devroot/gofr-np in container"
echo "Mounting $HOME/.ssh to /home/gofr-np/.ssh (read-only) in container"
echo "Mounting gofrnp_data_dev volume to /home/gofr-np/devroot/gofr-np/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT, MCPO port: $MCPO_PORT"

docker run -d \
--name gofrnp_dev \
--network $DOCKER_NETWORK \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/gofr-np":/home/gofr-np/devroot/gofr-np \
-v "$HOME/.ssh:/home/gofr-np/.ssh:ro" \
-v gofrnp_data_dev:/home/gofr-np/devroot/gofr-np/data \
-p 0.0.0.0:$MCP_PORT:8020 \
-p 0.0.0.0:$MCPO_PORT:8021 \
-p 0.0.0.0:$WEB_PORT:8022 \
gofrnp_dev:latest

if docker ps -q -f name=gofrnp_dev | grep -q .; then
    echo "Container gofrnp_dev is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofrnp_dev chown -R gofr-np:gofr-np /home/gofr-np/devroot/gofr-np/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "==================================================================="
    echo "Development Container Access:"
    echo "  Shell:         docker exec -it gofrnp_dev /bin/bash"
    echo "  VS Code:       Attach to container 'gofrnp_dev'"
    echo ""
    echo "Access from Host Machine:"
    echo "  Web Server:    http://localhost:$WEB_PORT"
    echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
    echo "  MCPO Proxy:    http://localhost:$MCPO_PORT"
    echo ""
    echo "Access from $DOCKER_NETWORK (other containers):"
    echo "  Web Server:    http://gofrnp_dev:8022"
    echo "  MCP Server:    http://gofrnp_dev:8020/mcp"
    echo "  MCPO Proxy:    http://gofrnp_dev:8021"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        gofrnp_data_dev"
    echo "  Source Mount:  $HOME/devroot/gofr-np (live-reload)"
    echo "  Network:       $DOCKER_NETWORK"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container gofrnp_dev failed to start"
    exit 1
fi