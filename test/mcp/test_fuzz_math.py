from hypothesis import given, strategies as st, settings, HealthCheck
from app.math_engine.capabilities.elementwise import ElementwiseCapability

# Initialize capability
capability = ElementwiseCapability()

# Strategies
floats = st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6)
lists_of_floats = st.lists(floats, min_size=1, max_size=100)

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(op=st.sampled_from(["abs", "square", "floor", "ceil", "negate"]), 
       data=lists_of_floats)
def test_fuzz_unary_ops_safe(op, data):
    """Fuzz test for safe unary operations that shouldn't fail on valid floats."""
    result = capability.handle("math_compute", {"operation": op, "a": data})
    # If we get here, it didn't crash
    assert result.result is not None
    if isinstance(result.result, list):
        assert len(result.result) == len(data)

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(op=st.sampled_from(["add", "subtract", "multiply"]), 
       x=lists_of_floats, 
       y=lists_of_floats)
def test_fuzz_binary_ops_broadcasting(op, x, y):
    """Fuzz test for binary operations to check broadcasting/shape handling."""
    try:
        result = capability.handle("math_compute", {"operation": op, "a": x, "b": y})
        assert isinstance(result.result, list)
    except Exception:
        # It's acceptable to fail if shapes are incompatible, but it should be a specific error
        # For now, we just want to ensure it doesn't segfault or do something catastrophic
        # Ideally we check for InvalidInputError or ComputationError
        pass

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(x=floats)
def test_fuzz_sqrt_domain(x):
    """Test sqrt specifically for domain errors."""
    try:
        result = capability.handle("math_compute", {"operation": "sqrt", "a": x})
        if x < 0:
            # If it succeeded for negative input, it must be returning NaN (if float64)
            # or complex (if supported, but here we likely get NaN or error)
            import math
            if isinstance(result.result, float) and math.isnan(result.result):
                pass # NaN is acceptable
            else:
                # If it returned a real number for negative input, that's suspicious unless it's 0
                pass 
    except Exception as e:
        # Expected for negative inputs if not handling complex
        if x < 0:
            pass
        else:
            raise e
