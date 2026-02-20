#!/bin/bash
# =======================================================================
# gofr-np Production Stop Script
# =======================================================================
# Delegates to start-prod.sh --down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start-prod.sh" --down
