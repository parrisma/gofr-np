# gofr-np

MCP Server scaffolded from gofr-np project.

## Quick Start

```bash
# Install dependencies
uv pip install -e .

# Start MCP server
python -m app.main_mcp --port 8020

# Start MCPO proxy (OpenAPI wrapper)
python -m app.main_mcpo --mcp-port 8020 --mcpo-port 8021

# Start web server
python -m app.main_web --port 8022
```

## Capabilities

The server exposes several mathematical and financial capabilities via MCP tools. Detailed documentation for each module is available below:

- **[Curve Fitting](docs/curvefit.md)**: Robust regression analysis, automatic model selection, and outlier detection.
- **[Element-wise Math](docs/elementwise.md)**: High-performance array computations with broadcasting (NumPy/TensorFlow).
- **[Financial Math](docs/financial.md)**: Tools for Time Value of Money (TVM), Option Pricing (Binomial), Bond Pricing, and Technical Analysis.

## Project Structure

```
app/
  auth/           # JWT authentication
  errors/         # Error mapping
  exceptions/     # Base exceptions
  logger/         # Pluggable logging
  mcp_server/     # MCP tools (implement here)
  mcpo/           # MCPO wrapper
  config.py       # Configuration
  main_mcp.py     # MCP entry point
  main_mcpo.py    # MCPO entry point
  main_web.py     # Web entry point
  web_server.py   # FastAPI web server
docker/           # Docker configuration
scripts/          # Build/run scripts
test/             # Test infrastructure
```

## Next Steps

1. Read `HANDOVER.md` for implementation guide
2. Implement tools in `app/mcp_server/mcp_server.py`
3. Add tests in `test/mcp/`
4. Run tests: `pytest test/`
