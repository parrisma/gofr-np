"""Tests for Financial Rate Conversion."""

import pytest
from app.math_engine.capabilities.financial import FinancialCapability

@pytest.fixture
def fin_cap():
    return FinancialCapability()

class TestFinancialRateConversion:
    
    def test_annual_to_monthly(self, fin_cap):
        """Test converting Annual (10%) to Monthly."""
        # EAR = 10%
        # Monthly rate r_m: (1 + r_m/12)^12 = 1.10
        # r_m = 12 * (1.10^(1/12) - 1)
        #     = 12 * (1.007974 - 1) = 0.095689...
        
        result = fin_cap.handle("financial_convert_rate", {
            "rate": 0.10,
            "from_freq": "annual",
            "to_freq": "monthly"
        })
        
        data = result.result
        assert abs(data["converted_rate"] - 0.09569) < 0.0001
        assert abs(data["effective_annual_rate"] - 0.10) < 0.0001

    def test_monthly_to_annual(self, fin_cap):
        """Test converting Monthly (12%) to Annual."""
        # Nominal 12% monthly means 1% per month
        # EAR = (1.01)^12 - 1 = 0.126825...
        
        result = fin_cap.handle("financial_convert_rate", {
            "rate": 0.12,
            "from_freq": "monthly",
            "to_freq": "annual"
        })
        
        data = result.result
        assert abs(data["converted_rate"] - 0.126825) < 0.0001
        assert abs(data["effective_annual_rate"] - 0.126825) < 0.0001

    def test_continuous_to_annual(self, fin_cap):
        """Test converting Continuous (10%) to Annual."""
        # EAR = e^0.10 - 1 = 0.10517...
        
        result = fin_cap.handle("financial_convert_rate", {
            "rate": 0.10,
            "from_freq": "continuous",
            "to_freq": "annual"
        })
        
        data = result.result
        assert abs(data["converted_rate"] - 0.10517) < 0.0001

    def test_annual_to_continuous(self, fin_cap):
        """Test converting Annual (10%) to Continuous."""
        # e^r = 1.10 => r = ln(1.10) = 0.09531...
        
        result = fin_cap.handle("financial_convert_rate", {
            "rate": 0.10,
            "from_freq": "annual",
            "to_freq": "continuous"
        })
        
        data = result.result
        assert abs(data["converted_rate"] - 0.09531) < 0.0001

    def test_simple_to_continuous(self, fin_cap):
        """Test converting Simple (10%) to Continuous."""
        # Simple 10% over 1 year -> 1.10 factor
        # Same as Annual 10% -> Continuous
        # r = ln(1.10) = 0.09531...
        
        result = fin_cap.handle("financial_convert_rate", {
            "rate": 0.10,
            "from_freq": "simple",
            "to_freq": "continuous"
        })
        
        data = result.result
        assert abs(data["converted_rate"] - 0.09531) < 0.0001

    def test_errors(self, fin_cap):
        """Test error handling."""
        with pytest.raises(ValueError, match="required"):
            fin_cap.handle("financial_convert_rate", {
                "rate": 0.10
            })
