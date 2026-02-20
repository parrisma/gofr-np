#!/bin/bash
# =============================================================================
# gofr-np Production Entrypoint
# =============================================================================
# Single-process, compose-friendly entrypoint:
# - ensures data/logs directories exist
# - fixes ownership (best-effort)
# - optionally appends --no-auth for python app services
# - drops privileges to gofr-np
# - execs the provided command
# =============================================================================

set -euo pipefail

GOFR_USER="gofr-np"
PROJECT_DIR="/home/${GOFR_USER}"

CREDS_SOURCE="/run/gofr-secrets/service_creds/gofr-np.json"
CREDS_TARGET_DIR="/run/secrets"
CREDS_TARGET="${CREDS_TARGET_DIR}/vault_creds"

DATA_DIR="${GOFR_NP_DATA_DIR:-${PROJECT_DIR}/data}"
STORAGE_DIR="${GOFR_NP_STORAGE_DIR:-${DATA_DIR}/storage}"
AUTH_DIR="${GOFR_NP_AUTH_DIR:-${DATA_DIR}/auth}"
LOG_DIR="${GOFR_NP_LOG_DIR:-${PROJECT_DIR}/logs}"

mkdir -p "${DATA_DIR}" "${STORAGE_DIR}" "${AUTH_DIR}" "${LOG_DIR}"
chown -R "${GOFR_USER}:${GOFR_USER}" "${DATA_DIR}" "${LOG_DIR}" 2>/dev/null || true

# Copy Vault AppRole credentials from shared gofr-secrets volume
mkdir -p "${CREDS_TARGET_DIR}"
if [ -f "${CREDS_SOURCE}" ]; then
    cp "${CREDS_SOURCE}" "${CREDS_TARGET}"
    chmod 600 "${CREDS_TARGET}" 2>/dev/null || true
    chown "${GOFR_USER}:${GOFR_USER}" "${CREDS_TARGET}" 2>/dev/null || true
else
    echo "WARNING: No AppRole credentials at ${CREDS_SOURCE}"
fi

if [ "$#" -eq 0 ]; then
    echo "ERROR: No command provided to entrypoint"
    exit 1
fi

cmd=("$@")

if [ "${GOFR_NP_NO_AUTH:-}" = "1" ]; then
    if printf '%s\n' "${cmd[@]}" | grep -qE 'app\.main_(mcp|web)'; then
        echo "WARNING: Authentication is DISABLED (GOFR_NP_NO_AUTH=1)"
        cmd+=("--no-auth")
    fi
fi

if [ "$(id -u)" -eq 0 ]; then
    cmd_quoted="$(printf '%q ' "${cmd[@]}")"
    exec su -s /bin/bash "${GOFR_USER}" -c "exec ${cmd_quoted}"
fi

exec "${cmd[@]}"
