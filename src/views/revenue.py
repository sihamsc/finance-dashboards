"""
Revenue tab — unified layout:
  Service Line  : distribution (Bar/Tile) → inline trend (Raw/Index)
  Sub-SL        : SL filter → distribution → inline trend
  Client        : concentration stats → bar → client selector → inline trend
  Detail        : table + CSV download
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.charts import build_index_rows, render_index_chart
from src.utils.constants import METRIC_COLOR
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m
from src.utils.view_helpers import dist_chart, inline_trend


_ACCENT = METRIC_COLOR["revenue"]
_PRIOR  = "#475569"


def _narrative(ctx):
    rev, rev_py = ctx["rev"], ctx["rev_py"]
    period = ctx["period_label"]
    df_curr = ctx["df_curr"]

    rev_dir = "up" if rev >= rev_py else "down"
    sl_grp = (
        clean_for_visuals(ctx.get("df_curr_decomp", df_curr))
        .groupby("service_line_name")["revenue"].sum()
    )
    top_sl = sl_grp.idxmax() if not sl_grp.empty else "—"
    top_pct = (sl_grp.max() / rev * 100) if rev > 0 and not sl_grp.empty else 0

    return (
        f"<b>{period}:</b> Revenue of <b>${rev/1e6:.1f}M</b> is "
        f"{rev_dir} <b>${abs(rev-rev_py)/1e6:.1f}M</b> vs prior year. "
        f"<b>{top_sl}</b> leads at <b>{top_pct:.0f}%</b> of total."
    )


def render_revenue(ctx):
    palette = ctx["palette"]
    PT      = ctx["PT"]

    df_curr         = ctx["df_curr"]
    df_prior        = ctx["df_prior"]
    df_curr_decomp  = ctx["df_curr_decomp"]
    df_prior_decomp = ctx.get("df_prior_decomp", df_prior)

    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid {_ACCENT};'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'{_narrative(ctx)}</div></div>',
        unsafe_allow_html=True,
    )

    base   = clean_for_visuals(df_curr_decomp)
    prior  = clean_for_visuals(df_prior_decomp)

    # ── SERVICE LINE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Revenue by Service Line</div>', unsafe_allow_html=True)

    sl_data = (base.groupby("service_line_name")["revenue"].sum()
               .reset_index().rename(columns={"service_line_name": "label", "revenue": "value"}))
    sl_data.columns = ["service_line_name", "revenue"]
    sl_data = sl_data[sl_data["revenue"] > 0]

    sl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="rev_sl_chart")
    dist_chart(sl_data, "service_line_name", "revenue", _ACCENT, PT, sl_chart, "rev_sl")
    inline_trend(ctx, base, prior, "revenue", _ACCENT, PT, "rev_sl", y_label="Revenue ($M)")

    # ── SUB-SERVICE LINE ──────────────────────────────────────
    st.markdown('<div class="section-header">Revenue by Sub-Service Line</div>', unsafe_allow_html=True)

    sl_opts = sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Service Line", sl_opts, key="rev_ssl_sl_filter")

    curr_sl  = base[base["service_line_name"] == selected_sl]
    prior_sl = prior[prior["service_line_name"] == selected_sl] if not prior.empty else prior

    ssl_data = (curr_sl.groupby("sub_service_line_name")["revenue"]
                .sum().reset_index())
    ssl_data = ssl_data[ssl_data["revenue"] > 0]

    if ssl_data.empty:
        st.info(f"No sub-service line data for {selected_sl}.")
    else:
        ssl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="rev_ssl_chart")
        dist_chart(ssl_data, "sub_service_line_name", "revenue", _ACCENT, PT, ssl_chart, "rev_ssl")
        inline_trend(ctx, curr_sl, prior_sl, "revenue", _ACCENT, PT, "rev_ssl",
                     y_label=f"Revenue ($M) — {selected_sl}")

    # ── CLIENT ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Revenue by Client</div>', unsafe_allow_html=True)

    rv_cl = (clean_for_visuals(df_curr)
             .groupby("top_level_parent_customer_name")["revenue"]
             .sum().reset_index()
             .sort_values("revenue", ascending=False))

    total_rev = rv_cl["revenue"].sum()
    top5_pct  = (rv_cl.head(5)["revenue"].sum() / total_rev * 100) if total_rev else 0
    top10_pct = (rv_cl.head(10)["revenue"].sum() / total_rev * 100) if total_rev else 0

    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.5rem;">'
        f'Top 5 clients = <span style="color:#cbd5e1">{top5_pct:.0f}%</span> of revenue &nbsp;|&nbsp; '
        f'Top 10 = <span style="color:#cbd5e1">{top10_pct:.0f}%</span> &nbsp;|&nbsp; '
        f'Total clients: <span style="color:#cbd5e1">{len(rv_cl)}</span></div>',
        unsafe_allow_html=True,
    )

    client_view = st.radio("Client view", ["Top 15", "Top 30", "All > $100k"],
                           horizontal=True, key="rev_client_view")
    if client_view == "All > $100k":
        rv_show = rv_cl[rv_cl["revenue"] >= 100_000].copy()
    else:
        rv_show = rv_cl.head({"Top 15": 15, "Top 30": 30}[client_view]).copy()

    rv_show["_m"]   = rv_show["revenue"] / 1e6
    rv_show["_pct"] = (rv_show["revenue"] / total_rev * 100).round(1) if total_rev else 0
    rv_show = rv_show.sort_values("revenue", ascending=True)

    fig_cl = go.Figure(go.Bar(
        x=rv_show["_m"],
        y=rv_show["top_level_parent_customer_name"],
        orientation="h",
        marker_color=_ACCENT,
        marker_line_width=0,
        text=rv_show.apply(lambda r: f"${r['_m']:.1f}M ({r['_pct']:.1f}%)", axis=1),
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8", family="DM Sans"),
    ))
    fig_cl.update_layout(
        **PT,
        height=max(340, len(rv_show) * 26),
        margin=dict(l=0, r=110, t=20, b=0),
    )
    fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
    st.plotly_chart(fig_cl, use_container_width=True)

    # Client trend
    client_trend_base  = clean_for_visuals(df_curr_decomp)
    client_prior_base  = clean_for_visuals(df_prior_decomp)
    client_opts = ["All"] + sorted(client_trend_base["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_client = st.selectbox("Client trend", client_opts, key="rev_cl_trend_filter")

    if sel_client == "All":
        curr_cl  = client_trend_base
        prior_cl = client_prior_base
    else:
        curr_cl  = client_trend_base[client_trend_base["top_level_parent_customer_name"] == sel_client]
        prior_cl = client_prior_base[client_prior_base["top_level_parent_customer_name"] == sel_client]

    inline_trend(ctx, curr_cl, prior_cl, "revenue", _ACCENT, PT, "rev_cl",
                 y_label=f"Revenue ($M) — {sel_client}")

    # ── DETAIL TABLE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Revenue Detail</div>', unsafe_allow_html=True)

    rv_tbl = (clean_for_visuals(df_curr)
              .groupby(["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
                       dropna=False)
              .agg(revenue=("revenue", "sum"))
              .reset_index())
    total = rv_tbl["revenue"].sum()
    rv_tbl["rev_pct"] = (rv_tbl["revenue"] / total * 100).round(1) if total else 0
    rv_tbl["revenue"] = (rv_tbl["revenue"] / 1e6).round(2)
    rv_tbl = rv_tbl.sort_values(["service_line_name", "revenue"], ascending=[True, False])
    rv_tbl.columns = [c.replace("_", " ").title() for c in rv_tbl.columns]

    st.dataframe(rv_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":  st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
        "Rev Pct":  st.column_config.NumberColumn("Revenue %",    format="%.1f%%"),
    })
    st.download_button("Download CSV", rv_tbl.to_csv(index=False).encode(),
                       "revenue_detail.csv", "text/csv", key="rev_dl")
