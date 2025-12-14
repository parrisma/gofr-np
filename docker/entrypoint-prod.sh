#!/bin/bash
# gofr-np Production Entrypoint
# Starts MCP, MCPO, and Web servers via supervisor
set -e

# Environment variables with defaults
export JWT_SECRET="${JWT_SECRET:-changeme}"
export MCP_PORT="${MCP_PORT:-8060}"
export MCPO_PORT="${MCPO_PORT:-8061}"
export WEB_PORT="${WEB_PORT:-8062}"

# gofr-np specific environment
export GOFR_NP_DATA_DIR="${GOFR_NP_DATA_DIR:-/home/gofr-np/data}"
export GOFR_NP_STORAGE_DIR="${GOFR_NP_STORAGE_DIR:-/home/gofr-np/data/storage}"
export GOFR_NP_AUTH_DIR="${GOFR_NP_AUTH_DIR:-/home/gofr-np/data/auth}"

# Path to venv
VENV_PATH="/home/gofr-np/.venv"

echo "=== gofr-np Production Container ==="
echo "MCP Port:  ${MCP_PORT}"
echo "MCPO Port: ${MCPO_PORT}"
echo "Web Port:  ${WEB_PORT}"
echo "Data Dir:  ${GOFR_NP_DATA_DIR}"

# Ensure data directories exist with correct permissions
mkdir -p "${GOFR_NP_DATA_DIR}" "${GOFR_NP_STORAGE_DIR}" "${GOFR_NP_AUTH_DIR}"
chown -R gofr-np:gofr-np /home/gofr-np/data

# Generate supervisor configuration
cat > /etc/supervisor/conf.d/gofr-np.conf << EOF
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[program:mcp]
command=${VENV_PATH}/bin/python -m app.main_mcp
directory=/home/gofr-np
user=gofr-np
autostart=true
autorestart=true
stdout_logfile=/home/gofr-np/logs/mcp.log
stderr_logfile=/home/gofr-np/logs/mcp-error.log
environment=PATH="${VENV_PATH}/bin:%(ENV_PATH)s",VIRTUAL_ENV="${VENV_PATH}",JWT_SECRET="%(ENV_JWT_SECRET)s",MCP_PORT="%(ENV_MCP_PORT)s",GOFR_NP_DATA_DIR="%(ENV_GOFR_NP_DATA_DIR)s",GOFR_NP_STORAGE_DIR="%(ENV_GOFR_NP_STORAGE_DIR)s",GOFR_NP_AUTH_DIR="%(ENV_GOFR_NP_AUTH_DIR)s"

[program:mcpo]
command=${VENV_PATH}/bin/mcpo --host 0.0.0.0 --port ${MCPO_PORT} -- ${VENV_PATH}/bin/python -m app.main_mcp
directory=/home/gofr-np
user=gofr-np
autostart=true
autorestart=true
stdout_logfile=/home/gofr-np/logs/mcpo.log
stderr_logfile=/home/gofr-np/logs/mcpo-error.log
environment=PATH="${VENV_PATH}/bin:%(ENV_PATH)s",VIRTUAL_ENV="${VENV_PATH}",JWT_SECRET="%(ENV_JWT_SECRET)s",GOFR_NP_DATA_DIR="%(ENV_GOFR_NP_DATA_DIR)s",GOFR_NP_STORAGE_DIR="%(ENV_GOFR_NP_STORAGE_DIR)s",GOFR_NP_AUTH_DIR="%(ENV_GOFR_NP_AUTH_DIR)s"

[program:web]
command=${VENV_PATH}/bin/python -m app.main_web
directory=/home/gofr-np
user=gofr-np
autostart=true
autorestart=true
stdout_logfile=/home/gofr-np/logs/web.log
stderr_logfile=/home/gofr-np/logs/web-error.log
environment=PATH="${VENV_PATH}/bin:%(ENV_PATH)s",VIRTUAL_ENV="${VENV_PATH}",JWT_SECRET="%(ENV_JWT_SECRET)s",WEB_PORT="%(ENV_WEB_PORT)s",GOFR_NP_DATA_DIR="%(ENV_GOFR_NP_DATA_DIR)s",GOFR_NP_STORAGE_DIR="%(ENV_GOFR_NP_STORAGE_DIR)s",GOFR_NP_AUTH_DIR="%(ENV_GOFR_NP_AUTH_DIR)s"
EOF

echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
