#!/bin/bash
# Token manager script for GOFRNP
# Wraps the Python token_manager module

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source centralized configuration
source "$SCRIPT_DIR/gofrnp.env"

# Parse environment argument if provided
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            export GOFRNP_ENV="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Re-source gofrnp.env with potentially updated GOFRNP_ENV to pick up correct paths
source "$SCRIPT_DIR/gofrnp.env"

# Run token manager with correct paths
cd "$GOFRNP_ROOT"
uv run python -m app.auth.token_manager \
    --gofr-np-env "$GOFRNP_ENV" \
    --token-store "$GOFRNP_TOKEN_STORE" \
    "$@"
