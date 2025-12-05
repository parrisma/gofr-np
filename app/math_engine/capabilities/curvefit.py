"""Curve Fitting Capability.

Provides robust curve fitting and model selection using NumPy and TensorFlow.
Automatically selects the best model complexity and handles outliers.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass

# Suppress TensorFlow logging
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

# Disable TensorFlow warnings
tf.get_logger().setLevel("ERROR")

from app.logger import session_logger as logger  # noqa: E402
from app.logger.decorators import log_execution_time  # noqa: E402
from app.math_engine.base import MathCapability, MathResult, ToolDefinition  # noqa: E402
from app.exceptions import InvalidInputError  # noqa: E402


@dataclass
class FitResult:
    """Internal result of a single model fit."""
    model_type: str
    params: List[float]
    r_squared: float
    rmse: float
    aic: float
    equation: str
    predict_fn: Callable[[Union[float, List[float]]], List[float]]


class CurveFitCapability(MathCapability):
    """Curve fitting with automatic model selection and validation."""

    @property
    def name(self) -> str:
        return "curvefit"

    @property
    def description(self) -> str:
        return "Robust curve fitting with automatic model selection and outlier detection"

    def __init__(self):
        """Initialize the curve fitting capability."""
        logger.info("CurveFitCapability initialized")
        self._fitted_models: Dict[str, FitResult] = {}

    def get_tools(self) -> List[ToolDefinition]:
        """Return tool definitions for curve fitting."""
        return [
            ToolDefinition(
                name="curve_fit",
                description=(
                    "Fit a mathematical model to X, Y data points to find the underlying relationship. "
                    "Use this tool to discover equations, trends, or physical laws from data. "
                    "\n\n"
                    "CAPABILITIES:\n"
                    "- Automatic Model Selection: Compares Polynomial, Exponential, Logarithmic, Power, and Sigmoid models to find the best fit.\n"
                    "- Robustness: Automatically detects and excludes outliers (bad data points) to prevent skewed results.\n"
                    "- Quality Metrics: Returns R² (accuracy), RMSE (error), and AIC (complexity penalty).\n"
                    "\n"
                    "WHEN TO USE:\n"
                    "- 'Find the equation for this data'\n"
                    "- 'What is the trend?'\n"
                    "- 'Extrapolate/Forecast future values' (use curve_fit then curve_predict)\n"
                    "- 'Does this data follow a power law or exponential growth?'\n"
                    "\n"
                    "MODEL TYPES (optional 'model_type' param):\n"
                    "- 'auto': (Default) Tries all and picks the best.\n"
                    "- 'polynomial': Linear (deg=1), Quadratic (deg=2), etc. Good for general trends.\n"
                    "- 'exponential': Growth/Decay (y = a * e^(bx) + c). Good for population, radioactive decay.\n"
                    "- 'logarithmic': Diminishing returns (y = a + b * ln(x)).\n"
                    "- 'power': Scaling laws (y = a * x^b). Physics/Biology relationships.\n"
                    "- 'sigmoid': S-curves (Logistic). Growth with saturation/limits.\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "equation": "y = 2.5 * x^2 + 1.0",\n'
                    '  "model_type": "polynomial_deg2",\n'
                    '  "quality": {"r_squared": 0.99, ...},\n'
                    '  "model_id": "..." (use this ID with curve_predict)\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "X coordinates of data points"
                        },
                        "y": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Y coordinates of data points"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["auto", "polynomial", "exponential", "logarithmic", "power", "sigmoid"],
                            "default": "auto",
                            "description": "Type of model to fit (default: auto-select best)"
                        },
                        "degree": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Polynomial degree (only for model_type='polynomial')"
                        }
                    },
                    "required": ["x", "y"]
                },
                handler_name="handle_fit"
            ),
            ToolDefinition(
                name="curve_predict",
                description="Predict Y values for new X values using a previously fitted model.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of the fitted model (returned by curve_fit)"
                        },
                        "x": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "X values to predict"
                        }
                    },
                    "required": ["model_id", "x"]
                },
                handler_name="handle_predict"
            )
        ]

    @log_execution_time
    def handle(self, tool_name: str, arguments: Dict[str, Any]) -> MathResult:
        """Route tool invocation to appropriate handler."""
        if tool_name == "curve_fit":
            return self.handle_fit(arguments)
        elif tool_name == "curve_predict":
            return self.handle_predict(arguments)
        else:
            raise InvalidInputError(f"Unknown tool: {tool_name}")

    def handle_fit(self, arguments: Dict[str, Any]) -> MathResult:
        """Handle curve_fit tool."""
        x_in = arguments.get("x")
        y_in = arguments.get("y")
        model_type = arguments.get("model_type", "auto")
        degree = arguments.get("degree")

        if not x_in or not y_in:
            raise InvalidInputError("Both 'x' and 'y' arrays are required")
        
        if len(x_in) != len(y_in):
            raise InvalidInputError(f"Input arrays must have same length. Got x={len(x_in)}, y={len(y_in)}")
        
        if len(x_in) < 3:
            raise InvalidInputError("At least 3 data points are required for curve fitting")

        # Convert to numpy arrays
        x = np.array(x_in, dtype=np.float64)
        y = np.array(y_in, dtype=np.float64)

        # Remove NaNs or Infs
        mask = np.isfinite(x) & np.isfinite(y)
        if not np.all(mask):
            x = x[mask]
            y = y[mask]
            if len(x) < 3:
                raise InvalidInputError("Too many invalid points (NaN/Inf)")

        # 1. Outlier Detection (Robust Z-score on residuals of a simple linear fit)
        # We do a quick linear fit to find obvious outliers
        p_init = np.polyfit(x, y, 1)
        y_pred_init = np.polyval(p_init, x)
        residuals = np.abs(y - y_pred_init)
        mad = np.median(residuals)
        if mad > 1e-9:
            modified_z_score = 0.6745 * residuals / mad
            # Threshold of 3.5 is standard for modified Z-score
            clean_mask = modified_z_score < 3.5
            
            # Only remove if we still have enough points
            if np.sum(clean_mask) >= 3:
                x_clean = x[clean_mask]
                y_clean = y[clean_mask]
            else:
                x_clean, y_clean = x, y
        else:
            x_clean, y_clean = x, y

        # 2. Model Selection / Fitting
        best_fit: Optional[FitResult] = None
        
        candidates = []
        
        if model_type == "auto" or model_type == "polynomial":
            # Try polynomials from degree 1 to min(10, len-2)
            max_deg = degree if degree else min(10, len(x_clean) - 2)
            min_deg = degree if degree else 1
            
            for d in range(min_deg, max_deg + 1):
                candidates.append(self._fit_polynomial(x_clean, y_clean, d))

        if model_type == "auto" or model_type == "exponential":
            candidates.append(self._fit_exponential(x_clean, y_clean))
            
        if model_type == "auto" or model_type == "logarithmic":
            candidates.append(self._fit_logarithmic(x_clean, y_clean))
            
        if model_type == "auto" or model_type == "power":
            candidates.append(self._fit_power(x_clean, y_clean))
            
        if model_type == "auto" or model_type == "sigmoid":
            candidates.append(self._fit_sigmoid(x_clean, y_clean))

        # Filter failed fits
        valid_candidates = [c for c in candidates if c is not None]
        
        if not valid_candidates:
            raise InvalidInputError("Could not fit any model to the data")

        # Select best by AIC (Akaike Information Criterion) to balance fit vs complexity
        # Lower AIC is better
        best_fit = min(valid_candidates, key=lambda c: c.aic)
        assert best_fit is not None

        # Store model for prediction
        import uuid
        model_id = f"fit_{uuid.uuid4().hex[:8]}"
        self._fitted_models[model_id] = best_fit

        return MathResult(
            result={
                "model_id": model_id,
                "model_type": best_fit.model_type,
                "equation": best_fit.equation,
                "parameters": best_fit.params,
                "quality": {
                    "r_squared": round(best_fit.r_squared, 4),
                    "rmse": round(best_fit.rmse, 4),
                    "aic": round(best_fit.aic, 2)
                },
                "data_points": len(x_clean),
                "outliers_removed": len(x) - len(x_clean)
            },
            shape=[],
            dtype="object"
        )

    def handle_predict(self, arguments: Dict[str, Any]) -> MathResult:
        """Handle curve_predict tool."""
        model_id = arguments.get("model_id")
        x_in = arguments.get("x")

        if not model_id or x_in is None:
            raise InvalidInputError("model_id and x are required")

        if model_id not in self._fitted_models:
            raise InvalidInputError(f"Model '{model_id}' not found. It may have expired or never existed.")

        fit = self._fitted_models[model_id]
        
        # Predict
        try:
            y_pred = fit.predict_fn(x_in)
        except Exception as e:
            raise InvalidInputError(f"Prediction failed: {str(e)}")

        return MathResult(
            result=y_pred,
            shape=[len(y_pred)],
            dtype="float64"
        )

    # --- Fitting Implementations ---

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, n_params: int) -> Tuple[float, float, float]:
        """Calculate R², RMSE, and AIC."""
        n = len(y_true)
        residuals = y_true - y_pred
        sse = np.sum(residuals**2)
        
        # RMSE
        rmse = np.sqrt(sse / n)
        
        # R-squared
        sst = np.sum((y_true - np.mean(y_true))**2)
        if sst < 1e-10:
            r_sq = 0.0 # Constant line
        else:
            r_sq = 1 - (sse / sst)
            
        # AIC (assuming normal errors)
        # AIC = n * ln(SSE/n) + 2k
        if sse < 1e-10:
            aic = -np.inf
        else:
            aic = n * np.log(sse / n) + 2 * n_params
            
        return r_sq, rmse, aic

    def _fit_polynomial(self, x: np.ndarray, y: np.ndarray, degree: int) -> Optional[FitResult]:
        """Fit polynomial of given degree using NumPy."""
        try:
            coeffs = np.polyfit(x, y, degree)
            y_pred = np.polyval(coeffs, x)
            
            r_sq, rmse, aic = self._calculate_metrics(y, y_pred, degree + 1)
            
            # Format equation
            terms = []
            for i, c in enumerate(coeffs):
                power = degree - i
                if abs(c) < 1e-10:
                    continue
                
                c_str = f"{c:.4g}"
                if power == 0:
                    terms.append(c_str)
                elif power == 1:
                    terms.append(f"{c_str}x")
                else:
                    terms.append(f"{c_str}x^{power}")
            
            eq = "y = " + " + ".join(terms).replace("+ -", "- ")
            
            # Capture coeffs for closure
            c_list = coeffs.tolist()
            
            return FitResult(
                model_type=f"polynomial_deg{degree}",
                params=c_list,
                r_squared=r_sq,
                rmse=rmse,
                aic=aic,
                equation=eq,
                predict_fn=lambda x_new: np.polyval(c_list, x_new).tolist()
            )
        except Exception:
            return None

    def _fit_exponential(self, x: np.ndarray, y: np.ndarray) -> Optional[FitResult]:
        """Fit y = a * exp(b * x) + c using TensorFlow."""
        try:
            # Smart initialization
            # 1. Estimate c
            # If curve is increasing convex, c < min(y). If decreasing convex, c < min(y).
            # Let's try to estimate c from 3 points: start, mid, end
            # But for robustness, let's just try a few guesses or use a heuristic.
            # Heuristic: c is slightly below min(y) if a > 0.
            
            y_min = np.min(y)
            y_max = np.max(y)
            y_range = y_max - y_min
            
            # Guess c is just below min y (assuming decay to asymptote or growth from asymptote)
            c_init = y_min - (y_range * 0.1) 
            
            # Linearize: ln(y - c) = ln(a) + bx
            # We need y - c > 0
            y_shifted = y - c_init
            if np.any(y_shifted <= 0):
                # Fallback
                c_init = y_min - 1.0
                y_shifted = y - c_init
            
            # Fit line to log(y_shifted)
            try:
                log_y = np.log(y_shifted)
                coeffs = np.polyfit(x, log_y, 1) # [b, ln(a)]
                b_init = coeffs[0]
                a_init = np.exp(coeffs[1])
            except Exception:
                # Fallback defaults
                a_init = 1.0
                b_init = 0.1
                c_init = 0.0

            # Use TF for optimization
            a = tf.Variable(a_init, dtype=tf.float64)
            b = tf.Variable(b_init, dtype=tf.float64)
            c = tf.Variable(c_init, dtype=tf.float64)
            
            x_tf = tf.constant(x, dtype=tf.float64)
            y_tf = tf.constant(y, dtype=tf.float64)
            
            optimizer = tf.optimizers.Adam(learning_rate=0.01)  # type: ignore
            
            # Training loop
            for _ in range(1000):
                with tf.GradientTape() as tape:
                    y_pred = a * tf.exp(b * x_tf) + c  # type: ignore
                    loss = tf.reduce_mean(tf.square(y_tf - y_pred))
                
                grads = tape.gradient(loss, [a, b, c])
                optimizer.apply_gradients(zip(grads, [a, b, c]))  # type: ignore
                
            # Extract values
            a_val, b_val, c_val = float(a.numpy()), float(b.numpy()), float(c.numpy())  # type: ignore
            
            y_pred_final = a_val * np.exp(b_val * x) + c_val
            r_sq, rmse, aic = self._calculate_metrics(y, y_pred_final, 3)
            
            return FitResult(
                model_type="exponential",
                params=[a_val, b_val, c_val],
                r_squared=r_sq,
                rmse=rmse,
                aic=aic,
                equation=f"y = {a_val:.4g} * e^({b_val:.4g}x) + {c_val:.4g}",
                predict_fn=lambda x_new: (a_val * np.exp(b_val * np.array(x_new)) + c_val).tolist()
            )
        except Exception:
            return None

    def _fit_logarithmic(self, x: np.ndarray, y: np.ndarray) -> Optional[FitResult]:
        """Fit y = a + b * ln(x)."""
        if np.any(x <= 0):
            return None
            
        try:
            # Linear fit on transformed x
            x_log = np.log(x)
            coeffs = np.polyfit(x_log, y, 1) # [b, a]
            b_val, a_val = coeffs[0], coeffs[1]
            
            y_pred = a_val + b_val * x_log
            r_sq, rmse, aic = self._calculate_metrics(y, y_pred, 2)
            
            return FitResult(
                model_type="logarithmic",
                params=[a_val, b_val],
                r_squared=r_sq,
                rmse=rmse,
                aic=aic,
                equation=f"y = {a_val:.4g} + {b_val:.4g} * ln(x)",
                predict_fn=lambda x_new: (a_val + b_val * np.log(np.array(x_new))).tolist()
            )
        except Exception:
            return None

    def _fit_power(self, x: np.ndarray, y: np.ndarray) -> Optional[FitResult]:
        """Fit y = a * x^b."""
        if np.any(x <= 0) or np.any(y <= 0):
            return None
            
        try:
            # Linear fit on log-log: ln(y) = ln(a) + b * ln(x)
            x_log = np.log(x)
            y_log = np.log(y)
            
            coeffs = np.polyfit(x_log, y_log, 1) # [b, ln(a)]
            b_val = coeffs[0]
            a_val = np.exp(coeffs[1])
            
            y_pred = a_val * np.power(x, b_val)
            r_sq, rmse, aic = self._calculate_metrics(y, y_pred, 2)
            
            return FitResult(
                model_type="power",
                params=[a_val, b_val],
                r_squared=r_sq,
                rmse=rmse,
                aic=aic,
                equation=f"y = {a_val:.4g} * x^{b_val:.4g}",
                predict_fn=lambda x_new: (a_val * np.power(np.array(x_new), b_val)).tolist()
            )
        except Exception:
            return None

    def _fit_sigmoid(self, x: np.ndarray, y: np.ndarray) -> Optional[FitResult]:
        """Fit y = L / (1 + e^(-k(x-x0))) + b using TensorFlow."""
        try:
            # Initial guesses
            L_init = np.max(y) - np.min(y)
            b_init = np.min(y)
            x0_init = np.median(x)
            k_init = 1.0
            
            L = tf.Variable(L_init, dtype=tf.float64)
            k = tf.Variable(k_init, dtype=tf.float64)
            x0 = tf.Variable(x0_init, dtype=tf.float64)
            b = tf.Variable(b_init, dtype=tf.float64)
            
            x_tf = tf.constant(x, dtype=tf.float64)
            y_tf = tf.constant(y, dtype=tf.float64)
            
            optimizer = tf.optimizers.Adam(learning_rate=0.05)  # type: ignore
            
            for _ in range(800):
                with tf.GradientTape() as tape:
                    y_pred = L / (1.0 + tf.exp(-k * (x_tf - x0))) + b  # type: ignore
                    loss = tf.reduce_mean(tf.square(y_tf - y_pred))
                
                grads = tape.gradient(loss, [L, k, x0, b])
                optimizer.apply_gradients(zip(grads, [L, k, x0, b]))  # type: ignore
                
            L_val, k_val, x0_val, b_val = float(L.numpy()), float(k.numpy()), float(x0.numpy()), float(b.numpy())  # type: ignore
            
            y_pred_final = L_val / (1.0 + np.exp(-k_val * (x - x0_val))) + b_val
            r_sq, rmse, aic = self._calculate_metrics(y, y_pred_final, 4)
            
            return FitResult(
                model_type="sigmoid",
                params=[L_val, k_val, x0_val, b_val],
                r_squared=r_sq,
                rmse=rmse,
                aic=aic,
                equation=f"y = {L_val:.4g} / (1 + e^(-{k_val:.4g}(x - {x0_val:.4g}))) + {b_val:.4g}",
                predict_fn=lambda x_new: (L_val / (1.0 + np.exp(-k_val * (np.array(x_new) - x0_val))) + b_val).tolist()
            )
        except Exception:
            return None
