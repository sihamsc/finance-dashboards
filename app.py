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
import pandas as pd
import streamlit as st

from src.models.financials import (
    get_gross_margin,
    get_pipeline,
    get_targets,
    get_labour_by_client,
)

from src.services.finance_service import (
    build_period_frames,
    build_headline_metrics,
)

from src.utils.styles import APP_CSS
from src.utils.theme import THEME_OPTIONS, get_theme_palette, PT
from src.utils.formatters import kpi
from src.utils.filters import (
    MONTH_MAP,
    MONTH_NAMES,
    EXCL,
    rolling_ym,
)

from src.views.overview import render_overview
from src.views.revenue import render_revenue
from src.views.cogs import render_cogs
from src.views.fixed_cost import render_fixed_cost
from src.views.margin import render_margin
from src.views.labor import render_labor
from src.views.contribution import render_contribution
from src.views.explorer import render_explorer
from src.views.pipeline import render_pipeline
from src.views.targets import render_targets


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
st.markdown(APP_CSS, unsafe_allow_html=True)


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


# ------------------------------------------------------------
# Shared filters dict
# ------------------------------------------------------------
filters = {
    "selected_sl": selected_sl,
    "selected_ssl": selected_ssl,
    "selected_vertical": selected_vertical,
    "selected_customer": selected_customer,
}

# Base filters for decomposition charts:
# keep time + vertical + client, but ignore service line / sub service line
decomp_filters = {
    "selected_sl": "All",
    "selected_ssl": "All",
    "selected_vertical": selected_vertical,
    "selected_customer": selected_customer,
}


# ------------------------------------------------------------
# Current/prior dataframes
# ------------------------------------------------------------
period_frames = build_period_frames(
    df_gm,
    df_lab,
    is_rolling=is_rolling,
    curr_ym=curr_ym,
    prior_ym=prior_ym,
    selected_year=selected_year,
    m_from=m_from,
    m_to=m_to,
    filters=filters,
)

decomp_period_frames = build_period_frames(
    df_gm,
    df_lab,
    is_rolling=is_rolling,
    curr_ym=curr_ym,
    prior_ym=prior_ym,
    selected_year=selected_year,
    m_from=m_from,
    m_to=m_to,
    filters=decomp_filters,
)

df_curr = period_frames["df_curr"]
df_prior = period_frames["df_prior"]
df_lab_curr = period_frames["df_lab_curr"]
df_lab_prior = period_frames["df_lab_prior"]

df_curr_decomp = decomp_period_frames["df_curr"]
df_lab_curr_decomp = decomp_period_frames["df_lab_curr"]


# ------------------------------------------------------------
# Core headline metrics
# ------------------------------------------------------------
headline = build_headline_metrics(
    df_curr,
    df_prior,
    df_lab_curr,
    df_lab_prior,
    EXCL,
)

rev = headline["rev"]
cogs = headline["cogs"]
fixed_cost = headline["fixed_cost"]
labor = headline["labor"]
gm = headline["gm"]
contrib = headline["contrib"]

rev_py = headline["rev_py"]
cogs_py = headline["cogs_py"]
fixed_cost_py = headline["fixed_cost_py"]
labor_py = headline["labor_py"]
gm_py = headline["gm_py"]
contrib_py = headline["contrib_py"]

num_clients = headline["num_clients"]
clients_py = headline["clients_py"]

gm_pct = headline["gm_pct"]
cm_pct = headline["cm_pct"]
gm_pct_py = headline["gm_pct_py"]
cm_pct_py = headline["cm_pct_py"]
fc_pct = headline["fc_pct"]
fc_pct_py = headline["fc_pct_py"]
lab_pct = headline["lab_pct"]
lab_pct_py = headline["lab_pct_py"]


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
# Shared context passed into views
# ------------------------------------------------------------
context = {
    "palette": palette,
    "PT": PT,
    "period_label": period_label,
    "is_rolling": is_rolling,
    "curr_ym": curr_ym,
    "prior_ym": prior_ym,
    "m_from": m_from,
    "m_to": m_to,
    "df_curr": df_curr,
    "df_prior": df_prior,
    "df_lab_curr": df_lab_curr,
    "df_lab_prior": df_lab_prior,
    "df_curr_decomp": df_curr_decomp,
    "df_lab_curr_decomp": df_lab_curr_decomp,
    "df_pipe": df_pipe,
    "df_tgt": df_tgt,
    "selected_year": selected_year,
    "rev": rev,
    "cogs": cogs,
    "fixed_cost": fixed_cost,
    "labor": labor,
    "gm": gm,
    "contrib": contrib,
    "rev_py": rev_py,
    "cogs_py": cogs_py,
    "fixed_cost_py": fixed_cost_py,
    "labor_py": labor_py,
    "gm_py": gm_py,
    "contrib_py": contrib_py,
    "num_clients": num_clients,
    "clients_py": clients_py,
    "gm_pct": gm_pct,
    "cm_pct": cm_pct,
    "gm_pct_py": gm_pct_py,
    "cm_pct_py": cm_pct_py,
    "fc_pct": fc_pct,
    "fc_pct_py": fc_pct_py,
    "lab_pct": lab_pct,
    "lab_pct_py": lab_pct_py,
    "filters": filters,
}


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

with tab_ov:
    render_overview(context)

with tab_rev:
    render_revenue(context)

with tab_cogs:
    render_cogs(context)

with tab_fc:
    render_fixed_cost(context)

with tab_margin:
    render_margin(context)

with tab_labor:
    render_labor(context)

with tab_contrib:
    render_contribution(context)

with tab_explorer:
    render_explorer(context)

with tab_pipe:
    render_pipeline(context)

with tab_tgt:
    render_targets(context)