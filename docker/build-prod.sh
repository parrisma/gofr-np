#!/bin/bash
# Build gofr-np production image with auto-versioning
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Extract version from pyproject.toml
VERSION=$(grep -m1 '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

echo "Building gofr-np production image version: $VERSION"

# Build the image with version tag and latest
docker build \
    -f docker/Dockerfile.prod \
    -t gofr-np-prod:${VERSION} \
    -t gofr-np-prod:latest \
    .

echo ""
echo "Successfully built:"
echo "  - gofr-np-prod:${VERSION}"
echo "  - gofr-np-prod:latest"
echo ""
docker images | grep gofr-np-prod | head -5
