# Financial Math Capability

The Financial Math capability provides a suite of tools for quantitative finance, including time value of money, option pricing, bond pricing, and technical analysis.

## Tools

### `financial_pv` (Present Value)
Calculates the Present Value (PV) of a series of cash flows.
- **Features:** Supports constant discount rates or yield curves. Handles discrete or continuous compounding.
- **Use Case:** Valuing future cash flows today.

### `financial_convert_rate`
Converts interest rates between different compounding frequencies.
- **Supported Frequencies:** Simple, Annual, Semiannual, Quarterly, Monthly, Weekly, Daily, Continuous.
- **Use Case:** Comparing rates quoted on different bases (e.g., Mortgage APR vs Savings APY).

### `financial_option_price`
Calculates the price of options using the **Binomial Option Pricing Model (CRR)**.
- **Features:** 
  - European and American exercise styles.
  - Call and Put options.
  - Discrete dividends support.
  - Returns Greeks (Delta, Gamma, Theta, Vega, Rho).
- **Use Case:** Pricing American options or options with discrete dividends.

### `financial_bond_price`
Calculates price and risk metrics for fixed-rate bonds.
- **Metrics:** Price, Macaulay Duration, Modified Duration, Convexity.
- **Use Case:** Bond valuation and interest rate risk management.

### `financial_technical_indicators`
Calculates common technical analysis indicators for time-series data.
- **Indicators:**
  - `sma`: Simple Moving Average
  - `ema`: Exponential Moving Average
  - `rsi`: Relative Strength Index
  - `macd`: Moving Average Convergence Divergence
  - `bollinger`: Bollinger Bands
  - `pe_ratio`: Price-to-Earnings Ratio
  - `cross_signal`: Golden Cross / Death Cross detection
- **Use Case:** Algorithmic trading signals and market analysis.
