"""Tests for Financial Technical Indicators."""

import pytest
from app.math_engine.capabilities.financial import FinancialCapability

@pytest.fixture
def fin_cap():
    return FinancialCapability()

class TestFinancialTechnicals:
    
    def test_sma(self, fin_cap):
        """Test Simple Moving Average."""
        prices = [10, 11, 12, 13, 14]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "sma",
            "prices": prices,
            "params": {"window": 3}
        })
        values = result.result["values"]
        # SMA(3) of [10, 11, 12] = 11
        # SMA(3) of [11, 12, 13] = 12
        # SMA(3) of [12, 13, 14] = 13
        # First 2 should be null/None (JSON-safe padding)
        assert values[0] is None
        assert values[1] is None
        assert values[2] == pytest.approx(11.0)
        assert values[3] == pytest.approx(12.0)
        assert values[4] == pytest.approx(13.0)

    def test_ema(self, fin_cap):
        """Test Exponential Moving Average."""
        prices = [10, 10, 10, 10, 10]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "ema",
            "prices": prices,
            "params": {"window": 3}
        })
        values = result.result["values"]
        # EMA of constant series is constant
        assert abs(values[-1] - 10.0) < 0.0001

    def test_rsi(self, fin_cap):
        """Test RSI."""
        # Up trend -> High RSI
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "rsi",
            "prices": prices,
            "params": {"window": 14}
        })
        values = result.result["values"]
        # Last value should be 100 because no losses
        assert values[-1] == 100.0

    def test_bollinger(self, fin_cap):
        """Test Bollinger Bands."""
        prices = [10, 10, 10, 10, 10]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "bollinger",
            "prices": prices,
            "params": {"window": 5, "num_std": 2}
        })
        data = result.result
        # Std dev is 0, so bands equal SMA
        assert data["upper_band"][-1] == 10.0
        assert data["lower_band"][-1] == 10.0
        assert data["middle_band"][-1] == 10.0

    def test_pe_ratio(self, fin_cap):
        """Test PE Ratio."""
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "pe_ratio",
            "params": {"price": 100, "earnings": 5}
        })
        assert result.result["pe_ratio"] == 20.0

    def test_death_cross(self, fin_cap):
        """Test Death Cross detection."""
        # Short term (SMA 2) crossing below Long term (SMA 4)
        # t=3: SMA2 > SMA4
        # t=4: SMA2 < SMA4
        
        prices = [10, 10, 10, 11, 0]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "cross_signal",
            "prices": prices,
            "params": {"short_window": 2, "long_window": 4}
        })
        assert result.result["signal"] == "death_cross"

    def test_golden_cross(self, fin_cap):
        """Test Golden Cross detection."""
        # Short term crossing above Long term
        # t=3: SMA2 < SMA4
        # t=4: SMA2 > SMA4
        
        prices = [10, 10, 10, 9, 20]
        result = fin_cap.handle("financial_technical_indicators", {
            "indicator": "cross_signal",
            "prices": prices,
            "params": {"short_window": 2, "long_window": 4}
        })
        assert result.result["signal"] == "golden_cross"
