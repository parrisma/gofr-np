"""Financial Math Capability.

Provides financial calculations including time value of money,
discounted cash flows, and yield curve analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

import numpy as np

from app.logger import session_logger as logger
from app.math_engine.base import MathCapability, MathResult, ToolDefinition


class FinancialCapability(MathCapability):
    """Financial calculations and analysis."""

    @property
    def name(self) -> str:
        return "financial"

    @property
    def description(self) -> str:
        return "Financial calculations including PV, NPV, and yield curve analysis"

    def __init__(self):
        """Initialize the financial capability."""
        logger.info("FinancialCapability initialized")

    def get_tools(self) -> List[ToolDefinition]:
        """Return tool definitions for financial operations."""
        return [
            ToolDefinition(
                name="financial_pv",
                description=(
                    "Calculate the Present Value (PV) of a series of cash flows. "
                    "Supports both constant discount rates and yield curves (term structures). "
                    "Can handle discrete or continuous compounding. "
                    "\n\n"
                    "WHEN TO USE:\n"
                    "- 'What is the value of these future payments today?'\n"
                    "- 'Discount these cash flows at 5%'\n"
                    "- 'Calculate PV given this yield curve'\n"
                    "\n"
                    "LIMITATIONS:\n"
                    "- Assumes simple years (no day count conventions like 30/360 or Actual/360).\n"
                    "- Yield curve interpolation is linear if rates are provided as a list.\n"
                    "\n"
                    "PARAMETERS:\n"
                    "- cash_flows: List of payment amounts\n"
                    "- times: List of time periods (years) for each flow. If omitted, assumes t=1, 2, 3...\n"
                    "- rate: Annual discount rate (e.g., 0.05 for 5%). Can be a single number or a list matching 'times' (yield curve).\n"
                    "- compounding: 'discrete' (default) or 'continuous'\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "present_value": 1234.56,\n'
                    '  "discounted_flows": [95.2, 90.7, ...], \n'
                    '  "total_undiscounted": 1500.0\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "cash_flows": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "List of cash flow amounts"
                        },
                        "rate": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "array", "items": {"type": "number"}}
                            ],
                            "description": "Discount rate (decimal, e.g. 0.05) or list of rates (yield curve)"
                        },
                        "times": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Time in years for each cash flow. Defaults to [1, 2, ... N]"
                        },
                        "compounding": {
                            "type": "string",
                            "enum": ["discrete", "continuous"],
                            "default": "discrete",
                            "description": "Compounding method"
                        }
                    },
                    "required": ["cash_flows", "rate"]
                },
                handler_name="handle_pv"
            ),
            ToolDefinition(
                name="financial_convert_rate",
                description=(
                    "Convert interest rates between different compounding frequencies. "
                    "Useful for comparing rates quoted with different terms (e.g., Annual vs Monthly vs Continuous). "
                    "\n\n"
                    "LIMITATIONS:\n"
                    "- Assumes 365 days for 'daily' compounding.\n"
                    "- Does not handle business day adjustments.\n"
                    "\n"
                    "PARAMETERS:\n"
                    "- rate: The input interest rate (decimal, e.g., 0.05 for 5%)\n"
                    "- from_freq: Frequency of the input rate ('simple', 'annual', 'semiannual', 'quarterly', 'monthly', 'weekly', 'daily', 'continuous')\n"
                    "- to_freq: Frequency to convert to (same options as above)\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "converted_rate": 0.04879, \n'
                    '  "effective_annual_rate": 0.05\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "rate": {
                            "type": "number",
                            "description": "Input interest rate (decimal)"
                        },
                        "from_freq": {
                            "type": "string",
                            "enum": ["simple", "annual", "semiannual", "quarterly", "monthly", "weekly", "daily", "continuous"],
                            "description": "Compounding frequency of input rate"
                        },
                        "to_freq": {
                            "type": "string",
                            "enum": ["simple", "annual", "semiannual", "quarterly", "monthly", "weekly", "daily", "continuous"],
                            "description": "Compounding frequency to convert to"
                        }
                    },
                    "required": ["rate", "from_freq", "to_freq"]
                },
                handler_name="handle_convert_rate"
            ),
            ToolDefinition(
                name="financial_option_price",
                description=(
                    "Calculate the price of an option using the Binomial Option Pricing Model (CRR). "
                    "Supports both European and American exercise styles, and Call/Put options. "
                    "This is a path-dependent model (lattice-based) suitable for American options. "
                    "\n\n"
                    "LIMITATIONS:\n"
                    "- Binomial model is an approximation. Accuracy improves with more 'steps' but increases computation time.\n"
                    "- Discrete dividends are handled via the Escrowed Dividend Model (spot price adjustment), which assumes dividends are known and fixed.\n"
                    "- Greeks (Delta, Gamma, etc.) are approximated from the tree or finite differences.\n"
                    "\n"
                    "PARAMETERS:\n"
                    "- S: Current spot price of the underlying asset\n"
                    "- K: Strike price of the option\n"
                    "- T: Time to maturity in years\n"
                    "- r: Risk-free interest rate (decimal, e.g., 0.05)\n"
                    "- q: Continuous dividend yield (decimal, e.g., 0.02). Default 0.\n"
                    "- dividends: List of discrete dividends [{'amount': 1.0, 'time': 0.5}, ...]. Optional.\n"
                    "- sigma: Volatility of the underlying asset (decimal, e.g., 0.20)\n"
                    "- option_type: 'call' or 'put'\n"
                    "- exercise_style: 'european' or 'american'\n"
                    "- steps: Number of time steps in the binomial tree (default: 100). Higher is more accurate but slower.\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "price": 10.50,\n'
                    '  "delta": 0.65,  // Approximate delta\n'
                    '  "gamma": 0.02,  // Approximate gamma\n'
                    '  "theta": -0.05, // Approximate theta (1 day)\n'
                    '  "vega": 0.20,   // Approximate vega (1% vol change)\n'
                    '  "rho": 0.15     // Approximate rho (1% rate change)\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "S": {"type": "number", "description": "Spot price"},
                        "K": {"type": "number", "description": "Strike price"},
                        "T": {"type": "number", "description": "Time to maturity (years)"},
                        "r": {"type": "number", "description": "Risk-free rate"},
                        "q": {"type": "number", "default": 0.0, "description": "Dividend yield"},
                        "dividends": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "amount": {"type": "number"},
                                    "time": {"type": "number"}
                                },
                                "required": ["amount", "time"]
                            },
                            "description": "Discrete dividends"
                        },
                        "sigma": {"type": "number", "description": "Volatility"},
                        "option_type": {
                            "type": "string",
                            "enum": ["call", "put"],
                            "description": "Option type"
                        },
                        "exercise_style": {
                            "type": "string",
                            "enum": ["european", "american"],
                            "description": "Exercise style"
                        },
                        "steps": {
                            "type": "integer",
                            "default": 100,
                            "description": "Number of tree steps"
                        }
                    },
                    "required": ["S", "K", "T", "r", "sigma", "option_type", "exercise_style"]
                },
                handler_name="handle_option_price"
            ),
            ToolDefinition(
                name="financial_bond_price",
                description=(
                    "Calculate the price and risk metrics of a fixed-rate bond. "
                    "Computes Price, Macaulay Duration, Modified Duration, and Convexity. "
                    "\n\n"
                    "LIMITATIONS:\n"
                    "- Assumes a fixed coupon rate and single yield to maturity (flat yield curve).\n"
                    "- Does not handle day count conventions (assumes integer periods).\n"
                    "- Assumes face value is paid at maturity along with the last coupon.\n"
                    "\n"
                    "PARAMETERS:\n"
                    "- face_value: Par value of the bond (default 100)\n"
                    "- coupon_rate: Annual coupon rate (decimal, e.g., 0.05)\n"
                    "- frequency: Coupon frequency per year (1=annual, 2=semi, 4=quarterly)\n"
                    "- years_to_maturity: Time to maturity in years\n"
                    "- yield_to_maturity: Annual yield to maturity (decimal, e.g., 0.06)\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "price": 95.50,\n'
                    '  "macaulay_duration": 4.2,\n'
                    '  "modified_duration": 4.0,\n'
                    '  "convexity": 20.5\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "face_value": {"type": "number", "default": 100.0, "description": "Face value"},
                        "coupon_rate": {"type": "number", "description": "Annual coupon rate"},
                        "frequency": {"type": "integer", "default": 2, "description": "Coupons per year"},
                        "years_to_maturity": {"type": "number", "description": "Years to maturity"},
                        "yield_to_maturity": {"type": "number", "description": "Yield to maturity (YTM)"}
                    },
                    "required": ["coupon_rate", "years_to_maturity", "yield_to_maturity"]
                },
                handler_name="handle_bond_price"
            ),
            ToolDefinition(
                name="financial_technical_indicators",
                description=(
                    "Calculate common technical analysis indicators for equity trading. "
                    "Supports Moving Averages (SMA, EMA), RSI, MACD, Bollinger Bands, and PE Ratio. "
                    "Also detects 'Golden Cross' and 'Death Cross' signals. "
                    "\n\n"
                    "LIMITATIONS:\n"
                    "- Requires sufficient historical data length (e.g., >200 points for 200-day SMA).\n"
                    "- RSI uses Wilder's Smoothing method.\n"
                    "- MACD uses standard 12/26/9 EMA settings unless overridden.\n"
                    "- Returns NaN for initial periods where data is insufficient.\n"
                    "\n"
                    "INDICATORS:\n"
                    "- 'sma': Simple Moving Average. Requires 'window'.\n"
                    "- 'ema': Exponential Moving Average. Requires 'window'.\n"
                    "- 'rsi': Relative Strength Index. Requires 'window' (default 14).\n"
                    "- 'macd': Moving Average Convergence Divergence. Requires 'fast' (12), 'slow' (26), 'signal' (9).\n"
                    "- 'bollinger': Bollinger Bands. Requires 'window' (20), 'num_std' (2).\n"
                    "- 'pe_ratio': Price-to-Earnings Ratio. Requires 'price' and 'earnings'.\n"
                    "- 'cross_signal': Detects Golden/Death Cross. Requires 'short_window' (50), 'long_window' (200).\n"
                    "\n"
                    "PARAMETERS:\n"
                    "- indicator: The name of the indicator (see above)\n"
                    "- prices: List of historical prices (required for most indicators)\n"
                    "- params: Dictionary of indicator-specific parameters (e.g., {'window': 20})\n"
                    "\n"
                    "RETURNS:\n"
                    "{\n"
                    '  "values": [100.1, 100.5, ...], // Indicator values\n'
                    '  "signal": "death_cross",       // For cross_signal\n'
                    '  "metadata": {...}              // Additional info\n'
                    "}"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "indicator": {
                            "type": "string",
                            "enum": ["sma", "ema", "rsi", "macd", "bollinger", "pe_ratio", "cross_signal"],
                            "description": "Indicator to calculate"
                        },
                        "prices": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Historical price series (ordered oldest to newest)"
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the indicator",
                            "additionalProperties": True
                        }
                    },
                    "required": ["indicator"]
                },
                handler_name="handle_technical_indicators"
            )
        ]

    def handle(self, tool_name: str, arguments: Dict[str, Any]) -> MathResult:
        """Route tool invocation to appropriate handler."""
        if tool_name == "financial_pv":
            return self.handle_pv(arguments)
        elif tool_name == "financial_convert_rate":
            return self.handle_convert_rate(arguments)
        elif tool_name == "financial_option_price":
            return self.handle_option_price(arguments)
        elif tool_name == "financial_bond_price":
            return self.handle_bond_price(arguments)
        elif tool_name == "financial_technical_indicators":
            return self.handle_technical_indicators(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _get_frequency(self, freq_str: str) -> float:
        """Convert frequency string to number of periods per year."""
        freq_map = {
            "simple": 1.0,
            "annual": 1.0,
            "semiannual": 2.0,
            "quarterly": 4.0,
            "monthly": 12.0,
            "weekly": 52.0,
            "daily": 365.0,
        }
        return freq_map.get(freq_str, 0.0)  # 0.0 indicates continuous or invalid

    def handle_convert_rate(self, arguments: Dict[str, Any]) -> MathResult:
        """Handle financial_convert_rate tool."""
        rate = arguments.get("rate")
        from_freq_str = arguments.get("from_freq")
        to_freq_str = arguments.get("to_freq")

        if rate is None or from_freq_str is None or to_freq_str is None:
            raise ValueError("rate, from_freq, and to_freq are required")

        r = float(rate)
        
        # Validate rate for discrete compounding
        if from_freq_str != "continuous" and r <= -1.0:
            raise ValueError("Rate must be greater than -1.0 (-100%) for discrete compounding")

        # 1. Convert to Effective Annual Rate (EAR)
        if from_freq_str == "continuous":
            ear = np.exp(r) - 1.0
        else:
            n_from = self._get_frequency(from_freq_str)
            if n_from <= 0:
                raise ValueError(f"Invalid from_freq: {from_freq_str}")
            ear = np.power(1.0 + r / n_from, n_from) - 1.0

        # 2. Convert EAR to target rate
        if to_freq_str == "continuous":
            if ear <= -1.0:
                 # Should not happen if input r > -1, but good for safety
                 raise ValueError("Effective annual rate <= -1.0 cannot be converted to continuous")
            target_rate = np.log(1.0 + ear)
        else:
            n_to = self._get_frequency(to_freq_str)
            if n_to <= 0:
                raise ValueError(f"Invalid to_freq: {to_freq_str}")
            target_rate = n_to * (np.power(1.0 + ear, 1.0 / n_to) - 1.0)

        return MathResult(
            result={
                "converted_rate": float(target_rate),
                "effective_annual_rate": float(ear),
                "from_frequency": from_freq_str,
                "to_frequency": to_freq_str
            },
            shape=[],
            dtype="object"
        )

    def handle_pv(self, arguments: Dict[str, Any]) -> MathResult:
        """Handle financial_pv tool."""
        cash_flows = arguments.get("cash_flows")
        rate = arguments.get("rate")
        times = arguments.get("times")
        compounding = arguments.get("compounding", "discrete")

        if cash_flows is None or rate is None:
            raise ValueError("cash_flows and rate are required")

        # Convert to numpy arrays
        cf = np.array(cash_flows, dtype=np.float64)
        n = len(cf)

        # Handle times
        if times is None:
            # Default to 1, 2, 3... N
            t = np.arange(1, n + 1, dtype=np.float64)
        else:
            t = np.array(times, dtype=np.float64)
            if len(t) != n:
                raise ValueError(f"Length of 'times' ({len(t)}) must match 'cash_flows' ({n})")

        # Handle rate
        if isinstance(rate, list):
            r = np.array(rate, dtype=np.float64)
            if len(r) != n:
                raise ValueError(f"Length of 'rate' yield curve ({len(r)}) must match 'cash_flows' ({n})")
        else:
            # Scalar rate broadcast to all times
            r = float(rate)

        # Calculate Discount Factors
        if compounding == "continuous":
            # DF = e^(-r*t)
            df = np.exp(-r * t)
        else:
            # Discrete: DF = 1 / (1 + r)^t
            df = 1.0 / np.power(1.0 + r, t)

        # Calculate PVs
        discounted_flows = cf * df
        total_pv = np.sum(discounted_flows)

        return MathResult(
            result={
                "present_value": float(total_pv),
                "discounted_flows": discounted_flows.tolist(),
                "total_undiscounted": float(np.sum(cf)),
                "effective_rates": r.tolist() if isinstance(r, np.ndarray) else [r] * n,
                "times": t.tolist()
            },
            shape=[],
            dtype="object"
        )

    def _calculate_binomial_price(
        self, S, K, T, r, q, dividends, sigma, option_type, style, N, return_greeks=False
    ):
        """Internal method to calculate price and optionally tree-based Greeks."""
        if T <= 0:
            if option_type == "call":
                val = max(0.0, S - K)
            else:
                val = max(0.0, K - S)
            return (val, 0.0, 0.0, 0.0) if return_greeks else val

        # Handle Discrete Dividends (Escrowed Dividend Model)
        valid_divs = [d for d in dividends if 0 < d["time"] <= T]
        pv_divs = sum(d["amount"] * np.exp(-r * d["time"]) for d in valid_divs)
        
        S_tree = S - pv_divs
        if S_tree <= 0:
            raise ValueError("Present value of dividends exceeds spot price")

        # 1. Setup Tree Parameters
        dt = T / N
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp((r - q) * dt) - d) / (u - d)
        discount = np.exp(-r * dt)

        # 2. Initialize Asset Prices at Maturity
        i_vals = np.arange(N + 1)
        tree_prices = S_tree * (u ** (N - i_vals)) * (d ** i_vals)
        asset_prices = tree_prices

        # 3. Initialize Option Values at Maturity
        if option_type == "call":
            option_values = np.maximum(0, asset_prices - K)
        else:
            option_values = np.maximum(0, K - asset_prices)

        # 4. Backward Induction
        val_node_1_0 = 0.0
        val_node_1_1 = 0.0
        val_node_2_0 = 0.0
        val_node_2_1 = 0.0
        val_node_2_2 = 0.0

        for j in range(N - 1, -1, -1):
            t_current = j * dt
            pv_remaining = sum(
                div["amount"] * np.exp(-r * (div["time"] - t_current))
                for div in valid_divs if div["time"] > t_current
            )

            continuation = discount * (p * option_values[:-1] + (1 - p) * option_values[1:])
            
            if style == "american":
                i_current = np.arange(j + 1)
                S_tree_current = S_tree * (u ** (j - i_current)) * (d ** i_current)
                S_current = S_tree_current + pv_remaining
                
                if option_type == "call":
                    intrinsic = np.maximum(0, S_current - K)
                else:
                    intrinsic = np.maximum(0, K - S_current)
                option_values = np.maximum(continuation, intrinsic)
            else:
                option_values = continuation
            
            if return_greeks:
                if j == 2:
                    val_node_2_0 = option_values[0]
                    val_node_2_1 = option_values[1]
                    val_node_2_2 = option_values[2]
                elif j == 1:
                    val_node_1_0 = option_values[0]
                    val_node_1_1 = option_values[1]

        price = option_values[0]

        if not return_greeks:
            return price

        # Calculate Tree Greeks (Delta, Gamma, Theta)
        t_1 = 1 * dt
        pv_rem_1 = sum(d["amount"] * np.exp(-r * (d["time"] - t_1)) for d in valid_divs if d["time"] > t_1)
        S_u = (S_tree * u) + pv_rem_1
        S_d = (S_tree * d) + pv_rem_1
        
        delta = (val_node_1_0 - val_node_1_1) / (S_u - S_d)

        t_2 = 2 * dt
        pv_rem_2 = sum(d["amount"] * np.exp(-r * (d["time"] - t_2)) for d in valid_divs if d["time"] > t_2)
        S_uu = (S_tree * u * u) + pv_rem_2
        S_ud = (S_tree) + pv_rem_2
        S_dd = (S_tree * d * d) + pv_rem_2
        
        delta_u = (val_node_2_0 - val_node_2_1) / (S_uu - S_ud)
        delta_d = (val_node_2_1 - val_node_2_2) / (S_ud - S_dd)
        
        h = 0.5 * (S_uu - S_dd)
        gamma = (delta_u - delta_d) / h

        theta_annual = (val_node_2_1 - price) / (2 * dt)
        theta_daily = theta_annual / 365.0

        return price, delta, gamma, theta_daily

    def handle_option_price(self, arguments: Dict[str, Any]) -> MathResult:
        """Calculate option price using Binomial Tree."""
        S = float(arguments["S"])
        K = float(arguments["K"])
        T = float(arguments["T"])
        r = float(arguments["r"])
        q = float(arguments.get("q", 0.0))
        dividends = arguments.get("dividends", [])
        sigma = float(arguments["sigma"])
        option_type = arguments["option_type"].lower()
        style = arguments["exercise_style"].lower()
        N = int(arguments.get("steps", 100))

        if S < 0:
            raise ValueError("Spot price (S) must be non-negative")
        if K < 0:
            raise ValueError("Strike price (K) must be non-negative")
        if sigma < 0:
            raise ValueError("Volatility (sigma) must be non-negative")
        if N < 1:
            raise ValueError("Steps must be at least 1")

        # 1. Base Calculation (Price + Tree Greeks)
        result_tuple = self._calculate_binomial_price(
            S, K, T, r, q, dividends, sigma, option_type, style, N, return_greeks=True
        )
        # Cast to tuple to satisfy type checker (it can't infer return type from bool arg)
        price, delta, gamma, theta = cast(Tuple[float, float, float, float], result_tuple)

        # 2. Vega (Bump Sigma)
        # dSigma = 1% relative or absolute? Usually absolute 0.01 or 0.0001.
        # Let's use 0.001 (0.1%)
        d_sigma = 0.001
        price_bump_sigma = self._calculate_binomial_price(
            S, K, T, r, q, dividends, sigma + d_sigma, option_type, style, N, return_greeks=False
        )
        # Ensure price_bump_sigma is a float
        if isinstance(price_bump_sigma, tuple):
            price_bump_sigma = price_bump_sigma[0]
            
        vega = (price_bump_sigma - price) / d_sigma * 0.01 # Scaled to 1% change

        # 3. Rho (Bump r)
        d_r = 0.001
        price_bump_r = self._calculate_binomial_price(
            S, K, T, r + d_r, q, dividends, sigma, option_type, style, N, return_greeks=False
        )
        # Ensure price_bump_r is a float
        if isinstance(price_bump_r, tuple):
            price_bump_r = price_bump_r[0]
            
        rho = (price_bump_r - price) / d_r * 0.01 # Scaled to 1% change

        return MathResult(
            result={
                "price": float(price),
                "delta": float(delta),
                "gamma": float(gamma),
                "theta": float(theta),
                "vega": float(vega),
                "rho": float(rho),
                "model": "Binomial CRR",
                "steps": N
            },
            shape=[],
            dtype="object"
        )

    def handle_bond_price(self, arguments: Dict[str, Any]) -> MathResult:
        """Calculate bond price and risk metrics."""
        face_value = float(arguments.get("face_value", 100.0))
        coupon_rate = float(arguments["coupon_rate"])
        frequency = int(arguments.get("frequency", 2))
        years = float(arguments["years_to_maturity"])
        ytm = float(arguments["yield_to_maturity"])

        if face_value < 0:
            raise ValueError("Face value must be non-negative")
        if frequency <= 0:
            raise ValueError("Frequency must be positive")
        if years <= 0:
            raise ValueError("Years to maturity must be positive")
        if ytm <= -1.0:
            raise ValueError("Yield to maturity must be greater than -1.0 (-100%)")

        # Number of periods
        n_periods = int(years * frequency)
        # Rate per period
        r = ytm / frequency
        # Coupon per period
        c = (coupon_rate * face_value) / frequency

        # Time periods array (1 to N)
        t = np.arange(1, n_periods + 1, dtype=np.float64)

        # Discount factors: 1 / (1+r)^t
        df = 1.0 / np.power(1.0 + r, t)

        # Cash flows: Coupons
        cash_flows = np.full(n_periods, c)
        # Add face value to last cash flow
        cash_flows[-1] += face_value

        # Price = sum(CF * DF)
        pv_flows = cash_flows * df
        price = np.sum(pv_flows)

        # Macaulay Duration
        # D_mac = (1/Price) * sum(t * CF / (1+r)^t) / frequency
        # Note: t here is period number. To get years, we divide by frequency at the end.
        weighted_flows = t * pv_flows
        mac_duration_periods = np.sum(weighted_flows) / price
        mac_duration_years = mac_duration_periods / frequency

        # Modified Duration
        # D_mod = D_mac / (1 + ytm/freq)
        mod_duration = mac_duration_years / (1.0 + r)

        # Convexity
        # C = (1 / (Price * (1+r)^2)) * sum(t*(t+1) * CF / (1+r)^t) / frequency^2
        # t is period number
        convexity_term = t * (t + 1) * pv_flows
        convexity = (np.sum(convexity_term) / (price * np.power(1.0 + r, 2))) / (frequency * frequency)

        return MathResult(
            result={
                "price": float(price),
                "macaulay_duration": float(mac_duration_years),
                "modified_duration": float(mod_duration),
                "convexity": float(convexity),
                "face_value": face_value,
                "coupon_rate": coupon_rate,
                "yield_to_maturity": ytm
            },
            shape=[],
            dtype="object"
        )

    def handle_technical_indicators(self, arguments: Dict[str, Any]) -> MathResult:
        """Handle technical analysis indicators."""
        indicator = arguments.get("indicator")
        prices_list = arguments.get("prices", [])
        params = arguments.get("params", {})

        if indicator == "pe_ratio":
            price = params.get("price")
            earnings = params.get("earnings")
            if price is None or earnings is None:
                # Try to get price from last element of prices list if available
                if prices_list and price is None:
                    price = prices_list[-1]
                
                if price is None or earnings is None:
                    raise ValueError("pe_ratio requires 'price' and 'earnings' in params")
            
            if earnings == 0:
                raise ValueError("Earnings cannot be zero for PE ratio")
            
            return MathResult({"pe_ratio": float(price) / float(earnings)}, [], "object")

        if not prices_list:
            raise ValueError(f"Indicator '{indicator}' requires 'prices' list")

        prices = np.array(prices_list, dtype=np.float64)
        n = len(prices)

        if indicator == "sma":
            window = int(params.get("window", 14))
            if window <= 0:
                raise ValueError("Window must be positive")
            if n < window:
                raise ValueError(f"Not enough data for SMA (window={window}, data={n})")
            
            # Simple Moving Average
            weights = np.ones(window) / window
            sma = np.convolve(prices, weights, mode="valid")
            # Pad with NaNs or just return valid? Let's return valid and metadata about offset
            # To match length, we can prepend NaNs
            full_sma = np.full(n, np.nan)
            full_sma[window-1:] = sma
            
            return MathResult({
                "values": full_sma.tolist(),
                "indicator": "sma",
                "window": window
            }, [], "object")

        elif indicator == "ema":
            window = int(params.get("window", 14))
            if window <= 0:
                raise ValueError("Window must be positive")
            if n < window:
                raise ValueError(f"Not enough data for EMA (window={window}, data={n})")
            
            # Exponential Moving Average
            # alpha = 2 / (N + 1)
            alpha = 2.0 / (window + 1.0)
            ema = np.zeros_like(prices)
            ema[0] = prices[0] # Seed with first price (or SMA of first N)
            # Better to seed with SMA of first window? Standard is usually SMA of first window.
            # Let's stick to simple recursive for now or pandas-like ewm.
            # Pandas ewm(adjust=False)
            
            # Vectorized EMA is hard, iterative is fine for reasonable N
            ema[0] = prices[0]
            for i in range(1, n):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
                
            return MathResult({
                "values": ema.tolist(),
                "indicator": "ema",
                "window": window
            }, [], "object")

        elif indicator == "rsi":
            window = int(params.get("window", 14))
            if window <= 0:
                raise ValueError("Window must be positive")
            if n < window + 1:
                raise ValueError(f"Not enough data for RSI (window={window}, data={n})")
            
            deltas = np.diff(prices)
            gains = np.maximum(deltas, 0.0)
            losses = -np.minimum(deltas, 0.0)
            
            # Wilder's Smoothing (RMA) is standard for RSI, which is EMA(alpha=1/N)
            # Not standard EMA(alpha=2/(N+1))
            alpha = 1.0 / window
            
            avg_gain = np.zeros(n)
            avg_loss = np.zeros(n)
            
            # Initial average
            avg_gain[window] = np.mean(gains[:window])
            avg_loss[window] = np.mean(losses[:window])
            
            for i in range(window + 1, n):
                avg_gain[i] = (avg_gain[i-1] * (window - 1) + gains[i-1]) / window
                avg_loss[i] = (avg_loss[i-1] * (window - 1) + losses[i-1]) / window
                
            rs = np.zeros(n)
            rsi = np.zeros(n)
            
            # Avoid division by zero
            mask = avg_loss > 0
            rs[mask] = avg_gain[mask] / avg_loss[mask]
            rsi[mask] = 100.0 - (100.0 / (1.0 + rs[mask]))
            rsi[~mask] = 100.0 # If loss is 0, RSI is 100
            
            # First 'window' elements are invalid
            rsi[:window] = np.nan
            
            return MathResult({
                "values": rsi.tolist(),
                "indicator": "rsi",
                "window": window
            }, [], "object")

        elif indicator == "macd":
            fast = int(params.get("fast", 12))
            slow = int(params.get("slow", 26))
            signal = int(params.get("signal", 9))
            
            # Helper for EMA
            def calc_ema(data, span):
                alpha = 2.0 / (span + 1.0)
                res = np.zeros_like(data)
                res[0] = data[0]
                for i in range(1, len(data)):
                    res[i] = alpha * data[i] + (1 - alpha) * res[i-1]
                return res
            
            ema_fast = calc_ema(prices, fast)
            ema_slow = calc_ema(prices, slow)
            macd_line = ema_fast - ema_slow
            signal_line = calc_ema(macd_line, signal)
            histogram = macd_line - signal_line
            
            return MathResult({
                "macd": macd_line.tolist(),
                "signal": signal_line.tolist(),
                "histogram": histogram.tolist(),
                "indicator": "macd"
            }, [], "object")

        elif indicator == "bollinger":
            window = int(params.get("window", 20))
            num_std = float(params.get("num_std", 2.0))
            
            if window <= 0:
                raise ValueError("Window must be positive")
            if n < window:
                raise ValueError("Not enough data for Bollinger Bands")
            
            # SMA
            weights = np.ones(window) / window
            sma = np.convolve(prices, weights, mode="valid")
            
            # Rolling Std Dev
            # Efficient rolling std dev?
            # std[i] = sqrt(mean(x^2) - mean(x)^2)
            # Or just loop
            rolling_std = np.zeros(n - window + 1)
            for i in range(len(rolling_std)):
                rolling_std[i] = np.std(prices[i:i+window])
            
            # Pad
            full_sma = np.full(n, np.nan)
            full_sma[window-1:] = sma
            
            full_upper = np.full(n, np.nan)
            full_upper[window-1:] = sma + num_std * rolling_std
            
            full_lower = np.full(n, np.nan)
            full_lower[window-1:] = sma - num_std * rolling_std
            
            return MathResult({
                "middle_band": full_sma.tolist(),
                "upper_band": full_upper.tolist(),
                "lower_band": full_lower.tolist(),
                "indicator": "bollinger"
            }, [], "object")

        elif indicator == "cross_signal":
            short_w = int(params.get("short_window", 50))
            long_w = int(params.get("long_window", 200))
            
            if n < long_w:
                raise ValueError("Not enough data for Cross Signal")
            
            # Calculate SMAs
            def get_sma(data, w):
                weights = np.ones(w) / w
                res = np.convolve(data, weights, mode="valid")
                padded = np.full(len(data), np.nan)
                padded[w-1:] = res
                return padded
            
            sma_short = get_sma(prices, short_w)
            sma_long = get_sma(prices, long_w)
            
            # Check last point
            current_short = sma_short[-1]
            current_long = sma_long[-1]
            prev_short = sma_short[-2]
            prev_long = sma_long[-2]
            
            signal = "neutral"
            if prev_short > prev_long and current_short < current_long:
                signal = "death_cross"
            elif prev_short < prev_long and current_short > current_long:
                signal = "golden_cross"
            
            return MathResult({
                "signal": signal,
                "sma_short": current_short,
                "sma_long": current_long,
                "indicator": "cross_signal"
            }, [], "object")

        else:
            raise ValueError(f"Unknown indicator: {indicator}")
