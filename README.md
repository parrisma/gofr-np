# GOFRNP: High-Performance Math & Financial MCP Server

GOFRNP is a robust Model Context Protocol (MCP) server designed to provide LLMs with high-precision mathematical, statistical, and financial computation capabilities. It bridges the gap between generative AI and deterministic computation using NumPy and TensorFlow.

## 🚀 Features

*   **High-Performance Math**: Element-wise operations, broadcasting, and matrix computations powered by TensorFlow and NumPy.
*   **Financial Analytics**:
    *   **Time Value of Money**: PV, NPV, IRR calculations with yield curve support.
    *   **Option Pricing**: Binomial Tree (CRR) models for American/European options with Greeks (Delta, Gamma, Theta, Vega, Rho).
    *   **Bond Pricing**: Duration (Macaulay/Modified), Convexity, and Yield to Maturity.
    *   **Technical Analysis**: SMA, EMA, RSI, MACD, Bollinger Bands.
*   **Curve Fitting**: Automatic model selection (Linear, Polynomial, Exponential, Sigmoid) with robust outlier detection.
*   **Enterprise Ready**:
    *   **Structured Logging**: JSON logging with session tracking for observability.
    *   **Error Recovery**: LLM-friendly error messages with actionable recovery strategies.
    *   **Security**: JWT-based authentication and granular permissions.

## 🏗️ Architecture

GOFRNP follows a modular architecture:

```mermaid
graph TD
    Client[LLM / Client] -->|MCP Protocol| MCPServer[MCP Server (Port 8020)]
    MCPServer --> Router[Tool Router]
    
    Router --> Cap1[Elementwise Capability]
    Router --> Cap2[Financial Capability]
    Router --> Cap3[CurveFit Capability]
    
    Cap1 --> TF[TensorFlow Engine]
    Cap2 --> NP[NumPy Engine]
    Cap3 --> TF
    Cap3 --> NP
    
    subgraph "Core Services"
        Logger[Structured Logger]
        Auth[Auth Service]
        Error[Error Mapper]
    end
    
    MCPServer -.-> Logger
    MCPServer -.-> Auth
    MCPServer -.-> Error
```

## 🛠️ Getting Started

### Prerequisites

*   Python 3.10+
*   `uv` (recommended) or `pip`

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/parrisma/gofr-np.git
    cd gofr-np
    ```

2.  **Install dependencies**:
    ```bash
    # Using uv (fastest)
    uv pip install -e .
    
    # Or using pip
    pip install -e .
    ```

### Running the Server

You can run the server components individually or using the provided scripts.

**Option 1: Using Scripts (Recommended)**
```bash
# Run all tests to verify installation
./scripts/run_tests.sh --all

# Start the development environment (requires Docker)
./docker/run-dev.sh
```

**Option 2: Manual Start**
```bash
# Start MCP Server (Port 8020)
python -m app.main_mcp --port 8020
```

## 📚 Documentation

Detailed documentation for each capability is available in the `docs/` directory:

*   **[Element-wise Operations](docs/elementwise.md)**: Vectorized math operations.
*   **[Financial Tools](docs/financial.md)**: TVM, Options, Bonds, Technicals.
*   **[Curve Fitting](docs/curvefit.md)**: Regression and forecasting.

## 🧪 Testing

GOFRNP maintains high test coverage. Use the test runner script:

```bash
# Run all tests
./scripts/run_tests.sh --all

# Run only unit tests
./scripts/run_tests.sh --unit

# Run boundary/edge case tests
./scripts/run_tests.sh --boundary

# Run with coverage report
./scripts/run_tests.sh --coverage
```

## 🤝 Contribution Guidelines

We welcome contributions! Please follow these steps:

1.  **Fork & Branch**: Create a feature branch (`feature/my-new-tool`).
2.  **Implement**: Add your capability in `app/math_engine/capabilities/`.
3.  **Test**: Add unit tests in `test/mcp/` covering happy paths and edge cases.
4.  **Document**: Update `docs/` and add tool definitions with rich descriptions.
5.  **Verify**: Run `./scripts/run_tests.sh --all` to ensure no regressions.
6.  **PR**: Submit a Pull Request with a clear description of changes.

### Coding Standards
*   Use **Type Hints** everywhere.
*   Use `GofrNpError` and its subclasses for exceptions.
*   Use `session_logger` for logging.
*   Follow the existing pattern for `ToolDefinition`.

## 🔍 Troubleshooting

**Common Issues:**

*   **TensorFlow Warnings**: You may see "CPU instructions" warnings. These are harmless and can be suppressed by setting `TF_CPP_MIN_LOG_LEVEL=2`.
*   **"Model not found"**: Curve fitting models are stored in memory. If the server restarts, models are lost. Re-run `curve_fit` to get a new `model_id`.
*   **Authentication Errors**: Ensure you are passing the correct JWT token in the headers if auth is enabled.

## 📄 License

[MIT License](LICENSE)
