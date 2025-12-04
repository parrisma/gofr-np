#!/bin/sh

# Usage: ./run-dev.sh [WEB_PORT] [MCP_PORT] [MCPO_PORT]
# Defaults: WEB_PORT=8022, MCP_PORT=8020, MCPO_PORT=8021
# Example: ./run-dev.sh 9012 9010 9011

# Parse command line arguments
WEB_PORT=${1:-8022}
MCP_PORT=${2:-8020}
MCPO_PORT=${3:-8021}

# Create docker network if it doesn't exist
echo "Checking for gofr-net network..."
if ! docker network inspect gofr-net >/dev/null 2>&1; then
    echo "Creating gofr-net network..."
    docker network create gofr-net
else
    echo "Network gofr-net already exists"
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
--network gofr-net \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/gofr-np":/home/gofr-np/devroot/gofr-np \
-v "$HOME/.ssh:/home/gofr-np/.ssh:ro" \
-v gofrnp_data_dev:/home/gofr-np/devroot/gofr-np/data \
-p $MCP_PORT:8020 \
-p $MCPO_PORT:8021 \
-p $WEB_PORT:8022 \
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
    echo "Access from gofr-net (other containers):"
    echo "  Web Server:    http://gofrnp_dev:8022"
    echo "  MCP Server:    http://gofrnp_dev:8020/mcp"
    echo "  MCPO Proxy:    http://gofrnp_dev:8021"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        gofrnp_data_dev"
    echo "  Source Mount:  $HOME/devroot/gofr-np (live-reload)"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container gofrnp_dev failed to start"
    exit 1
fi