# Tool Reference

Complete reference for every MCP tool exposed by **gofr-np**.

This document is derived from the current codebase (not runtime-scraped). For the exact, authoritative JSON Schema that clients should enforce, rely on the server’s `list_tools` response.

---

## Response Shape Notes

gofr-np has two response styles:

- **Plain object**: Some tools return an object directly (no wrapper). This is used when the internal `dtype` is `"object"`.
- **MathResult wrapper**: Some tools return a standard wrapper:

```json
{
  "result": <number|array|object>,
  "shape": [<int>...],
  "dtype": "float64"|"float32"|"bool"|...
}
```

Errors are returned as:

```json
{ "error": "..." }
```

---

## Discovery Tools

Tools for connectivity checks and basic discovery.

---

### ping

Health check. Returns `{status: "ok", service: "gofr-np"}` when the MCP server is reachable.

**Parameters:** none

**Returns (plain object):** `{status, service}`

---

## Element-wise Math (TensorFlow)

---

### math_compute

Perform element-wise mathematical operations on scalars or arrays with broadcasting.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| operation | string | yes | — | Operation name. See `math_list_operations` for categories, or use the operation enum from `list_tools`. |
| a | number \| array | yes | — | First operand (scalar or array). Nested arrays are allowed. |
| b | number \| array | no | — | Second operand for binary operations. Required when `operation` is binary. |
| precision | string | no | `"float64"` | Computation precision: `"float32"` or `"float64"`. |

**Returns (MathResult wrapper):** `{result, shape, dtype}`

**Common errors:** Missing required args, unknown operation, invalid shapes/types.

---

### math_list_operations

List all supported element-wise operations.

**Parameters:** none

**Returns (plain object):**

```json
{ "unary": ["abs", "exp", ...], "binary": ["add", "divide", ...] }
```

---

## Curve Fitting (NumPy + TensorFlow)

---

### curve_fit

Fit a model to X/Y data with automatic model selection and robust outlier handling.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| x | number[] | yes | — | X coordinates. |
| y | number[] | yes | — | Y coordinates (same length as `x`). |
| model_type | string | no | `"auto"` | One of: `auto`, `polynomial`, `exponential`, `logarithmic`, `power`, `sigmoid`. |
| degree | integer | no | — | Polynomial degree (only when `model_type="polynomial"`). |

**Returns (plain object):**

```json
{
  "model_id": "fit_...",
  "model_type": "polynomial_deg2"|"exponential"|...,
  "equation": "y = ...",
  "parameters": [1.23, 4.56],
  "quality": {"r_squared": 0.99, "rmse": 0.12, "aic": 10.2},
  "data_points": 12,
  "outliers_removed": 1
}
```

**Common errors:** too few points (<3), mismatched x/y lengths, all candidates fail.

---

### curve_predict

Predict Y values for new X values using a previously fitted model.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| model_id | string | yes | — | Model id returned by `curve_fit`. |
| x | number[] | yes | — | X values to predict. |

**Returns (MathResult wrapper):** `{result, shape, dtype}` where `result` is a numeric array.

**Common errors:** unknown/expired `model_id`, prediction failure.

---

## Financial Math (NumPy)

---

### financial_pv

Calculate the present value (PV) of cash flows using a scalar discount rate or a per-period yield curve.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| cash_flows | number[] | yes | — | Cash flow amounts. |
| rate | number \| number[] | yes | — | Scalar discount rate or yield curve array matching `cash_flows` length. |
| times | number[] | no | — | Time periods for cash flows; defaults to `1..N`. Must match length. |
| compounding | string | no | `"discrete"` | `"discrete"` or `"continuous"`. |

**Returns (plain object):**

```json
{
  "present_value": 123.45,
  "discounted_flows": [..],
  "total_undiscounted": 150.0,
  "effective_rates": [..],
  "times": [..]
}
```

---

### financial_convert_rate

Convert an interest rate between compounding conventions.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| rate | number | yes | — | Rate to convert. |
| from_freq | string | yes | — | Source frequency: `annual`, `semiannual`, `quarterly`, `monthly`, `weekly`, `daily`, `continuous` (also accepts `simple`). |
| to_freq | string | yes | — | Target frequency. |

**Returns (plain object):** `{converted_rate, effective_annual_rate, from_frequency, to_frequency}`

---

### financial_option_price

Price an option and compute Greeks using a Cox-Ross-Rubinstein (CRR) binomial tree.

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| S | number | yes | — | Spot price. |
| K | number | yes | — | Strike price. |
| T | number | yes | — | Time to maturity in years. |
| r | number | yes | — | Risk-free rate. |
| sigma | number | yes | — | Volatility. |
| option_type | string | yes | — | `call` or `put`. |
| exercise_style | string | yes | — | `european` or `american`. |
| steps | integer | no | `100` | Binomial steps. |
| q | number | no | `0.0` | Dividend yield (continuous). |
| dividends | object[] | no | — | Discrete dividends: `[{"amount": number, "time": number}, ...]`. |

**Returns (plain object):**

```json
{ "price": 1.23, "delta": 0.5, "gamma": 0.02, "theta": -0.01, "vega": 0.12, "rho": 0.08, "model": "Binomial CRR", "steps": 100 }
```

---

### financial_bond_price

Compute bond price and risk metrics (duration/convexity).

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| face_value | number | no | `100.0` | Face value. |
| coupon_rate | number | yes | — | Annual coupon rate (decimal). |
| years_to_maturity | number | yes | — | Years to maturity. |
| yield_to_maturity | number | yes | — | Yield to maturity (decimal). |
| frequency | integer | no | `2` | Coupons per year. |

**Returns (plain object):** `{price, macaulay_duration, modified_duration, convexity, face_value, coupon_rate, yield_to_maturity}`

---

### financial_technical_indicators

Compute technical analysis indicators over a price series (and a few scalar-style metrics).

**Parameters**

| Parameter | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| indicator | string | yes | — | Indicator name. The `list_tools` schema currently advertises: `sma`, `ema`, `rsi`, `pe_ratio`. |
| prices | number[] | conditionally | — | Required for time-series indicators (SMA/EMA/RSI/etc.). |
| params | object | no | `{}` | Indicator-specific params (e.g. windows, spans). |

**Implementation supports (in addition to schema):** `macd`, `bollinger`, `cross_signal`.

**Returns (plain object):** object containing indicator output arrays and metadata.

---

## Web Server (Stub)

The optional REST web server (separate from MCP) provides minimal endpoints.

### GET /
Returns `{service, status, message}`.

### GET /ping
Returns a standard ping payload.

### GET /health
Returns a standard health payload including whether auth is enabled.
