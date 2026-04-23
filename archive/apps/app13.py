# ============================================================
# MarketCast Finance Dashboard
#
# Structure
# - Header KPI rows show the current selected period
# - Time modes:
#     * Full Year
#     * YTD / Range
#     * Rolling 12M
# - Rolling 12M uses an exact ordered list of (year, month) tuples
#   and aligns Current vs Prior Year on the same month axis
#
# Tab order
#   1. Overview
#   2. Revenue
#   3. COGS
#   4. Fixed Cost
#   5. Margin
#   6. Labor
#   7. Contribution
#   8. Insight Explorer
#   9. Pipeline
#  10. Targets
#
# Design principles
# - CFO-style flow: top-line first, then decomposition
# - All user-facing spelling uses "Labor"
# - Main tables display $M
# - Revenue / COGS / Fixed Cost / Labor tabs use:
#     * service-line chart
#     * explicit sub-service-line drilldown selector
#     * client chart with rank window (top 15 by default)
# - Margin / Contribution tabs keep the bubble chart as the focus
# - Insight Explorer is the interactive super-tab for finance investigation
# ============================================================

import base64
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.models.financials import (
    get_gross_margin,
    get_pipeline,
    get_targets,
    get_labour_by_client,
)

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="MarketCast Finance",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Branding
# ------------------------------------------------------------
def get_base64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


logo_base64 = get_base64_image("assets/logo.png")

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background: #07090e;
        color: #f3f4f6;
    }

    .block-container {
        padding: 1.6rem 2.1rem 2.3rem 2.1rem;
        max-width: 100% !important;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1016 0%, #090b10 100%);
        border-right: 1px solid #1b2230;
    }

    div[data-testid="stSidebar"] .block-container {
        padding: 1.25rem 0.95rem 1.8rem 0.95rem;
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }

    .sb-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }

    .sb-logo {
        width: 28px;
        height: 28px;
        object-fit: contain;
        border-radius: 6px;
        flex-shrink: 0;
    }

    .sb-brand-name {
        font-size: 17px;
        font-weight: 700;
        color: #f5f7fb;
        letter-spacing: -0.02em;
        line-height: 1;
    }

    .sb-brand-sub {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #667085;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .sb-section {
        background: #0f131b;
        border: 1px solid #1b2230;
        border-radius: 14px;
        padding: 0.95rem 0.85rem 0.5rem 0.85rem;
        margin-bottom: 0.8rem;
    }

    .sb-section-title {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.65rem;
    }

    .sb-active-view {
        background: linear-gradient(180deg, rgba(215,243,74,0.08) 0%, rgba(215,243,74,0.03) 100%);
        border: 1px solid rgba(215,243,74,0.16);
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        margin-top: 0.2rem;
    }

    .sb-view-label {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #d7f34a;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .sb-view-value {
        font-size: 13px;
        font-weight: 600;
        color: #f3f4f6;
        margin-bottom: 0.35rem;
    }

    .sb-view-sub {
        font-size: 11px;
        color: #9ca3af;
        line-height: 1.45;
    }

    .sb-bottom-spacer {
        flex: 1 1 auto;
        min-height: 1rem;
    }

    .stSelectbox label,
    .stRadio > label,
    .stSelectSlider > label,
    .stToggle label,
    .stTextInput label {
        font-family: 'DM Mono', monospace !important;
        font-size: 9px !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: #6b7280 !important;
    }

    div[data-baseweb="select"] > div {
        background: #090d14 !important;
        border: 1px solid #202938 !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] span {
        color: #e5e7eb !important;
    }

    div[data-baseweb="select"] svg {
        fill: #6b7280 !important;
    }

    div[role="radiogroup"] label {
        background: #0a0d14;
        border: 1px solid #202938;
        border-radius: 10px;
        padding: 0.35rem 0.6rem;
    }

    .metric-card {
        background: linear-gradient(180deg, #0c1017 0%, #0a0d13 100%);
        border: 1px solid #1b2230;
        border-radius: 14px;
        padding: 0.95rem 1.05rem;
        min-height: 88px;
    }

    .metric-label {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.45rem;
        white-space: nowrap;
    }

    .metric-value {
        font-size: 19px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.05;
        letter-spacing: -0.03em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .metric-delta {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        margin-top: 0.45rem;
        white-space: nowrap;
    }

    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }

    .formula-bar {
        background: #0b0f16;
        border: 1px solid #18202d;
        border-radius: 12px;
        padding: 0.75rem 0.95rem;
        margin-bottom: 1rem;
    }

    .formula-text {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: #a3aab8;
        letter-spacing: 0.02em;
    }

    .section-header {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #6b7280;
        border-bottom: 1px solid #161c27;
        padding-bottom: 0.45rem;
        margin-bottom: 1rem;
        margin-top: 1.6rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid #161c27;
        gap: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #667085;
        padding: 0.7rem 1.25rem;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        background: transparent;
    }

    .stTabs [aria-selected="true"] {
        color: #d7f34a !important;
        border-bottom: 2px solid #d7f34a !important;
        background: transparent !important;
    }

    .stExpander {
        border: 1px solid #1b2230 !important;
        border-radius: 12px !important;
        background: #0b0f16 !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
MONTH_MAP = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}
MONTH_NAMES = [MONTH_MAP[i] for i in range(1, 13)]
EXCL = ["Unassigned", "(blank)"]

THEME_OPTIONS = [
    "Executive / minimal",
    "Finance / Bloomberg-ish",
    "MarketCast-accented",
    "Monochrome blue",
    "Grey + accent",
]

# ------------------------------------------------------------
# Theme helpers
# ------------------------------------------------------------
def get_theme_palette(name: str):
    themes = {
        "Executive / minimal": {
            "series": ["#7aa2f7", "#5b7cbe", "#4b5563", "#94a3b8", "#64748b"],
            "blue_scale": ["#1e3a5f", "#2f5f9e", "#7aa2f7"],
            "donut": ["#93c5fd", "#60a5fa", "#3b82f6"],
            "wf_total": "#d4af37",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#7aa2f7",
            "line_prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Finance / Bloomberg-ish": {
            "series": ["#4c78a8", "#2f4b7c", "#6b7280", "#9ca3af", "#1f5a91"],
            "blue_scale": ["#0f2d4a", "#1f5a91", "#5fa8ff"],
            "donut": ["#0f4c81", "#2563eb", "#60a5fa"],
            "wf_total": "#93c5fd",
            "wf_pos": "#4ade80",
            "wf_neg": "#ef4444",
            "line_current": "#60a5fa",
            "line_prior": "#6b7280",
            "accent_scale": ["#0f2d4a", "#5fa8ff"],
        },
        "MarketCast-accented": {
            "series": ["#d7f34a", "#4ade80", "#60a5fa", "#a78bfa", "#fb923c"],
            "blue_scale": ["#1e3a5f", "#3b82f6", "#d7f34a"],
            "donut": ["#d7f34a", "#60a5fa", "#a78bfa"],
            "wf_total": "#d7f34a",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#d7f34a",
            "line_prior": "#475569",
            "accent_scale": ["#141a0d", "#d7f34a"],
        },
        "Monochrome blue": {
            "series": ["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
            "blue_scale": ["#17324d", "#2b6ea5", "#93c5fd"],
            "donut": ["#93c5fd", "#60a5fa", "#2563eb"],
            "wf_total": "#60a5fa",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#60a5fa",
            "line_prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Grey + accent": {
            "series": ["#94a3b8", "#64748b", "#475569", "#d7f34a", "#334155"],
            "blue_scale": ["#334155", "#64748b", "#d7f34a"],
            "donut": ["#475569", "#64748b", "#d7f34a"],
            "wf_total": "#d7f34a",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#94a3b8",
            "line_prior": "#475569",
            "accent_scale": ["#334155", "#d7f34a"],
        },
    }
    return themes[name]


PT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    xaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1"),
    ),
    yaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1"),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=10),
    ),
    margin=dict(l=0, r=0, t=40, b=0),
)

# ------------------------------------------------------------
# Generic helpers
# ------------------------------------------------------------
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


def clean_for_visuals(df, client_col="top_level_parent_customer_name"):
    d = df.copy()
    for col in ["service_line_name", "sub_service_line_name", "vertical_name"]:
        if col in d.columns:
            d = d[d[col] != "(blank)"]
    if client_col in d.columns:
        d = d[~d[client_col].isin(EXCL)]
    return d


def apply_dim_filters(d):
    if selected_sl != "All":
        d = d[d["service_line_name"] == selected_sl]
    if selected_ssl != "All":
        d = d[d["sub_service_line_name"] == selected_ssl]
    if selected_vertical != "All":
        d = d[d["vertical_name"] == selected_vertical]
    if selected_customer != "All":
        d = d[d["top_level_parent_customer_name"] == selected_customer]
    return d


def filt(data, year, m1=1, m2=12):
    d = data[(data["yr"] == year) & (data["month_num"] >= m1) & (data["month_num"] <= m2)].copy()
    return apply_dim_filters(d)


def rolling_ym(base_year, end_month):
    start_month = (end_month % 12) + 1
    if start_month == 1:
        return [(base_year, m) for m in range(1, 13)]
    return (
        [(base_year - 1, m) for m in range(start_month, 13)] +
        [(base_year, m) for m in range(1, end_month + 1)]
    )


def filt_rolling(data, ym_list):
    if not ym_list:
        return pd.DataFrame(columns=data.columns)
    mask = pd.Series(False, index=data.index)
    for yr, mn in ym_list:
        mask |= ((data["yr"] == yr) & (data["month_num"] == mn))
    d = data[mask].copy()
    return apply_dim_filters(d)


def ordered_month_axis_labels(ym_list):
    return [MONTH_MAP[m] for _, m in ym_list]


def rank_window_slice(df, sort_col, start_rank, window_size=15):
    d = df.sort_values(sort_col, ascending=False).reset_index(drop=True).copy()
    d["rank"] = d.index + 1
    end_rank = start_rank + window_size - 1
    return d[(d["rank"] >= start_rank) & (d["rank"] <= end_rank)].copy(), end_rank, len(d)


def rank_window_options(n_items, window_size=15):
    if n_items <= 0:
        return [1]
    return list(range(1, n_items + 1, window_size))


def service_line_selector_block(
    agg_df: pd.DataFrame,
    selected_metric_col: str,
    revenue_col: str,
    title_prefix: str,
    color_scale,
    percent_label: str,
    selector_key: str,
):
    d = clean_for_visuals(agg_df, client_col="top_level_parent_customer_name")
    sl_options = sorted(d["service_line_name"].dropna().unique().tolist())
    if not sl_options:
        st.info(f"No {title_prefix.lower()} drilldown available for the current selection.")
        return

    selected_service = st.selectbox(
        f"{title_prefix} drilldown — service line",
        sl_options,
        key=selector_key,
    )

    sub = (
        d[d["service_line_name"] == selected_service]
        .groupby("sub_service_line_name", dropna=False)
        .agg(metric=(selected_metric_col, "sum"), revenue=(revenue_col, "sum"))
        .reset_index()
    )
    sub = sub[sub["sub_service_line_name"] != "(blank)"]
    sub["pct_of_rev"] = (sub["metric"] / sub["revenue"].replace(0, float("nan")) * 100).round(1)
    sub = sub.sort_values("metric", ascending=True)

    fig = px.bar(
        sub,
        x="metric",
        y="sub_service_line_name",
        orientation="h",
        color="metric",
        color_continuous_scale=color_scale,
        text=sub["pct_of_rev"].map(pct_text),
        title=f"{title_prefix} — {selected_service}",
        labels={"metric": f"{title_prefix} ($)", "sub_service_line_name": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=360)
    fig.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig, use_container_width=True)

    sub_display = sub.copy()
    sub_display["metric"] = (sub_display["metric"] / 1e6).round(2)
    sub_display["revenue"] = (sub_display["revenue"] / 1e6).round(2)

    metric_col_name = f"{title_prefix} ($M)"
    revenue_col_name = "Revenue ($M)"
    if title_prefix == "Revenue":
        revenue_col_name = "Total Revenue ($M)"

    sub_display = sub_display.rename(columns={
        "sub_service_line_name": "Sub Service Line",
        "metric": metric_col_name,
        "revenue": revenue_col_name,
        "pct_of_rev": percent_label,
    })

    st.dataframe(
        sub_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            metric_col_name: st.column_config.NumberColumn(metric_col_name, format="$%.2f"),
            revenue_col_name: st.column_config.NumberColumn(revenue_col_name, format="$%.2f"),
            percent_label: st.column_config.NumberColumn(percent_label, format="%.1f%%"),
        },
    )


def build_explorer_detail(df_curr_in: pd.DataFrame, df_lab_curr_in: pd.DataFrame) -> pd.DataFrame:
    """
    Build a single detailed grain table at:
      service line × sub service line × client
    with all core P&L metrics and ratios.
    """
    gm_detail = (
        df_curr_in.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )

    labor_detail = (
        df_lab_curr_in.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    detail = gm_detail.merge(
        labor_detail,
        on=["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
        how="left",
    )
    detail["labor"] = detail["labor"].fillna(0)
    detail["contribution"] = detail["gross_margin"] - detail["labor"]

    detail["gm_pct"] = (detail["gross_margin"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["cm_pct"] = (detail["contribution"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["cogs_pct"] = (detail["cogs"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["fixed_cost_pct"] = (detail["fixed_cost"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["labor_pct"] = (detail["labor"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)

    return detail


def waterfall_for_slice(row, title: str):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total", "relative", "total"],
        x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labor", "Contribution"],
        y=[row["revenue"], -row["cogs"], -row["fixed_cost"], None, -row["labor"], None],
        connector={"line": {"color": "#243041"}},
        increasing={"marker": {"color": WFP, "line": {"width": 0}}},
        decreasing={"marker": {"color": WFN, "line": {"width": 0}}},
        totals={"marker": {"color": WFT, "line": {"width": 0}}},
        text=[
            fmt_m(row["revenue"]),
            fmt_m(row["cogs"]),
            fmt_m(row["fixed_cost"]),
            fmt_m(row["gross_margin"]),
            fmt_m(row["labor"]),
            fmt_m(row["contribution"]),
        ],
        textposition="outside",
    ))
    fig.update_layout(**PT, title=title, title_font_color="#cbd5e1", showlegend=False, height=420)
    return fig


def summary_cards_for_slice(row, metric_label: str, metric_col: str):
    cards = st.columns(4)
    cards[0].markdown(kpi(metric_label, row[metric_col]), unsafe_allow_html=True)
    cards[1].markdown(kpi("GM %", row["gm_pct"], kind="pct"), unsafe_allow_html=True)
    cards[2].markdown(kpi("CM %", row["cm_pct"], kind="pct"), unsafe_allow_html=True)
    cards[3].markdown(kpi("Revenue", row["revenue"]), unsafe_allow_html=True)


# ------------------------------------------------------------
# Data loading
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df_gm = get_gross_margin(year_from=2022).copy()
    df_gm["accounting_period_start_date"] = pd.to_datetime(df_gm["accounting_period_start_date"])
    df_gm["yr"] = df_gm["accounting_period_start_date"].dt.year
    df_gm["month_num"] = df_gm["accounting_period_start_date"].dt.month

    for c in ["revenue", "cogs", "labour", "be_allocation", "ae_allocation", "rta_allocation", "gross_margin"]:
        df_gm[c] = df_gm[c].fillna(0)

    df_gm["fixed_cost"] = df_gm["be_allocation"] + df_gm["ae_allocation"] + df_gm["rta_allocation"]
    df_gm["contribution"] = df_gm["gross_margin"] - df_gm["labour"]

    for c in ["service_line_name", "sub_service_line_name", "vertical_name", "top_level_parent_customer_name"]:
        df_gm[c] = df_gm[c].fillna("(blank)")

    df_lab = get_labour_by_client(year_from=2022).copy()
    df_lab["accounting_period_start_date"] = pd.to_datetime(df_lab["accounting_period_start_date"])
    df_lab["yr"] = df_lab["accounting_period_start_date"].dt.year
    df_lab["month_num"] = df_lab["accounting_period_start_date"].dt.month

    for c in ["service_line_name", "sub_service_line_name", "vertical_name", "top_level_parent_customer_name"]:
        df_lab[c] = df_lab[c].fillna("(blank)")

    df_pipe = get_pipeline().copy()
    if "pipeline_value_usd" in df_pipe.columns:
        df_pipe["pipeline_value_usd"] = df_pipe["pipeline_value_usd"].fillna(0)
    for c in ["service_line", "vertical"]:
        if c in df_pipe.columns:
            df_pipe[c] = df_pipe[c].fillna("(blank)")

    df_tgt = get_targets().copy()
    df_tgt["quarter_start_date"] = pd.to_datetime(df_tgt["quarter_start_date"])
    df_tgt["yr"] = df_tgt["quarter_start_date"].dt.year

    return df_gm, df_lab, df_pipe, df_tgt


df_gm, df_lab, df_pipe, df_tgt = load_data()

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div class="sb-brand"><img src="data:image/png;base64,{logo_base64}" class="sb-logo"/>'
        f'<div><div class="sb-brand-name">MarketCast</div>'
        f'<div class="sb-brand-sub">Finance Dashboard</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sb-section"><div class="sb-section-title">Time Period</div>', unsafe_allow_html=True)
    years = sorted(df_gm["yr"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("Year", years, index=years.index(2025) if 2025 in years else 0)
    view_mode = st.radio("View", ["Full Year", "YTD / Range", "Rolling 12M"], horizontal=False)

    is_rolling = False
    curr_ym = []
    prior_ym = []

    if view_mode == "YTD / Range":
        avail = sorted(df_gm[df_gm["yr"] == selected_year]["month_num"].dropna().unique().tolist())
        max_m = max(avail) if avail else 12
        month_range = st.select_slider("Month Range", options=MONTH_NAMES, value=("Jan", MONTH_MAP[max_m]))
        m_from = MONTH_NAMES.index(month_range[0]) + 1
        m_to = MONTH_NAMES.index(month_range[1]) + 1
        period_label = f"{month_range[0]}–{month_range[1]} {selected_year}"

    elif view_mode == "Rolling 12M":
        avail = sorted(df_gm[df_gm["yr"] == selected_year]["month_num"].dropna().unique().tolist())
        default_end = max(avail) if avail else 12
        end_month_name = st.select_slider(
            "Rolling window end month",
            options=MONTH_NAMES,
            value=MONTH_MAP[default_end],
        )
        end_month = MONTH_NAMES.index(end_month_name) + 1
        curr_ym = rolling_ym(selected_year, end_month)
        prior_ym = rolling_ym(selected_year - 1, end_month)
        is_rolling = True

        start_year, start_month = curr_ym[0]
        period_label = f"Rolling 12M: {MONTH_MAP[start_month]} {start_year}–{MONTH_MAP[end_month]} {selected_year}"
        m_from, m_to = 1, 12

    else:
        m_from, m_to = 1, 12
        period_label = f"{selected_year} Full Year"

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section"><div class="sb-section-title">Business Filters</div>', unsafe_allow_html=True)
    sl_opts = ["All"] + sorted([x for x in df_gm["service_line_name"].unique() if x != "(blank)"])
    selected_sl = st.selectbox("Service Line", sl_opts)

    ssl_pool = df_gm if selected_sl == "All" else df_gm[df_gm["service_line_name"] == selected_sl]
    ssl_opts = ["All"] + sorted([x for x in ssl_pool["sub_service_line_name"].unique() if x != "(blank)"])
    selected_ssl = st.selectbox("Sub Service Line", ssl_opts)

    v_pool = ssl_pool if selected_ssl == "All" else ssl_pool[ssl_pool["sub_service_line_name"] == selected_ssl]
    v_opts = ["All"] + sorted([x for x in v_pool["vertical_name"].unique() if x != "(blank)"])
    selected_vertical = st.selectbox("Vertical", v_opts)

    c_pool = v_pool if selected_vertical == "All" else v_pool[v_pool["vertical_name"] == selected_vertical]
    c_opts = ["All"] + sorted([x for x in c_pool["top_level_parent_customer_name"].unique() if x not in EXCL])
    selected_customer = st.selectbox("Client", c_opts)
    st.markdown('</div>', unsafe_allow_html=True)

    filters_active = [x for x in [
        selected_sl if selected_sl != "All" else None,
        selected_ssl if selected_ssl != "All" else None,
        selected_vertical if selected_vertical != "All" else None,
        selected_customer if selected_customer != "All" else None,
    ] if x]

    st.markdown(
        f'<div class="sb-active-view"><div class="sb-view-label">Active View</div>'
        f'<div class="sb-view-value">{period_label}</div>'
        f'<div class="sb-view-sub">{" · ".join(filters_active) if filters_active else "No additional filters"}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sb-bottom-spacer"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section"><div class="sb-section-title">Visual Style</div>', unsafe_allow_html=True)
    selected_theme = st.radio("Visual Style", THEME_OPTIONS, index=1)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# Theme extraction
# ------------------------------------------------------------
palette = get_theme_palette(selected_theme)
SC = palette["series"]
BS = palette["blue_scale"]
DC = palette["donut"]
WFT = palette["wf_total"]
WFP = palette["wf_pos"]
WFN = palette["wf_neg"]
LC = palette["line_current"]
LP = palette["line_prior"]
AC = palette["accent_scale"]

# ------------------------------------------------------------
# Current/prior dataframes
# ------------------------------------------------------------
if is_rolling:
    df_curr = filt_rolling(df_gm, curr_ym)
    df_prior = filt_rolling(df_gm, prior_ym)
    df_lab_curr = filt_rolling(df_lab, curr_ym)
    df_lab_prior = filt_rolling(df_lab, prior_ym)
else:
    df_curr = filt(df_gm, selected_year, m_from, m_to)
    df_prior = filt(df_gm, selected_year - 1, m_from, m_to)
    df_lab_curr = filt(df_lab, selected_year, m_from, m_to)
    df_lab_prior = filt(df_lab, selected_year - 1, m_from, m_to)

# ------------------------------------------------------------
# Core headline metrics
# ------------------------------------------------------------
rev = df_curr["revenue"].sum()
cogs = df_curr["cogs"].sum()
fixed_cost = df_curr["fixed_cost"].sum()
labor = df_lab_curr["labour_cost"].sum() if not df_lab_curr.empty else df_curr["labour"].sum()
gm = rev - cogs - fixed_cost
contrib = gm - labor

rev_py = df_prior["revenue"].sum()
cogs_py = df_prior["cogs"].sum()
fixed_cost_py = df_prior["fixed_cost"].sum()
labor_py = df_lab_prior["labour_cost"].sum() if not df_lab_prior.empty else df_prior["labour"].sum()
gm_py = rev_py - cogs_py - fixed_cost_py
contrib_py = gm_py - labor_py

num_clients = df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()
clients_py = df_prior[~df_prior["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()

gm_pct = safe_pct(gm, rev)
cm_pct = safe_pct(contrib, rev)
gm_pct_py = safe_pct(gm_py, rev_py)
cm_pct_py = safe_pct(contrib_py, rev_py)
fc_pct = safe_pct(fixed_cost, rev)
fc_pct_py = safe_pct(fixed_cost_py, rev_py)
lab_pct = safe_pct(labor, rev)
lab_pct_py = safe_pct(labor_py, rev_py)

# ------------------------------------------------------------
# Header + KPI rows
# ------------------------------------------------------------
st.markdown(f"### Finance Dashboard — {period_label}")
st.markdown(
    '<div class="formula-bar"><div class="formula-text">'
    'Gross Margin = Revenue – COGS – Fixed Cost &nbsp;&nbsp;|&nbsp;&nbsp; '
    'Contribution = Gross Margin – Labor'
    '</div></div>',
    unsafe_allow_html=True,
)

r1 = st.columns(8)
r1[0].markdown(kpi("Revenue", rev, rev - rev_py, "vs PY"), unsafe_allow_html=True)
r1[1].markdown(kpi("Clients", num_clients, num_clients - clients_py, "vs PY", kind="count"), unsafe_allow_html=True)
r1[2].markdown(kpi("COGS", cogs, cogs - cogs_py, "vs PY"), unsafe_allow_html=True)
r1[3].markdown(kpi("Fixed Cost", fixed_cost, fixed_cost - fixed_cost_py, "vs PY"), unsafe_allow_html=True)
r1[4].markdown(kpi("Labor", labor, labor - labor_py, "vs PY"), unsafe_allow_html=True)
r1[5].markdown(kpi("Gross Margin", gm, gm - gm_py, "vs PY"), unsafe_allow_html=True)
r1[6].markdown(kpi("GM %", gm_pct, gm_pct - gm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r1[7].markdown(kpi("Contribution", contrib, contrib - contrib_py, "vs PY"), unsafe_allow_html=True)

r2 = st.columns(8)
r2[0].markdown(kpi("Contribution %", cm_pct, cm_pct - cm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[1].markdown(kpi("Fixed Cost % Rev", fc_pct, fc_pct - fc_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[2].markdown(kpi("Labor % Rev", lab_pct, lab_pct - lab_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)

st.divider()

# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------
tab_ov, tab_rev, tab_cogs, tab_fc, tab_margin, tab_labor, tab_contrib, tab_explorer, tab_pipe, tab_tgt = st.tabs([
    "Overview",
    "Revenue",
    "COGS",
    "Fixed Cost",
    "Margin",
    "Labor",
    "Contribution",
    "Insight Explorer",
    "Pipeline",
    "Targets",
])

# ============================================================
# TAB 1 — OVERVIEW
# ============================================================
with tab_ov:
    col_wf, col_yoy = st.columns(2)

    with col_wf:
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total", "relative", "total"],
            x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labor", "Contribution"],
            y=[rev, -cogs, -fixed_cost, None, -labor, None],
            connector={"line": {"color": "#243041"}},
            increasing={"marker": {"color": WFP, "line": {"width": 0}}},
            decreasing={"marker": {"color": WFN, "line": {"width": 0}}},
            totals={"marker": {"color": WFT, "line": {"width": 0}}},
            text=[fmt_m(rev), fmt_m(cogs), fmt_m(fixed_cost), fmt_m(gm), fmt_m(labor), fmt_m(contrib)],
            textfont={"color": "#cbd5e1", "size": 10, "family": "DM Mono"},
            textposition="outside",
        ))
        wf.update_layout(**PT, title="P&L Bridge — Revenue to Contribution", title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(wf, use_container_width=True)

    with col_yoy:
        if is_rolling:
            month_labels = ordered_month_axis_labels(curr_ym)

            curr_monthly = (
                df_curr.groupby(["yr", "month_num"])["revenue"]
                .sum()
                .reset_index()
            )
            prior_monthly = (
                df_prior.groupby(["yr", "month_num"])["revenue"]
                .sum()
                .reset_index()
            )

            rows = []
            for i, (yr, mn) in enumerate(curr_ym):
                val = curr_monthly.loc[
                    (curr_monthly["yr"] == yr) & (curr_monthly["month_num"] == mn),
                    "revenue"
                ]
                rows.append({"order": i, "label": month_labels[i], "Revenue": float(val.iloc[0]) if len(val) else 0, "Period": "Current"})

            for i, (yr, mn) in enumerate(prior_ym):
                val = prior_monthly.loc[
                    (prior_monthly["yr"] == yr) & (prior_monthly["month_num"] == mn),
                    "revenue"
                ]
                rows.append({"order": i, "label": month_labels[i], "Revenue": float(val.iloc[0]) if len(val) else 0, "Period": "Prior Year"})

            yoy_df = pd.DataFrame(rows)
            x_col = "label"
            x_order = month_labels

        else:
            months_in_range = list(range(m_from, m_to + 1))
            cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Current"})
            py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Prior Year"})
            base = pd.DataFrame({"month_num": months_in_range})
            yoy_raw = base.merge(cy, on="month_num", how="left").merge(py, on="month_num", how="left").fillna(0)
            yoy_raw["label"] = yoy_raw["month_num"].map(MONTH_MAP)
            yoy_df = yoy_raw.melt(
                id_vars=["month_num", "label"],
                value_vars=["Current", "Prior Year"],
                var_name="Period",
                value_name="Revenue",
            )
            x_col = "label"
            x_order = [MONTH_MAP[m] for m in months_in_range]

        fig = px.line(
            yoy_df,
            x=x_col,
            y="Revenue",
            color="Period",
            markers=True,
            color_discrete_map={"Current": LC, "Prior Year": LP},
            title="Revenue vs Prior Year",
            labels={x_col: "", "Revenue": "Revenue ($)"},
            category_orders={x_col: x_order},
        )
        fig.update_traces(line_width=2.5)
        fig.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig.update_yaxes(tickformat="$,.0f")
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 2 — REVENUE
# ============================================================
with tab_rev:
    st.markdown('<div class="section-header">Revenue Decomposition</div>', unsafe_allow_html=True)

    col_rsl, col_rcl = st.columns(2)

    with col_rsl:
        rv_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")["revenue"]
            .sum()
            .reset_index()
        )
        rv_sl = rv_sl[rv_sl["revenue"] > 0].sort_values("revenue", ascending=True)

        fig = px.bar(
            rv_sl,
            x="revenue",
            y="service_line_name",
            orientation="h",
            color="service_line_name",
            color_discrete_sequence=SC,
            title="Revenue by Service Line",
            labels={"revenue": "Revenue ($)", "service_line_name": ""},
        )
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**PT, showlegend=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_rcl:
        rv_cl = (
            clean_for_visuals(df_curr)
            .groupby("top_level_parent_customer_name")["revenue"]
            .sum()
            .reset_index()
        )
        start_options = rank_window_options(len(rv_cl), 15)
        start_rank = st.select_slider(
            "Show client ranks",
            options=start_options,
            value=1,
            key="rev_client_rank",
        )
        rv_cl_window, end_rank, total_clients = rank_window_slice(rv_cl, "revenue", start_rank, 15)

        fig = px.bar(
            rv_cl_window,
            x="revenue",
            y="top_level_parent_customer_name",
            orientation="h",
            color="revenue",
            color_continuous_scale=BS,
            title=f"Revenue by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"revenue": "Revenue ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Revenue Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_curr,
        selected_metric_col="revenue",
        revenue_col="revenue",
        title_prefix="Revenue",
        color_scale=BS,
        percent_label="Share of Revenue",
        selector_key="rev_sl_selector",
    )

    st.markdown('<div class="section-header">Revenue Detail — Service Line × Sub Service Line ($M)</div>', unsafe_allow_html=True)
    lab_join = (
        df_lab_curr.groupby(["service_line_name", "sub_service_line_name"])["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )
    rv_tbl = (
        df_curr.groupby(["service_line_name", "sub_service_line_name"], dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique()),
        )
        .reset_index()
    )
    rv_tbl = rv_tbl.merge(lab_join, on=["service_line_name", "sub_service_line_name"], how="left")
    rv_tbl["labor"] = rv_tbl["labor"].fillna(0)
    rv_tbl["contribution"] = rv_tbl["gross_margin"] - rv_tbl["labor"]
    rv_tbl["gm_pct"] = (rv_tbl["gross_margin"] / rv_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    rv_tbl["cm_pct"] = (rv_tbl["contribution"] / rv_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        rv_tbl[c] = (rv_tbl[c] / 1e6).round(2)
    rv_tbl = rv_tbl.sort_values(["service_line_name", "revenue"], ascending=[True, False])
    rv_tbl.columns = [c.replace("_", " ").title() for c in rv_tbl.columns]
    st.dataframe(
        rv_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "Gm Pct": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("CM %", format="%.1f%%"),
            "Clients": st.column_config.NumberColumn("Clients", format="%d"),
        },
    )

    st.markdown('<div class="section-header">Revenue by Client ($M)</div>', unsafe_allow_html=True)
    lab_cl_join = (
        df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )
    cl_rev_tbl = (
        df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]
        .groupby("top_level_parent_customer_name")
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )
    cl_rev_tbl = cl_rev_tbl.merge(lab_cl_join, on="top_level_parent_customer_name", how="left")
    cl_rev_tbl["labor"] = cl_rev_tbl["labor"].fillna(0)
    cl_rev_tbl["contribution"] = cl_rev_tbl["gross_margin"] - cl_rev_tbl["labor"]
    cl_rev_tbl["gm_pct"] = (cl_rev_tbl["gross_margin"] / cl_rev_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    cl_rev_tbl["cm_pct"] = (cl_rev_tbl["contribution"] / cl_rev_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        cl_rev_tbl[c] = (cl_rev_tbl[c] / 1e6).round(2)
    cl_rev_tbl = cl_rev_tbl.sort_values("revenue", ascending=False)
    cl_rev_tbl.columns = [c.replace("_", " ").title() for c in cl_rev_tbl.columns]
    st.dataframe(
        cl_rev_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "Gm Pct": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("CM %", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 3 — COGS
# ============================================================
with tab_cogs:
    st.markdown('<div class="section-header">COGS Decomposition</div>', unsafe_allow_html=True)

    col_csl, col_ccl = st.columns(2)

    with col_csl:
        cogs_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")
            .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
            .reset_index()
        )
        cogs_sl["pct_of_rev"] = (cogs_sl["cogs"] / cogs_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        cogs_sl = cogs_sl[cogs_sl["cogs"] > 0].sort_values("cogs", ascending=True)

        fig = px.bar(
            cogs_sl,
            x="cogs",
            y="service_line_name",
            orientation="h",
            color="cogs",
            color_continuous_scale=BS,
            text=cogs_sl["pct_of_rev"].map(pct_text),
            title="COGS by Service Line",
            labels={"cogs": "COGS ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_ccl:
        cogs_cl = (
            clean_for_visuals(df_curr)
            .groupby("top_level_parent_customer_name")
            .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
            .reset_index()
        )
        cogs_cl["pct_of_rev"] = (cogs_cl["cogs"] / cogs_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(cogs_cl), 15)
        start_rank = st.select_slider(
            "Show client ranks",
            options=start_options,
            value=1,
            key="cogs_client_rank",
        )
        cogs_cl_window, end_rank, total_clients = rank_window_slice(cogs_cl, "cogs", start_rank, 15)

        fig = px.bar(
            cogs_cl_window,
            x="cogs",
            y="top_level_parent_customer_name",
            orientation="h",
            color="cogs",
            color_continuous_scale=BS,
            text=cogs_cl_window["pct_of_rev"].map(pct_text),
            title=f"COGS by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"cogs": "COGS ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">COGS Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_curr,
        selected_metric_col="cogs",
        revenue_col="revenue",
        title_prefix="COGS",
        color_scale=BS,
        percent_label="COGS % Rev",
        selector_key="cogs_sl_selector",
    )

    st.markdown('<div class="section-header">COGS Detail ($M)</div>', unsafe_allow_html=True)
    cg_tbl = (
        df_curr.groupby(["service_line_name", "sub_service_line_name"], dropna=False)
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
        .reset_index()
    )
    cg_tbl["cogs_pct"] = (cg_tbl["cogs"] / cg_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    cg_tbl["cogs"] = (cg_tbl["cogs"] / 1e6).round(2)
    cg_tbl["revenue"] = (cg_tbl["revenue"] / 1e6).round(2)
    cg_tbl = cg_tbl.sort_values(["service_line_name", "cogs"], ascending=[True, False])
    cg_tbl.columns = [c.replace("_", " ").title() for c in cg_tbl.columns]
    st.dataframe(
        cg_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Cogs Pct": st.column_config.NumberColumn("COGS %", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 4 — FIXED COST
# ============================================================
with tab_fc:
    st.markdown('<div class="section-header">Fixed Cost Split</div>', unsafe_allow_html=True)

    asp = pd.DataFrame({
        "Type": ["Brand Effect", "AE Synd", "RTA"],
        "Amount": [
            df_curr["be_allocation"].sum(),
            df_curr["ae_allocation"].sum(),
            df_curr["rta_allocation"].sum(),
        ],
    })
    asp = asp[asp["Amount"] > 0]

    fig_donut = px.pie(
        asp,
        names="Type",
        values="Amount",
        hole=0.68,
        title="Fixed Cost Split — Brand Effect / AE Synd / RTA",
        color="Type",
        color_discrete_map={"Brand Effect": DC[0], "AE Synd": DC[1], "RTA": DC[2]},
    )
    fig_donut.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
    fig_donut.add_annotation(
        text=fmt_m(fixed_cost),
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="#f8fafc", family="DM Sans"),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown('<div class="section-header">Fixed Cost Decomposition</div>', unsafe_allow_html=True)
    col_fsl, col_fcl = st.columns(2)

    with col_fsl:
        fc_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")
            .agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum"))
            .reset_index()
        )
        fc_sl["pct_of_rev"] = (fc_sl["fixed_cost"] / fc_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        fc_sl = fc_sl[fc_sl["fixed_cost"] > 0].sort_values("fixed_cost", ascending=True)

        fig = px.bar(
            fc_sl,
            x="fixed_cost",
            y="service_line_name",
            orientation="h",
            color="fixed_cost",
            color_continuous_scale=BS,
            text=fc_sl["pct_of_rev"].map(pct_text),
            title="Fixed Cost by Service Line",
            labels={"fixed_cost": "Fixed Cost ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_fcl:
        fc_cl = (
            clean_for_visuals(df_curr)
            .groupby("top_level_parent_customer_name")
            .agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum"))
            .reset_index()
        )
        fc_cl["pct_of_rev"] = (fc_cl["fixed_cost"] / fc_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(fc_cl), 15)
        start_rank = st.select_slider(
            "Show client ranks",
            options=start_options,
            value=1,
            key="fc_client_rank",
        )
        fc_cl_window, end_rank, total_clients = rank_window_slice(fc_cl, "fixed_cost", start_rank, 15)

        fig = px.bar(
            fc_cl_window,
            x="fixed_cost",
            y="top_level_parent_customer_name",
            orientation="h",
            color="fixed_cost",
            color_continuous_scale=BS,
            text=fc_cl_window["pct_of_rev"].map(pct_text),
            title=f"Fixed Cost by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"fixed_cost": "Fixed Cost ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Fixed Cost Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_curr,
        selected_metric_col="fixed_cost",
        revenue_col="revenue",
        title_prefix="Fixed Cost",
        color_scale=BS,
        percent_label="Fixed Cost % Rev",
        selector_key="fc_sl_selector",
    )

    st.markdown('<div class="section-header">Fixed Cost by Service Line ($M)</div>', unsafe_allow_html=True)
    fc_tbl = (
        df_curr.groupby("service_line_name")
        .agg(
            revenue=("revenue", "sum"),
            be=("be_allocation", "sum"),
            ae=("ae_allocation", "sum"),
            rta=("rta_allocation", "sum"),
            total_fc=("fixed_cost", "sum"),
        )
        .reset_index()
    )
    fc_tbl["fc_pct"] = (fc_tbl["total_fc"] / fc_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    for c in ["revenue", "be", "ae", "rta", "total_fc"]:
        fc_tbl[c] = (fc_tbl[c] / 1e6).round(2)
    fc_tbl = fc_tbl.sort_values("total_fc", ascending=False)
    fc_tbl.columns = [c.replace("_", " ").title() for c in fc_tbl.columns]
    st.dataframe(
        fc_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Be": st.column_config.NumberColumn("Brand Effect ($M)", format="$%.2f"),
            "Ae": st.column_config.NumberColumn("AE Synd ($M)", format="$%.2f"),
            "Rta": st.column_config.NumberColumn("RTA ($M)", format="$%.2f"),
            "Total Fc": st.column_config.NumberColumn("Total FC ($M)", format="$%.2f"),
            "Fc Pct": st.column_config.NumberColumn("FC % Rev", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 5 — MARGIN
# ============================================================
with tab_margin:
    st.markdown('<div class="section-header">Gross Margin Analysis</div>', unsafe_allow_html=True)

    lab_cl = (
        df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    cl_gm = (
        clean_for_visuals(df_curr)
        .groupby("top_level_parent_customer_name")
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )
    cl_gm = cl_gm.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl_gm["labor"] = cl_gm["labor"].fillna(0)
    cl_gm["contribution"] = cl_gm["gross_margin"] - cl_gm["labor"]
    cl_gm["gm_pct"] = (cl_gm["gross_margin"] / cl_gm["revenue"].replace(0, float("nan")) * 100).round(1)
    cl_gm["cm_pct"] = (cl_gm["contribution"] / cl_gm["revenue"].replace(0, float("nan")) * 100).round(1)
    cl_gm = cl_gm[cl_gm["revenue"] > 0].sort_values("revenue", ascending=False)

    bubble_col, side_col = st.columns([3, 2])

    with bubble_col:
        top_n = st.select_slider(
            "Show top N clients by revenue",
            options=[5, 10, 15, 20, 25, 30],
            value=15,
            key="margin_topn",
        )

        cl_plot = cl_gm.head(top_n)

        fig = px.scatter(
            cl_plot,
            x="revenue",
            y="gm_pct",
            size="gross_margin",
            size_max=48,
            color="gm_pct",
            color_continuous_scale=BS,
            text="top_level_parent_customer_name",
            hover_name="top_level_parent_customer_name",
            hover_data={
                "revenue": ":,.0f",
                "gm_pct": ":.1f",
                "cm_pct": ":.1f",
                "gross_margin": ":,.0f",
                "labor": ":,.0f",
                "contribution": ":,.0f",
            },
            title=f"Client Gross Margin — Top {top_n} by Revenue",
            labels={"revenue": "Revenue ($)", "gm_pct": "Gross Margin %", "gross_margin": "Gross Margin"},
        )
        fig.update_traces(textposition="top center", textfont=dict(size=9, color="#cbd5e1"))
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        gm_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")
            .agg(revenue=("revenue", "sum"), gm=("gross_margin", "sum"))
            .reset_index()
        )
        gm_sl["gm_pct"] = (gm_sl["gm"] / gm_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        gm_sl = gm_sl[gm_sl["revenue"] > 0].sort_values("gm_pct", ascending=True)

        fig = px.bar(
            gm_sl,
            x="gm_pct",
            y="service_line_name",
            orientation="h",
            color="gm_pct",
            color_continuous_scale=BS,
            title="GM % by Service Line",
            labels={"gm_pct": "Gross Margin %", "service_line_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Gross Margin Detail — All Clients ($M)</div>', unsafe_allow_html=True)
    gm_tbl = cl_gm.copy()
    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        gm_tbl[c] = (gm_tbl[c] / 1e6).round(2)
    gm_tbl = gm_tbl.sort_values("revenue", ascending=False)
    gm_tbl.columns = [c.replace("_", " ").title() for c in gm_tbl.columns]
    st.dataframe(
        gm_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "Gm Pct": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("CM %", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 6 — LABOR
# ============================================================
with tab_labor:
    st.markdown('<div class="section-header">Labor Overview</div>', unsafe_allow_html=True)

    total_labor = df_lab_curr["labour_cost"].sum()
    total_labor_py = df_lab_prior["labour_cost"].sum()
    total_hours = df_lab_curr["total_hours"].sum()
    avg_hr = total_labor / total_hours if total_hours > 0 else 0

    lk = st.columns(4)
    lk[0].markdown(kpi("Total Labor", total_labor, total_labor - total_labor_py, "vs PY"), unsafe_allow_html=True)
    lk[1].markdown(kpi("Labor % Rev", safe_pct(total_labor, rev), kind="pct"), unsafe_allow_html=True)
    lk[2].markdown(kpi("Total Hours", total_hours, kind="count"), unsafe_allow_html=True)
    lk[3].markdown(kpi("Avg Cost/hr", avg_hr, kind="dollar"), unsafe_allow_html=True)

    col_lsl, col_lcl = st.columns(2)

    with col_lsl:
        labor_sl = (
            clean_for_visuals(df_lab_curr)
            .groupby("service_line_name")
            .agg(labor=("labour_cost", "sum"))
            .reset_index()
        )
        rev_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")["revenue"]
            .sum()
            .reset_index()
        )
        labor_sl = labor_sl.merge(rev_sl, on="service_line_name", how="left")
        labor_sl["pct_of_rev"] = (labor_sl["labor"] / labor_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        labor_sl = labor_sl[labor_sl["labor"] > 0].sort_values("labor", ascending=True)

        fig = px.bar(
            labor_sl,
            x="labor",
            y="service_line_name",
            orientation="h",
            color="labor",
            color_continuous_scale=BS,
            text=labor_sl["pct_of_rev"].map(pct_text),
            title="Labor by Service Line",
            labels={"labor": "Labor ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_lcl:
        labor_cl = (
            clean_for_visuals(df_lab_curr)
            .groupby("top_level_parent_customer_name")
            .agg(labor=("labour_cost", "sum"))
            .reset_index()
        )
        rev_cl = (
            clean_for_visuals(df_curr)
            .groupby("top_level_parent_customer_name")["revenue"]
            .sum()
            .reset_index()
        )
        labor_cl = labor_cl.merge(rev_cl, on="top_level_parent_customer_name", how="left")
        labor_cl["pct_of_rev"] = (labor_cl["labor"] / labor_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(labor_cl), 15)
        start_rank = st.select_slider(
            "Show client ranks",
            options=start_options,
            value=1,
            key="labor_client_rank",
        )
        labor_cl_window, end_rank, total_clients = rank_window_slice(labor_cl, "labor", start_rank, 15)

        fig = px.bar(
            labor_cl_window,
            x="labor",
            y="top_level_parent_customer_name",
            orientation="h",
            color="labor",
            color_continuous_scale=BS,
            text=labor_cl_window["pct_of_rev"].map(pct_text),
            title=f"Labor by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"labor": "Labor ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Labor Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)

    labor_drill_base = (
        df_lab_curr.merge(
            df_curr[["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name", "revenue"]]
            .groupby(
                ["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
                as_index=False
            )["revenue"].sum(),
            on=["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            how="left"
        )
    )
    labor_drill_base["revenue"] = labor_drill_base["revenue"].fillna(0)
    labor_drill_base["labor_value"] = labor_drill_base["labour_cost"]

    service_line_selector_block(
        agg_df=labor_drill_base,
        selected_metric_col="labor_value",
        revenue_col="revenue",
        title_prefix="Labor",
        color_scale=BS,
        percent_label="Labor % Rev",
        selector_key="labor_sl_selector",
    )

    st.markdown('<div class="section-header">Labor Detail — Client × Service Line ($M)</div>', unsafe_allow_html=True)
    ld = (
        clean_for_visuals(df_lab_curr)
        .groupby(["top_level_parent_customer_name", "service_line_name", "sub_service_line_name"])
        .agg(labour_cost=("labour_cost", "sum"), total_hours=("total_hours", "sum"))
        .reset_index()
        .sort_values("labour_cost", ascending=False)
    )
    ld["cost_per_hour"] = (ld["labour_cost"] / ld["total_hours"].replace(0, float("nan"))).round(0)
    ld["labour_cost"] = (ld["labour_cost"] / 1e6).round(3)
    ld.columns = [c.replace("_", " ").title() for c in ld.columns]
    st.dataframe(
        ld,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Labour Cost": st.column_config.NumberColumn("Labor ($M)", format="$%.3f"),
            "Total Hours": st.column_config.NumberColumn("Hours", format="%.0f"),
            "Cost Per Hour": st.column_config.NumberColumn("$/hr", format="$%.0f"),
        },
    )

# ============================================================
# TAB 7 — CONTRIBUTION
# ============================================================
with tab_contrib:
    st.markdown('<div class="section-header">Contribution Analysis</div>', unsafe_allow_html=True)

    bubble_col, side_col = st.columns([3, 2])

    with bubble_col:
        top_n_cm = st.select_slider(
            "Show top N clients by revenue",
            options=[5, 10, 15, 20, 25, 30],
            value=15,
            key="contrib_topn",
        )

        cl_cm_plot = cl_gm.head(top_n_cm)

        fig = px.scatter(
            cl_cm_plot,
            x="revenue",
            y="cm_pct",
            size="contribution",
            size_max=48,
            color="cm_pct",
            color_continuous_scale=BS,
            text="top_level_parent_customer_name",
            hover_name="top_level_parent_customer_name",
            hover_data={
                "revenue": ":,.0f",
                "gm_pct": ":.1f",
                "cm_pct": ":.1f",
                "gross_margin": ":,.0f",
                "labor": ":,.0f",
                "contribution": ":,.0f",
            },
            title=f"Client Contribution — Top {top_n_cm} by Revenue",
            labels={"revenue": "Revenue ($)", "cm_pct": "Contribution %", "contribution": "Contribution"},
        )
        fig.update_traces(textposition="top center", textfont=dict(size=9, color="#cbd5e1"))
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        cm_sl = (
            clean_for_visuals(df_curr)
            .groupby("service_line_name")
            .agg(revenue=("revenue", "sum"), gm=("gross_margin", "sum"))
            .reset_index()
        )
        lab_sl_cm = (
            clean_for_visuals(df_lab_curr)
            .groupby("service_line_name")["labour_cost"]
            .sum()
            .reset_index()
            .rename(columns={"labour_cost": "labor"})
        )
        cm_sl = cm_sl.merge(lab_sl_cm, on="service_line_name", how="left")
        cm_sl["labor"] = cm_sl["labor"].fillna(0)
        cm_sl["contribution"] = cm_sl["gm"] - cm_sl["labor"]
        cm_sl["cm_pct"] = (cm_sl["contribution"] / cm_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        cm_sl = cm_sl[cm_sl["revenue"] > 0].sort_values("cm_pct", ascending=True)

        fig = px.bar(
            cm_sl,
            x="cm_pct",
            y="service_line_name",
            orientation="h",
            color="cm_pct",
            color_continuous_scale=BS,
            title="Contribution % by Service Line",
            labels={"cm_pct": "Contribution %", "service_line_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Contribution Detail — All Clients ($M)</div>', unsafe_allow_html=True)
    cm_tbl = cl_gm.copy()
    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        cm_tbl[c] = (cm_tbl[c] / 1e6).round(2)
    cm_tbl = cm_tbl.sort_values("contribution", ascending=False)
    cm_tbl.columns = [c.replace("_", " ").title() for c in cm_tbl.columns]
    st.dataframe(
        cm_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "Gm Pct": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("CM %", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 8 — INSIGHT EXPLORER
# Interactive super-tab:
# - metric selector
# - grouping selector
# - drill filters
# - single-slice or compare mode
# - main decomposition chart
# - selected-slice bridge
# - dynamic detail table
# ============================================================
with tab_explorer:
    st.markdown('<div class="section-header">Insight Explorer</div>', unsafe_allow_html=True)

    explorer_detail = build_explorer_detail(df_curr, df_lab_curr)
    explorer_detail = clean_for_visuals(explorer_detail)

    metric_options = {
        "Revenue": "revenue",
        "COGS": "cogs",
        "Fixed Cost": "fixed_cost",
        "Labor": "labor",
        "Gross Margin": "gross_margin",
        "Contribution": "contribution",
    }
    ratio_options = {
        "Absolute $": None,
        "% of Revenue": "ratio_of_revenue",
    }
    level_options = {
        "Service Line": "service_line_name",
        "Sub Service Line": "sub_service_line_name",
        "Client": "top_level_parent_customer_name",
    }

    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        explorer_metric_label = st.selectbox("Metric", list(metric_options.keys()), key="explorer_metric")
    with ctrl2:
        explorer_level_label = st.selectbox("View Level", list(level_options.keys()), key="explorer_level")
    with ctrl3:
        explorer_mode = st.radio("Mode", ["Explore", "Compare"], horizontal=True, key="explorer_mode")
    with ctrl4:
        explorer_top_n = st.select_slider("Top N", options=[10, 15, 20, 25, 30, 50], value=15, key="explorer_topn")

    metric_col = metric_options[explorer_metric_label]
    level_col = level_options[explorer_level_label]

    # Local drill controls inside super-tab
    drill1, drill2, drill3, drill4 = st.columns(4)

    with drill1:
        exp_service = st.selectbox(
            "Service Line Drill",
            ["All"] + sorted(explorer_detail["service_line_name"].dropna().unique().tolist()),
            key="explorer_service",
        )

    exp_df = explorer_detail.copy()
    if exp_service != "All":
        exp_df = exp_df[exp_df["service_line_name"] == exp_service]

    with drill2:
        ssl_options = ["All"] + sorted(exp_df["sub_service_line_name"].dropna().unique().tolist())
        exp_ssl = st.selectbox("Sub Service Line Drill", ssl_options, key="explorer_ssl")

    if exp_ssl != "All":
        exp_df = exp_df[exp_df["sub_service_line_name"] == exp_ssl]

    with drill3:
        client_options = ["All"] + sorted(exp_df["top_level_parent_customer_name"].dropna().unique().tolist())
        exp_client = st.selectbox("Client Drill", client_options, key="explorer_client")

    if exp_client != "All":
        exp_df = exp_df[exp_df["top_level_parent_customer_name"] == exp_client]

    with drill4:
        search_text = st.text_input("Search", value="", key="explorer_search")

    if search_text.strip():
        txt = search_text.strip().lower()
        mask = (
            exp_df["service_line_name"].str.lower().str.contains(txt, na=False) |
            exp_df["sub_service_line_name"].str.lower().str.contains(txt, na=False) |
            exp_df["top_level_parent_customer_name"].str.lower().str.contains(txt, na=False)
        )
        exp_df = exp_df[mask]

    grouped = (
        exp_df.groupby(level_col)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            labor=("labor", "sum"),
            gross_margin=("gross_margin", "sum"),
            contribution=("contribution", "sum"),
        )
        .reset_index()
    )

    grouped["gm_pct"] = (grouped["gross_margin"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["cm_pct"] = (grouped["contribution"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["cogs_pct"] = (grouped["cogs"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["fixed_cost_pct"] = (grouped["fixed_cost"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["labor_pct"] = (grouped["labor"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)

    ratio_map = {
        "revenue": None,
        "cogs": "cogs_pct",
        "fixed_cost": "fixed_cost_pct",
        "labor": "labor_pct",
        "gross_margin": "gm_pct",
        "contribution": "cm_pct",
    }
    ratio_col = ratio_map[metric_col]

    chart_df = grouped.sort_values(metric_col, ascending=False).head(explorer_top_n).copy()

    main_col, side_col = st.columns([3, 2])

    with main_col:
        main_fig = px.bar(
            chart_df.sort_values(metric_col, ascending=True),
            x=metric_col,
            y=level_col,
            orientation="h",
            color=metric_col,
            color_continuous_scale=BS,
            text=chart_df.sort_values(metric_col, ascending=True)[ratio_col].map(pct_text) if ratio_col else None,
            title=f"{explorer_metric_label} by {explorer_level_label}",
            labels={metric_col: f"{explorer_metric_label} ($)", level_col: ""},
        )
        if ratio_col:
            main_fig.update_traces(textposition="outside")
        main_fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        main_fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(main_fig, use_container_width=True)

    with side_col:
        if explorer_mode == "Explore":
            entity_options = chart_df[level_col].tolist() if not chart_df.empty else []
            if entity_options:
                selected_entity = st.selectbox("Selected Slice", entity_options, key="explorer_entity")
                selected_row = grouped[grouped[level_col] == selected_entity].iloc[0]
                summary_cards_for_slice(selected_row, explorer_metric_label, metric_col)
            else:
                selected_entity = None
                st.info("No data for current explorer selection.")
        else:
            entity_options = grouped[level_col].tolist()
            if len(entity_options) >= 2:
                cmp_a = st.selectbox("Compare A", entity_options, key="explorer_cmp_a")
                cmp_b = st.selectbox(
                    "Compare B",
                    [x for x in entity_options if x != cmp_a],
                    key="explorer_cmp_b",
                )

                row_a = grouped[grouped[level_col] == cmp_a].iloc[0]
                row_b = grouped[grouped[level_col] == cmp_b].iloc[0]

                st.markdown("#### Compare")
                ca, cb = st.columns(2)
                ca.markdown(kpi(cmp_a[:18], row_a[metric_col]), unsafe_allow_html=True)
                cb.markdown(kpi(cmp_b[:18], row_b[metric_col]), unsafe_allow_html=True)
                ca.markdown(kpi("GM %", row_a["gm_pct"], kind="pct"), unsafe_allow_html=True)
                cb.markdown(kpi("GM %", row_b["gm_pct"], kind="pct"), unsafe_allow_html=True)
                ca.markdown(kpi("CM %", row_a["cm_pct"], kind="pct"), unsafe_allow_html=True)
                cb.markdown(kpi("CM %", row_b["cm_pct"], kind="pct"), unsafe_allow_html=True)
            else:
                cmp_a = cmp_b = None
                st.info("Need at least two slices to compare.")

    if explorer_mode == "Explore":
        st.markdown('<div class="section-header">Selected Slice Bridge</div>', unsafe_allow_html=True)
        if selected_entity is not None:
            st.plotly_chart(
                waterfall_for_slice(selected_row, f"{selected_entity} — P&L Bridge"),
                use_container_width=True,
            )

            detail_filtered = exp_df[exp_df[level_col] == selected_entity].copy()
        else:
            detail_filtered = exp_df.copy()

    else:
        st.markdown('<div class="section-header">Compare Slice Bridges</div>', unsafe_allow_html=True)
        if 'row_a' in locals() and 'row_b' in locals():
            wa, wb = st.columns(2)
            with wa:
                st.plotly_chart(
                    waterfall_for_slice(row_a, f"{cmp_a} — P&L Bridge"),
                    use_container_width=True,
                )
            with wb:
                st.plotly_chart(
                    waterfall_for_slice(row_b, f"{cmp_b} — P&L Bridge"),
                    use_container_width=True,
                )
            detail_filtered = exp_df[exp_df[level_col].isin([cmp_a, cmp_b])].copy()
        else:
            detail_filtered = exp_df.copy()

    st.markdown('<div class="section-header">Explorer Detail Table ($M)</div>', unsafe_allow_html=True)
    detail_tbl = detail_filtered.copy()
    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        detail_tbl[c] = (detail_tbl[c] / 1e6).round(2)

    detail_tbl = detail_tbl.rename(columns={
        "service_line_name": "Service Line",
        "sub_service_line_name": "Sub Service Line",
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue",
        "cogs": "COGS",
        "fixed_cost": "Fixed Cost",
        "gross_margin": "Gross Margin",
        "labor": "Labor",
        "contribution": "Contribution",
        "gm_pct": "GM %",
        "cm_pct": "CM %",
        "cogs_pct": "COGS % Rev",
        "fixed_cost_pct": "Fixed Cost % Rev",
        "labor_pct": "Labor % Rev",
    })

    st.dataframe(
        detail_tbl.sort_values("Revenue", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "COGS": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "GM %": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "CM %": st.column_config.NumberColumn("CM %", format="%.1f%%"),
            "COGS % Rev": st.column_config.NumberColumn("COGS % Rev", format="%.1f%%"),
            "Fixed Cost % Rev": st.column_config.NumberColumn("Fixed Cost % Rev", format="%.1f%%"),
            "Labor % Rev": st.column_config.NumberColumn("Labor % Rev", format="%.1f%%"),
        },
    )

# ============================================================
# TAB 9 — PIPELINE
# ============================================================
with tab_pipe:
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)

    dp = df_pipe.drop_duplicates("deal_id")
    if "service_line" in dp.columns:
        dp = dp[~dp["service_line"].isin(EXCL)]

    tp = dp["pipeline_value_usd"].sum()
    td = dp["deal_id"].nunique()
    ad = tp / td if td > 0 else 0

    pk = st.columns(3)
    pk[0].markdown(kpi("Total Pipeline", tp), unsafe_allow_html=True)
    pk[1].markdown(kpi("Active Deals", td, kind="count"), unsafe_allow_html=True)
    pk[2].markdown(kpi("Avg Deal Size", ad), unsafe_allow_html=True)

    col_ps, col_psl = st.columns(2)

    with col_ps:
        ps2 = (
            dp.groupby("deal_pipeline_stage_name")
            .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
            .reset_index()
            .sort_values("value", ascending=True)
        )
        fig = px.bar(
            ps2,
            x="value",
            y="deal_pipeline_stage_name",
            orientation="h",
            color="value",
            color_continuous_scale=BS,
            title="Pipeline by Stage",
            labels={"value": "Pipeline Value ($)", "deal_pipeline_stage_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig, use_container_width=True)

    with col_psl:
        psl = (
            dp.groupby("service_line")
            .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
            .reset_index()
            .sort_values("value", ascending=False)
        )
        fig = px.bar(
            psl,
            x="service_line",
            y="value",
            color="value",
            color_continuous_scale=BS,
            title="Pipeline by Service Line",
            labels={"value": "Pipeline Value ($)", "service_line": ""},
        )
        fig.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Pipeline Detail</div>', unsafe_allow_html=True)
    ptbl = (
        dp.groupby(["deal_pipeline_stage_name", "service_line", "vertical"])
        .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
        .reset_index()
        .sort_values("value", ascending=False)
    )
    ptbl["value"] = (ptbl["value"] / 1e6).round(2)
    ptbl.columns = [c.replace("_", " ").title() for c in ptbl.columns]
    st.dataframe(
        ptbl,
        use_container_width=True,
        hide_index=True,
        column_config={"Value": st.column_config.NumberColumn("Value ($M)", format="$%.2f")},
    )

# ============================================================
# TAB 10 — TARGETS
# ============================================================
with tab_tgt:
    st.markdown('<div class="section-header">Targets vs Actuals</div>', unsafe_allow_html=True)

    dty = df_tgt[df_tgt["yr"] == selected_year].copy()
    tt = dty["target_usd"].sum() if not dty.empty else 0
    vt = rev - tt
    ptt = safe_pct(rev, tt) if tt not in (0, None) else 0

    tk = st.columns(4)
    tk[0].markdown(kpi(f"{selected_year} Target", tt), unsafe_allow_html=True)
    tk[1].markdown(kpi("Actual Revenue", rev, vt, "vs Target"), unsafe_allow_html=True)
    tk[2].markdown(kpi("Attainment %", ptt, kind="pct"), unsafe_allow_html=True)
    tk[3].markdown(kpi("Teams", dty["team_primary_name"].nunique() if not dty.empty else 0, kind="count"), unsafe_allow_html=True)

    col_qt, col_ta = st.columns(2)

    with col_qt:
        if not dty.empty:
            qt = (
                dty.assign(ql="Q" + dty["quarter_start_date"].dt.quarter.astype(str))
                .groupby(["ql", "quarter_start_date"], as_index=False)["target_usd"]
                .sum()
                .sort_values("quarter_start_date")
            )
            fig = px.bar(
                qt,
                x="ql",
                y="target_usd",
                color="target_usd",
                color_continuous_scale=BS,
                title="Quarterly Targets",
                labels={"target_usd": "Target ($M)", "ql": "Quarter"},
                category_orders={"ql": qt["ql"].tolist()},
            )
            fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No target data for {selected_year}. Targets only from Q1 2025.")

    with col_ta:
        if not dty.empty:
            ta = (
                dty.groupby("team_primary_name")["target_usd"]
                .sum()
                .reset_index()
                .sort_values("target_usd", ascending=True)
            )
            fig = px.bar(
                ta,
                x="target_usd",
                y="team_primary_name",
                orientation="h",
                color="target_usd",
                color_continuous_scale=BS,
                title="Annual Target by Team",
                labels={"target_usd": "Annual Target ($M)", "team_primary_name": ""},
            )
            fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Target Detail</div>', unsafe_allow_html=True)
    if not dty.empty:
        ttbl = dty.copy()
        ttbl["target_usd"] = (ttbl["target_usd"] / 1e6).round(2)
        ttbl.columns = [c.replace("_", " ").title() for c in ttbl.columns]
        st.dataframe(
            ttbl,
            use_container_width=True,
            hide_index=True,
            column_config={"Target Usd": st.column_config.NumberColumn("Target ($M)", format="$%.2f")},
        )
    else:
        st.info("Targets only available from Q1 2025 onwards.")