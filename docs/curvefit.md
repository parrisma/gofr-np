# Curve Fitting Capability

The Curve Fitting capability provides robust tools for finding mathematical models that best describe your data. It leverages `numpy` and `tensorflow` (where applicable) to perform regression analysis, automatically selecting the best model complexity and handling outliers.

## Tools

### `curve_fit`

Fits a mathematical model to X, Y data points to find the underlying relationship.

**Capabilities:**
- **Automatic Model Selection:** Compares Polynomial, Exponential, Logarithmic, Power, and Sigmoid models to find the best fit.
- **Robustness:** Automatically detects and excludes outliers (bad data points) using Modified Z-Score to prevent skewed results.
- **Quality Metrics:** Returns $R^2$ (accuracy), RMSE (error), and AIC (complexity penalty).

**Model Types:**
- `auto`: (Default) Tries all and picks the best based on AIC/RMSE.
- `polynomial`: Linear ($y = mx + c$), Quadratic ($y = ax^2 + bx + c$), etc.
- `exponential`: Growth/Decay ($y = a \cdot e^{bx} + c$).
- `logarithmic`: Diminishing returns ($y = a + b \cdot \ln(x)$).
- `power`: Scaling laws ($y = a \cdot x^b$).
- `sigmoid`: S-curves (Logistic function) ($y = \frac{L}{1 + e^{-k(x-x_0)}} + b$).

**Example Usage:**
```json
{
  "x": [1, 2, 3, 4, 5],
  "y": [2.1, 3.9, 8.2, 15.8, 32.1],
  "model_type": "exponential"
}
```

### `curve_predict`

Predicts Y values for new X values using a previously fitted model.

**Parameters:**
- `model_id`: The ID returned by a successful `curve_fit` call.
- `x`: Array of X values to predict.

**Example Usage:**
```json
{
  "model_id": "model_12345",
  "x": [6, 7, 8]
}
```
