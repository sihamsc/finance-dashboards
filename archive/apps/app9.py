import base64
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.models.financials import get_gross_margin, get_pipeline, get_targets, get_labour_by_client

st.set_page_config(
    page_title="MarketCast Finance",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_base64_image(path: str) -> str:
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_base64 = get_base64_image("assets/logo.png")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #07090e; color: #f3f4f6; }
    .block-container { padding: 1.6rem 2.1rem 2.3rem 2.1rem; max-width: 100% !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1016 0%, #090b10 100%); border-right: 1px solid #1b2230; }
    div[data-testid="stSidebar"] .block-container { padding: 1.25rem 0.95rem 1.8rem 0.95rem; display: flex; flex-direction: column; min-height: 100vh; }
    .sb-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 1rem; }
    .sb-logo { width: 28px; height: 28px; object-fit: contain; border-radius: 6px; flex-shrink: 0; }
    .sb-brand-name { font-size: 17px; font-weight: 700; color: #f5f7fb; letter-spacing: -0.02em; line-height: 1; }
    .sb-brand-sub { font-family: 'DM Mono', monospace; font-size: 9px; color: #667085; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 3px; }
    .sb-section { background: #0f131b; border: 1px solid #1b2230; border-radius: 14px; padding: 0.95rem 0.85rem 0.5rem 0.85rem; margin-bottom: 0.8rem; }
    .sb-section-title { font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: #6b7280; margin-bottom: 0.65rem; }
    .sb-active-view { background: linear-gradient(180deg, rgba(215,243,74,0.08) 0%, rgba(215,243,74,0.03) 100%); border: 1px solid rgba(215,243,74,0.16); border-radius: 12px; padding: 0.8rem 0.9rem; margin-top: 0.2rem; }
    .sb-view-label { font-family: 'DM Mono', monospace; font-size: 9px; color: #d7f34a; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.35rem; }
    .sb-view-value { font-size: 13px; font-weight: 600; color: #f3f4f6; margin-bottom: 0.35rem; }
    .sb-view-sub { font-size: 11px; color: #9ca3af; line-height: 1.45; }
    .sb-bottom-spacer { flex: 1 1 auto; min-height: 1rem; }
    .stSelectbox label, .stRadio > label, .stSelectSlider > label, .stToggle label { font-family: 'DM Mono', monospace !important; font-size: 9px !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; color: #6b7280 !important; }
    div[data-baseweb="select"] > div { background: #090d14 !important; border: 1px solid #202938 !important; border-radius: 10px !important; }
    div[data-baseweb="select"] span { color: #e5e7eb !important; }
    div[data-baseweb="select"] svg { fill: #6b7280 !important; }
    div[role="radiogroup"] label { background: #0a0d14; border: 1px solid #202938; border-radius: 10px; padding: 0.35rem 0.6rem; }
    .metric-card { background: linear-gradient(180deg, #0c1017 0%, #0a0d13 100%); border: 1px solid #1b2230; border-radius: 14px; padding: 0.95rem 1.05rem; min-height: 88px; }
    .metric-label { font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; margin-bottom: 0.45rem; white-space: nowrap; }
    .metric-value { font-size: 19px; font-weight: 700; color: #f8fafc; line-height: 1.05; letter-spacing: -0.03em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .metric-delta { font-family: 'DM Mono', monospace; font-size: 10px; margin-top: 0.45rem; white-space: nowrap; }
    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }
    .formula-bar { background: #0b0f16; border: 1px solid #18202d; border-radius: 12px; padding: 0.75rem 0.95rem; margin-bottom: 1rem; }
    .formula-text { font-family: 'DM Mono', monospace; font-size: 10px; color: #a3aab8; letter-spacing: 0.02em; }
    .section-header { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: #6b7280; border-bottom: 1px solid #161c27; padding-bottom: 0.45rem; margin-bottom: 1rem; margin-top: 1.6rem; }
    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid #161c27; gap: 0; }
    .stTabs [data-baseweb="tab"] { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: #667085; padding: 0.7rem 1.25rem; border-radius: 0; border-bottom: 2px solid transparent; background: transparent; }
    .stTabs [aria-selected="true"] { color: #d7f34a !important; border-bottom: 2px solid #d7f34a !important; background: transparent !important; }
    .stExpander { border: 1px solid #1b2230 !important; border-radius: 12px !important; background: #0b0f16 !important; }
</style>
""", unsafe_allow_html=True)

MONTH_MAP   = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
MONTH_NAMES = [MONTH_MAP[i] for i in range(1,13)]
EXCL        = ["Unassigned","(blank)"]

THEME_OPTIONS = ["Executive / minimal","Finance / Bloomberg-ish","MarketCast-accented","Monochrome blue","Grey + accent"]

def get_theme_palette(theme_name):
    themes = {
        "Executive / minimal":   {"series":["#7aa2f7","#5b7cbe","#4b5563","#94a3b8","#64748b"],"blue_scale":["#1e3a5f","#2f5f9e","#7aa2f7"],"donut":["#93c5fd","#60a5fa","#3b82f6"],"waterfall_total":"#d4af37","waterfall_pos":"#4ade80","waterfall_neg":"#f87171","current":"#7aa2f7","prior":"#475569","accent_scale":["#122033","#60a5fa"]},
        "Finance / Bloomberg-ish":{"series":["#4c78a8","#2f4b7c","#6b7280","#9ca3af","#1f5a91"],"blue_scale":["#0f2d4a","#1f5a91","#5fa8ff"],"donut":["#0f4c81","#2563eb","#60a5fa"],"waterfall_total":"#93c5fd","waterfall_pos":"#4ade80","waterfall_neg":"#ef4444","current":"#60a5fa","prior":"#6b7280","accent_scale":["#0f2d4a","#5fa8ff"]},
        "MarketCast-accented":   {"series":["#d7f34a","#4ade80","#60a5fa","#a78bfa","#fb923c"],"blue_scale":["#1e3a5f","#3b82f6","#d7f34a"],"donut":["#d7f34a","#60a5fa","#a78bfa"],"waterfall_total":"#d7f34a","waterfall_pos":"#4ade80","waterfall_neg":"#f87171","current":"#d7f34a","prior":"#475569","accent_scale":["#141a0d","#d7f34a"]},
        "Monochrome blue":       {"series":["#93c5fd","#60a5fa","#3b82f6","#2563eb","#1d4ed8"],"blue_scale":["#17324d","#2b6ea5","#93c5fd"],"donut":["#93c5fd","#60a5fa","#2563eb"],"waterfall_total":"#60a5fa","waterfall_pos":"#4ade80","waterfall_neg":"#f87171","current":"#60a5fa","prior":"#475569","accent_scale":["#122033","#60a5fa"]},
        "Grey + accent":         {"series":["#94a3b8","#64748b","#475569","#d7f34a","#334155"],"blue_scale":["#334155","#64748b","#d7f34a"],"donut":["#475569","#64748b","#d7f34a"],"waterfall_total":"#d7f34a","waterfall_pos":"#4ade80","waterfall_neg":"#f87171","current":"#94a3b8","prior":"#475569","accent_scale":["#334155","#d7f34a"]},
    }
    return themes[theme_name]

PT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    xaxis=dict(gridcolor="#141924", linecolor="#1b2230", tickcolor="#1b2230", tickfont=dict(color="#cbd5e1"), title_font=dict(color="#cbd5e1")),
    yaxis=dict(gridcolor="#141924", linecolor="#1b2230", tickcolor="#1b2230", tickfont=dict(color="#cbd5e1"), title_font=dict(color="#cbd5e1")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=10)),
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
    elif kind == "rate":
        val_str = f"${value:,.2f}"
        d_str = f"${abs(delta):,.2f}" if delta is not None else ""
    else:
        val_str = fmt_m(value)
        d_str = fmt_m(abs(delta)) if delta is not None else ""

    delta_html = ""
    if delta is not None:
        cls  = "delta-pos" if delta >= 0 else "delta-neg"
        sign = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="metric-delta {cls}">{sign} {d_str} {delta_label}</div>'

    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{val_str}</div>{delta_html}</div>'

@st.cache_data
def load_data():
    # Gross margin
    df_gm = get_gross_margin(year_from=2022).copy()
    df_gm["accounting_period_start_date"] = pd.to_datetime(df_gm["accounting_period_start_date"])
    df_gm["yr"] = df_gm["accounting_period_start_date"].dt.year
    df_gm["month_num"] = df_gm["accounting_period_start_date"].dt.month
    for col in ["revenue", "cogs", "labour", "be_allocation", "ae_allocation", "rta_allocation", "gross_margin"]:
        df_gm[col] = df_gm[col].fillna(0)
    df_gm["contribution"] = df_gm["gross_margin"] - df_gm["labour"]
    df_gm["fixed_cost"] = df_gm["be_allocation"] + df_gm["ae_allocation"] + df_gm["rta_allocation"]
    for col in ["service_line_name", "sub_service_line_name", "vertical_name", "top_level_parent_customer_name"]:
        df_gm[col] = df_gm[col].fillna("(blank)")

    # Labour attributed by client and service line
    df_lab = get_labour_by_client(year_from=2022).copy()
    df_lab["accounting_period_start_date"] = pd.to_datetime(df_lab["accounting_period_start_date"])
    df_lab["yr"] = df_lab["accounting_period_start_date"].dt.year
    df_lab["month_num"] = df_lab["accounting_period_start_date"].dt.month
    for col in ["service_line_name", "sub_service_line_name", "vertical_name", "top_level_parent_customer_name"]:
        df_lab[col] = df_lab[col].fillna("(blank)")

    # Pipeline
    df_pipe = get_pipeline().copy()
    df_pipe["pipeline_value_usd"] = df_pipe["pipeline_value_usd"].fillna(0)
    for col in ["service_line", "vertical"]:
        if col in df_pipe.columns:
            df_pipe[col] = df_pipe[col].fillna("(blank)")

    # Targets
    df_tgt = get_targets().copy()
    df_tgt["quarter_start_date"] = pd.to_datetime(df_tgt["quarter_start_date"])
    df_tgt["yr"] = df_tgt["quarter_start_date"].dt.year

    return df_gm, df_lab, df_pipe, df_tgt

df_gm, df_lab, df_pipe, df_tgt = load_data()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="sb-brand"><img src="data:image/png;base64,{logo_base64}" class="sb-logo"/><div><div class="sb-brand-name">MarketCast</div><div class="sb-brand-sub">Finance Dashboard</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section"><div class="sb-section-title">Time Period</div>', unsafe_allow_html=True)
    years = sorted(df_gm["yr"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("Year", years, index=years.index(2025) if 2025 in years else 0)
    basis = st.radio("View", ["Full Year", "YTD / Range"], horizontal=True)
    if basis == "YTD / Range":
        avail = sorted(df_gm[df_gm["yr"] == selected_year]["month_num"].dropna().unique().tolist())
        max_m = max(avail) if avail else 12
        month_range = st.select_slider("Month Range", options=MONTH_NAMES, value=("Jan", MONTH_MAP[max_m]))
        m_from = MONTH_NAMES.index(month_range[0]) + 1
        m_to = MONTH_NAMES.index(month_range[1]) + 1
        period_label = f"{month_range[0]}–{month_range[1]} {selected_year}"
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
        f'<div class="sb-active-view"><div class="sb-view-label">Active View</div><div class="sb-view-value">{period_label}</div><div class="sb-view-sub">{" · ".join(filters_active) if filters_active else "No additional filters"}</div></div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="sb-bottom-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-section"><div class="sb-section-title">Visual Style</div>', unsafe_allow_html=True)
    selected_theme = st.radio("Visual Style", THEME_OPTIONS, index=1)
    st.markdown('</div>', unsafe_allow_html=True)

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

# ── Filter ────────────────────────────────────────────────────
def filt(data, year, m1=1, m2=12):
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

df_curr = filt(df_gm, selected_year, m_from, m_to)
df_prior = filt(df_gm, selected_year - 1, m_from, m_to)
df_lab_curr = filt(df_lab, selected_year, m_from, m_to)
df_lab_prior = filt(df_lab, selected_year - 1, m_from, m_to)

# ── Aggregates ────────────────────────────────────────────────
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
fixed_cost_pct = safe_pct(fixed_cost, rev)
fixed_cost_pct_py = safe_pct(fixed_cost_py, rev_py)
labor_pct = safe_pct(labor, rev)
labor_pct_py = safe_pct(labor_py, rev_py)

# ── Header ────────────────────────────────────────────────────
st.markdown(f"### Finance Dashboard — {period_label}")
st.markdown('<div class="formula-bar"><div class="formula-text">Gross Margin = Revenue – COGS – Fixed Cost &nbsp;&nbsp;|&nbsp;&nbsp; Contribution = Gross Margin – Labor</div></div>', unsafe_allow_html=True)

r1 = st.columns(8)
r1[0].markdown(kpi("Revenue", rev, rev - rev_py, "vs PY"), unsafe_allow_html=True)
r1[1].markdown(kpi("Clients", num_clients, num_clients - clients_py, "vs PY", kind="count"), unsafe_allow_html=True)
r1[2].markdown(kpi("COGS", cogs), unsafe_allow_html=True)
r1[3].markdown(kpi("Fixed Cost", fixed_cost), unsafe_allow_html=True)
r1[4].markdown(kpi("Labor", labor, labor - labor_py, "vs PY"), unsafe_allow_html=True)
r1[5].markdown(kpi("Gross Margin", gm, gm - gm_py, "vs PY"), unsafe_allow_html=True)
r1[6].markdown(kpi("Gross Margin %", gm_pct, gm_pct - gm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r1[7].markdown(kpi("Contribution", contrib, contrib - contrib_py, "vs PY"), unsafe_allow_html=True)

r2 = st.columns(8)
r2[0].markdown(kpi("Contribution %", cm_pct, cm_pct - cm_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[1].markdown(kpi("Fixed Cost % Revenue", fixed_cost_pct, fixed_cost_pct - fixed_cost_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)
r2[2].markdown(kpi("Labor % Revenue", labor_pct, labor_pct - labor_pct_py, "vs PY", kind="pct"), unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Revenue & Margin", "Clients & Products", "Labor", "Pipeline", "Targets"
])

# ── Tab 1: Revenue & Margin ───────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">Performance Overview</div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca:
        rm = df_curr.groupby(["accounting_period_start_date", "service_line_name"])["revenue"].sum().reset_index()
        f = px.bar(
            rm, x="accounting_period_start_date", y="revenue", color="service_line_name",
            color_discrete_sequence=SERIES_COLORS, title="Monthly Revenue Trend",
            labels={"revenue":"Revenue","accounting_period_start_date":"Month","service_line_name":""}
        )
        f.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        f.update_traces(marker_line_width=0)
        st.plotly_chart(f, use_container_width=True)
    with cb:
        gs = df_curr.groupby("service_line_name").agg(revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index()
        gs["gm_pct"] = (gs["gm"] / gs["revenue"].replace(0, float("nan")) * 100).round(1)
        gs = gs.sort_values("gm_pct", ascending=True)
        f2 = px.bar(
            gs, x="gm_pct", y="service_line_name", orientation="h", color="gm_pct",
            color_continuous_scale=BLUE_SCALE, title="Gross Margin % by Service Line",
            labels={"gm_pct":"Gross Margin %","service_line_name":""}
        )
        f2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(f2, use_container_width=True)

    cc, cd = st.columns(2)
    with cc:
        cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Current"})
        py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Prior Year"})
        yoy = pd.DataFrame({"month_num": list(range(m_from, m_to + 1))}).merge(cy, on="month_num", how="left").merge(py, on="month_num", how="left").fillna(0)
        yoy["ml"] = yoy["month_num"].map(MONTH_MAP)
        ym = yoy.melt(id_vars=["month_num","ml"], value_vars=["Current","Prior Year"], var_name="Period", value_name="Revenue")
        f3 = px.line(
            ym, x="ml", y="Revenue", color="Period", markers=True,
            color_discrete_map={"Current":LINE_CURRENT,"Prior Year":LINE_PRIOR},
            title="Revenue vs Prior Year", labels={"ml":"Month"}
        )
        f3.update_layout(**PT, title_font_color="#cbd5e1")
        f3.update_traces(line_width=2.5)
        st.plotly_chart(f3, use_container_width=True)
    with cd:
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","relative","total","relative","total"],
            x=["Revenue","COGS","Fixed Cost","Gross Margin","Labor","Contribution"],
            y=[rev,-cogs,-fixed_cost,None,-labor,None],
            connector={"line":{"color":"#243041"}},
            increasing={"marker":{"color":WF_POS}},
            decreasing={"marker":{"color":WF_NEG}},
            totals={"marker":{"color":WF_TOTAL}},
            text=[fmt_m(rev),fmt_m(cogs),fmt_m(fixed_cost),fmt_m(gm),fmt_m(labor),fmt_m(contrib)],
            textposition="outside"
        ))
        wf.update_layout(**PT, title="Revenue to Contribution Bridge", title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(wf, use_container_width=True)

    ce, cf = st.columns(2)
    with ce:
        asp = pd.DataFrame({
            "Allocation Type":["Brand Effect","AE Synd","RTA"],
            "Amount":[df_curr["be_allocation"].sum(), df_curr["ae_allocation"].sum(), df_curr["rta_allocation"].sum()]
        })
        asp = asp[asp["Amount"] > 0]
        fa = px.pie(
            asp, names="Allocation Type", values="Amount", hole=0.68, title="Fixed Cost Split",
            color="Allocation Type",
            color_discrete_map={"Brand Effect":DONUT_COLORS[0], "AE Synd":DONUT_COLORS[1], "RTA":DONUT_COLORS[2]}
        )
        fa.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fa.add_annotation(text=fmt_m(fixed_cost), x=0.5, y=0.5, showarrow=False, font=dict(size=18,color="#f8fafc",family="DM Sans"))
        st.plotly_chart(fa, use_container_width=True)
    with cf:
        gt = df_curr.groupby("accounting_period_start_date").agg(revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index().sort_values("accounting_period_start_date")
        gt["gm_pct"] = (gt["gm"] / gt["revenue"].replace(0, float("nan")) * 100).round(1)
        fg = px.area(
            gt, x="accounting_period_start_date", y="gm_pct", title="Monthly Gross Margin % Trend",
            labels={"accounting_period_start_date":"Month","gm_pct":"Gross Margin %"},
            color_discrete_sequence=[LINE_CURRENT]
        )
        fg.update_traces(line_width=2)
        fg.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-45)
        st.plotly_chart(fg, use_container_width=True)

    st.markdown('<div class="section-header">Margin Detail — with Attributed Labour</div>', unsafe_allow_html=True)

    lab_sl = df_lab_curr.groupby(["service_line_name","sub_service_line_name"])["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour_attributed"})
    ps = (
        df_curr.groupby(["service_line_name","sub_service_line_name"], dropna=False)
        .agg(
            revenue=("revenue","sum"),
            cogs=("cogs","sum"),
            fixed_cost=("fixed_cost","sum"),
            gross_margin=("gross_margin","sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
        )
        .reset_index()
    )
    ps = ps.merge(lab_sl, on=["service_line_name","sub_service_line_name"], how="left")
    ps["labour_attributed"] = ps["labour_attributed"].fillna(0)
    ps["contribution"] = ps["gross_margin"] - ps["labour_attributed"]
    ps["gm_pct"] = (ps["gross_margin"] / ps["revenue"].replace(0, float("nan")) * 100).round(1)
    ps["cm_pct"] = (ps["contribution"] / ps["revenue"].replace(0, float("nan")) * 100).round(1)
    for col in ["revenue","cogs","fixed_cost","gross_margin","labour_attributed","contribution"]:
        ps[col] = (ps[col] / 1000).round(0)
    ps = ps.sort_values(["service_line_name","sub_service_line_name"], ascending=[True,True])
    ps.columns = [c.replace("_"," ").title() for c in ps.columns]
    st.dataframe(ps, use_container_width=True, hide_index=True, column_config={
        "Revenue":st.column_config.NumberColumn("Revenue ($k)",format="$%.0f"),
        "Cogs":st.column_config.NumberColumn("COGS ($k)",format="$%.0f"),
        "Fixed Cost":st.column_config.NumberColumn("Fixed Cost ($k)",format="$%.0f"),
        "Gross Margin":st.column_config.NumberColumn("GM ($k)",format="$%.0f"),
        "Labour Attributed":st.column_config.NumberColumn("Labor ($k)",format="$%.0f"),
        "Contribution":st.column_config.NumberColumn("Contribution ($k)",format="$%.0f"),
        "Gm Pct":st.column_config.NumberColumn("GM %",format="%.1f%%"),
        "Cm Pct":st.column_config.NumberColumn("CM %",format="%.1f%%"),
        "Clients":st.column_config.NumberColumn("Clients",format="%d"),
    })

# ── Tab 2: Clients & Products ─────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">Client & Product Performance</div>', unsafe_allow_html=True)
    st.markdown("<div style='font-family:DM Mono,monospace;font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:#6b7280;margin-bottom:0.35rem;'>Client Value Metric</div>", unsafe_allow_html=True)
    use_contribution = st.toggle("Use Contribution", value=False, key="client_metric_toggle")
    mc = "contribution" if use_contribution else "gross_margin"
    pc = "cm_pct" if use_contribution else "gm_pct"
    mt = "Contribution" if use_contribution else "Gross Margin"
    pt2 = "Contribution %" if use_contribution else "Gross Margin %"

    lab_cl = df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour_attributed"})
    ca2 = (
        df_curr[~df_curr["top_level_parent_customer_name"].isin(EXCL)]
        .groupby("top_level_parent_customer_name")
        .agg(revenue=("revenue","sum"), cogs=("cogs","sum"), fixed_cost=("fixed_cost","sum"), gross_margin=("gross_margin","sum"))
        .reset_index()
    )
    ca2 = ca2.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    ca2["labour_attributed"] = ca2["labour_attributed"].fillna(0)
    ca2["contribution"] = ca2["gross_margin"] - ca2["labour_attributed"]
    ca2["gm_pct"] = (ca2["gross_margin"] / ca2["revenue"].replace(0, float("nan")) * 100).round(1)
    ca2["cm_pct"] = (ca2["contribution"] / ca2["revenue"].replace(0, float("nan")) * 100).round(1)

    cg, ch = st.columns(2)
    with cg:
        tc = ca2.sort_values(mc, ascending=True).tail(15)
        f4 = px.bar(
            tc, x=mc, y="top_level_parent_customer_name", orientation="h", color="revenue",
            color_continuous_scale=ACCENT_SCALE, title=f"Top 15 Clients by {mt}",
            labels={mc:mt,"top_level_parent_customer_name":"","revenue":"Revenue"}
        )
        f4.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(f4, use_container_width=True)
    with ch:
        cs = ca2.sort_values("revenue", ascending=False).head(20)
        f5 = px.scatter(
            cs, x="revenue", y=pc, size=mc, text="top_level_parent_customer_name",
            title=f"Client Portfolio — Revenue vs {pt2}", size_max=36,
            labels={"revenue":"Revenue", pc:pt2, mc:mt, "top_level_parent_customer_name":""}
        )
        f5.update_traces(marker=dict(color=LINE_CURRENT, sizemode="area", opacity=0.9), textposition="top center", textfont=dict(size=9,color="#cbd5e1"))
        f5.update_layout(**PT, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(f5, use_container_width=True)

    st.markdown('<div class="section-header">Expandable Product Hierarchy</div>', unsafe_allow_html=True)

    lab_sl2 = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index().rename(columns={"labour_cost":"labour_attributed"})
    slsum = (
        df_curr.groupby("service_line_name", dropna=False)
        .agg(
            revenue=("revenue","sum"),
            cogs=("cogs","sum"),
            fixed_cost=("fixed_cost","sum"),
            gross_margin=("gross_margin","sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
        )
        .reset_index()
    )
    slsum = slsum.merge(lab_sl2, on="service_line_name", how="left")
    slsum["labour_attributed"] = slsum["labour_attributed"].fillna(0)
    slsum["contribution"] = slsum["gross_margin"] - slsum["labour_attributed"]
    slsum["gm_pct"] = (slsum["gross_margin"] / slsum["revenue"].replace(0, float("nan")) * 100).round(1)
    slsum["cm_pct"] = (slsum["contribution"] / slsum["revenue"].replace(0, float("nan")) * 100).round(1)
    slsum = slsum.sort_values("revenue", ascending=False)

    for _, row in slsum.iterrows():
        sl_name = row["service_line_name"]
        with st.expander(f"{sl_name}  |  Revenue: {fmt_m(row['revenue'])}  |  GM%: {row['gm_pct']:.1f}%  |  CM%: {row['cm_pct']:.1f}%"):
            st.dataframe(
                pd.DataFrame({
                    "Metric":["Revenue","COGS","Fixed Cost","GM","Labor","Contribution","GM%","CM%","Clients"],
                    "Value":[
                        fmt_m(row["revenue"]),
                        fmt_m(row["cogs"]),
                        fmt_m(row["fixed_cost"]),
                        fmt_m(row["gross_margin"]),
                        fmt_m(row["labour_attributed"]),
                        fmt_m(row["contribution"]),
                        f"{row['gm_pct']:.1f}%",
                        f"{row['cm_pct']:.1f}%",
                        fmt_int(row["clients"])
                    ]
                }),
                use_container_width=True,
                hide_index=True
            )

            sub_gm = (
                df_curr[df_curr["service_line_name"] == sl_name]
                .groupby("sub_service_line_name", dropna=False)
                .agg(
                    revenue=("revenue","sum"),
                    cogs=("cogs","sum"),
                    fixed_cost=("fixed_cost","sum"),
                    gross_margin=("gross_margin","sum"),
                    clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique())
                )
                .reset_index()
            )
            sub_lab = (
                df_lab_curr[df_lab_curr["service_line_name"] == sl_name]
                .groupby("sub_service_line_name")["labour_cost"].sum().reset_index()
                .rename(columns={"labour_cost":"labour_attributed"})
            )
            sub_gm = sub_gm.merge(sub_lab, on="sub_service_line_name", how="left")
            sub_gm["labour_attributed"] = sub_gm["labour_attributed"].fillna(0)
            sub_gm["contribution"] = sub_gm["gross_margin"] - sub_gm["labour_attributed"]
            sub_gm["gm_pct"] = (sub_gm["gross_margin"] / sub_gm["revenue"].replace(0, float("nan")) * 100).round(1)
            sub_gm["cm_pct"] = (sub_gm["contribution"] / sub_gm["revenue"].replace(0, float("nan")) * 100).round(1)
            sub_gm = sub_gm.sort_values("revenue", ascending=False)
            disp = sub_gm.copy()
            for col in ["revenue","cogs","fixed_cost","gross_margin","labour_attributed","contribution"]:
                disp[col] = (disp[col] / 1000).round(0)
            disp.columns = [c.replace("_"," ").title() for c in disp.columns]
            st.dataframe(disp, use_container_width=True, hide_index=True, column_config={
                "Revenue":st.column_config.NumberColumn("Revenue ($k)",format="$%.0f"),
                "Cogs":st.column_config.NumberColumn("COGS ($k)",format="$%.0f"),
                "Fixed Cost":st.column_config.NumberColumn("Fixed Cost ($k)",format="$%.0f"),
                "Gross Margin":st.column_config.NumberColumn("GM ($k)",format="$%.0f"),
                "Labour Attributed":st.column_config.NumberColumn("Labor ($k)",format="$%.0f"),
                "Contribution":st.column_config.NumberColumn("Contribution ($k)",format="$%.0f"),
                "Gm Pct":st.column_config.NumberColumn("GM %",format="%.1f%%"),
                "Cm Pct":st.column_config.NumberColumn("CM %",format="%.1f%%"),
                "Clients":st.column_config.NumberColumn("Clients",format="%d"),
            })

# ── Tab 3: Labour Analysis ────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Labour Overview</div>', unsafe_allow_html=True)
    tlab = df_lab_curr["labour_cost"].sum()
    tlab_py = df_lab_prior["labour_cost"].sum()
    thrs = df_lab_curr["total_hours"].sum()

    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.markdown(kpi("Total Labour", tlab, tlab - tlab_py, "vs PY"), unsafe_allow_html=True)
    lc2.markdown(kpi("Labour % Revenue", safe_pct(tlab, rev), kind="pct"), unsafe_allow_html=True)
    lc3.markdown(kpi("Total Hours", thrs, kind="count"), unsafe_allow_html=True)
    lc4.markdown(kpi("Avg Cost/hr", tlab / thrs if thrs > 0 else 0, kind="rate"), unsafe_allow_html=True)

    cla, clb = st.columns(2)
    with cla:
        lm = df_lab_curr.groupby(["accounting_period_start_date","service_line_name"])["labour_cost"].sum().reset_index()
        flm = px.bar(
            lm, x="accounting_period_start_date", y="labour_cost", color="service_line_name",
            color_discrete_sequence=SERIES_COLORS, title="Labour by Service Line — Monthly",
            labels={"labour_cost":"Labour Cost","accounting_period_start_date":"Month","service_line_name":""}
        )
        flm.update_traces(marker_line_width=0)
        flm.update_layout(**PT, xaxis_tickangle=-45, title_font_color="#cbd5e1")
        st.plotly_chart(flm, use_container_width=True)
    with clb:
        lbc = (
            df_lab_curr[~df_lab_curr["top_level_parent_customer_name"].isin(EXCL)]
            .groupby("top_level_parent_customer_name")["labour_cost"].sum().reset_index()
            .sort_values("labour_cost", ascending=True).tail(15)
        )
        flc = px.bar(
            lbc, x="labour_cost", y="top_level_parent_customer_name", orientation="h",
            color="labour_cost", color_continuous_scale=BLUE_SCALE,
            title="Top 15 Clients by Labour Cost",
            labels={"labour_cost":"Labour Cost","top_level_parent_customer_name":""}
        )
        flc.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(flc, use_container_width=True)

    clc, cld = st.columns(2)
    with clc:
        lrv = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index()
        rvsl = df_curr.groupby("service_line_name")["revenue"].sum().reset_index()
        lrv = lrv.merge(rvsl, on="service_line_name", how="left")
        lrv["labour_pct"] = (lrv["labour_cost"] / lrv["revenue"].replace(0, float("nan")) * 100).round(1)
        lrv = lrv[lrv["revenue"] > 0].sort_values("labour_pct", ascending=True)
        flr = px.bar(
            lrv, x="labour_pct", y="service_line_name", orientation="h",
            color="labour_pct", color_continuous_scale=BLUE_SCALE,
            title="Labour % of Revenue by Service Line",
            labels={"labour_pct":"Labour %","service_line_name":""}
        )
        flr.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(flr, use_container_width=True)
    with cld:
        lyc = df_lab_curr.groupby("service_line_name")["labour_cost"].sum().reset_index().assign(period=str(selected_year))
        lyp = df_lab_prior.groupby("service_line_name")["labour_cost"].sum().reset_index().assign(period=str(selected_year - 1))
        lyoy = pd.concat([lyc, lyp])
        fly = px.bar(
            lyoy, x="service_line_name", y="labour_cost", color="period", barmode="group",
            color_discrete_sequence=[LINE_CURRENT, LINE_PRIOR], title="Labour YoY by Service Line",
            labels={"labour_cost":"Labour Cost","service_line_name":"","period":"Year"}
        )
        fly.update_traces(marker_line_width=0)
        fly.update_layout(**PT, xaxis_tickangle=-30, title_font_color="#cbd5e1")
        st.plotly_chart(fly, use_container_width=True)

    st.markdown('<div class="section-header">Labour Detail — Client × Service Line</div>', unsafe_allow_html=True)
    ld = (
        df_lab_curr[~df_lab_curr["top_level_parent_customer_name"].isin(EXCL)]
        .groupby(["top_level_parent_customer_name","service_line_name","sub_service_line_name"])
        .agg(labour_cost=("labour_cost","sum"), total_hours=("total_hours","sum"))
        .reset_index()
        .sort_values("labour_cost", ascending=False)
    )

    ld["cost_per_hour"] = (ld["labour_cost"] / ld["total_hours"].replace(0, float("nan"))).round(2)
    ld["labour_cost"] = (ld["labour_cost"] / 1000).round(0)

    ld.columns = [c.replace("_"," ").title() for c in ld.columns]
    st.dataframe(ld, use_container_width=True, hide_index=True, column_config={
        "Labour Cost":   st.column_config.NumberColumn("Labour ($k)", format="$%.0f"),
        "Total Hours":   st.column_config.NumberColumn("Hours", format="%.0f"),
        "Cost Per Hour": st.column_config.NumberColumn("$/hr", format="$%.2f"),
    })

# ── Tab 4: Pipeline ───────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)
    dp = df_pipe.drop_duplicates("deal_id")
    if "service_line" in dp.columns:
        dp = dp[~dp["service_line"].isin(EXCL)]
    tp = dp["pipeline_value_usd"].sum()
    td = dp["deal_id"].nunique()
    ad = tp / td if td > 0 else 0
    pc2 = st.columns(3)
    pc2[0].markdown(kpi("Total Pipeline", tp), unsafe_allow_html=True)
    pc2[1].markdown(kpi("Active Deals", td, kind="count"), unsafe_allow_html=True)
    pc2[2].markdown(kpi("Average Deal Size", ad), unsafe_allow_html=True)

    ci, cj = st.columns(2)
    with ci:
        ps2 = dp.groupby("deal_pipeline_stage_name").agg(deals=("deal_id","nunique"), value=("pipeline_value_usd","sum")).reset_index().sort_values("value", ascending=True)
        f8 = px.bar(
            ps2, x="value", y="deal_pipeline_stage_name", orientation="h", color="value",
            color_continuous_scale=BLUE_SCALE, title="Pipeline by Stage",
            labels={"value":"Pipeline Value","deal_pipeline_stage_name":""}
        )
        f8.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(f8, use_container_width=True)
    with cj:
        psl = dp.groupby("service_line").agg(deals=("deal_id","nunique"), value=("pipeline_value_usd","sum")).reset_index().sort_values("value", ascending=False)
        f9 = px.bar(
            psl, x="service_line", y="value", color="value", color_continuous_scale=BLUE_SCALE,
            title="Pipeline by Service Line", labels={"value":"Pipeline Value","service_line":""}
        )
        f9.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(f9, use_container_width=True)

    st.markdown('<div class="section-header">Pipeline Detail</div>', unsafe_allow_html=True)
    ptbl = dp.groupby(["deal_pipeline_stage_name","service_line","vertical"]).agg(deals=("deal_id","nunique"), value=("pipeline_value_usd","sum")).reset_index().sort_values("value", ascending=False)
    ptbl["value"] = (ptbl["value"] / 1000).round(0)
    ptbl.columns = [c.replace("_"," ").title() for c in ptbl.columns]
    st.dataframe(ptbl, use_container_width=True, hide_index=True, column_config={"Value":st.column_config.NumberColumn("Value ($k)", format="$%.0f")})

# ── Tab 5: Targets ────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">Targets Overview</div>', unsafe_allow_html=True)
    dty = df_tgt[df_tgt["yr"] == selected_year].copy()
    tt = dty["target_usd"].sum() if not dty.empty else 0
    vt = rev - tt
    pt3 = safe_pct(rev, tt) if tt not in (0, None) else 0

    tr = st.columns(4)
    tr[0].markdown(kpi(f"{selected_year} Target", tt), unsafe_allow_html=True)
    tr[1].markdown(kpi("Actual Revenue", rev, vt, "vs Target"), unsafe_allow_html=True)
    tr[2].markdown(kpi("Revenue vs Target", pt3, kind="pct"), unsafe_allow_html=True)
    tr[3].markdown(kpi("Teams", dty["team_primary_name"].nunique() if not dty.empty else 0, kind="count"), unsafe_allow_html=True)

    ck, cl = st.columns(2)
    with ck:
        if not dty.empty:
            qt = (
                dty.assign(ql="Q" + dty["quarter_start_date"].dt.quarter.astype(str))
                .groupby(["ql","quarter_start_date"], as_index=False)["target_usd"].sum()
                .sort_values("quarter_start_date")
            )
            f10 = px.bar(
                qt, x="ql", y="target_usd", color="target_usd", color_continuous_scale=BLUE_SCALE,
                title="Quarterly Targets", labels={"target_usd":"Target","ql":"Quarter"},
                category_orders={"ql":qt["ql"].tolist()}
            )
            f10.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
            st.plotly_chart(f10, use_container_width=True)
        else:
            st.info(f"No target data for {selected_year}.")
    with cl:
        if not dty.empty:
            ta = dty.groupby("team_primary_name")["target_usd"].sum().reset_index().sort_values("target_usd", ascending=True)
            f11 = px.bar(
                ta, x="target_usd", y="team_primary_name", orientation="h", color="target_usd",
                color_continuous_scale=BLUE_SCALE, title="Annual Target by Team",
                labels={"target_usd":"Annual Target","team_primary_name":""}
            )
            f11.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            st.plotly_chart(f11, use_container_width=True)

    st.markdown('<div class="section-header">Target Detail</div>', unsafe_allow_html=True)
    if not dty.empty:
        ttbl = dty.copy()
        ttbl["target_usd"] = (ttbl["target_usd"] / 1000).round(0)
        ttbl.columns = [c.replace("_"," ").title() for c in ttbl.columns]
        st.dataframe(
            ttbl,
            use_container_width=True,
            hide_index=True,
            column_config={"Target Usd":st.column_config.NumberColumn("Target ($k)", format="$%.0f")}
        )
    else:
        st.info(f"No targets for {selected_year}.")