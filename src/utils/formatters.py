import pandas as pd

def safe_pct(a, b):
    return (a / b * 100) if b not in (0, None) else 0.0

def fmt_m(v):
    return f"${v/1e6:.1f}M"

def fmt_int(v):
    return f"{int(v):,}"

def pct_text(v):
    return "" if pd.isna(v) else f"{v:.1f}%"

def kpi(label, value, delta=None, delta_label="", kind="money"):
    if kind == "pct":
        val_str = f"{value:.1f}%"
    elif kind == "count":
        val_str = fmt_int(value)
    elif kind == "dollar":
        val_str = f"${value:,.0f}"
    else:
        val_str = fmt_m(value)

    delta_html = ""
    if delta is not None:
        cls = "delta-pos" if delta >= 0 else "delta-neg"
        sign = "▲" if delta >= 0 else "▼"

        if kind == "pct":
            d_str = f"{abs(delta):.1f} pts"
        elif kind == "count":
            d_str = fmt_int(abs(delta))
        elif kind == "dollar":
            d_str = f"${abs(delta):,.0f}"
        else:
            d_str = fmt_m(abs(delta))

        delta_html = f'<div class="metric-delta {cls}">{sign} {d_str} {delta_label}</div>'

    return (
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{val_str}</div>{delta_html}</div>'
    )