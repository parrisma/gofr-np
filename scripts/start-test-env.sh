#!/bin/bash
# =============================================================================
# gofr-np Test Environment Manager
# =============================================================================
# Builds the prod image (if needed), creates the test network, and starts
# the docker/compose.dev.yml stack. Polls Docker health checks until all
# services are healthy or a timeout is reached.
#
# Usage:
#   ./scripts/start-test-env.sh            # Start (build if image missing)
#   ./scripts/start-test-env.sh --build    # Force rebuild + start
#   ./scripts/start-test-env.sh --down     # Tear down the stack
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${PROJECT_ROOT}/docker/compose.dev.yml"
DOCKERFILE="${PROJECT_ROOT}/docker/Dockerfile.prod"
PORTS_ENV="${PROJECT_ROOT}/lib/gofr-common/config/gofr_ports.env"

VAULT_DOCKERFILE="${PROJECT_ROOT}/lib/gofr-common/docker/Dockerfile.vault"
VAULT_IMAGE="gofr-vault:latest"
VAULT_CONTAINER="gofr-np-vault-test"
VAULT_INTERNAL_URL="http://gofr-np-vault-test:8201"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

if [ ! -f "${PORTS_ENV}" ]; then
    fail "Port config not found: ${PORTS_ENV}"
fi
set -a
source "${PORTS_ENV}"
set +a

export GOFR_NP_MCP_HOST_PORT=${GOFR_NP_MCP_PORT_TEST}
export GOFR_NP_MCPO_HOST_PORT=${GOFR_NP_MCPO_PORT_TEST}
export GOFR_NP_WEB_HOST_PORT=${GOFR_NP_WEB_PORT_TEST}

ok "Ports loaded - test ports (MCP=${GOFR_NP_MCP_HOST_PORT}, MCPO=${GOFR_NP_MCPO_HOST_PORT}, Web=${GOFR_NP_WEB_HOST_PORT})"

ensure_vault_image() {
    if docker image inspect "${VAULT_IMAGE}" >/dev/null 2>&1; then
        ok "Vault image exists: ${VAULT_IMAGE}"
        return 0
    fi

    info "Vault image missing; building ${VAULT_IMAGE}..."
    docker build -f "${VAULT_DOCKERFILE}" -t "${VAULT_IMAGE}" "${PROJECT_ROOT}/lib/gofr-common"
    ok "Vault image built: ${VAULT_IMAGE}"
}

_tools_vault_url() {
    if [ -f "/.dockerenv" ]; then
        echo "${VAULT_INTERNAL_URL}"
        return 0
    fi
    # Host execution fallback: published test port.
    echo "http://127.0.0.1:${GOFR_VAULT_PORT_TEST:-8301}"
}

ensure_self_on_test_network() {
    if [ ! -f "/.dockerenv" ]; then
        return 0
    fi
    if ! command -v docker >/dev/null 2>&1; then
        return 0
    fi

    local self_ref
    self_ref="$(hostname)"
    if ! docker inspect "${self_ref}" >/dev/null 2>&1; then
        if docker inspect "gofr-np-dev" >/dev/null 2>&1; then
            self_ref="gofr-np-dev"
        fi
    fi

    docker network connect "${TEST_NETWORK}" "${self_ref}" >/dev/null 2>&1 || true
}

bootstrap_test_vault() {
    info "Starting isolated Vault for tests (${VAULT_CONTAINER})..."
    docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" up -d vault

    info "Waiting for Vault API to be reachable..."
    local status_json=""
    for i in $(seq 1 30); do
        status_json=$(docker exec "${VAULT_CONTAINER}" vault status -format=json 2>/dev/null || true)
        if [ -n "${status_json}" ]; then
            ok "Vault API is reachable"
            break
        fi
        sleep 2
        if [ "$i" -eq 30 ]; then
            docker logs "${VAULT_CONTAINER}" 2>&1 || true
            fail "Vault API did not become reachable"
        fi
    done

    mkdir -p "${PROJECT_ROOT}/secrets"
    local root_token_file="${PROJECT_ROOT}/secrets/vault_root_token"
    local unseal_key_file="${PROJECT_ROOT}/secrets/vault_unseal_key"

    status_json=$(docker exec "${VAULT_CONTAINER}" vault status -format=json 2>/dev/null || true)
    if echo "${status_json}" | grep -q '"initialized"\s*:\s*false'; then
        info "Initializing Vault (test instance)..."
        docker exec "${VAULT_CONTAINER}" vault operator init -key-shares=1 -key-threshold=1 \
            | tee "${PROJECT_ROOT}/secrets/vault_init_output" >/dev/null
        local unseal_key
        local root_token
        unseal_key=$(grep 'Unseal Key 1:' "${PROJECT_ROOT}/secrets/vault_init_output" | awk '{print $4}')
        root_token=$(grep 'Initial Root Token:' "${PROJECT_ROOT}/secrets/vault_init_output" | awk '{print $4}')
        echo -n "${unseal_key}" > "${unseal_key_file}"
        echo -n "${root_token}" > "${root_token_file}"
        chmod 600 "${unseal_key_file}" "${root_token_file}" 2>/dev/null || true
    fi

    if [ ! -f "${unseal_key_file}" ] || [ ! -f "${root_token_file}" ]; then
        fail "Missing Vault bootstrap artifacts under ${PROJECT_ROOT}/secrets (vault_root_token/vault_unseal_key)"
    fi

    local unseal_key
    local root_token
    unseal_key=$(cat "${unseal_key_file}")
    root_token=$(cat "${root_token_file}")

    status_json=$(docker exec "${VAULT_CONTAINER}" vault status -format=json 2>/dev/null || true)
    if echo "${status_json}" | grep -q '"sealed"\s*:\s*true'; then
        info "Unsealing Vault..."
        docker exec "${VAULT_CONTAINER}" vault operator unseal "${unseal_key}" >/dev/null
    fi

    info "Ensuring KV v2 and AppRole auth are enabled..."
    docker exec -e VAULT_ADDR="http://127.0.0.1:8201" -e VAULT_TOKEN="${root_token}" "${VAULT_CONTAINER}" \
        vault secrets enable -path=secret kv-v2 >/dev/null 2>&1 || true
    docker exec -e VAULT_ADDR="http://127.0.0.1:8201" -e VAULT_TOKEN="${root_token}" "${VAULT_CONTAINER}" \
        vault auth enable approle >/dev/null 2>&1 || true

    info "Ensuring JWT signing secret exists..."
    if ! docker exec -e VAULT_ADDR="http://127.0.0.1:8201" -e VAULT_TOKEN="${root_token}" "${VAULT_CONTAINER}" \
         vault kv get -field=value secret/gofr/config/jwt-signing-secret >/dev/null 2>&1; then
        local jwt_secret
        jwt_secret=$(openssl rand -hex 32)
        docker exec -e VAULT_ADDR="http://127.0.0.1:8201" -e VAULT_TOKEN="${root_token}" "${VAULT_CONTAINER}" \
            vault kv put secret/gofr/config/jwt-signing-secret value="${jwt_secret}" >/dev/null
    fi

    ok "Vault bootstrap complete"
}

ensure_auth_infra() {
    ensure_vault_image
    bootstrap_test_vault

    ensure_self_on_test_network

    info "Provisioning gofr-np AppRole credentials for runtime..."
    mkdir -p "${PROJECT_ROOT}/secrets/service_creds"

    export GOFR_VAULT_URL="$(_tools_vault_url)"
    uv run "${PROJECT_ROOT}/lib/gofr-common/scripts/setup_approle.py" \
        --project-root "${PROJECT_ROOT}" \
        --config "${PROJECT_ROOT}/config/gofr_approles.test.json"

    local creds_file="${PROJECT_ROOT}/secrets/service_creds/gofr-np.json"
    if [ ! -f "${creds_file}" ]; then
        fail "Missing AppRole credentials file: ${creds_file}"
    fi
    ok "AppRole credentials present: ${creds_file}"

    info "Syncing AppRole creds into docker volume (gofr-secrets-test)..."
    docker volume create gofr-secrets-test >/dev/null 2>&1 || true
    cat "${creds_file}" | docker run --rm -i \
        -v gofr-secrets-test:/run/gofr-secrets \
        alpine:3.20 sh -eu -c '
            mkdir -p /run/gofr-secrets/service_creds
            cat > /run/gofr-secrets/service_creds/gofr-np.json
            chmod 600 /run/gofr-secrets/service_creds/gofr-np.json || true
        '
    ok "Secrets volume populated"

    info "Minting a test JWT token (stored in Vault token store)..."
    local root_token
    root_token="$(cat "${PROJECT_ROOT}/secrets/vault_root_token")"
    uv run python "${PROJECT_ROOT}/scripts/ensure_test_tokens.py" \
        --vault-url "$(_tools_vault_url)" \
        --vault-token "${root_token}" \
        --vault-path-prefix "gofr/auth" \
        --jwt-secret-path "gofr/config/jwt-signing-secret" \
        --audience "gofr-api" \
        --group "public" \
        --out "${PROJECT_ROOT}/secrets/test_tokens.env"
    ok "Test token written: ${PROJECT_ROOT}/secrets/test_tokens.env"
}

IMAGE_NAME="gofr-np-prod:latest"
TEST_NETWORK="gofr-test-net"

CONTAINERS=("gofr-np-mcp-test" "gofr-np-mcpo-test" "gofr-np-web-test")

FORCE_BUILD=false
TEAR_DOWN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build) FORCE_BUILD=true; shift ;;
        --down)  TEAR_DOWN=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--build] [--down]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

tear_down() {
    info "Tearing down gofr-np test stack..."
    docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" down --remove-orphans -v 2>/dev/null || true

    docker rm -f \
        gofr-np-mcp-test \
        gofr-np-mcpo-test \
        gofr-np-web-test \
        gofr-np-vault-test \
        2>/dev/null || true
    ok "Stack removed."
}

if [ "${TEAR_DOWN}" = true ]; then
    tear_down
    exit 0
fi

echo ""
info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    fail "docker is not installed or not on PATH"
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker daemon is not running (or current user cannot connect)"
fi

if ! docker compose version &>/dev/null 2>&1; then
    fail "docker compose plugin is not installed (need 'docker compose')"
fi

ok "Docker + Compose available"

if ! docker network ls --format '{{.Name}}' | grep -q "^${TEST_NETWORK}$"; then
    info "Creating test network: ${TEST_NETWORK}"
    docker network create "${TEST_NETWORK}"
else
    ok "Network '${TEST_NETWORK}' exists"
fi

VERSION=$(grep -m1 '^version = ' "${PROJECT_ROOT}/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ "${FORCE_BUILD}" = true ] || ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
    if [ "${FORCE_BUILD}" = true ]; then
        info "Force-building image..."
    else
        info "Image '${IMAGE_NAME}' not found - building automatically..."
    fi

    docker build \
        -f "${DOCKERFILE}" \
        -t "gofr-np-prod:${VERSION}" \
        -t "${IMAGE_NAME}" \
        "${PROJECT_ROOT}"

    ok "Built gofr-np-prod:${VERSION} (also tagged :latest)"
else
    ok "Image '${IMAGE_NAME}' already exists (use --build to rebuild)"
fi

tear_down

ensure_auth_infra

info "Starting gofr-np test stack..."
set +e
docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" up -d
COMPOSE_UP_EXIT_CODE=$?
set -e

if [ ${COMPOSE_UP_EXIT_CODE} -ne 0 ]; then
    echo -e "${RED}=== docker compose up failed (exit code: ${COMPOSE_UP_EXIT_CODE}) ===${NC}"
    echo ""
    echo "--- docker compose ps ---"
    docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" ps 2>&1 || true
    echo ""

    for cname in "${CONTAINERS[@]}"; do
        echo "--- container logs (${cname}) ---"
        docker logs "${cname}" 2>&1 || true
        echo ""

        echo "--- health status (${cname}) ---"
        docker inspect --format='{{json .State.Health}}' "${cname}" 2>&1 || true
        echo ""
    done

    exit ${COMPOSE_UP_EXIT_CODE}
fi

MAX_RETRIES=20
RETRY_INTERVAL=3

info "Waiting for services to become healthy (max $((MAX_RETRIES * RETRY_INTERVAL))s)..."

all_healthy=false
for attempt in $(seq 1 ${MAX_RETRIES}); do
    healthy_count=0
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "missing")
        if [ "${status}" = "healthy" ]; then
            healthy_count=$((healthy_count + 1))
        fi
    done

    if [ ${healthy_count} -eq ${#CONTAINERS[@]} ]; then
        all_healthy=true
        break
    fi

    echo -n "  [${attempt}/${MAX_RETRIES}] healthy: ${healthy_count}/${#CONTAINERS[@]}"
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "?")
        echo -n "  ${cname##gofr-np-}=${status}"
    done
    echo ""
    sleep "${RETRY_INTERVAL}"
done

echo ""
if [ "${all_healthy}" = true ]; then
    ok "All gofr-np test services healthy"
else
    echo -e "${RED}=== Some services did NOT become healthy ===${NC}"
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "missing")
        case "${status}" in
            *healthy*) ok "${cname##gofr-np-}: ${status}" ;;
            *)         warn "${cname##gofr-np-}: ${status}" ;;
        esac
        if [ "${status}" != "healthy" ]; then
            echo "  --- full logs ---"
            docker logs "${cname}" 2>&1
        fi
    done
    exit 1
fi

echo ""
echo "======================================================================="
echo "  gofr-np test stack is running"
echo "======================================================================="
echo ""
HOST_ADDR="127.0.0.1"
if [ -f "/.dockerenv" ]; then
    HOST_ADDR="host.docker.internal"
fi
echo "  MCP Server:  http://${HOST_ADDR}:${GOFR_NP_MCP_PORT_TEST}/mcp"
echo "  MCPO Server: http://${HOST_ADDR}:${GOFR_NP_MCPO_PORT_TEST}/openapi.json"
echo "  Web Server:  http://${HOST_ADDR}:${GOFR_NP_WEB_PORT_TEST}/ping"
echo ""
echo "  Network:     ${TEST_NETWORK}"
