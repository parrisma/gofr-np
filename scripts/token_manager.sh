#!/bin/bash
# GOFR-NP Token Manager
# Wrapper for the shared token_manager.sh script
#
# Usage: ./token_manager.sh [--env PROD|TEST] <command> [options]
#
# Commands:
#   create    Create a new token
#   list      List all tokens
#   verify    Verify a token
#   revoke    Revoke a token

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPTS="$SCRIPT_DIR/../../gofr-common/scripts"

# Check for lib/gofr-common location first (inside container)
if [ -d "$SCRIPT_DIR/../lib/gofr-common/scripts" ]; then
    COMMON_SCRIPTS="$SCRIPT_DIR/../lib/gofr-common/scripts"
fi

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

# Re-source gofrnp.env with potentially updated GOFRNP_ENV
source "$SCRIPT_DIR/gofrnp.env"

# Map project-specific vars to common vars
export GOFR_PROJECT_NAME="gofr-np"
export GOFR_PROJECT_ROOT="$GOFRNP_ROOT"
export GOFR_TOKEN_STORE="$GOFRNP_TOKEN_STORE"
export GOFR_ENV="$GOFRNP_ENV"
export GOFR_ENV_VAR_PREFIX="GOFRNP"
export GOFR_TOKEN_MODULE="app.auth.token_manager"

# Call shared script
source "$COMMON_SCRIPTS/token_manager.sh" "$@"
