"""Tests for Financial Option Pricing (Binomial Model)."""

import pytest
from app.math_engine.capabilities.financial import FinancialCapability
from app.exceptions import InvalidInputError


class TestFinancialOptionPricing:

    @pytest.fixture
    def fin_cap(self):
        return FinancialCapability()
    
    def test_european_call_at_the_money(self, fin_cap):
        """Test European Call ATM. S=100, K=100, T=1, r=0.05, sigma=0.2"""
        # Black-Scholes approx: 10.45
        result = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "exercise_style": "european", "steps": 100
        })
        price = result.result["price"]
        assert 10.30 < price < 10.60
        assert result.result["delta"] > 0.5  # ATM Call Delta ~ 0.6ish (N(d1))
        
    def test_european_put_at_the_money(self, fin_cap):
        """Test European Put ATM. S=100, K=100, T=1, r=0.05, sigma=0.2"""
        # Black-Scholes approx: 5.57
        result = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "option_type": "put", "exercise_style": "european", "steps": 100
        })
        price = result.result["price"]
        assert 5.40 < price < 5.70
        assert result.result["delta"] < -0.3 # ATM Put Delta ~ -0.4ish

    def test_american_call_equals_european_call(self, fin_cap):
        """American Call on non-dividend paying stock should equal European Call."""
        params = {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "steps": 50
        }
        euro = fin_cap.handle("financial_option_price", {**params, "exercise_style": "european"})
        amer = fin_cap.handle("financial_option_price", {**params, "exercise_style": "american"})
        
        assert abs(euro.result["price"] - amer.result["price"]) < 0.0001

    def test_american_put_early_exercise(self, fin_cap):
        """Test American Put where early exercise is optimal."""
        # Deep ITM Put: S=80, K=100. Intrinsic = 20.
        # r=0.10 (high rate makes waiting costly for puts)
        params = {
            "S": 80, "K": 100, "T": 1.0, "r": 0.10, "sigma": 0.2,
            "option_type": "put", "steps": 100
        }
        
        euro = fin_cap.handle("financial_option_price", {**params, "exercise_style": "european"})
        amer = fin_cap.handle("financial_option_price", {**params, "exercise_style": "american"})
        
        # European put should be less than intrinsic (20) because of time value of money on K
        # PV(K) = 100 * e^-0.1 = 90.48. S=80. Lower bound is K*e^-rT - S = 10.48.
        # Actually Put price is roughly max(0, K*e^-rT - S) + time value.
        # Here intrinsic is 20.
        # American put should be at least 20.
        
        assert amer.result["price"] >= 20.0
        assert amer.result["price"] > euro.result["price"]

    def test_expiry_payoff(self, fin_cap):
        """Test T=0 returns intrinsic value."""
        result = fin_cap.handle("financial_option_price", {
            "S": 110, "K": 100, "T": 0, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "exercise_style": "european"
        })
        assert result.result["price"] == 10.0

    def test_greeks_signs(self, fin_cap):
        """Check signs of Greeks for a Call."""
        result = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 0.5, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "exercise_style": "european"
        })
        data = result.result
        assert data["delta"] > 0  # Call delta positive
        assert data["gamma"] > 0  # Long option gamma positive
        assert data["theta"] < 0  # Time decay hurts long option

    def test_invalid_inputs(self, fin_cap):
        with pytest.raises(InvalidInputError):
            fin_cap.handle("financial_option_price", {
                "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
                "option_type": "call", "exercise_style": "european",
                "steps": 0
            })

    def test_dividend_impact(self, fin_cap):
        """Test that dividends lower Call price and raise Put price."""
        params = {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "exercise_style": "european", "steps": 50
        }
        
        # No dividend
        call_no_div = fin_cap.handle("financial_option_price", {**params, "option_type": "call", "q": 0.0})
        put_no_div = fin_cap.handle("financial_option_price", {**params, "option_type": "put", "q": 0.0})
        
        # With dividend
        call_div = fin_cap.handle("financial_option_price", {**params, "option_type": "call", "q": 0.05})
        put_div = fin_cap.handle("financial_option_price", {**params, "option_type": "put", "q": 0.05})
        
        assert call_div.result["price"] < call_no_div.result["price"]
        assert put_div.result["price"] > put_no_div.result["price"]

    def test_american_call_early_exercise_with_dividend(self, fin_cap):
        """Test American Call early exercise with high dividend."""
        # Deep ITM Call: S=120, K=100. Intrinsic = 20.
        # High dividend q=0.10 makes holding the stock attractive (or holding option costly as you miss div)
        # Actually, if you hold option, you don't get dividend.
        # If dividend is high enough, you exercise early to get the stock and the dividend.
        params = {
            "S": 120, "K": 100, "T": 1.0, "r": 0.02, "q": 0.20, "sigma": 0.2,
            "option_type": "call", "steps": 100
        }
        
        euro = fin_cap.handle("financial_option_price", {**params, "exercise_style": "european"})
        amer = fin_cap.handle("financial_option_price", {**params, "exercise_style": "american"})
        
        # American should be worth more than European due to early exercise possibility
        assert amer.result["price"] > euro.result["price"]
    
    def test_discrete_dividends(self, fin_cap):
        """Test discrete dividends using Escrowed Dividend Model."""
        # S=100, K=100, T=1, r=0.05, sigma=0.2
        # Dividend of 5.0 at T=0.5
        params = {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "exercise_style": "european", "steps": 50,
            "dividends": [{"amount": 5.0, "time": 0.5}]
        }
        
        # Price should be lower than no-dividend call
        call_div = fin_cap.handle("financial_option_price", {**params, "option_type": "call"})
        
        # Compare to no dividend
        call_no_div = fin_cap.handle("financial_option_price", {**params, "option_type": "call", "dividends": []})
        
        assert call_div.result["price"] < call_no_div.result["price"]
        
        # Compare to equivalent continuous yield approx
        # 5% dividend at 0.5 years is roughly 5% yield? No, 5/100 = 5%.
        # PV(Div) = 5 * e^(-0.05*0.5) = 4.87
        # S_adj = 95.13.
        # Continuous yield q that gives S*e^-qT = S_adj?
        # 100 * e^-q = 95.13 => e^-q = 0.9513 => q = 0.05 roughly.
        
        call_yield = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
            "exercise_style": "european", "steps": 50,
            "option_type": "call",
            "q": 0.05
        })
        
        # They should be somewhat close
        assert abs(call_div.result["price"] - call_yield.result["price"]) < 1.0

    def test_discrete_dividend_american_early_exercise(self, fin_cap):
        """Test American Call early exercise just before discrete dividend."""
        # S=100, K=80 (Deep ITM). Dividend 10.0 at T=0.5. T=1.0.
        # If we wait, price drops by 10.
        # Intrinsic now = 20.
        # PV(Div) = 10 * e^-r*0.5.
        # If we exercise just before T=0.5, we get S(0.5-) - K.
        # S(0.5-) includes the dividend.
        
        params = {
            "S": 100, "K": 80, "T": 1.0, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "steps": 100,
            "dividends": [{"amount": 10.0, "time": 0.5}]
        }
        
        amer = fin_cap.handle("financial_option_price", {**params, "exercise_style": "american"})
        euro = fin_cap.handle("financial_option_price", {**params, "exercise_style": "european"})
        
        # American should be significantly higher because optimal strategy is to exercise just before ex-div
        assert amer.result["price"] > euro.result["price"] + 0.5 # significant difference

    def test_vega_rho_signs(self, fin_cap):
        """Check signs of Vega and Rho for a Call."""
        result = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 0.5, "r": 0.05, "sigma": 0.2,
            "option_type": "call", "exercise_style": "european"
        })
        data = result.result
        assert "vega" in data
        assert "rho" in data
        assert data["vega"] > 0  # Long option vega positive
        assert data["rho"] > 0   # Call rho positive (usually)
        
        # Put Rho is usually negative
        result_put = fin_cap.handle("financial_option_price", {
            "S": 100, "K": 100, "T": 0.5, "r": 0.05, "sigma": 0.2,
            "option_type": "put", "exercise_style": "european"
        })
        assert result_put.result["rho"] < 0
