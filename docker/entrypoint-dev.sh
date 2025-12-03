#!/bin/bash
set -e

# Fix data directory permissions if mounted as volume
if [ -d "/home/gofr-np/devroot/gofr-np/data" ]; then
    # Check if we can write to data directory
    if [ ! -w "/home/gofr-np/devroot/gofr-np/data" ]; then
        echo "Fixing permissions for /home/gofr-np/devroot/gofr-np/data..."
        # This will work if container is started with appropriate privileges
        sudo chown -R gofr-np:gofr-np /home/gofr-np/devroot/gofr-np/data 2>/dev/null || \
            echo "Warning: Could not fix permissions. Run container with --user $(id -u):$(id -g)"
    fi
fi

# Create subdirectories if they don't exist
mkdir -p /home/gofr-np/devroot/gofr-np/data/storage /home/gofr-np/devroot/gofr-np/data/auth

# Install/sync Python dependencies if requirements.txt exists
if [ -f "/home/gofr-np/devroot/gofr-np/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    cd /home/gofr-np/devroot/gofr-np
    # Use 'uv pip install' instead of 'sync' to ensure transitive dependencies are installed
    VIRTUAL_ENV=/home/gofr-np/devroot/gofr-np/.venv uv pip install -r requirements.txt || \
        echo "Warning: Could not install dependencies"
fi

# Execute the main command
exec "$@"
