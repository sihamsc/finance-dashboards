from src.utils.filters import rolling_ym

def test_rolling_ym_returns_12_months():
    out = rolling_ym(2025, 3)
    assert len(out) == 12
    assert out[0] == (2024, 4)
    assert out[-1] == (2025, 3)
