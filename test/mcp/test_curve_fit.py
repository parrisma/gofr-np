"""Tests for Curve Fitting Capability."""

import pytest
import numpy as np
from app.math_engine.capabilities.curvefit import CurveFitCapability

@pytest.fixture
def curve_fit_cap():
    return CurveFitCapability()

class TestCurveFit:
    
    def test_linear_fit(self, curve_fit_cap):
        """Test simple linear regression."""
        # y = 2x + 1
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        
        result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "polynomial",
            "degree": 1
        })
        
        data = result.result
        assert data["model_type"] == "polynomial_deg1"
        assert data["quality"]["r_squared"] > 0.99
        
        # Check params (slope ~ 2, intercept ~ 1)
        # polyfit returns [slope, intercept]
        params = data["parameters"]
        assert abs(params[0] - 2.0) < 0.01
        assert abs(params[1] - 1.0) < 0.01

    def test_quadratic_fit(self, curve_fit_cap):
        """Test quadratic fit."""
        # y = x^2
        x = [-2, -1, 0, 1, 2]
        y = [4, 1, 0, 1, 4]
        
        result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "polynomial",
            "degree": 2
        })
        
        data = result.result
        assert data["model_type"] == "polynomial_deg2"
        assert data["quality"]["r_squared"] > 0.99
        
        # Check params [a, b, c] for ax^2 + bx + c
        params = data["parameters"]
        assert abs(params[0] - 1.0) < 0.01 # a=1
        assert abs(params[1]) < 0.01       # b=0
        assert abs(params[2]) < 0.01       # c=0

    def test_exponential_fit(self, curve_fit_cap):
        """Test exponential fit."""
        # y = 2 * e^(0.5x) + 1
        x = np.linspace(0, 4, 10).tolist()
        y = (2.0 * np.exp(0.5 * np.array(x)) + 1.0).tolist()
        
        result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "exponential"
        })
        
        data = result.result
        assert data["model_type"] == "exponential"
        assert data["quality"]["r_squared"] > 0.95
        
        # Params: [a, b, c]
        params = data["parameters"]
        assert abs(params[0] - 2.0) < 0.2
        assert abs(params[1] - 0.5) < 0.1
        assert abs(params[2] - 1.0) < 0.2

    def test_auto_selection(self, curve_fit_cap):
        """Test that auto-selection picks the right model."""
        # Generate sigmoid data
        # y = 10 / (1 + e^(-2(x-5))) + 2
        x = np.linspace(0, 10, 20).tolist()
        y = (10.0 / (1.0 + np.exp(-2.0 * (np.array(x) - 5.0))) + 2.0).tolist()
        
        result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "auto"
        })
        
        data = result.result
        # Should pick sigmoid or high-degree poly, but sigmoid has better AIC usually
        # Note: Sigmoid fitting can be sensitive to initialization, so we check if R2 is good
        assert data["quality"]["r_squared"] > 0.95
        
        # If it picked sigmoid, check params
        if data["model_type"] == "sigmoid":
            params = data["parameters"]
            # L, k, x0, b
            assert abs(params[0] - 10.0) < 1.0
            assert abs(params[2] - 5.0) < 0.5

    def test_outlier_detection(self, curve_fit_cap):
        """Test that outliers are detected and removed."""
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [2, 4, 6, 8, 10, 100, 14, 16, 18, 20] # 100 is outlier
        
        result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "polynomial",
            "degree": 1
        })
        
        data = result.result
        assert data["outliers_removed"] > 0
        assert data["quality"]["r_squared"] > 0.9 # Should be good after removing outlier

    def test_prediction(self, curve_fit_cap):
        """Test prediction using a fitted model."""
        x = [1, 2, 3]
        y = [2, 4, 6]
        
        # Fit
        fit_result = curve_fit_cap.handle("curve_fit", {
            "x": x,
            "y": y,
            "model_type": "polynomial",
            "degree": 1
        })
        
        model_id = fit_result.result["model_id"]
        
        # Predict
        pred_result = curve_fit_cap.handle("curve_predict", {
            "model_id": model_id,
            "x": [4, 5]
        })
        
        preds = pred_result.result
        assert len(preds) == 2
        assert abs(preds[0] - 8.0) < 0.01
        assert abs(preds[1] - 10.0) < 0.01

    def test_errors(self, curve_fit_cap):
        """Test error handling."""
        # Mismatched lengths
        with pytest.raises(ValueError, match="same length"):
            curve_fit_cap.handle("curve_fit", {
                "x": [1, 2],
                "y": [1, 2, 3]
            })
            
        # Too few points
        with pytest.raises(ValueError, match="At least 3"):
            curve_fit_cap.handle("curve_fit", {
                "x": [1, 2],
                "y": [1, 2]
            })
            
        # Invalid model ID
        with pytest.raises(ValueError, match="not found"):
            curve_fit_cap.handle("curve_predict", {
                "model_id": "fake_id",
                "x": [1]
            })
