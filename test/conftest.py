"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import Config


@pytest.fixture(scope="function", autouse=True)
def test_data_dir(tmp_path):
    """
    Automatically provide a temporary data directory for each test

    This fixture:
    - Creates a unique temporary directory for each test
    - Configures app.config to use this directory
    - Cleans up after the test completes
    """
    # Set up test mode with temporary directory
    test_dir = tmp_path / "gofrnp_test_data"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (test_dir / "storage").mkdir(exist_ok=True)
    (test_dir / "auth").mkdir(exist_ok=True)

    # Configure for testing
    Config.set_test_mode(test_dir)

    yield test_dir

    Config.clear_test_mode()


@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path):
    """
    Provide a temporary storage directory for specific tests that need it

    Returns:
        Path object pointing to temporary storage directory
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture(scope="function")
def temp_auth_dir(tmp_path):
    """
    Provide a temporary auth directory for specific tests that need it

    Returns:
        Path object pointing to temporary auth directory
    """
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir


@pytest.fixture(scope="session")
def mcp_auth_token() -> str:
    """Bearer token for auth-enabled MCP integration tests.

    This token is minted by scripts/start-test-env.sh and exported by
    scripts/run_tests.sh as GOFR_NP_TEST_TOKEN.
    """

    token = os.environ.get("GOFR_NP_TEST_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Missing GOFR_NP_TEST_TOKEN. Run tests via ./scripts/run_tests.sh --integration or --all "
            "so the test stack bootstraps Vault and mints a token."
        )
    return token


@pytest.fixture(scope="session")
def mcp_auth_args(mcp_auth_token: str) -> dict:
    """Tool-call arguments fragment that supplies auth to MCP routing."""

    return {"auth_token": mcp_auth_token}


# ============================================================================
# MOCK IMAGE SERVER FOR TESTING
# ============================================================================


@pytest.fixture(scope="function")
def image_server():
    """
    Provide a lightweight HTTP server for serving test images.

    The server serves files from test/mock/data directory on port 8765.
    Use image_server.get_url(filename) to get the full URL for a test image.

    Usage:
        def test_image_download(image_server):
            url = image_server.get_url("graph.png")
            # url is "http://localhost:8765/graph.png"
            # Make requests to this URL

    Returns:
        ImageServer: Server instance with start(), stop(), and get_url() methods
    """
    import sys
    from pathlib import Path

    # Add test directory to path for imports
    test_dir = Path(__file__).parent
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    from mock.image_server import ImageServer  # type: ignore[import-not-found]

    server = ImageServer(port=8765)
    server.start()

    yield server

    server.stop()
