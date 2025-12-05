"""Tests for boundary cases and edge conditions.

This test module validates handling of:
- Empty arrays and inputs
- Single element arrays
- Zero/negative values where applicable
- Missing required parameters
- Type coercion edge cases

These tests address gaps found during code review.
"""

import math
import pytest
from app.math_engine.capabilities.elementwise import ElementwiseCapability
from app.math_engine.capabilities.curvefit import CurveFitCapability
from app.math_engine.capabilities.financial import FinancialCapability
from app.exceptions import InvalidInputError


class TestElementwiseBoundaries:
    """Test boundary cases for elementwise operations."""

    @pytest.fixture
    def capability(self):
        return ElementwiseCapability()

    def test_empty_array_unary(self, capability):
        """Test unary operations with empty arrays."""
        result = capability.compute(
            operation="sqrt",
            a=[],
            b=None,
            precision="float64"
        )
        assert result.result == []
        assert result.shape == [0]

    def test_empty_array_binary(self, capability):
        """Test binary operations with empty arrays."""
        result = capability.compute(
            operation="add",
            a=[],
            b=[],
            precision="float64"
        )
        assert result.result == []
        assert result.shape == [0]

    def test_single_element_array(self, capability):
        """Test operations with single element arrays."""
        result = capability.compute(
            operation="sqrt",
            a=[4],
            b=None,
            precision="float64"
        )
        assert result.result == [2.0]
        assert result.shape == [1]

    def test_scalar_input(self, capability):
        """Test operations with scalar inputs."""
        result = capability.compute(
            operation="sqrt",
            a=9,
            b=None,
            precision="float64"
        )
        assert result.result == 3.0
        assert result.shape == []  # Scalar has empty shape

    def test_divide_by_zero(self, capability):
        """Test division by zero produces infinity, not error."""
        result = capability.compute(
            operation="divide",
            a=[1, 2, 3],
            b=[0, 0, 0],
            precision="float64"
        )
        # Should produce inf, not error
        assert all(math.isinf(x) for x in result.result)

    def test_log_of_zero(self, capability):
        """Test log of zero produces -infinity."""
        result = capability.compute(
            operation="log",
            a=[0],
            b=None,
            precision="float64"
        )
        assert math.isinf(result.result[0]) and result.result[0] < 0

    def test_log_of_negative(self, capability):
        """Test log of negative produces NaN."""
        result = capability.compute(
            operation="log",
            a=[-1],
            b=None,
            precision="float64"
        )
        assert math.isnan(result.result[0])

    def test_sqrt_of_negative(self, capability):
        """Test sqrt of negative produces NaN."""
        result = capability.compute(
            operation="sqrt",
            a=[-4],
            b=None,
            precision="float64"
        )
        assert math.isnan(result.result[0])

    def test_very_large_numbers(self, capability):
        """Test operations with very large numbers."""
        # TensorFlow has limits on tensor conversion
        # Use a large but valid number and a multiplication that overflows
        result = capability.compute(
            operation="exp",
            a=[1000],  # exp(1000) will overflow to inf
            b=None,
            precision="float64"
        )
        # Should overflow to inf
        assert math.isinf(result.result[0])

    def test_very_small_numbers(self, capability):
        """Test operations with very small numbers."""
        result = capability.compute(
            operation="multiply",
            a=[1e-308],
            b=[1e-100],
            precision="float64"
        )
        # Should underflow to 0
        assert result.result[0] == 0.0 or result.result[0] < 1e-308

    def test_missing_operation_parameter(self, capability):
        """Test error when operation is missing."""
        with pytest.raises(InvalidInputError, match="Unknown operation"):
            capability.compute(
                operation="",
                a=[1, 2, 3],
                b=None,
                precision="float64"
            )

    def test_invalid_operation(self, capability):
        """Test error for invalid operation name."""
        with pytest.raises(InvalidInputError, match="Unknown operation"):
            capability.compute(
                operation="invalid_op",
                a=[1, 2, 3],
                b=None,
                precision="float64"
            )

    def test_binary_op_missing_b(self, capability):
        """Test binary operation without b parameter."""
        with pytest.raises(InvalidInputError, match="requires two operands|b is missing"):
            capability.compute(
                operation="add",
                a=[1, 2, 3],
                b=None,
                precision="float64"
            )


class TestCurveFitBoundaries:
    """Test boundary cases for curve fitting."""

    @pytest.fixture
    def capability(self):
        return CurveFitCapability()

    def test_minimum_points(self, capability):
        """Test with exactly 3 points (minimum required)."""
        result = capability.handle("curve_fit", {
            "x": [1, 2, 3],
            "y": [2, 4, 6],
            "model_type": "polynomial",
            "degree": 1
        })
        assert result.result["quality"]["r_squared"] > 0.99

    def test_two_points_error(self, capability):
        """Test error with only 2 points."""
        with pytest.raises(InvalidInputError, match="At least 3"):
            capability.handle("curve_fit", {
                "x": [1, 2],
                "y": [2, 4],
                "model_type": "polynomial",
                "degree": 1
            })

    def test_empty_arrays_error(self, capability):
        """Test error with empty arrays."""
        with pytest.raises(InvalidInputError, match="At least 3|required"):
            capability.handle("curve_fit", {
                "x": [],
                "y": [],
                "model_type": "polynomial"
            })

    def test_nan_in_data(self, capability):
        """Test handling of NaN values in data."""
        # NaN values should be filtered out
        result = capability.handle("curve_fit", {
            "x": [1, 2, float('nan'), 4, 5],
            "y": [2, 4, 6, 8, 10],
            "model_type": "polynomial",
            "degree": 1
        })
        # Should still work after filtering
        assert "quality" in result.result

    def test_inf_in_data(self, capability):
        """Test handling of infinity in data."""
        # Inf values should be filtered out
        result = capability.handle("curve_fit", {
            "x": [1, 2, float('inf'), 4, 5],
            "y": [2, 4, 6, 8, 10],
            "model_type": "polynomial",
            "degree": 1
        })
        assert "quality" in result.result

    def test_constant_y_values(self, capability):
        """Test fitting when all y values are the same."""
        result = capability.handle("curve_fit", {
            "x": [1, 2, 3, 4, 5],
            "y": [5, 5, 5, 5, 5],
            "model_type": "polynomial",
            "degree": 1
        })
        # Should fit y = 5 (horizontal line)
        params = result.result["parameters"]
        assert abs(params[0]) < 0.01  # slope near 0
        assert abs(params[1] - 5) < 0.01  # intercept near 5

    def test_predict_extrapolation_warning(self, capability):
        """Test prediction outside training range."""
        # Fit on x=[1,5]
        fit_result = capability.handle("curve_fit", {
            "x": [1, 2, 3, 4, 5],
            "y": [1, 4, 9, 16, 25],  # y = x^2
            "model_type": "polynomial",
            "degree": 2
        })
        
        model_id = fit_result.result["model_id"]
        
        # Predict far outside range - should still work but may be inaccurate
        pred_result = capability.handle("curve_predict", {
            "model_id": model_id,
            "x": [10, 20, 100]
        })
        
        # Should return predictions (may be inaccurate but shouldn't error)
        assert len(pred_result.result) == 3


class TestFinancialBoundaries:
    """Test boundary cases for financial calculations."""

    @pytest.fixture
    def capability(self):
        return FinancialCapability()

    def test_pv_empty_cash_flows(self, capability):
        """Test PV with empty cash flows."""
        result = capability.handle("financial_pv", {
            "cash_flows": [],
            "rate": 0.05,
            "times": []
        })
        assert result.result["present_value"] == 0.0
        assert result.result["discounted_flows"] == []

    def test_pv_single_cash_flow(self, capability):
        """Test PV with single cash flow."""
        result = capability.handle("financial_pv", {
            "cash_flows": [100],
            "rate": 0.05,
            "times": [1]
        })
        # PV = 100 / 1.05 = 95.238
        assert abs(result.result["present_value"] - 95.238) < 0.001

    def test_pv_zero_rate(self, capability):
        """Test PV with zero discount rate."""
        result = capability.handle("financial_pv", {
            "cash_flows": [100, 100],
            "rate": 0.0,
            "times": [1, 2]
        })
        # PV = 100 + 100 = 200 (no discounting)
        assert abs(result.result["present_value"] - 200.0) < 0.001

    def test_pv_negative_rate(self, capability):
        """Test PV with negative discount rate (unusual but valid)."""
        result = capability.handle("financial_pv", {
            "cash_flows": [100],
            "rate": -0.05,  # Negative rate
            "times": [1]
        })
        # PV = 100 / 0.95 > 100
        assert result.result["present_value"] > 100

    def test_bond_zero_coupon(self, capability):
        """Test zero coupon bond pricing."""
        result = capability.handle("financial_bond_price", {
            "face_value": 1000,
            "coupon_rate": 0.0,  # Zero coupon
            "frequency": 2,
            "years_to_maturity": 5,
            "yield_to_maturity": 0.05
        })
        # Price should be PV of face value = 1000 / (1.025)^10
        expected = 1000 / (1.025 ** 10)
        assert abs(result.result["price"] - expected) < 1.0

    def test_option_at_the_money(self, capability):
        """Test option pricing when S = K (at the money)."""
        result = capability.handle("financial_option_price", {
            "S": 100,
            "K": 100,
            "T": 1,
            "r": 0.05,
            "sigma": 0.2,
            "option_type": "call",
            "exercise_style": "european",
            "steps": 100
        })
        # ATM call should have positive value
        assert result.result["price"] > 0
        # Delta should be around 0.5-0.6 for ATM call
        assert 0.4 < result.result["delta"] < 0.7

    def test_option_deep_in_money(self, capability):
        """Test deep in-the-money option."""
        result = capability.handle("financial_option_price", {
            "S": 150,  # Deep ITM
            "K": 100,
            "T": 1,
            "r": 0.05,
            "sigma": 0.2,
            "option_type": "call",
            "exercise_style": "european",
            "steps": 100
        })
        # Deep ITM call should have price close to intrinsic value
        intrinsic = 150 - 100
        assert result.result["price"] > intrinsic * 0.9
        # Delta should be close to 1
        assert result.result["delta"] > 0.9

    def test_option_deep_out_of_money(self, capability):
        """Test deep out-of-the-money option."""
        result = capability.handle("financial_option_price", {
            "S": 50,  # Deep OTM
            "K": 100,
            "T": 1,
            "r": 0.05,
            "sigma": 0.2,
            "option_type": "call",
            "exercise_style": "european",
            "steps": 100
        })
        # Deep OTM call should have very low price
        assert result.result["price"] < 1.0
        # Delta should be close to 0
        assert result.result["delta"] < 0.1

    def test_option_expiring(self, capability):
        """Test option very close to expiry."""
        result = capability.handle("financial_option_price", {
            "S": 100,
            "K": 100,
            "T": 0.001,  # Very close to expiry
            "r": 0.05,
            "sigma": 0.2,
            "option_type": "call",
            "exercise_style": "european",
            "steps": 100
        })
        # Near expiry ATM option should have very low time value
        assert result.result["price"] < 1.0

    def test_technical_indicator_insufficient_data(self, capability):
        """Test technical indicator with insufficient data."""
        # SMA with window larger than data
        with pytest.raises(InvalidInputError, match="Not enough data|window.*data"):
            capability.handle("financial_technical_indicators", {
                "indicator": "sma",
                "prices": [100, 101, 102],  # Only 3 prices
                "params": {"window": 20}  # But window is 20
            })

    def test_technical_indicator_missing_prices(self, capability):
        """Test technical indicator without prices parameter."""
        with pytest.raises(InvalidInputError, match="requires.*prices|prices.*list"):
            capability.handle("financial_technical_indicators", {
                "indicator": "sma",
                "params": {"window": 5}
                # Missing 'prices'
            })


class TestErrorMessageQuality:
    """Test that error messages are helpful for LLM/users."""

    @pytest.fixture
    def elem_cap(self):
        return ElementwiseCapability()

    @pytest.fixture
    def fin_cap(self):
        return FinancialCapability()

    def test_binary_op_error_message_helpful(self, elem_cap):
        """Verify error message for missing b is actionable."""
        try:
            elem_cap.compute(operation="add", a=[1, 2], b=None, precision="float64")
            pytest.fail("Should have raised InvalidInputError")
        except InvalidInputError as e:
            error_msg = str(e).lower()
            # Should mention what's needed
            assert "b" in error_msg or "second" in error_msg or "operand" in error_msg

    def test_unknown_tool_error_message(self, fin_cap):
        """Verify error for unknown tool is helpful."""
        try:
            fin_cap.handle("unknown_tool", {})
            pytest.fail("Should have raised InvalidInputError")
        except InvalidInputError as e:
            error_msg = str(e).lower()
            assert "unknown" in error_msg or "tool" in error_msg


class TestTypeCoercion:
    """Test type coercion and input flexibility."""

    @pytest.fixture
    def capability(self):
        return ElementwiseCapability()

    def test_integer_input_coerced_to_float(self, capability):
        """Test that integer inputs are properly coerced."""
        result = capability.compute(
            operation="sqrt",
            a=[4, 9, 16],  # Integers
            b=None,
            precision="float64"
        )
        # Should work and return floats
        assert result.dtype == "float64"
        assert result.result == [2.0, 3.0, 4.0]

    def test_mixed_int_float_input(self, capability):
        """Test mixed integer and float inputs."""
        result = capability.compute(
            operation="add",
            a=[1, 2.5, 3],  # Mixed
            b=[0.5, 0.5, 0.5],
            precision="float64"
        )
        assert result.result == [1.5, 3.0, 3.5]

    def test_nested_array_flattening(self, capability):
        """Test that nested arrays are handled correctly."""
        result = capability.compute(
            operation="add",
            a=[[1, 2], [3, 4]],  # 2D array
            b=[[10, 20], [30, 40]],
            precision="float64"
        )
        assert result.result == [[11.0, 22.0], [33.0, 44.0]]
        assert result.shape == [2, 2]
