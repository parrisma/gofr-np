import pytest
from app.math_engine.capabilities.financial import FinancialCapability

class TestFinancialBondPricing:
    """Test suite for financial_bond_price tool."""

    @pytest.fixture
    def capability(self):
        return FinancialCapability()

    def test_par_bond(self, capability):
        """Test that a bond priced at par has Price = Face Value."""
        # Coupon = YTM => Price = Par
        result = capability.handle_bond_price({
            "face_value": 1000,
            "coupon_rate": 0.05,
            "frequency": 2,
            "years_to_maturity": 10,
            "yield_to_maturity": 0.05
        })
        
        data = result.result
        assert data["price"] == pytest.approx(1000.0, abs=0.01)
        # Modified duration should be roughly similar to Macaulay / (1+r)

    def test_premium_bond(self, capability):
        """Test bond pricing when Coupon > YTM (Premium)."""
        result = capability.handle_bond_price({
            "face_value": 100,
            "coupon_rate": 0.10, # 10% coupon
            "frequency": 1,      # Annual
            "years_to_maturity": 5,
            "yield_to_maturity": 0.08 # 8% yield
        })
        
        data = result.result
        assert data["price"] > 100.0
        assert data["price"] == pytest.approx(107.985, abs=0.01)

    def test_discount_bond(self, capability):
        """Test bond pricing when Coupon < YTM (Discount)."""
        result = capability.handle_bond_price({
            "face_value": 100,
            "coupon_rate": 0.05, # 5% coupon
            "frequency": 1,      # Annual
            "years_to_maturity": 5,
            "yield_to_maturity": 0.10 # 10% yield
        })
        
        data = result.result
        assert data["price"] < 100.0
        assert data["price"] == pytest.approx(81.046, abs=0.01)

    def test_zero_coupon_bond(self, capability):
        """Test zero coupon bond pricing."""
        # Price = Face / (1+r)^t
        face = 100
        ytm = 0.05
        years = 10
        
        result = capability.handle_bond_price({
            "face_value": face,
            "coupon_rate": 0.0,
            "frequency": 1,
            "years_to_maturity": years,
            "yield_to_maturity": ytm
        })
        
        expected_price = face / ((1 + ytm) ** years)
        data = result.result
        assert data["price"] == pytest.approx(expected_price, abs=0.01)
        
        # Macaulay Duration of zero coupon bond = Maturity
        assert data["macaulay_duration"] == pytest.approx(years, abs=0.01)

    def test_duration_convexity(self, capability):
        """Test duration and convexity calculations."""
        # Example from a textbook or known calculator
        # Face=100, Coupon=6%, Semi-annual, 2 years, YTM=5%
        # Price should be 101.88
        
        result = capability.handle_bond_price({
            "face_value": 100,
            "coupon_rate": 0.06,
            "frequency": 2,
            "years_to_maturity": 2,
            "yield_to_maturity": 0.05
        })
        
        data = result.result
        assert data["price"] == pytest.approx(101.88, abs=0.01)
        
        # Check that Modified Duration is roughly (Price(y-dy) - Price(y+dy)) / (2 * Price * dy)
        # Let's verify directionally
        mod_dur = data["modified_duration"]
        price = data["price"]
        
        # Bump yield down
        res_down = capability.handle_bond_price({
            "face_value": 100,
            "coupon_rate": 0.06,
            "frequency": 2,
            "years_to_maturity": 2,
            "yield_to_maturity": 0.04
        })
        price_down = res_down.result["price"]
        
        # Bump yield up
        res_up = capability.handle_bond_price({
            "face_value": 100,
            "coupon_rate": 0.06,
            "frequency": 2,
            "years_to_maturity": 2,
            "yield_to_maturity": 0.06
        })
        price_up = res_up.result["price"]
        
        # Approx Mod Duration
        approx_mod_dur = (price_down - price_up) / (2 * price * 0.01)
        assert mod_dur == pytest.approx(approx_mod_dur, abs=0.05)

    def test_invalid_inputs(self, capability):
        """Test error handling for invalid inputs."""
        with pytest.raises(ValueError, match="Frequency must be positive"):
            capability.handle_bond_price({
                "coupon_rate": 0.05,
                "years_to_maturity": 10,
                "yield_to_maturity": 0.05,
                "frequency": 0
            })

        with pytest.raises(ValueError, match="Years to maturity must be positive"):
            capability.handle_bond_price({
                "coupon_rate": 0.05,
                "years_to_maturity": -1,
                "yield_to_maturity": 0.05
            })
