"""
Fixed Cost tab — unified layout:
  Allocation methodology card
  Service Line  : distribution (Tile only — tile makes sense here) → inline trend (Raw/Index)
  Allocation split donut + FC% area trend (side-by-side, contextual)
  Client        : bar → client selector → inline trend
  Detail        : table + CSV download
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.constants import METRIC_COLOR
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m
from src.utils.theme import plotly_layout
from src.utils.view_helpers import dist_chart, inline_trend, client_tile_chart


_ACCENT = "#60a5fa"


def _narrative(ctx):
    fixed_cost = ctx["fixed_cost"]
    rev        = ctx["rev"]
    fc_py      = ctx.get("fixed_cost_py", 0)
    period     = ctx["period_label"]
    fc_pct     = (fixed_cost / rev * 100) if rev else 0
    dir_       = "up" if fixed_cost >= fc_py else "down"
    return (
        f"<b>{period}:</b> Fixed costs of <b>{fmt_m(fixed_cost)}</b> represent "
        f"<b>{fc_pct:.1f}%</b> of revenue, "
        f"{dir_} <b>{fmt_m(abs(fixed_cost - fc_py))}</b> vs prior year."
    )


def render_fixed_cost(ctx):
    palette    = ctx["palette"]
    PT         = ctx["PT"]
    df_curr    = ctx["df_curr"]
    df_prior   = ctx["df_prior"]
    df_curr_decomp = ctx["df_curr_decomp"]
    fixed_cost = ctx["fixed_cost"]

    DC = palette["donut"]

    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid {_ACCENT};'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'{_narrative(ctx)}</div></div>',
        unsafe_allow_html=True,
    )

    # Methodology card
    be_total  = df_curr["be_allocation"].sum()
    ae_total  = df_curr["ae_allocation"].sum()
    rta_total = df_curr["rta_allocation"].sum()
    st.markdown(
        f'<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #60a5fa;'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
        f'text-transform:uppercase;margin-bottom:0.4rem;">Allocation Methodology</div>'
        f'<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;line-height:1.6;">'
        f'<b style="color:#cbd5e1;">Brand Effect {fmt_m(be_total)}</b> — proportional by client BE revenue share / 12M'
        f' &nbsp;|&nbsp; <b style="color:#cbd5e1;">AE Synd {fmt_m(ae_total)}</b> — proportional by AE revenue share'
        f' &nbsp;|&nbsp; <b style="color:#cbd5e1;">RTA {fmt_m(rta_total)}</b> — proportional by RTA revenue share'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    base  = clean_for_visuals(df_curr_decomp)
    prior = clean_for_visuals(df_prior)

    chart_type = st.radio("View type", ["Bar", "Tile"], horizontal=True, key="fc_chart_type")

    # ── SERVICE LINE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Fixed Cost by Service Line</div>', unsafe_allow_html=True)

    fc_sl = (base.groupby("service_line_name")
             .agg(revenue=("revenue","sum"), fixed_cost=("fixed_cost","sum"))
             .reset_index())
    fc_sl = fc_sl[fc_sl["fixed_cost"] > 0]

    dist_chart(fc_sl, "service_line_name", "fixed_cost", _ACCENT, PT, chart_type, "fc_sl",
               value_label="Fixed Cost")
    inline_trend(ctx, base, prior, "fixed_cost", _ACCENT, PT, "fc_sl",
                 y_label="Fixed Cost ($M)")

    # ── ALLOCATION SPLIT ─────────────────────────────────────
    st.markdown('<div class="section-header">Allocation Type Split</div>', unsafe_allow_html=True)
    col_don, col_trend = st.columns(2)

    with col_don:
        asp = pd.DataFrame({
            "Type":   ["Brand Effect", "AE Synd", "RTA"],
            "Amount": [be_total, ae_total, rta_total],
        })
        asp = asp[asp["Amount"] > 0]
        fig_d = px.pie(asp, names="Type", values="Amount", hole=0.68,
                       title="BE / AE Synd / RTA",
                       color="Type",
                       color_discrete_map={"Brand Effect": DC[0], "AE Synd": DC[1], "RTA": DC[2]})
        fig_d.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fig_d.add_annotation(text=fmt_m(fixed_cost), x=0.5, y=0.5, showarrow=False,
                             font=dict(size=20, color="#f8fafc", family="DM Sans"))
        st.plotly_chart(fig_d, use_container_width=True, key="fc_alloc_donut")

    with col_trend:
        mth = (df_curr_decomp
               .groupby("accounting_period_start_date")
               .agg(revenue=("revenue","sum"), fc=("fixed_cost","sum"))
               .reset_index()
               .sort_values("accounting_period_start_date"))
        mth["fc_pct"] = (mth["fc"] / mth["revenue"].replace(0,float("nan")) * 100).round(1)
        fig_t = px.area(mth, x="accounting_period_start_date", y="fc_pct",
                        title="FC % of Revenue",
                        labels={"accounting_period_start_date": "", "fc_pct": "FC %"},
                        color_discrete_sequence=[_ACCENT])
        fig_t.update_traces(line_width=2)
        fig_t.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig_t.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_t, use_container_width=True, key="fc_pct_trend")

    # ── CLIENT ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Fixed Cost by Client</div>', unsafe_allow_html=True)

    filtered = clean_for_visuals(df_curr)
    fc_cl = (filtered.groupby("top_level_parent_customer_name")
             .agg(revenue=("revenue","sum"), fixed_cost=("fixed_cost","sum"))
             .reset_index()
             .sort_values("fixed_cost", ascending=False))
    fc_cl["pct_rev"] = (fc_cl["fixed_cost"] / fc_cl["revenue"].replace(0,float("nan")) * 100).round(1)

    client_view = st.radio("Client view", ["Top 15", "Top 30", "All"],
                           horizontal=True, key="fc_client_view")
    n_show = {"Top 15": 15, "Top 30": 30, "All": None}[client_view]

    if chart_type == "Tile":
        client_tile_chart(fc_cl, "top_level_parent_customer_name", "fixed_cost",
                          n_show, _ACCENT, "fc_client_tile", "Fixed Cost")
    else:
        cl_show = (fc_cl.head(n_show) if n_show else fc_cl).copy()
        cl_show = cl_show.sort_values("fixed_cost", ascending=True)
        cl_show["_m"] = cl_show["fixed_cost"] / 1e6
        fig_cl = go.Figure(go.Bar(
            x=cl_show["_m"],
            y=cl_show["top_level_parent_customer_name"],
            orientation="h",
            marker_color=_ACCENT,
            marker_line_width=0,
            text=cl_show.apply(lambda r: f"${r['_m']:.1f}M ({r['pct_rev']:.1f}% rev)", axis=1),
            textposition="outside",
            textfont=dict(size=10, color="#94a3b8", family="DM Sans"),
        ))
        n_bar = n_show or len(cl_show)
        fig_cl.update_layout(**plotly_layout(height=max(340, n_bar * 26),
                                             margin=dict(l=0, r=130, t=20, b=0)))
        fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_cl, use_container_width=True, key="fc_client_bar")

    # Client trend
    prior_filt = clean_for_visuals(df_prior)
    cl_opts = ["All"] + sorted(filtered["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_client = st.selectbox("Client trend", cl_opts, key="fc_cl_trend_filter")

    if sel_client == "All":
        curr_cl, prior_cl = filtered, prior_filt
    else:
        curr_cl  = filtered[filtered["top_level_parent_customer_name"] == sel_client]
        prior_cl = prior_filt[prior_filt["top_level_parent_customer_name"] == sel_client]

    inline_trend(ctx, curr_cl, prior_cl, "fixed_cost", _ACCENT, PT, "fc_cl",
                 y_label=f"Fixed Cost ($M) — {sel_client}")

    # ── DETAIL TABLE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Fixed Cost Detail</div>', unsafe_allow_html=True)

    tbl = (filtered.groupby(["service_line_name","sub_service_line_name","top_level_parent_customer_name"],
                             dropna=False)
           .agg(revenue=("revenue","sum"), fixed_cost=("fixed_cost","sum"))
           .reset_index())
    total_fc = tbl["fixed_cost"].sum()
    tbl["fc_pct_rev"] = (tbl["fixed_cost"] / tbl["revenue"].replace(0,float("nan")) * 100).round(1)
    tbl["fc_pct_tot"] = (tbl["fixed_cost"] / total_fc * 100).round(1) if total_fc else 0
    for c in ["revenue","fixed_cost"]:
        tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values(["service_line_name","fixed_cost"], ascending=[True,False])
    tbl.columns = [c.replace("_"," ").title() for c in tbl.columns]

    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":    st.column_config.NumberColumn("Revenue ($M)",    format="$%.2f"),
        "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
        "Fc Pct Rev": st.column_config.NumberColumn("FC % Rev",        format="%.1f%%"),
        "Fc Pct Tot": st.column_config.NumberColumn("FC % Total",      format="%.1f%%"),
    })
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       "fixed_cost_detail.csv", "text/csv", key="fc_dl")
