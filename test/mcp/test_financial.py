"""Tests for Financial Capability."""

import pytest
from app.math_engine.capabilities.financial import FinancialCapability

@pytest.fixture
def fin_cap():
    return FinancialCapability()

class TestFinancialPV:
    
    def test_simple_pv_discrete(self, fin_cap):
        """Test simple PV with constant rate."""
        # PV = 100 / 1.05 + 100 / 1.05^2
        #    = 95.238 + 90.703 = 185.941
        
        result = fin_cap.handle("financial_pv", {
            "cash_flows": [100, 100],
            "rate": 0.05,
            "times": [1, 2]
        })
        
        data = result.result
        assert abs(data["present_value"] - 185.941) < 0.001
        assert len(data["discounted_flows"]) == 2
        assert abs(data["discounted_flows"][0] - 95.238) < 0.001

    def test_default_times(self, fin_cap):
        """Test that times default to 1, 2, 3..."""
        result = fin_cap.handle("financial_pv", {
            "cash_flows": [100, 100, 100],
            "rate": 0.10
        })
        
        data = result.result
        times = data["times"]
        assert times == [1.0, 2.0, 3.0]
        
        # PV of annuity: 100 * (1 - (1.1)^-3) / 0.1 = 248.685
        assert abs(data["present_value"] - 248.685) < 0.001

    def test_yield_curve(self, fin_cap):
        """Test PV with a yield curve (different rates for different times)."""
        # Year 1: 100 @ 5%
        # Year 2: 100 @ 6%
        
        # PV = 100/1.05 + 100/(1.06)^2
        #    = 95.238 + 88.9996 = 184.237
        
        result = fin_cap.handle("financial_pv", {
            "cash_flows": [100, 100],
            "rate": [0.05, 0.06],
            "times": [1, 2]
        })
        
        data = result.result
        assert abs(data["present_value"] - 184.238) < 0.001

    def test_continuous_compounding(self, fin_cap):
        """Test continuous compounding."""
        # PV = 100 * e^(-0.05 * 1)
        #    = 100 * 0.951229 = 95.123
        
        result = fin_cap.handle("financial_pv", {
            "cash_flows": [100],
            "rate": 0.05,
            "times": [1],
            "compounding": "continuous"
        })
        
        data = result.result
        assert abs(data["present_value"] - 95.123) < 0.001

    def test_errors(self, fin_cap):
        """Test error handling."""
        # Missing rate
        with pytest.raises(ValueError, match="required"):
            fin_cap.handle("financial_pv", {
                "cash_flows": [100]
            })
            
        # Mismatched times
        with pytest.raises(ValueError, match="Length of 'times'"):
            fin_cap.handle("financial_pv", {
                "cash_flows": [100, 200],
                "rate": 0.05,
                "times": [1]
            })
            
        # Mismatched yield curve
        with pytest.raises(ValueError, match="Length of 'rate'"):
            fin_cap.handle("financial_pv", {
                "cash_flows": [100, 200],
                "rate": [0.05], # Only one rate for two flows
                "times": [1, 2]
            })
