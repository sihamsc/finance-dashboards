from src.utils.formatters import safe_pct

def test_safe_pct_basic():
    assert safe_pct(50, 100) == 50.0

def test_safe_pct_zero_denominator():
    assert safe_pct(50, 0) == 0.0
