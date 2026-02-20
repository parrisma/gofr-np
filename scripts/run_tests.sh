#!/bin/bash

# =============================================================================
# GOFR-NP Test Runner
# =============================================================================
#
# Integration tests use the ephemeral docker compose test stack managed by
# scripts/start-test-env.sh.
#
# Default addressing mode is docker-network hostnames since gofr-np is usually
# executed inside a dev container.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_NAME="gofr-np"
LOG_DIR="${PROJECT_ROOT}/logs"

mkdir -p "${LOG_DIR}"

VENV_DIR="${PROJECT_ROOT}/.venv"
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
    echo "Activated venv: ${VENV_DIR}"
else
    echo -e "${YELLOW}Warning: Virtual environment not found at ${VENV_DIR}${NC}"
fi

export GOFR_NP_ENV="TEST"

if [ -f "${SCRIPT_DIR}/project.env" ]; then
    source "${SCRIPT_DIR}/project.env"
fi

if [ -d "${PROJECT_ROOT}/lib/gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/lib/gofr-common/src:${PYTHONPATH:-}"
else
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
fi

export GOFR_NP_AUTH_BACKEND="${GOFR_NP_AUTH_BACKEND:-vault}"
export GOFR_NP_VAULT_URL="${GOFR_NP_VAULT_URL:-http://gofr-np-vault-test:8201}"
export GOFR_NP_VAULT_PATH_PREFIX="${GOFR_NP_VAULT_PATH_PREFIX:-gofr/auth}"
export GOFR_NP_VAULT_MOUNT="${GOFR_NP_VAULT_MOUNT:-secret}"

START_DEV_SCRIPT="${SCRIPT_DIR}/start-test-env.sh"
START_SERVERS=true

USE_DOCKER=false

COVERAGE=false
COVERAGE_HTML=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_QUICK=false
RUN_BOUNDARY=false
RUN_ALL=false
STOP_ONLY=false
CLEANUP_ONLY=false
PYTEST_ARGS=()

print_header() {
    echo -e "${GREEN}=== ${PROJECT_NAME} Test Runner ===${NC}"
    echo "Project root: ${PROJECT_ROOT}"
    echo "Environment:  ${GOFR_NP_ENV}"
    if [ "$USE_DOCKER" = true ]; then
        echo "Addressing:   docker network (service hostnames)"
    else
        echo "Addressing:   host ports (published test ports via host.docker.internal when in a container)"
    fi
    echo "Auth backend: ${GOFR_NP_AUTH_BACKEND}"
    echo "Vault URL:    ${GOFR_NP_VAULT_URL}"
    echo "Vault path:   ${GOFR_NP_VAULT_PATH_PREFIX}"
    echo ""
}

start_services() {
    echo -e "${GREEN}=== Starting Ephemeral Docker Services ===${NC}"
    if [ ! -x "${START_DEV_SCRIPT}" ]; then
        echo -e "${RED}start-test-env.sh not found or not executable: ${START_DEV_SCRIPT}${NC}"
        exit 1
    fi
    "${START_DEV_SCRIPT}" --build
    echo ""
}

ensure_devcontainer_on_test_network() {
    if [ ! -f "/.dockerenv" ]; then
        return 0
    fi
    if [ "$USE_DOCKER" != true ]; then
        return 0
    fi

    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: docker CLI not available; cannot connect dev container to gofr-test-net${NC}"
        return 0
    fi

    local self_ref
    self_ref="$(hostname)"
    if ! docker inspect "${self_ref}" >/dev/null 2>&1; then
        if docker inspect "gofr-np-dev" >/dev/null 2>&1; then
            self_ref="gofr-np-dev"
        fi
    fi

    docker network connect gofr-test-net "${self_ref}" >/dev/null 2>&1 || true
}

stop_services() {
    echo -e "${YELLOW}Stopping ephemeral Docker services...${NC}"
    if [ -x "${START_DEV_SCRIPT}" ]; then
        "${START_DEV_SCRIPT}" --down 2>/dev/null || true
    fi
    echo -e "${GREEN}Services stopped${NC}"
}

cleanup_environment() {
    echo -e "${YELLOW}Cleaning up test environment...${NC}"
    stop_services
    echo -e "${GREEN}Cleanup complete${NC}"
}

apply_addressing_mode() {
    if [ "$USE_DOCKER" = true ]; then
        export GOFR_NP_MCP_HOST="gofr-np-mcp-test"
        export GOFR_NP_WEB_HOST="gofr-np-web-test"
        export GOFR_NP_MCP_PORT="${GOFR_NP_MCP_PORT}"
        export GOFR_NP_WEB_PORT="${GOFR_NP_WEB_PORT}"
    else
        export GOFR_NP_MCP_HOST="127.0.0.1"
        export GOFR_NP_WEB_HOST="127.0.0.1"
        export GOFR_NP_MCP_PORT="${GOFR_NP_MCP_PORT_TEST}"
        export GOFR_NP_WEB_PORT="${GOFR_NP_WEB_PORT_TEST}"
    fi
}

if [ -f "/.dockerenv" ]; then
    USE_DOCKER=true
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --coverage|--cov)
            COVERAGE=true
            shift
            ;;
        --coverage-html)
            COVERAGE=true
            COVERAGE_HTML=true
            shift
            ;;
        --unit)
            RUN_UNIT=true
            START_SERVERS=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            START_SERVERS=true
            shift
            ;;
        --quick)
            RUN_QUICK=true
            START_SERVERS=false
            shift
            ;;
        --boundary)
            RUN_BOUNDARY=true
            START_SERVERS=false
            shift
            ;;
        --all)
            RUN_ALL=true
            START_SERVERS=true
            shift
            ;;
        --no-servers)
            START_SERVERS=false
            shift
            ;;
        --with-servers)
            START_SERVERS=true
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --stop|--stop-servers)
            STOP_ONLY=true
            shift
            ;;
        --cleanup-only)
            CLEANUP_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [PYTEST_ARGS...]"
            echo ""
            echo "Options:"
            echo "  --coverage       Run with coverage report"
            echo "  --coverage-html  Run with HTML coverage report"
            echo "  --unit           Run unit tests only (no servers)"
            echo "  --integration    Run integration tests (requires compose stack)"
            echo "  --quick          Run quick validation (code quality + unit)"
            echo "  --boundary       Run boundary/edge case tests only (no servers)"
            echo "  --all            Run all test categories"
            echo "  --no-servers     Do not start compose stack"
            echo "  --docker         Use docker-network addressing (default)"
            echo "  --no-docker      Use host port addressing (published test ports)"
            echo "  --stop           Stop compose stack and exit"
            echo "  --cleanup-only   Cleanup and exit"
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

apply_addressing_mode
print_header

if [ "$STOP_ONLY" = true ]; then
    stop_services
    exit 0
fi

if [ "$CLEANUP_ONLY" = true ]; then
    cleanup_environment
    exit 0
fi

trap 'stop_services' EXIT

if [ "$START_SERVERS" = true ]; then
    start_services
    ensure_devcontainer_on_test_network

    # Export test token for pytest (minted during start-test-env bootstrap)
    TOKEN_ENV_FILE="${PROJECT_ROOT}/secrets/test_tokens.env"
    if [ -f "${TOKEN_ENV_FILE}" ]; then
        set -a
        # shellcheck disable=SC1090
        source "${TOKEN_ENV_FILE}"
        set +a
    else
        echo -e "${RED}ERROR: Missing test token env file: ${TOKEN_ENV_FILE}${NC}"
        echo -e "${YELLOW}Fix: re-run with --integration/--all so the stack bootstraps Vault and tokens${NC}"
        exit 1
    fi
fi

COVERAGE_ARGS=""
if [ "$COVERAGE" = true ]; then
    COVERAGE_ARGS="--cov=app --cov-report=term-missing"
    if [ "$COVERAGE_HTML" = true ]; then
        COVERAGE_ARGS="${COVERAGE_ARGS} --cov-report=html:htmlcov"
    fi
    echo -e "${BLUE}Coverage reporting enabled${NC}"
fi

echo -e "${GREEN}=== Running Tests ===${NC}"

set +e
TEST_EXIT_CODE=0

if [ "$RUN_QUICK" = true ]; then
    echo -e "${BLUE}Running QUICK validation (code quality + unit tests)...${NC}"
    uv run python -m pytest test/code_quality/ -v
    CODE_QUALITY_EXIT=$?
    if [ ${CODE_QUALITY_EXIT} -ne 0 ]; then
        TEST_EXIT_CODE=${CODE_QUALITY_EXIT}
    else
        uv run python -m pytest test/mcp/test_curve_fit.py test/mcp/test_financial.py test/mcp/test_financial_edge_cases.py -v ${COVERAGE_ARGS}
        TEST_EXIT_CODE=$?
    fi

elif [ "$RUN_UNIT" = true ]; then
    echo -e "${BLUE}Running UNIT tests only (no servers)...${NC}"
    uv run python -m pytest test/mcp/test_curve_fit.py test/mcp/test_financial.py test/mcp/test_financial_*.py -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ "$RUN_BOUNDARY" = true ]; then
    echo -e "${BLUE}Running BOUNDARY/edge case tests only (no servers)...${NC}"
    uv run python -m pytest test/mcp/test_boundary_cases.py -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}Running INTEGRATION tests (compose stack required)...${NC}"
    uv run python -m pytest test/mcp/test_math_compute.py -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ "$RUN_ALL" = true ]; then
    echo -e "${BLUE}Running ALL tests...${NC}"
    uv run python -m pytest test/code_quality/ -v
    CODE_QUALITY_EXIT=$?
    if [ ${CODE_QUALITY_EXIT} -ne 0 ]; then
        TEST_EXIT_CODE=${CODE_QUALITY_EXIT}
    else
        uv run python -m pytest test/mcp/test_curve_fit.py test/mcp/test_financial.py test/mcp/test_financial_*.py -v ${COVERAGE_ARGS}
        UNIT_EXIT=$?
        if [ ${UNIT_EXIT} -ne 0 ]; then
            TEST_EXIT_CODE=${UNIT_EXIT}
        else
            uv run python -m pytest test/mcp/test_math_compute.py -v ${COVERAGE_ARGS}
            TEST_EXIT_CODE=$?
        fi
    fi

elif [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    echo -e "${BLUE}Running code quality tests...${NC}"
    uv run python -m pytest test/code_quality/ -v
    CODE_QUALITY_EXIT=$?
    if [ ${CODE_QUALITY_EXIT} -ne 0 ]; then
        TEST_EXIT_CODE=${CODE_QUALITY_EXIT}
    else
        echo ""
        echo -e "${BLUE}Running MCP tests...${NC}"
        uv run python -m pytest test/mcp/ -v ${COVERAGE_ARGS}
        TEST_EXIT_CODE=$?
    fi

else
    uv run python -m pytest "${PYTEST_ARGS[@]}" ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?
fi

set -e

echo "{}" > "${GOFRNP_TOKEN_STORE}" 2>/dev/null || true

echo ""
if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}=== Tests Passed ===${NC}"
    if [ "$COVERAGE" = true ] && [ "$COVERAGE_HTML" = true ]; then
        echo -e "${BLUE}HTML coverage report: ${PROJECT_ROOT}/htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}=== Tests Failed (exit code: ${TEST_EXIT_CODE}) ===${NC}"
fi

exit ${TEST_EXIT_CODE}
