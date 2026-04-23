import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.models.financials import get_gross_margin, get_pipeline, get_targets

st.set_page_config(
    page_title="MarketCast Finance",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

    /* Sidebar */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1016 0%, #090b10 100%);
        border-right: 1px solid #1b2230;
    }

    div[data-testid="stSidebar"] .block-container {
        padding: 1.25rem 0.95rem 1.8rem 0.95rem;
    }

    .sb-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }

    .sb-brand-dot {
        width: 26px;
        height: 26px;
        border-radius: 8px;
        background: #d7f34a;
        flex-shrink: 0;
        box-shadow: 0 0 16px rgba(215,243,74,0.18);
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

    /* Inputs */
    .stSelectbox label, .stRadio > label, .stSelectSlider > label {
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

    /* KPI cards */
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

    /* Tabs */
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

MONTH_MAP = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
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

def get_theme_palette(theme_name: str):
    themes = {
        "Executive / minimal": {
            "series": ["#7aa2f7", "#5b7cbe", "#4b5563", "#94a3b8", "#64748b"],
            "blue_scale": ["#1e3a5f", "#2f5f9e", "#7aa2f7"],
            "donut": ["#93c5fd", "#60a5fa", "#3b82f6"],
            "waterfall_total": "#d4af37",
            "waterfall_pos": "#4ade80",
            "waterfall_neg": "#f87171",
            "current": "#7aa2f7",
            "prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Finance / Bloomberg-ish": {
            "series": ["#4c78a8", "#2f4b7c", "#6b7280", "#9ca3af", "#1f5a91"],
            "blue_scale": ["#0f2d4a", "#1f5a91", "#5fa8ff"],
            "donut": ["#0f4c81", "#2563eb", "#60a5fa"],
            "waterfall_total": "#93c5fd",
            "waterfall_pos": "#4ade80",
            "waterfall_neg": "#ef4444",
            "current": "#60a5fa",
            "prior": "#6b7280",
            "accent_scale": ["#0f2d4a", "#5fa8ff"],
        },
        "MarketCast-accented": {
            "series": ["#d7f34a", "#4ade80", "#60a5fa", "#a78bfa", "#fb923c"],
            "blue_scale": ["#1e3a5f", "#3b82f6", "#d7f34a"],
            "donut": ["#d7f34a", "#60a5fa", "#a78bfa"],
            "waterfall_total": "#d7f34a",
            "waterfall_pos": "#4ade80",
            "waterfall_neg": "#f87171",
            "current": "#d7f34a",
            "prior": "#475569",
            "accent_scale": ["#141a0d", "#d7f34a"],
        },
        "Monochrome blue": {
            "series": ["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
            "blue_scale": ["#17324d", "#2b6ea5", "#93c5fd"],
            "donut": ["#93c5fd", "#60a5fa", "#2563eb"],
            "waterfall_total": "#60a5fa",
            "waterfall_pos": "#4ade80",
            "waterfall_neg": "#f87171",
            "current": "#60a5fa",
            "prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Grey + accent": {
            "series": ["#94a3b8", "#64748b", "#475569", "#d7f34a", "#334155"],
            "blue_scale": ["#334155", "#64748b", "#d7f34a"],
            "donut": ["#475569", "#64748b", "#d7f34a"],
            "waterfall_total": "#d7f34a",
            "waterfall_pos": "#4ade80",
            "waterfall_neg": "#f87171",
            "current": "#94a3b8",
            "prior": "#475569",
            "accent_scale": ["#334155", "#d7f34a"],
        },
    }
    return themes[theme_name]

PT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    xaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1")
    ),
    yaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1")
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=10)
    ),
    margin=dict(l=0, r=0, t=40, b=0),
)

def safe_pct(a, b):
    return (a / b * 100) if b not in (0, None) else 0.0

def fmt_m(v):
    return f"${v/1e6:.1f}M"

def fmt_int(v):
    return f"{int(v):,}"

def kpi(label, value, delta=None, delta_label="", kind="money"):
    if kind == "pct":
        val_str = f"{value:.1f}%"
        d_str = f"{abs(delta):.1f} pts" if delta is not None else ""
    elif kind == "count":
        val_str = fmt_int(value)
        d_str = fmt_int(abs(delta)) if delta is not None else ""
    else:
        val_str = fmt_m(value)
        d_str = fmt_m(abs(delta)) if delta is not None else ""

    delta_html = ""
    if delta is not None:
        cls = "delta-pos" if delta >= 0 else "delta-neg"
        sign = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="metric-delta {cls}">{sign} {d_str} {delta_label}</div>'

    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{val_str}</div>
        {delta_html}
    </div>
    """

@st.cache_data
def load_data():
    df_gm = get_gross_margin(year_from=2022).copy()
    df_gm["accounting_period_start_date"] = pd.to_datetime(df_gm["accounting_period_start_date"])
    df_gm["yr"] = df_gm["accounting_period_start_date"].dt.year
    df_gm["month_num"] = df_gm["accounting_period_start_date"].dt.month
    df_gm["contribution"] = df_gm["gross_margin"] - df_gm["labour"]
    df_gm["fixed_cost"] = (
        df_gm["be_allocation"].fillna(0)
        + df_gm["ae_allocation"].fillna(0)
        + df_gm["rta_allocation"].fillna(0)
    )

    for col in ["service_line_name", "sub_service_line_name", "vertical_name", "top_level_parent_customer_name"]:
        df_gm[col] = df_gm[col].fillna("(blank)")

    df_pipe = get_pipeline().copy()
    if "pipeline_value_usd" in df_pipe.columns:
        df_pipe["pipeline_value_usd"] = df_pipe["pipeline_value_usd"].fillna(0)
    for col in ["service_line", "vertical"]:
        if col in df_pipe.columns:
            df_pipe[col] = df_pipe[col].fillna("(blank)")

    df_tgt = get_targets().copy()
    if "quarter_start_date" in df_tgt.columns:
        df_tgt["quarter_start_date"] = pd.to_datetime(df_tgt["quarter_start_date"])
        df_tgt["yr"] = df_tgt["quarter_start_date"].dt.year

    return df_gm, df_pipe, df_tgt

df_gm, df_pipe, df_tgt = load_data()

with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-dot"></div>
        <div>
            <div class="sb-brand-name">MarketCast</div>
            <div class="sb-brand-sub">Finance Dashboard</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-title">Time Period</div>', unsafe_allow_html=True)

    years = sorted(df_gm["yr"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("Year", years, index=0)

    basis = st.radio("View", ["Full Year", "YTD / Range"], horizontal=True)

    if basis == "YTD / Range":
        available_months = sorted(
            df_gm[df_gm["yr"] == selected_year]["month_num"].dropna().unique().tolist()
        )
        max_month = max(available_months) if available_months else 12
        month_range = st.select_slider(
            "Month Range",
            options=MONTH_NAMES,
            value=("Jan", MONTH_MAP[max_month])
        )
        m_from = MONTH_NAMES.index(month_range[0]) + 1
        m_to = MONTH_NAMES.index(month_range[1]) + 1
        period_label = f"{month_range[0]}–{month_range[1]} {selected_year}"
    else:
        m_from, m_to = 1, 12
        period_label = f"{selected_year} Full Year"

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-title">Business Filters</div>', unsafe_allow_html=True)

    service_lines = ["All"] + sorted(df_gm["service_line_name"].unique().tolist())
    selected_sl = st.selectbox("Service Line", service_lines)

    sub_service_lines = ["All"] + sorted(df_gm["sub_service_line_name"].unique().tolist())
    selected_ssl = st.selectbox("Sub Service Line", sub_service_lines)

    verticals = ["All"] + sorted(df_gm["vertical_name"].unique().tolist())
    selected_vertical = st.selectbox("Vertical", verticals)

    customers = ["All"] + sorted(df_gm["top_level_parent_customer_name"].unique().tolist())
    selected_customer = st.selectbox("Client", customers)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-title">Visual Style</div>', unsafe_allow_html=True)

    selected_theme = st.radio(
        "Visual Style",
        THEME_OPTIONS,
        index=3
    )

    st.markdown('</div>', unsafe_allow_html=True)

    filters_active = [x for x in [
        selected_sl if selected_sl != "All" else None,
        selected_ssl if selected_ssl != "All" else None,
        selected_vertical if selected_vertical != "All" else None,
        selected_customer if selected_customer != "All" else None,
    ] if x]
    filter_str = " · ".join(filters_active) if filters_active else "No additional filters"
    filter_str = f"{filter_str} · {selected_theme}"

    st.markdown(f"""
    <div class="sb-active-view">
        <div class="sb-view-label">Active View</div>
        <div class="sb-view-value">{period_label}</div>
        <div class="sb-view-sub">{filter_str}</div>
    </div>
    """, unsafe_allow_html=True)

palette = get_theme_palette(selected_theme)
SERIES_COLORS = palette["series"]
BLUE_SCALE = palette["blue_scale"]
DONUT_COLORS = palette["donut"]
WF_TOTAL = palette["waterfall_total"]
WF_POS = palette["waterfall_pos"]
WF_NEG = palette["waterfall_neg"]
LINE_CURRENT = palette["current"]
LINE_PRIOR = palette["prior"]
ACCENT_SCALE = palette["accent_scale"]

def filter_gm(data, year, m1=1, m2=12):
    d = data[(data["yr"] == year) & (data["month_num"] >= m1) & (data["month_num"] <= m2)].copy()
    if selected_sl != "All":
        d = d[d["service_line_name"] == selected_sl]
    if selected_ssl != "All":
        d = d[d["sub_service_line_name"] == selected_ssl]
    if selected_vertical != "All":
        d = d[d["vertical_name"] == selected_vertical]
    if selected_customer != "All":
        d = d[d["top_level_parent_customer_name"] == selected_customer]
    return d

df_curr = filter_gm(df_gm, selected_year, m_from, m_to)
df_prior = filter_gm(df_gm, selected_year - 1, m_from, m_to)

rev = df_curr["revenue"].sum()
cogs = df_curr["cogs"].sum()
labour = df_curr["labour"].sum()
fixed_cost = df_curr["fixed_cost"].sum()

gm = rev - cogs - fixed_cost
contrib = gm - labour

rev_py = df_prior["revenue"].sum()
cogs_py = df_prior["cogs"].sum()
fixed_cost_py = df_prior["fixed_cost"].sum()
labour_py = df_prior["labour"].sum()
gm_py = rev_py - cogs_py - fixed_cost_py
contrib_py = gm_py - labour_py

num_clients = df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()
clients_py = df_prior[~df_prior["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()

gm_pct = safe_pct(gm, rev)
cm_pct = safe_pct(contrib, rev)
gm_pct_py = safe_pct(gm_py, rev_py)
cm_pct_py = safe_pct(contrib_py, rev_py)

fixed_cost_pct = safe_pct(fixed_cost, rev)
fixed_cost_pct_py = safe_pct(fixed_cost_py, rev_py)
labour_pct = safe_pct(labour, rev)
labour_pct_py = safe_pct(labour_py, rev_py)

st.markdown(f"### Finance Dashboard — {period_label}")

st.markdown("""
<div class="formula-bar">
    <div class="formula-text">
        Gross Margin = Revenue – COGS – Fixed Cost &nbsp;&nbsp;|&nbsp;&nbsp;
        Contribution = Gross Margin – Labour
    </div>
</div>
""", unsafe_allow_html=True)

r1 = st.columns(8)
r1[0].markdown(kpi("Revenue", rev, rev - rev_py, "vs PY"), unsafe_allow_html=True)
r1[1].markdown(kpi("Clients", num_clients, num_clients - clients_py, "vs PY", kind="count"), unsafe_allow_html=True)
r1[2].markdown(kpi("COGS", cogs), unsafe_allow_html=True)
r1[3].markdown(kpi("Fixed Cost", fixed_cost), unsafe_allow_html=True)
r1[4].markdown(kpi("Labour", labour), unsafe_allow_html=True)
r1[5].markdown(kpi("Gross Margin", gm, gm - gm_py, "vs PY"), unsafe_allow_html=True)
r1[6].markdown(kpi("Gross Margin %", gm_pct, gm_pct - gm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r1[7].markdown(kpi("Contribution", contrib, contrib - contrib_py, "vs PY"), unsafe_allow_html=True)

r2 = st.columns(8)
r2[0].markdown(kpi("Contribution %", cm_pct, cm_pct - cm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[1].markdown(kpi("Fixed Cost % of Revenue", fixed_cost_pct, fixed_cost_pct - fixed_cost_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[2].markdown(kpi("Labour % of Revenue", labour_pct, labour_pct - labour_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Revenue & Margin",
    "Clients & Products",
    "Pipeline",
    "Targets",
])

with tab1:
    st.markdown('<div class="section-header">Performance Overview</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        rev_monthly = (
            df_curr.groupby(["accounting_period_start_date", "service_line_name"])["revenue"]
            .sum()
            .reset_index()
        )
        fig = px.bar(
            rev_monthly,
            x="accounting_period_start_date",
            y="revenue",
            color="service_line_name",
            color_discrete_sequence=SERIES_COLORS,
            title="Monthly Revenue Trend",
            labels={"revenue": "Revenue", "accounting_period_start_date": "Month", "service_line_name": ""}
        )
        fig.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        gm_sl = (
            df_curr.groupby("service_line_name")
            .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
            .reset_index()
        )
        gm_sl["gm_pct"] = (gm_sl["gross_margin"] / gm_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        gm_sl = gm_sl.sort_values("gm_pct", ascending=True)

        fig2 = px.bar(
            gm_sl,
            x="gm_pct",
            y="service_line_name",
            orientation="h",
            color="gm_pct",
            color_continuous_scale=BLUE_SCALE,
            title="Gross Margin % by Service Line",
            labels={"gm_pct": "Gross Margin %", "service_line_name": ""}
        )
        fig2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Current"})
        py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Prior Year"})
        yoy = (
            pd.DataFrame({"month_num": list(range(m_from, m_to + 1))})
            .merge(cy, on="month_num", how="left")
            .merge(py, on="month_num", how="left")
            .fillna(0)
        )
        yoy["month_label"] = yoy["month_num"].map(MONTH_MAP)
        yoy_melt = yoy.melt(
            id_vars=["month_num", "month_label"],
            value_vars=["Current", "Prior Year"],
            var_name="Period",
            value_name="Revenue"
        )

        fig3 = px.line(
            yoy_melt,
            x="month_label",
            y="Revenue",
            color="Period",
            markers=True,
            color_discrete_map={"Current": LINE_CURRENT, "Prior Year": LINE_PRIOR},
            title="Revenue vs Prior Year",
            labels={"month_label": "Month"}
        )
        fig3.update_layout(**PT, title_font_color="#cbd5e1")
        fig3.update_traces(line_width=2.5)
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total", "relative", "total"],
            x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labour", "Contribution"],
            y=[rev, -cogs, -fixed_cost, None, -labour, None],
            connector={"line": {"color": "#243041"}},
            increasing={"marker": {"color": WF_POS}},
            decreasing={"marker": {"color": WF_NEG}},
            totals={"marker": {"color": WF_TOTAL}},
            text=[fmt_m(rev), fmt_m(cogs), fmt_m(fixed_cost), fmt_m(gm), fmt_m(labour), fmt_m(contrib)],
            textposition="outside"
        ))
        wf.update_layout(
            **PT,
            title="Revenue to Contribution Bridge",
            title_font_color="#cbd5e1",
            showlegend=False
        )
        st.plotly_chart(wf, use_container_width=True)

    col_e, col_f = st.columns(2)

    with col_e:
        alloc_split = pd.DataFrame({
            "Allocation Type": ["Brand Effect", "AE Synd", "RTA"],
            "Amount": [
                df_curr["be_allocation"].sum(),
                df_curr["ae_allocation"].sum(),
                df_curr["rta_allocation"].sum(),
            ]
        })
        alloc_split = alloc_split[alloc_split["Amount"] > 0]

        fig_alloc = px.pie(
            alloc_split,
            names="Allocation Type",
            values="Amount",
            hole=0.68,
            title="Fixed Cost Split",
            color="Allocation Type",
            color_discrete_map={
                "Brand Effect": DONUT_COLORS[0],
                "AE Synd": DONUT_COLORS[1],
                "RTA": DONUT_COLORS[2],
            }
        )
        fig_alloc.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fig_alloc.add_annotation(
            text=fmt_m(fixed_cost),
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=18, color="#f8fafc", family="DM Sans")
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

    with col_f:
        gm_trend = (
            df_curr.groupby("accounting_period_start_date")
            .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
            .reset_index()
            .sort_values("accounting_period_start_date")
        )
        gm_trend["gm_pct"] = (gm_trend["gross_margin"] / gm_trend["revenue"].replace(0, float("nan")) * 100).round(1)

        fig_gm_trend = px.area(
            gm_trend,
            x="accounting_period_start_date",
            y="gm_pct",
            title="Monthly Gross Margin % Trend",
            labels={"accounting_period_start_date": "Month", "gm_pct": "Gross Margin %"},
            color_discrete_sequence=[LINE_CURRENT]
        )
        fig_gm_trend.update_traces(line_width=2)
        fig_gm_trend.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-45)
        st.plotly_chart(fig_gm_trend, use_container_width=True)

    st.markdown('<div class="section-header">Margin Detail</div>', unsafe_allow_html=True)
    product_summary = (
        df_curr.groupby(["service_line_name", "sub_service_line_name"], dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
            labour=("labour", "sum"),
            contribution=("contribution", "sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
        )
        .reset_index()
    )
    product_summary["gm_pct"] = (product_summary["gross_margin"] / product_summary["revenue"].replace(0, float("nan")) * 100).round(1)
    product_summary["cm_pct"] = (product_summary["contribution"] / product_summary["revenue"].replace(0, float("nan")) * 100).round(1)

    for col in ["revenue", "cogs", "fixed_cost", "gross_margin", "labour", "contribution"]:
        product_summary[col] = (product_summary[col] / 1000).round(0)

    product_summary = product_summary.sort_values("revenue", ascending=False)
    product_summary.columns = [c.replace("_", " ").title() for c in product_summary.columns]

    st.dataframe(
        product_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($k)", format="$%.0f"),
            "Cogs": st.column_config.NumberColumn("COGS ($k)", format="$%.0f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($k)", format="$%.0f"),
            "Gross Margin": st.column_config.NumberColumn("Gross Margin ($k)", format="$%.0f"),
            "Labour": st.column_config.NumberColumn("Labour ($k)", format="$%.0f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($k)", format="$%.0f"),
            "Gm Pct": st.column_config.NumberColumn("Gross Margin %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("Contribution %", format="%.1f%%"),
            "Clients": st.column_config.NumberColumn("Clients", format="%d"),
        }
    )

with tab2:
    st.markdown('<div class="section-header">Client & Product Performance</div>', unsafe_allow_html=True)
    col_g, col_h = st.columns(2)

    with col_g:
        top_clients = (
            df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]
            .groupby("top_level_parent_customer_name")
            .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
            .reset_index()
            .sort_values("gross_margin", ascending=True)
            .tail(15)
        )
        fig4 = px.bar(
            top_clients,
            x="gross_margin",
            y="top_level_parent_customer_name",
            orientation="h",
            color="revenue",
            color_continuous_scale=ACCENT_SCALE,
            title="Top 15 Clients by Gross Margin",
            labels={"gross_margin": "Gross Margin", "top_level_parent_customer_name": "", "revenue": "Revenue"}
        )
        fig4.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig4, use_container_width=True)

    with col_h:
        client_perf = (
            df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]
            .groupby("top_level_parent_customer_name")
            .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
            .reset_index()
        )
        client_perf["gm_pct"] = (client_perf["gross_margin"] / client_perf["revenue"].replace(0, float("nan")) * 100).round(1)
        client_perf = client_perf.sort_values("revenue", ascending=False).head(20)

        fig5 = px.scatter(
            client_perf,
            x="revenue",
            y="gm_pct",
            size="revenue",
            color="gm_pct",
            color_continuous_scale=BLUE_SCALE,
            text="top_level_parent_customer_name",
            title="Client Portfolio — Revenue vs Gross Margin %",
            labels={"revenue": "Revenue", "gm_pct": "Gross Margin %", "top_level_parent_customer_name": ""}
        )
        fig5.update_traces(textposition="top center", textfont=dict(size=9, color="#cbd5e1"))
        fig5.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown('<div class="section-header">Expandable Product Hierarchy</div>', unsafe_allow_html=True)

    sl_summary = (
        df_curr.groupby("service_line_name", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
            labour=("labour", "sum"),
            contribution=("contribution", "sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    sl_summary["gm_pct"] = (sl_summary["gross_margin"] / sl_summary["revenue"].replace(0, float("nan")) * 100).round(1)
    sl_summary["cm_pct"] = (sl_summary["contribution"] / sl_summary["revenue"].replace(0, float("nan")) * 100).round(1)

    for _, row in sl_summary.iterrows():
        sl_name = row["service_line_name"]
        with st.expander(
            f"{sl_name}  |  Revenue: {fmt_m(row['revenue'])}  |  Gross Margin %: {row['gm_pct']:.1f}%  |  Contribution %: {row['cm_pct']:.1f}%"
        ):
            service_metrics = pd.DataFrame({
                "Metric": [
                    "Revenue", "COGS", "Fixed Cost", "Gross Margin",
                    "Labour", "Contribution", "Gross Margin %", "Contribution %", "Clients"
                ],
                "Value": [
                    fmt_m(row["revenue"]),
                    fmt_m(row["cogs"]),
                    fmt_m(row["fixed_cost"]),
                    fmt_m(row["gross_margin"]),
                    fmt_m(row["labour"]),
                    fmt_m(row["contribution"]),
                    f"{row['gm_pct']:.1f}%",
                    f"{row['cm_pct']:.1f}%",
                    fmt_int(row["clients"]),
                ]
            })
            st.dataframe(service_metrics, use_container_width=True, hide_index=True)

            sub_df = (
                df_curr[df_curr["service_line_name"] == sl_name]
                .groupby("sub_service_line_name", dropna=False)
                .agg(
                    revenue=("revenue", "sum"),
                    cogs=("cogs", "sum"),
                    fixed_cost=("fixed_cost", "sum"),
                    gross_margin=("gross_margin", "sum"),
                    labour=("labour", "sum"),
                    contribution=("contribution", "sum"),
                    clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
                )
                .reset_index()
                .sort_values("revenue", ascending=False)
            )
            sub_df["gm_pct"] = (sub_df["gross_margin"] / sub_df["revenue"].replace(0, float("nan")) * 100).round(1)
            sub_df["cm_pct"] = (sub_df["contribution"] / sub_df["revenue"].replace(0, float("nan")) * 100).round(1)

            display = sub_df.copy()
            for col in ["revenue", "cogs", "fixed_cost", "gross_margin", "labour", "contribution"]:
                display[col] = (display[col] / 1000).round(0)

            display.columns = [c.replace("_", " ").title() for c in display.columns]

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Revenue": st.column_config.NumberColumn("Revenue ($k)", format="$%.0f"),
                    "Cogs": st.column_config.NumberColumn("COGS ($k)", format="$%.0f"),
                    "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($k)", format="$%.0f"),
                    "Gross Margin": st.column_config.NumberColumn("Gross Margin ($k)", format="$%.0f"),
                    "Labour": st.column_config.NumberColumn("Labour ($k)", format="$%.0f"),
                    "Contribution": st.column_config.NumberColumn("Contribution ($k)", format="$%.0f"),
                    "Gm Pct": st.column_config.NumberColumn("Gross Margin %", format="%.1f%%"),
                    "Cm Pct": st.column_config.NumberColumn("Contribution %", format="%.1f%%"),
                    "Clients": st.column_config.NumberColumn("Clients", format="%d"),
                }
            )

with tab3:
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)

    df_pipe_dedup = df_pipe.drop_duplicates("deal_id")
    if "service_line" in df_pipe_dedup.columns:
        df_pipe_dedup = df_pipe_dedup[~df_pipe_dedup["service_line"].isin(EXCL)]

    total_pipeline = df_pipe_dedup["pipeline_value_usd"].sum()
    total_deals = df_pipe_dedup["deal_id"].nunique()
    avg_deal = total_pipeline / total_deals if total_deals > 0 else 0

    pc = st.columns(3)
    pc[0].markdown(kpi("Total Pipeline", total_pipeline), unsafe_allow_html=True)
    pc[1].markdown(kpi("Active Deals", total_deals, kind="count"), unsafe_allow_html=True)
    pc[2].markdown(kpi("Average Deal Size", avg_deal), unsafe_allow_html=True)

    col_i, col_j = st.columns(2)

    with col_i:
        pipe_stage = (
            df_pipe_dedup.groupby("deal_pipeline_stage_name")
            .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
            .reset_index()
            .sort_values("value", ascending=True)
        )
        fig8 = px.bar(
            pipe_stage,
            x="value",
            y="deal_pipeline_stage_name",
            orientation="h",
            color="value",
            color_continuous_scale=BLUE_SCALE,
            title="Pipeline by Stage",
            labels={"value": "Pipeline Value", "deal_pipeline_stage_name": ""}
        )
        fig8.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig8, use_container_width=True)

    with col_j:
        pipe_sl = (
            df_pipe_dedup.groupby("service_line")
            .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
            .reset_index()
            .sort_values("value", ascending=False)
        )
        fig9 = px.bar(
            pipe_sl,
            x="service_line",
            y="value",
            color="value",
            color_continuous_scale=BLUE_SCALE,
            title="Pipeline by Service Line",
            labels={"value": "Pipeline Value", "service_line": ""}
        )
        fig9.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(fig9, use_container_width=True)

    st.markdown('<div class="section-header">Pipeline Detail</div>', unsafe_allow_html=True)
    pipe_tbl = (
        df_pipe_dedup.groupby(["deal_pipeline_stage_name", "service_line", "vertical"])
        .agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum"))
        .reset_index()
        .sort_values("value", ascending=False)
    )
    pipe_tbl["value"] = (pipe_tbl["value"] / 1000).round(0)
    pipe_tbl.columns = [c.replace("_", " ").title() for c in pipe_tbl.columns]
    st.dataframe(
        pipe_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={"Value": st.column_config.NumberColumn("Value ($k)", format="$%.0f")}
    )

with tab4:
    st.markdown('<div class="section-header">Targets Overview</div>', unsafe_allow_html=True)

    df_tgt_year = df_tgt[df_tgt["yr"] == selected_year].copy()
    total_target = df_tgt_year["target_usd"].sum() if not df_tgt_year.empty else 0
    variance_to_target = rev - total_target
    pct_to_target = safe_pct(rev, total_target) if total_target not in (0, None) else 0

    trow = st.columns(4)
    trow[0].markdown(kpi(f"{selected_year} Target", total_target), unsafe_allow_html=True)
    trow[1].markdown(kpi("Actual Revenue", rev, variance_to_target, "vs Target"), unsafe_allow_html=True)
    trow[2].markdown(kpi("Revenue vs Target", pct_to_target, kind="pct"), unsafe_allow_html=True)
    trow[3].markdown(kpi("Teams", df_tgt_year["team_primary_name"].nunique() if not df_tgt_year.empty else 0, kind="count"), unsafe_allow_html=True)

    col_k, col_l = st.columns(2)

    with col_k:
        if not df_tgt_year.empty:
            q_targets = (
                df_tgt_year.groupby("quarter_start_date", as_index=False)["target_usd"]
                .sum()
                .sort_values("quarter_start_date")
            )
            fig10 = px.bar(
                q_targets,
                x="quarter_start_date",
                y="target_usd",
                color="target_usd",
                color_continuous_scale=BLUE_SCALE,
                title="Quarterly Targets",
                labels={"target_usd": "Target", "quarter_start_date": "Quarter"}
            )
            fig10.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.info(f"No target data available for {selected_year}.")

    with col_l:
        if not df_tgt_year.empty:
            team_annual = (
                df_tgt_year.groupby("team_primary_name")["target_usd"]
                .sum()
                .reset_index()
                .sort_values("target_usd", ascending=True)
            )
            fig11 = px.bar(
                team_annual,
                x="target_usd",
                y="team_primary_name",
                orientation="h",
                color="target_usd",
                color_continuous_scale=BLUE_SCALE,
                title="Annual Target by Team",
                labels={"target_usd": "Annual Target", "team_primary_name": ""}
            )
            fig11.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            st.plotly_chart(fig11, use_container_width=True)

    st.markdown('<div class="section-header">Target Detail</div>', unsafe_allow_html=True)
    if not df_tgt_year.empty:
        tgt_tbl = df_tgt_year.copy()
        tgt_tbl["target_usd"] = (tgt_tbl["target_usd"] / 1000).round(0)
        tgt_tbl.columns = [c.replace("_", " ").title() for c in tgt_tbl.columns]
        st.dataframe(
            tgt_tbl,
            use_container_width=True,
            hide_index=True,
            column_config={"Target Usd": st.column_config.NumberColumn("Target ($k)", format="$%.0f")}
        )
    else:
        st.info(f"No targets loaded for {selected_year}.")