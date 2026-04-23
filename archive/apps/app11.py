# ============================================================
# MarketCast Finance Dashboard
# Refactored per Chris (Finance) feedback — 22 April 2026
#
# TAB STRUCTURE (top-down P&L flow):
#   Tab 1 — Overview        : Total P&L waterfall + headline KPIs
#   Tab 2 — Revenue         : Decompose revenue by SL / sub-SL / vertical
#   Tab 3 — Gross Margin    : GM bubble chart, GM% by SL, fixed cost split
#   Tab 4 — Clients         : Client blow-up — full P&L per client
#   Tab 5 — Labour          : Labour by client/SL — from Screendragon join
#   Tab 6 — Pipeline        : Stages 1-6, by SL
#   Tab 7 — Targets         : vs actuals by team/quarter
#
# KEY CHANGES vs previous version:
#   - All $ values shown in $M (not $k) per Chris request
#   - Bubble chart on GM tab shows CM% label on left of each bubble
#   - Client tab is a full blow-up: select client → full P&L
#   - Top 15 clients scrollable + "All" toggle
#   - Rolling 12M selector added (Jan 2025 default)
#   - COGS breakdown added within Revenue tab
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

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="MarketCast Finance",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_base64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_image("assets/logo.png")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #07090e; color: #f3f4f6; }
    .block-container { padding: 1.6rem 2.1rem 2.3rem 2.1rem; max-width: 100% !important; }

    /* ── Sidebar ── */
    div[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1016 0%,#090b10 100%); border-right:1px solid #1b2230; }
    div[data-testid="stSidebar"] .block-container { padding:1.25rem 0.95rem 1.8rem 0.95rem; display:flex; flex-direction:column; min-height:100vh; }
    .sb-brand { display:flex; align-items:center; gap:10px; margin-bottom:1rem; }
    .sb-logo  { width:28px; height:28px; object-fit:contain; border-radius:6px; flex-shrink:0; }
    .sb-brand-name { font-size:17px; font-weight:700; color:#f5f7fb; letter-spacing:-0.02em; line-height:1; }
    .sb-brand-sub  { font-family:'DM Mono',monospace; font-size:9px; color:#667085; letter-spacing:0.12em; text-transform:uppercase; margin-top:3px; }
    .sb-section { background:#0f131b; border:1px solid #1b2230; border-radius:14px; padding:0.95rem 0.85rem 0.5rem 0.85rem; margin-bottom:0.8rem; }
    .sb-section-title { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.16em; text-transform:uppercase; color:#6b7280; margin-bottom:0.65rem; }
    .sb-active-view { background:linear-gradient(180deg,rgba(215,243,74,0.08) 0%,rgba(215,243,74,0.03) 100%); border:1px solid rgba(215,243,74,0.16); border-radius:12px; padding:0.8rem 0.9rem; margin-top:0.2rem; }
    .sb-view-label { font-family:'DM Mono',monospace; font-size:9px; color:#d7f34a; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.35rem; }
    .sb-view-value { font-size:13px; font-weight:600; color:#f3f4f6; margin-bottom:0.35rem; }
    .sb-view-sub   { font-size:11px; color:#9ca3af; line-height:1.45; }
    .sb-bottom-spacer { flex:1 1 auto; min-height:1rem; }

    /* ── Inputs ── */
    .stSelectbox label, .stRadio > label, .stSelectSlider > label, .stToggle label {
        font-family:'DM Mono',monospace !important; font-size:9px !important;
        letter-spacing:0.12em !important; text-transform:uppercase !important; color:#6b7280 !important; }
    div[data-baseweb="select"] > div { background:#090d14 !important; border:1px solid #202938 !important; border-radius:10px !important; }
    div[data-baseweb="select"] span  { color:#e5e7eb !important; }
    div[data-baseweb="select"] svg   { fill:#6b7280 !important; }
    div[role="radiogroup"] label { background:#0a0d14; border:1px solid #202938; border-radius:10px; padding:0.35rem 0.6rem; }

    /* ── KPI cards ── */
    .metric-card  { background:linear-gradient(180deg,#0c1017 0%,#0a0d13 100%); border:1px solid #1b2230; border-radius:14px; padding:0.95rem 1.05rem; min-height:88px; }
    .metric-label { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.14em; text-transform:uppercase; color:#6b7280; margin-bottom:0.45rem; white-space:nowrap; }
    .metric-value { font-size:19px; font-weight:700; color:#f8fafc; line-height:1.05; letter-spacing:-0.03em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .metric-delta { font-family:'DM Mono',monospace; font-size:10px; margin-top:0.45rem; white-space:nowrap; }
    .delta-pos { color:#4ade80; }
    .delta-neg { color:#f87171; }

    /* ── Formula bar ── */
    .formula-bar  { background:#0b0f16; border:1px solid #18202d; border-radius:12px; padding:0.75rem 0.95rem; margin-bottom:1rem; }
    .formula-text { font-family:'DM Mono',monospace; font-size:10px; color:#a3aab8; letter-spacing:0.02em; }

    /* ── Section headers ── */
    .section-header { font-family:'DM Mono',monospace; font-size:10px; letter-spacing:0.16em; text-transform:uppercase;
        color:#6b7280; border-bottom:1px solid #161c27; padding-bottom:0.45rem; margin-bottom:1rem; margin-top:1.6rem; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] { background:transparent; border-bottom:1px solid #161c27; gap:0; }
    .stTabs [data-baseweb="tab"] { font-family:'DM Mono',monospace; font-size:10px; letter-spacing:0.08em; text-transform:uppercase;
        color:#667085; padding:0.7rem 1.25rem; border-radius:0; border-bottom:2px solid transparent; background:transparent; }
    .stTabs [aria-selected="true"] { color:#d7f34a !important; border-bottom:2px solid #d7f34a !important; background:transparent !important; }
    .stExpander { border:1px solid #1b2230 !important; border-radius:12px !important; background:#0b0f16 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────
MONTH_MAP   = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
MONTH_NAMES = [MONTH_MAP[i] for i in range(1,13)]
EXCL        = ["Unassigned","(blank)"]

THEME_OPTIONS = ["Executive / minimal","Finance / Bloomberg-ish","MarketCast-accented","Monochrome blue","Grey + accent"]

def get_theme_palette(name):
    themes = {
        "Executive / minimal":    {"series":["#7aa2f7","#5b7cbe","#4b5563","#94a3b8","#64748b"],"blue_scale":["#1e3a5f","#2f5f9e","#7aa2f7"],"donut":["#93c5fd","#60a5fa","#3b82f6"],"wf_total":"#d4af37","wf_pos":"#4ade80","wf_neg":"#f87171","current":"#7aa2f7","prior":"#475569","accent":["#122033","#60a5fa"]},
        "Finance / Bloomberg-ish":{"series":["#4c78a8","#2f4b7c","#6b7280","#9ca3af","#1f5a91"],"blue_scale":["#0f2d4a","#1f5a91","#5fa8ff"],"donut":["#0f4c81","#2563eb","#60a5fa"],"wf_total":"#93c5fd","wf_pos":"#4ade80","wf_neg":"#ef4444","current":"#60a5fa","prior":"#6b7280","accent":["#0f2d4a","#5fa8ff"]},
        "MarketCast-accented":    {"series":["#d7f34a","#4ade80","#60a5fa","#a78bfa","#fb923c"],"blue_scale":["#1e3a5f","#3b82f6","#d7f34a"],"donut":["#d7f34a","#60a5fa","#a78bfa"],"wf_total":"#d7f34a","wf_pos":"#4ade80","wf_neg":"#f87171","current":"#d7f34a","prior":"#475569","accent":["#141a0d","#d7f34a"]},
        "Monochrome blue":        {"series":["#93c5fd","#60a5fa","#3b82f6","#2563eb","#1d4ed8"],"blue_scale":["#17324d","#2b6ea5","#93c5fd"],"donut":["#93c5fd","#60a5fa","#2563eb"],"wf_total":"#60a5fa","wf_pos":"#4ade80","wf_neg":"#f87171","current":"#60a5fa","prior":"#475569","accent":["#122033","#60a5fa"]},
        "Grey + accent":          {"series":["#94a3b8","#64748b","#475569","#d7f34a","#334155"],"blue_scale":["#334155","#64748b","#d7f34a"],"donut":["#475569","#64748b","#d7f34a"],"wf_total":"#d7f34a","wf_pos":"#4ade80","wf_neg":"#f87171","current":"#94a3b8","prior":"#475569","accent":["#334155","#d7f34a"]},
    }
    return themes[name]

# Base Plotly theme — all text light
PT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    xaxis=dict(gridcolor="#141924", linecolor="#1b2230", tickcolor="#1b2230", tickfont=dict(color="#cbd5e1"), title_font=dict(color="#cbd5e1")),
    yaxis=dict(gridcolor="#141924", linecolor="#1b2230", tickcolor="#1b2230", tickfont=dict(color="#cbd5e1"), title_font=dict(color="#cbd5e1")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=10)),
    margin=dict(l=0, r=0, t=40, b=0),
)

# ── Helpers ───────────────────────────────────────────────────
def safe_pct(a, b): return (a/b*100) if b not in (0, None) else 0.0
def fmt_m(v):       return f"${v/1e6:.1f}M"          # display in $M per Chris request
def fmt_m2(v):      return f"${v/1e6:.2f}M"
def fmt_int(v):     return f"{int(v):,}"
def fmt_hr(v):      return f"${v:,.0f}"

def kpi(label, value, delta=None, delta_label="", kind="money"):
    """Render a KPI metric card. kind: money | pct | count | dollar"""
    if kind == "pct":       val_str = f"{value:.1f}%"
    elif kind == "count":   val_str = fmt_int(value)
    elif kind == "dollar":  val_str = f"${value:,.0f}"
    else:                   val_str = fmt_m(value)
    delta_html = ""
    if delta is not None:
        cls  = "delta-pos" if delta >= 0 else "delta-neg"
        sign = "▲" if delta >= 0 else "▼"
        if kind == "pct":      d_str = f"{abs(delta):.1f} pts"
        elif kind == "count":  d_str = fmt_int(abs(delta))
        elif kind == "dollar": d_str = f"${abs(delta):,.0f}"
        else:                  d_str = fmt_m(abs(delta))
        delta_html = f'<div class="metric-delta {cls}">{sign} {d_str} {delta_label}</div>'
    return (f'<div class="metric-card">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value">{val_str}</div>'
            f'{delta_html}</div>')

def tc(color): return f'title_font_color="{color}"'  # shorthand

# ── Data loading ──────────────────────────────────────────────
@st.cache_data
def load_data():
    """
    Load all four data sources from the warehouse.
    Cached for the session — only runs once per load.
    """
    # --- Gross margin: revenue, COGS, allocations, labour (NULL rows) ---
    df_gm = get_gross_margin(year_from=2022).copy()
    df_gm["accounting_period_start_date"] = pd.to_datetime(df_gm["accounting_period_start_date"])
    df_gm["yr"]        = df_gm["accounting_period_start_date"].dt.year
    df_gm["month_num"] = df_gm["accounting_period_start_date"].dt.month
    for col in ["revenue","cogs","labour","be_allocation","ae_allocation","rta_allocation","gross_margin"]:
        df_gm[col] = df_gm[col].fillna(0)
    df_gm["fixed_cost"]   = df_gm["be_allocation"] + df_gm["ae_allocation"] + df_gm["rta_allocation"]
    df_gm["contribution"] = df_gm["gross_margin"] - df_gm["labour"]
    for col in ["service_line_name","sub_service_line_name","vertical_name","top_level_parent_customer_name"]:
        df_gm[col] = df_gm[col].fillna("(blank)")

    # --- Labour: Screendragon join via netsuite_project_id → project_id ---
    # timesheet_internal_cost verified = exact match to NULL rows in rpt table
    # Enables labour split by client AND service line (not just (blank) row)
    df_lab = get_labour_by_client(year_from=2022).copy()
    df_lab["accounting_period_start_date"] = pd.to_datetime(df_lab["accounting_period_start_date"])
    df_lab["yr"]        = df_lab["accounting_period_start_date"].dt.year
    df_lab["month_num"] = df_lab["accounting_period_start_date"].dt.month
    for col in ["service_line_name","sub_service_line_name","vertical_name","top_level_parent_customer_name"]:
        df_lab[col] = df_lab[col].fillna("(blank)")

    # --- Pipeline: HubSpot active deals ---
    df_pipe = get_pipeline().copy()
    df_pipe["pipeline_value_usd"] = df_pipe["pipeline_value_usd"].fillna(0)
    for col in ["service_line","vertical"]:
        if col in df_pipe.columns: df_pipe[col] = df_pipe[col].fillna("(blank)")

    # --- Targets: quarterly targets by team (Q1 2025+ only in DB) ---
    df_tgt = get_targets().copy()
    df_tgt["quarter_start_date"] = pd.to_datetime(df_tgt["quarter_start_date"])
    df_tgt["yr"] = df_tgt["quarter_start_date"].dt.year

    return df_gm, df_lab, df_pipe, df_tgt

df_gm, df_lab, df_pipe, df_tgt = load_data()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    # Brand header
    st.markdown(
        f'<div class="sb-brand">'
        f'<img src="data:image/png;base64,{logo_base64}" class="sb-logo"/>'
        f'<div><div class="sb-brand-name">MarketCast</div>'
        f'<div class="sb-brand-sub">Finance Dashboard</div></div></div>',
        unsafe_allow_html=True
    )

    # ── Time period ───────────────────────────────────────────
    st.markdown('<div class="sb-section"><div class="sb-section-title">Time Period</div>', unsafe_allow_html=True)
    years = sorted(df_gm["yr"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("Year", years, index=years.index(2025) if 2025 in years else 0)

    view_mode = st.radio("View", ["Full Year","YTD / Range","Rolling 12M"], horizontal=False)

    if view_mode == "YTD / Range":
        avail = sorted(df_gm[df_gm["yr"]==selected_year]["month_num"].dropna().unique().tolist())
        max_m = max(avail) if avail else 12
        month_range = st.select_slider("Month Range", options=MONTH_NAMES, value=("Jan", MONTH_MAP[max_m]))
        m_from = MONTH_NAMES.index(month_range[0]) + 1
        m_to   = MONTH_NAMES.index(month_range[1]) + 1
        period_label = f"{month_range[0]}–{month_range[1]} {selected_year}"
        rolling = False

    elif view_mode == "Rolling 12M":
        # Rolling 12 months ending at the latest available month in selected year
        # e.g. Jan 2025 → Dec 2025 rolling back 12 months
        avail = sorted(df_gm[df_gm["yr"]==selected_year]["month_num"].dropna().unique().tolist())
        end_m = max(avail) if avail else 12
        m_from, m_to = 1, 12
        period_label = f"Rolling 12M to {MONTH_MAP[end_m]} {selected_year}"
        rolling = True  # flag used in filter

    else:  # Full Year
        m_from, m_to = 1, 12
        period_label = f"{selected_year} Full Year"
        rolling = False

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Business filters (cascading) ──────────────────────────
    st.markdown('<div class="sb-section"><div class="sb-section-title">Business Filters</div>', unsafe_allow_html=True)

    sl_opts = ["All"] + sorted([x for x in df_gm["service_line_name"].unique() if x != "(blank)"])
    selected_sl = st.selectbox("Service Line", sl_opts)

    ssl_pool = df_gm if selected_sl=="All" else df_gm[df_gm["service_line_name"]==selected_sl]
    ssl_opts = ["All"] + sorted([x for x in ssl_pool["sub_service_line_name"].unique() if x != "(blank)"])
    selected_ssl = st.selectbox("Sub Service Line", ssl_opts)

    v_pool  = ssl_pool if selected_ssl=="All" else ssl_pool[ssl_pool["sub_service_line_name"]==selected_ssl]
    v_opts  = ["All"] + sorted([x for x in v_pool["vertical_name"].unique() if x != "(blank)"])
    selected_vertical = st.selectbox("Vertical", v_opts)

    c_pool  = v_pool if selected_vertical=="All" else v_pool[v_pool["vertical_name"]==selected_vertical]
    c_opts  = ["All"] + sorted([x for x in c_pool["top_level_parent_customer_name"].unique() if x not in EXCL])
    selected_customer = st.selectbox("Client", c_opts)
    st.markdown('</div>', unsafe_allow_html=True)

    # Active view summary card
    filters_active = [x for x in [
        selected_sl if selected_sl!="All" else None,
        selected_ssl if selected_ssl!="All" else None,
        selected_vertical if selected_vertical!="All" else None,
        selected_customer if selected_customer!="All" else None,
    ] if x]
    st.markdown(
        f'<div class="sb-active-view">'
        f'<div class="sb-view-label">Active View</div>'
        f'<div class="sb-view-value">{period_label}</div>'
        f'<div class="sb-view-sub">{" · ".join(filters_active) if filters_active else "No additional filters"}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="sb-bottom-spacer"></div>', unsafe_allow_html=True)

    # ── Visual theme ──────────────────────────────────────────
    st.markdown('<div class="sb-section"><div class="sb-section-title">Visual Style</div>', unsafe_allow_html=True)
    selected_theme = st.radio("Visual Style", THEME_OPTIONS, index=1)
    st.markdown('</div>', unsafe_allow_html=True)

# Extract palette colours
p = get_theme_palette(selected_theme)
SC = p["series"]; BS = p["blue_scale"]; DC = p["donut"]
WFT = p["wf_total"]; WFP = p["wf_pos"]; WFN = p["wf_neg"]
LC = p["current"]; LP = p["prior"]; AC = p["accent"]

# ── Filter function ───────────────────────────────────────────
def filt(data, year, m1=1, m2=12):
    """Apply year, month range and sidebar dimension filters."""
    d = data[(data["yr"]==year) & (data["month_num"]>=m1) & (data["month_num"]<=m2)].copy()
    if selected_sl!="All":       d = d[d["service_line_name"]==selected_sl]
    if selected_ssl!="All":      d = d[d["sub_service_line_name"]==selected_ssl]
    if selected_vertical!="All": d = d[d["vertical_name"]==selected_vertical]
    if selected_customer!="All": d = d[d["top_level_parent_customer_name"]==selected_customer]
    return d

# For rolling 12M: pull previous year months to backfill
if rolling:
    avail_curr  = sorted(df_gm[df_gm["yr"]==selected_year]["month_num"].dropna().unique().tolist())
    end_m       = max(avail_curr) if avail_curr else 12
    # months in current year: 1..end_m | months from prior year to fill: (end_m+1)..12
    df_curr_part  = filt(df_gm,  selected_year,   1, end_m)
    df_curr_prior = filt(df_gm,  selected_year-1, end_m+1, 12)
    df_curr       = pd.concat([df_curr_prior, df_curr_part], ignore_index=True)
    df_lab_curr_p = filt(df_lab, selected_year,   1, end_m)
    df_lab_curr_q = filt(df_lab, selected_year-1, end_m+1, 12)
    df_lab_curr   = pd.concat([df_lab_curr_q, df_lab_curr_p], ignore_index=True)
    # Prior rolling 12M = same logic one year back
    df_prior_part  = filt(df_gm,  selected_year-1, 1, end_m)
    df_prior_prev  = filt(df_gm,  selected_year-2, end_m+1, 12)
    df_prior       = pd.concat([df_prior_prev, df_prior_part], ignore_index=True)
    df_lab_prior   = pd.concat([filt(df_lab,selected_year-2,end_m+1,12), filt(df_lab,selected_year-1,1,end_m)], ignore_index=True)
else:
    df_curr      = filt(df_gm,  selected_year,   m_from, m_to)
    df_prior     = filt(df_gm,  selected_year-1, m_from, m_to)
    df_lab_curr  = filt(df_lab, selected_year,   m_from, m_to)
    df_lab_prior = filt(df_lab, selected_year-1, m_from, m_to)

# ── Aggregate P&L ─────────────────────────────────────────────
rev        = df_curr["revenue"].sum()
cogs       = df_curr["cogs"].sum()
fixed_cost = df_curr["fixed_cost"].sum()
# Labour from Screendragon (verified exact match); fallback to NULL rows if empty
labor      = df_lab_curr["labour_cost"].sum() if not df_lab_curr.empty else df_curr["labour"].sum()
gm         = rev - cogs - fixed_cost
contrib    = gm - labor

rev_py     = df_prior["revenue"].sum()
cogs_py    = df_prior["cogs"].sum()
fc_py      = df_prior["fixed_cost"].sum()
labor_py   = df_lab_prior["labour_cost"].sum() if not df_lab_prior.empty else df_prior["labour"].sum()
gm_py      = rev_py - cogs_py - fc_py
contrib_py = gm_py - labor_py

num_clients = df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()
clients_py  = df_prior[~df_prior["top_level_parent_customer_name"].isin(EXCL)]["top_level_parent_customer_name"].nunique()

gm_pct     = safe_pct(gm, rev);      cm_pct     = safe_pct(contrib, rev)
gm_pct_py  = safe_pct(gm_py,rev_py); cm_pct_py  = safe_pct(contrib_py,rev_py)
fc_pct     = safe_pct(fixed_cost,rev); fc_pct_py = safe_pct(fc_py,rev_py)
lab_pct    = safe_pct(labor,rev);     lab_pct_py = safe_pct(labor_py,rev_py)

# ── Page header ───────────────────────────────────────────────
st.markdown(f"### Finance Dashboard — {period_label}")
st.markdown(
    '<div class="formula-bar"><div class="formula-text">'
    'Gross Margin = Revenue – COGS – Fixed Cost &nbsp;&nbsp;|&nbsp;&nbsp;'
    'Contribution = Gross Margin – Labour'
    '</div></div>',
    unsafe_allow_html=True
)

# ── Top KPI row ───────────────────────────────────────────────
# All values in $M per Chris request
r1 = st.columns(8)
r1[0].markdown(kpi("Revenue",       rev,        rev-rev_py,           "vs PY"), unsafe_allow_html=True)
r1[1].markdown(kpi("Clients",       num_clients,num_clients-clients_py,"vs PY",kind="count"), unsafe_allow_html=True)
r1[2].markdown(kpi("COGS",          cogs), unsafe_allow_html=True)
r1[3].markdown(kpi("Fixed Cost",    fixed_cost), unsafe_allow_html=True)
r1[4].markdown(kpi("Labour",        labor,      labor-labor_py,       "vs PY"), unsafe_allow_html=True)
r1[5].markdown(kpi("Gross Margin",  gm,         gm-gm_py,             "vs PY"), unsafe_allow_html=True)
r1[6].markdown(kpi("GM %",          gm_pct,     gm_pct-gm_pct_py,    "vs PY", kind="pct"), unsafe_allow_html=True)
r1[7].markdown(kpi("Contribution",  contrib,    contrib-contrib_py,   "vs PY"), unsafe_allow_html=True)

r2 = st.columns(8)
r2[0].markdown(kpi("Contribution %",   cm_pct,  cm_pct-cm_pct_py,   "vs PY", kind="pct"), unsafe_allow_html=True)
r2[1].markdown(kpi("Fixed Cost % Rev", fc_pct,  fc_pct-fc_pct_py,   "vs PY", kind="pct"), unsafe_allow_html=True)
r2[2].markdown(kpi("Labour % Rev",     lab_pct, lab_pct-lab_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)

st.divider()

# ============================================================
# TABS — top-down P&L flow as requested by Chris
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview",        # Full P&L waterfall
    "Revenue",         # Decompose revenue D1→D2→D3
    "Gross Margin",    # GM bubble chart + GM% by SL
    "Clients",         # Client blow-up
    "Labour",          # By client/SL from Screendragon
    "Pipeline",        # Stages, SL breakdown
    "Targets",         # vs actuals
])

# ============================================================
# TAB 1 — OVERVIEW
# Full P&L story in one view: waterfall + monthly trend + allocation
# ============================================================
with tab1:
    st.markdown('<div class="section-header">P&L Summary</div>', unsafe_allow_html=True)

    col_wf, col_tr = st.columns(2)

    with col_wf:
        # Waterfall: Revenue → COGS → Fixed Cost → [GM] → Labour → [Contribution]
        # This is the top-down flow Chris requested
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","relative","total","relative","total"],
            x=["Revenue","COGS","Fixed Cost","Gross Margin","Labour","Contribution"],
            y=[rev, -cogs, -fixed_cost, None, -labor, None],
            connector={"line":{"color":"#243041"}},
            increasing={"marker":{"color":WFP,"line":{"width":0}}},
            decreasing={"marker":{"color":WFN,"line":{"width":0}}},
            totals={"marker":{"color":WFT,"line":{"width":0}}},
            # Show $M values on bars
            text=[fmt_m(rev),fmt_m(cogs),fmt_m(fixed_cost),fmt_m(gm),fmt_m(labor),fmt_m(contrib)],
            textfont={"color":"#cbd5e1","size":10,"family":"DM Mono"},
            textposition="outside"
        ))
        wf.update_layout(**PT, title="Revenue to Contribution Bridge",
                         title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(wf, use_container_width=True)

    with col_tr:
        # Monthly revenue trend stacked by service line
        rm = df_curr.groupby(["accounting_period_start_date","service_line_name"])["revenue"].sum().reset_index()
        ft = px.bar(rm, x="accounting_period_start_date", y="revenue", color="service_line_name",
                    color_discrete_sequence=SC, title="Monthly Revenue by Service Line",
                    labels={"revenue":"Revenue ($)","accounting_period_start_date":"","service_line_name":""})
        ft.update_traces(marker_line_width=0)
        ft.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1", bargap=0.2)
        st.plotly_chart(ft, use_container_width=True)

    col_yoy, col_alloc = st.columns(2)

    with col_yoy:
        # Revenue vs prior year line chart
        cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Current"})
        py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Prior Year"})
        yoy = pd.DataFrame({"month_num":list(range(1,13))}).merge(cy,on="month_num",how="left").merge(py,on="month_num",how="left").fillna(0)
        yoy["ml"] = yoy["month_num"].map(MONTH_MAP)
        ym = yoy.melt(id_vars=["month_num","ml"], value_vars=["Current","Prior Year"], var_name="Period", value_name="Revenue")
        f3 = px.line(ym, x="ml", y="Revenue", color="Period", markers=True,
                     color_discrete_map={"Current":LC,"Prior Year":LP},
                     title="Revenue vs Prior Year", labels={"ml":"","Revenue":""})
        f3.update_traces(line_width=2.5); f3.update_layout(**PT, title_font_color="#cbd5e1")
        st.plotly_chart(f3, use_container_width=True)

    with col_alloc:
        # Fixed cost donut — Brand Effect / AE Synd / RTA split
        asp = pd.DataFrame({
            "Type":["Brand Effect","AE Synd","RTA"],
            "Amount":[df_curr["be_allocation"].sum(),df_curr["ae_allocation"].sum(),df_curr["rta_allocation"].sum()]
        })
        asp = asp[asp["Amount"]>0]
        fa = px.pie(asp, names="Type", values="Amount", hole=0.68, title="Fixed Cost Allocation Split",
                    color="Type", color_discrete_map={"Brand Effect":DC[0],"AE Synd":DC[1],"RTA":DC[2]})
        fa.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fa.add_annotation(text=fmt_m(fixed_cost), x=0.5, y=0.5, showarrow=False,
                          font=dict(size=18,color="#f8fafc",family="DM Sans"))
        st.plotly_chart(fa, use_container_width=True)

# ============================================================
# TAB 2 — REVENUE
# D1: Total revenue KPI
# D2: Decompose by service line (bar chart, controllable)
# D3: Sub service line + COGS breakdown
# ============================================================
with tab2:
    st.markdown('<div class="section-header">D1 — Total Revenue</div>', unsafe_allow_html=True)
    d1c1, d1c2, d1c3 = st.columns(3)
    d1c1.markdown(kpi("Total Revenue",   rev,  rev-rev_py,   "vs PY"), unsafe_allow_html=True)
    d1c2.markdown(kpi("COGS",            cogs, cogs-cogs_py, "vs PY"), unsafe_allow_html=True)
    d1c3.markdown(kpi("Gross Margin",    gm,   gm-gm_py,     "vs PY"), unsafe_allow_html=True)

    st.markdown('<div class="section-header">D2 — Revenue by Service Line</div>', unsafe_allow_html=True)

    col_sl, col_sub = st.columns(2)

    with col_sl:
        # Revenue by service line — horizontal bar, sorted descending
        rv_sl = df_curr.groupby("service_line_name").agg(
            revenue=("revenue","sum"), cogs=("cogs","sum")).reset_index()
        rv_sl = rv_sl[rv_sl["revenue"]>0].sort_values("revenue",ascending=True)
        fsl = px.bar(rv_sl, x="revenue", y="service_line_name", orientation="h",
                     color="service_line_name", color_discrete_sequence=SC,
                     title="Revenue by Service Line",
                     labels={"revenue":"Revenue ($M)","service_line_name":""})
        fsl.update_traces(marker_line_width=0)
        fsl.update_layout(**PT, showlegend=False, title_font_color="#cbd5e1")
        # Format x-axis in $M
        fsl.update_xaxes(tickformat="$,.0f")
        st.plotly_chart(fsl, use_container_width=True)

    with col_sub:
        # Revenue vs COGS grouped bar by service line — shows direct cost ratio
        rv_sl_m = rv_sl.melt(id_vars="service_line_name", value_vars=["revenue","cogs"],
                             var_name="Metric", value_name="Value")
        fcg = px.bar(rv_sl_m, x="service_line_name", y="Value", color="Metric",
                     barmode="group", color_discrete_map={"revenue":LC,"cogs":SC[2]},
                     title="Revenue vs COGS by Service Line",
                     labels={"Value":"$","service_line_name":"","Metric":""})
        fcg.update_traces(marker_line_width=0)
        fcg.update_layout(**PT, xaxis_tickangle=-30, title_font_color="#cbd5e1", bargap=0.25)
        st.plotly_chart(fcg, use_container_width=True)

    st.markdown('<div class="section-header">D3 — Sub Service Line Breakdown</div>', unsafe_allow_html=True)

    # Selectable service line for sub-SL drill-down
    sl_list = sorted([x for x in df_curr["service_line_name"].unique() if x!="(blank)"])
    drill_sl = st.selectbox("Select Service Line to drill into", sl_list, key="revenue_drill")

    df_drill = df_curr[df_curr["service_line_name"]==drill_sl]

    col_d3a, col_d3b = st.columns(2)

    with col_d3a:
        # Revenue by sub service line — stacked monthly bar
        sub_monthly = df_drill.groupby(["accounting_period_start_date","sub_service_line_name"])["revenue"].sum().reset_index()
        fd3 = px.bar(sub_monthly, x="accounting_period_start_date", y="revenue",
                     color="sub_service_line_name", color_discrete_sequence=SC,
                     title=f"{drill_sl} — Monthly Revenue by Sub Service Line",
                     labels={"revenue":"Revenue","accounting_period_start_date":"","sub_service_line_name":""})
        fd3.update_traces(marker_line_width=0)
        fd3.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        st.plotly_chart(fd3, use_container_width=True)

    with col_d3b:
        # COGS breakdown by sub service line
        cogs_sub = df_drill.groupby("sub_service_line_name")["cogs"].sum().reset_index().sort_values("cogs",ascending=True)
        fc2 = px.bar(cogs_sub, x="cogs", y="sub_service_line_name", orientation="h",
                     color="cogs", color_continuous_scale=BS,
                     title=f"{drill_sl} — COGS by Sub Service Line",
                     labels={"cogs":"COGS ($)","sub_service_line_name":""})
        fc2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fc2, use_container_width=True)

    # Full P&L data table — service line + sub service line grain
    st.markdown('<div class="section-header">Revenue Detail Table — $M</div>', unsafe_allow_html=True)

    # Join attributed labour into the summary table
    lab_sl_join = df_lab_curr.groupby(["service_line_name","sub_service_line_name"])["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour_attributed"})
    rv_tbl = (df_curr.groupby(["service_line_name","sub_service_line_name"],dropna=False)
              .agg(revenue=("revenue","sum"), cogs=("cogs","sum"),
                   fixed_cost=("fixed_cost","sum"), gross_margin=("gross_margin","sum"),
                   clients=("top_level_parent_customer_name",lambda s:s[~s.isin(EXCL)].nunique()))
              .reset_index())
    rv_tbl = rv_tbl.merge(lab_sl_join, on=["service_line_name","sub_service_line_name"], how="left")
    rv_tbl["labour_attributed"] = rv_tbl["labour_attributed"].fillna(0)
    rv_tbl["contribution"] = rv_tbl["gross_margin"] - rv_tbl["labour_attributed"]
    rv_tbl["gm_pct"] = (rv_tbl["gross_margin"]/rv_tbl["revenue"].replace(0,float("nan"))*100).round(1)
    rv_tbl["cm_pct"] = (rv_tbl["contribution"]/rv_tbl["revenue"].replace(0,float("nan"))*100).round(1)
    # Display in $M per Chris request
    for col in ["revenue","cogs","fixed_cost","gross_margin","labour_attributed","contribution"]:
        rv_tbl[col] = (rv_tbl[col]/1e6).round(2)
    rv_tbl = rv_tbl.sort_values(["service_line_name","revenue"],ascending=[True,False])
    rv_tbl.columns = [c.replace("_"," ").title() for c in rv_tbl.columns]
    st.dataframe(rv_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":            st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":               st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":         st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin":       st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labour Attributed":  st.column_config.NumberColumn("Labour ($M)",       format="$%.2f"),
        "Contribution":       st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":             st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":             st.column_config.NumberColumn("CM %",              format="%.1f%%"),
        "Clients":            st.column_config.NumberColumn("Clients",           format="%d"),
    })

# ============================================================
# TAB 3 — GROSS MARGIN
# Bubble chart: client bubbles, x=revenue, y=GM%, size=contribution
# Left side of chart shows CM% label on each bubble (Chris request)
# Top 15 default with toggle to show all
# ============================================================
with tab3:
    st.markdown('<div class="section-header">Client Gross Margin Analysis</div>', unsafe_allow_html=True)

    # Build client-level aggregation with attributed labour
    lab_cl = df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour_attributed"})
    cl_agg = (df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]
              .groupby("top_level_parent_customer_name")
              .agg(revenue=("revenue","sum"), cogs=("cogs","sum"),
                   fixed_cost=("fixed_cost","sum"), gross_margin=("gross_margin","sum"))
              .reset_index())
    cl_agg = cl_agg.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl_agg["labour_attributed"] = cl_agg["labour_attributed"].fillna(0)
    cl_agg["contribution"] = cl_agg["gross_margin"] - cl_agg["labour_attributed"]
    cl_agg["gm_pct"] = (cl_agg["gross_margin"]/cl_agg["revenue"].replace(0,float("nan"))*100).round(1)
    cl_agg["cm_pct"] = (cl_agg["contribution"]/cl_agg["revenue"].replace(0,float("nan"))*100).round(1)
    cl_agg = cl_agg[cl_agg["revenue"]>0]

    # Top 15 toggle (Chris requested scrollable top 15 or all)
    show_all = st.toggle("Show all clients (default: top 15 by revenue)", value=False, key="gm_show_all")
    cl_plot = cl_agg.sort_values("revenue",ascending=False) if show_all else cl_agg.sort_values("revenue",ascending=False).head(15)

    col_bub, col_bar = st.columns([3,2])

    with col_bub:
        # Bubble chart — GM tab centrepiece
        # x=revenue, y=GM%, bubble size=contribution, colour=GM%
        # CM% shown as text label on left side of each bubble (Chris request)
        fbub = px.scatter(
            cl_plot,
            x="revenue",
            y="gm_pct",
            size="gross_margin",
            size_max=50,
            color="gm_pct",
            color_continuous_scale=BS,
            hover_name="top_level_parent_customer_name",
            hover_data={
                "revenue":      ":.2f",
                "gm_pct":       ":.1f",
                "cm_pct":       ":.1f",
                "gross_margin": ":.2f",
                "labour_attributed":":.2f",
                "contribution": ":.2f",
            },
            title=f"Client GM% vs Revenue — {'All Clients' if show_all else 'Top 15'}",
            labels={"revenue":"Revenue ($M)","gm_pct":"Gross Margin %","gross_margin":"Gross Margin"},
        )
        # Add CM% as text annotation to the left of each bubble
        for _, row in cl_plot.iterrows():
            fbub.add_annotation(
                x=row["revenue"],
                y=row["gm_pct"],
                text=f"CM {row['cm_pct']:.0f}%",
                showarrow=False,
                xanchor="right",
                xshift=-10,
                font=dict(size=8, color="#6b7280", family="DM Mono"),
            )
        fbub.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        fbub.update_xaxes(tickformat="$,.0f")
        st.plotly_chart(fbub, use_container_width=True)

    with col_bar:
        # GM% horizontal bar by service line — context for the bubble chart
        gm_sl = df_curr.groupby("service_line_name").agg(revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index()
        gm_sl["gm_pct"] = (gm_sl["gm"]/gm_sl["revenue"].replace(0,float("nan"))*100).round(1)
        gm_sl = gm_sl[gm_sl["revenue"]>0].sort_values("gm_pct",ascending=True)
        fgmsl = px.bar(gm_sl, x="gm_pct", y="service_line_name", orientation="h",
                       color="gm_pct", color_continuous_scale=BS,
                       title="GM % by Service Line",
                       labels={"gm_pct":"Gross Margin %","service_line_name":""})
        fgmsl.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fgmsl, use_container_width=True)

    st.markdown('<div class="section-header">GM % Monthly Trend</div>', unsafe_allow_html=True)
    col_gmt, col_cms = st.columns(2)

    with col_gmt:
        gmt = df_curr.groupby("accounting_period_start_date").agg(revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index().sort_values("accounting_period_start_date")
        gmt["gm_pct"] = (gmt["gm"]/gmt["revenue"].replace(0,float("nan"))*100).round(1)
        fgt = px.area(gmt, x="accounting_period_start_date", y="gm_pct",
                      title="Monthly Gross Margin % Trend",
                      labels={"accounting_period_start_date":"","gm_pct":"GM %"},
                      color_discrete_sequence=[LC])
        fgt.update_traces(line_width=2)
        fgt.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        st.plotly_chart(fgt, use_container_width=True)

    with col_cms:
        # Contribution % by SL for comparison with GM%
        lab_sl3 = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour"})
        cm_sl = df_curr.groupby("service_line_name").agg(revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index()
        cm_sl = cm_sl.merge(lab_sl3, on="service_line_name", how="left"); cm_sl["labour"] = cm_sl["labour"].fillna(0)
        cm_sl["contribution"] = cm_sl["gm"] - cm_sl["labour"]
        cm_sl["cm_pct"] = (cm_sl["contribution"]/cm_sl["revenue"].replace(0,float("nan"))*100).round(1)
        cm_sl = cm_sl[cm_sl["revenue"]>0].sort_values("cm_pct",ascending=True)
        fcs = px.bar(cm_sl, x="cm_pct", y="service_line_name", orientation="h",
                     color="cm_pct", color_continuous_scale=BS,
                     title="Contribution % by Service Line",
                     labels={"cm_pct":"Contribution %","service_line_name":""})
        fcs.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fcs, use_container_width=True)

# ============================================================
# TAB 4 — CLIENTS
# "Blow-up" per client: select client → full P&L view
# Top 15 bar + scatter overview, then drill into individual client
# ============================================================
with tab4:
    st.markdown('<div class="section-header">Client Overview</div>', unsafe_allow_html=True)

    use_cm = st.toggle("Sort/size by Contribution (default: Gross Margin)", value=False, key="client_toggle")
    mc = "contribution" if use_cm else "gross_margin"
    mt = "Contribution" if use_cm else "Gross Margin"

    # Reuse cl_agg from GM tab (already has labour attributed)
    col_top, col_scat = st.columns(2)

    with col_top:
        # Top 15 clients — scrollable dataframe below the chart
        tc2 = cl_agg.sort_values(mc, ascending=True).tail(15)
        ft15 = px.bar(tc2, x=mc, y="top_level_parent_customer_name", orientation="h",
                      color="revenue", color_continuous_scale=AC,
                      title=f"Top 15 Clients by {mt}",
                      labels={mc:mt,"top_level_parent_customer_name":"","revenue":"Revenue"})
        ft15.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(ft15, use_container_width=True)

    with col_scat:
        cs2 = cl_agg.sort_values("revenue",ascending=False).head(20)
        pct_col = "cm_pct" if use_cm else "gm_pct"
        pct_lbl = "CM %" if use_cm else "GM %"
        fsc = px.scatter(cs2, x="revenue", y=pct_col, size=mc, text="top_level_parent_customer_name",
                         title=f"Revenue vs {pct_lbl}", size_max=36,
                         labels={"revenue":"Revenue",pct_col:pct_lbl,mc:mt})
        fsc.update_traces(marker=dict(color=LC,sizemode="area",opacity=0.85),
                          textposition="top center", textfont=dict(size=8,color="#cbd5e1"))
        fsc.update_layout(**PT, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(fsc, use_container_width=True)

    # ── Client blow-up ────────────────────────────────────────
    # Per Chris: select a client → see full P&L broken down by SL
    st.markdown('<div class="section-header">Client Blow-Up — Full P&L</div>', unsafe_allow_html=True)

    all_clients = sorted(cl_agg["top_level_parent_customer_name"].tolist())
    selected_client_detail = st.selectbox("Select client", all_clients, key="client_blowup")

    # Filter gross margin and lab data to this specific client
    df_client_gm  = df_curr[df_curr["top_level_parent_customer_name"]==selected_client_detail]
    df_client_lab = df_lab_curr[df_lab_curr["top_level_parent_customer_name"]==selected_client_detail]

    # Client-level headline numbers
    cl_rev   = df_client_gm["revenue"].sum()
    cl_cogs  = df_client_gm["cogs"].sum()
    cl_fc    = df_client_gm["fixed_cost"].sum()
    cl_gm    = df_client_gm["gross_margin"].sum()
    cl_lab   = df_client_lab["labour_cost"].sum()
    cl_cont  = cl_gm - cl_lab
    cl_gmpct = safe_pct(cl_gm, cl_rev)
    cl_cmpct = safe_pct(cl_cont, cl_rev)

    kc = st.columns(6)
    kc[0].markdown(kpi("Revenue",     cl_rev),  unsafe_allow_html=True)
    kc[1].markdown(kpi("COGS",        cl_cogs), unsafe_allow_html=True)
    kc[2].markdown(kpi("Fixed Cost",  cl_fc),   unsafe_allow_html=True)
    kc[3].markdown(kpi("Gross Margin",cl_gm,    kind="money"),   unsafe_allow_html=True)
    kc[4].markdown(kpi("GM %",        cl_gmpct, kind="pct"),     unsafe_allow_html=True)
    kc[5].markdown(kpi("Contribution",cl_cont,  kind="money"),   unsafe_allow_html=True)

    col_cbl, col_cbr = st.columns(2)

    with col_cbl:
        # Client P&L waterfall
        cl_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","relative","total","relative","total"],
            x=["Revenue","COGS","Fixed Cost","Gross Margin","Labour","Contribution"],
            y=[cl_rev,-cl_cogs,-cl_fc,None,-cl_lab,None],
            connector={"line":{"color":"#243041"}},
            increasing={"marker":{"color":WFP,"line":{"width":0}}},
            decreasing={"marker":{"color":WFN,"line":{"width":0}}},
            totals={"marker":{"color":WFT,"line":{"width":0}}},
            text=[fmt_m(cl_rev),fmt_m(cl_cogs),fmt_m(cl_fc),fmt_m(cl_gm),fmt_m(cl_lab),fmt_m(cl_cont)],
            textfont={"color":"#cbd5e1","size":10},
            textposition="outside"
        ))
        cl_wf.update_layout(**PT, title=f"{selected_client_detail} — P&L Bridge",
                             title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(cl_wf, use_container_width=True)

    with col_cbr:
        # Client revenue by sub service line
        cl_sub = (df_client_gm.groupby("sub_service_line_name")
                  .agg(revenue=("revenue","sum"), gm=("gross_margin","sum"))
                  .reset_index().sort_values("revenue",ascending=True))
        cl_sub["gm_pct"] = (cl_sub["gm"]/cl_sub["revenue"].replace(0,float("nan"))*100).round(1)
        fcl_sub = px.bar(cl_sub, x="revenue", y="sub_service_line_name", orientation="h",
                         color="gm_pct", color_continuous_scale=BS,
                         title=f"{selected_client_detail} — Revenue by Sub Service Line",
                         labels={"revenue":"Revenue","sub_service_line_name":"","gm_pct":"GM %"})
        fcl_sub.update_layout(**PT, title_font_color="#cbd5e1")
        st.plotly_chart(fcl_sub, use_container_width=True)

    # Client monthly trend
    cl_mth = df_client_gm.groupby("accounting_period_start_date").agg(
        revenue=("revenue","sum"), gm=("gross_margin","sum")).reset_index().sort_values("accounting_period_start_date")
    cl_mth["gm_pct"] = (cl_mth["gm"]/cl_mth["revenue"].replace(0,float("nan"))*100).round(1)
    cl_mth["ml"] = pd.to_datetime(cl_mth["accounting_period_start_date"]).dt.strftime("%b %Y")
    fclm = px.line(cl_mth, x="ml", y=["revenue","gm"], markers=True,
                   color_discrete_map={"revenue":LC,"gm":SC[1]},
                   title=f"{selected_client_detail} — Monthly Revenue & GM",
                   labels={"ml":"","value":"$","variable":""})
    fclm.update_traces(line_width=2)
    fclm.update_layout(**PT, title_font_color="#cbd5e1")
    st.plotly_chart(fclm, use_container_width=True)

    # All clients scrollable table — shown below the blow-up
    st.markdown('<div class="section-header">All Clients — P&L Summary ($M)</div>', unsafe_allow_html=True)
    cl_tbl = cl_agg.copy()
    for col in ["revenue","cogs","fixed_cost","gross_margin","labour_attributed","contribution"]:
        cl_tbl[col] = (cl_tbl[col]/1e6).round(2)
    cl_tbl = cl_tbl.sort_values("revenue",ascending=False)
    cl_tbl.columns = [c.replace("_"," ").title() for c in cl_tbl.columns]
    st.dataframe(cl_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":            st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":               st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":         st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin":       st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labour Attributed":  st.column_config.NumberColumn("Labour ($M)",       format="$%.2f"),
        "Contribution":       st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":             st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":             st.column_config.NumberColumn("CM %",              format="%.1f%%"),
    })

# ============================================================
# TAB 5 — LABOUR
# Screendragon timesheet data joined to revenue fact table
# Breakdown by client, service line, sub service line
# ============================================================
with tab5:
    st.markdown('<div class="section-header">Labour Overview</div>', unsafe_allow_html=True)

    tlab    = df_lab_curr["labour_cost"].sum()
    tlab_py = df_lab_prior["labour_cost"].sum()
    thrs    = df_lab_curr["total_hours"].sum()
    avghr   = tlab/thrs if thrs>0 else 0

    lk = st.columns(4)
    lk[0].markdown(kpi("Total Labour",   tlab,  tlab-tlab_py,"vs PY"), unsafe_allow_html=True)
    lk[1].markdown(kpi("Labour % Rev",   safe_pct(tlab,rev), kind="pct"), unsafe_allow_html=True)
    lk[2].markdown(kpi("Total Hours",    thrs,               kind="count"), unsafe_allow_html=True)
    lk[3].markdown(kpi("Avg Cost/hr",    avghr,              kind="dollar"), unsafe_allow_html=True)

    cla, clb = st.columns(2)
    with cla:
        # Monthly labour by service line stacked bar
        lm = df_lab_curr.groupby(["accounting_period_start_date","service_line_name"])["labour_cost"].sum().reset_index()
        flm = px.bar(lm, x="accounting_period_start_date", y="labour_cost", color="service_line_name",
                     color_discrete_sequence=SC, title="Labour by Service Line — Monthly",
                     labels={"labour_cost":"Labour Cost","accounting_period_start_date":"","service_line_name":""})
        flm.update_traces(marker_line_width=0)
        flm.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        st.plotly_chart(flm, use_container_width=True)

    with clb:
        # Top 15 clients by labour cost
        lbc = (df_lab_curr[~df_lab_curr["top_level_parent_customer_name"].isin(EXCL)]
               .groupby("top_level_parent_customer_name")["labour_cost"].sum().reset_index()
               .sort_values("labour_cost",ascending=True).tail(15))
        flc = px.bar(lbc, x="labour_cost", y="top_level_parent_customer_name", orientation="h",
                     color="labour_cost", color_continuous_scale=BS,
                     title="Top 15 Clients by Labour Cost",
                     labels={"labour_cost":"Labour Cost","top_level_parent_customer_name":""})
        flc.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(flc, use_container_width=True)

    clc, cld = st.columns(2)
    with clc:
        # Labour as % of revenue by service line — shows where labour is heaviest
        lrv = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index()
        rvsl2 = df_curr.groupby("service_line_name")["revenue"].sum().reset_index()
        lrv = lrv.merge(rvsl2, on="service_line_name", how="left")
        lrv["labour_pct"] = (lrv["labour_cost"]/lrv["revenue"].replace(0,float("nan"))*100).round(1)
        lrv = lrv[lrv["revenue"]>0].sort_values("labour_pct",ascending=True)
        flr = px.bar(lrv, x="labour_pct", y="service_line_name", orientation="h",
                     color="labour_pct", color_continuous_scale=BS,
                     title="Labour % of Revenue by Service Line",
                     labels={"labour_pct":"Labour %","service_line_name":""})
        flr.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(flr, use_container_width=True)

    with cld:
        # Year-over-year labour comparison by service line
        lyc = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index().assign(period=str(selected_year))
        lyp = df_lab_prior.groupby("service_line_name")["labour_cost"].sum().reset_index().assign(period=str(selected_year-1))
        lyoy = pd.concat([lyc,lyp])
        fly = px.bar(lyoy, x="service_line_name", y="labour_cost", color="period", barmode="group",
                     color_discrete_sequence=[LC,LP], title="Labour YoY by Service Line",
                     labels={"labour_cost":"Labour Cost","service_line_name":"","period":"Year"})
        fly.update_traces(marker_line_width=0)
        fly.update_layout(**PT, xaxis_tickangle=-30, title_font_color="#cbd5e1")
        st.plotly_chart(fly, use_container_width=True)

    # Full labour detail table — client × SL × sub-SL
    st.markdown('<div class="section-header">Labour Detail — Client × Service Line ($M)</div>', unsafe_allow_html=True)
    ld = (df_lab_curr[~df_lab_curr["top_level_parent_customer_name"].isin(EXCL)]
          .groupby(["top_level_parent_customer_name","service_line_name","sub_service_line_name"])
          .agg(labour_cost=("labour_cost","sum"), total_hours=("total_hours","sum"))
          .reset_index().sort_values("labour_cost",ascending=False))
    ld["cost_per_hour"] = (ld["labour_cost"]/ld["total_hours"].replace(0,float("nan"))).round(0)
    ld["labour_cost"]   = (ld["labour_cost"]/1e6).round(3)  # $M
    ld.columns = [c.replace("_"," ").title() for c in ld.columns]
    st.dataframe(ld, use_container_width=True, hide_index=True, column_config={
        "Labour Cost":   st.column_config.NumberColumn("Labour ($M)", format="$%.3f"),
        "Total Hours":   st.column_config.NumberColumn("Hours",       format="%.0f"),
        "Cost Per Hour": st.column_config.NumberColumn("$/hr",        format="$%.0f"),
    })

# ============================================================
# TAB 6 — PIPELINE
# HubSpot active deals — stages, service line breakdown
# Note: Chris wants stages 1-6 — map from current stage names needed
# Currently shows actual stage names from HubSpot; mapping TBC with John
# ============================================================
with tab6:
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)

    dp = df_pipe.drop_duplicates("deal_id")
    if "service_line" in dp.columns:
        dp = dp[~dp["service_line"].isin(EXCL)]

    tp = dp["pipeline_value_usd"].sum()
    td = dp["deal_id"].nunique()
    ad = tp/td if td>0 else 0

    pk = st.columns(3)
    pk[0].markdown(kpi("Total Pipeline",    tp), unsafe_allow_html=True)
    pk[1].markdown(kpi("Active Deals",      td, kind="count"), unsafe_allow_html=True)
    pk[2].markdown(kpi("Avg Deal Size",     ad), unsafe_allow_html=True)

    col_ps, col_psl = st.columns(2)

    with col_ps:
        # Pipeline by stage — sorted by value descending
        # TODO: map to stages 1-6 once Chris confirms naming convention
        ps2 = dp.groupby("deal_pipeline_stage_name").agg(
            deals=("deal_id","nunique"), value=("pipeline_value_usd","sum")).reset_index().sort_values("value",ascending=True)
        fp8 = px.bar(ps2, x="value", y="deal_pipeline_stage_name", orientation="h",
                     color="value", color_continuous_scale=BS,
                     title="Pipeline by Stage",
                     labels={"value":"Pipeline Value ($)","deal_pipeline_stage_name":""})
        fp8.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fp8, use_container_width=True)

    with col_psl:
        # Pipeline by service line
        psl = dp.groupby("service_line").agg(
            deals=("deal_id","nunique"), value=("pipeline_value_usd","sum")).reset_index().sort_values("value",ascending=False)
        fp9 = px.bar(psl, x="service_line", y="value", color="value", color_continuous_scale=BS,
                     title="Pipeline by Service Line",
                     labels={"value":"Pipeline Value ($)","service_line":""})
        fp9.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False,
                          title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(fp9, use_container_width=True)

    st.markdown('<div class="section-header">Pipeline Detail</div>', unsafe_allow_html=True)
    ptbl = (dp.groupby(["deal_pipeline_stage_name","service_line","vertical"])
            .agg(deals=("deal_id","nunique"), value=("pipeline_value_usd","sum"))
            .reset_index().sort_values("value",ascending=False))
    ptbl["value"] = (ptbl["value"]/1e6).round(2)  # $M
    ptbl.columns = [c.replace("_"," ").title() for c in ptbl.columns]
    st.dataframe(ptbl, use_container_width=True, hide_index=True,
                 column_config={"Value":st.column_config.NumberColumn("Value ($M)", format="$%.2f")})

# ============================================================
# TAB 7 — TARGETS
# Quarterly targets by team vs actual revenue
# Data only from Q1 2025 onwards (limitation — flag to Chris)
# ============================================================
with tab7:
    st.markdown('<div class="section-header">Targets vs Actuals</div>', unsafe_allow_html=True)

    dty = df_tgt[df_tgt["yr"]==selected_year].copy()
    tt  = dty["target_usd"].sum() if not dty.empty else 0
    vt  = rev - tt
    ptt = safe_pct(rev, tt) if tt not in (0,None) else 0

    tk = st.columns(4)
    tk[0].markdown(kpi(f"{selected_year} Target", tt), unsafe_allow_html=True)
    tk[1].markdown(kpi("Actual Revenue", rev, vt, "vs Target"), unsafe_allow_html=True)
    tk[2].markdown(kpi("Attainment %",   ptt, kind="pct"), unsafe_allow_html=True)
    tk[3].markdown(kpi("Teams", dty["team_primary_name"].nunique() if not dty.empty else 0, kind="count"), unsafe_allow_html=True)

    col_qt, col_ta = st.columns(2)

    with col_qt:
        if not dty.empty:
            qt = (dty.assign(ql="Q"+dty["quarter_start_date"].dt.quarter.astype(str))
                  .groupby(["ql","quarter_start_date"],as_index=False)["target_usd"].sum()
                  .sort_values("quarter_start_date"))
            fqt = px.bar(qt, x="ql", y="target_usd", color="target_usd", color_continuous_scale=BS,
                         title="Quarterly Targets", labels={"target_usd":"Target","ql":"Quarter"},
                         category_orders={"ql":qt["ql"].tolist()})
            fqt.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
            st.plotly_chart(fqt, use_container_width=True)
        else:
            st.info(f"No target data for {selected_year}. Targets only loaded from Q1 2025.")

    with col_ta:
        if not dty.empty:
            ta = dty.groupby("team_primary_name")["target_usd"].sum().reset_index().sort_values("target_usd",ascending=True)
            fta = px.bar(ta, x="target_usd", y="team_primary_name", orientation="h",
                         color="target_usd", color_continuous_scale=BS,
                         title="Annual Target by Team",
                         labels={"target_usd":"Annual Target","team_primary_name":""})
            fta.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            st.plotly_chart(fta, use_container_width=True)

    st.markdown('<div class="section-header">Target Detail</div>', unsafe_allow_html=True)
    if not dty.empty:
        ttbl = dty.copy()
        ttbl["target_usd"] = (ttbl["target_usd"]/1e6).round(2)  # $M
        ttbl.columns = [c.replace("_"," ").title() for c in ttbl.columns]
        st.dataframe(ttbl, use_container_width=True, hide_index=True,
                     column_config={"Target Usd":st.column_config.NumberColumn("Target ($M)", format="$%.2f")})
    else:
        st.info("No targets loaded. Note: targets only available from Q1 2025 onwards in the DB.")
