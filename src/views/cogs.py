"""
COGS tab — unified layout:
  Service Line  : distribution (Bar/Tile) → inline trend (Raw/Index)
  Sub-SL        : SL filter → distribution → inline trend
  Client        : warning banner → bar → client selector → inline trend
  Detail        : table + CSV download
"""

import plotly.graph_objects as go
import streamlit as st

from src.utils.constants import COGS_HIGH_PCT, METRIC_COLOR
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m
from src.utils.view_helpers import dist_chart, inline_trend


_ACCENT = METRIC_COLOR["cogs"]


def _narrative(ctx):
    cogs, cogs_py = ctx["cogs"], ctx.get("cogs_py", 0)
    rev    = ctx["rev"]
    period = ctx["period_label"]
    pct    = (cogs / rev * 100) if rev else 0
    dir_   = "up" if cogs >= cogs_py else "down"
    return (
        f"<b>{period}:</b> COGS of <b>{fmt_m(cogs)}</b> represents "
        f"<b>{pct:.1f}%</b> of revenue, "
        f"{dir_} <b>{fmt_m(abs(cogs - cogs_py))}</b> vs prior year."
    )


def render_cogs(ctx):
    PT = ctx["PT"]

    df_curr         = ctx["df_curr"]
    df_prior        = ctx["df_prior"]
    df_curr_decomp  = ctx["df_curr_decomp"]
    df_prior_decomp = df_prior

    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid {_ACCENT};'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'{_narrative(ctx)}</div></div>',
        unsafe_allow_html=True,
    )

    base  = clean_for_visuals(df_curr_decomp)
    prior = clean_for_visuals(df_prior_decomp)

    # ── SERVICE LINE ──────────────────────────────────────────
    st.markdown('<div class="section-header">COGS by Service Line</div>', unsafe_allow_html=True)

    cogs_sl = (base.groupby("service_line_name")
               .agg(revenue=("revenue","sum"), cogs=("cogs","sum"))
               .reset_index())
    cogs_sl = cogs_sl[cogs_sl["cogs"] > 0]

    sl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="cogs_sl_chart")
    dist_chart(cogs_sl, "service_line_name", "cogs", _ACCENT, PT, sl_chart, "cogs_sl")
    inline_trend(ctx, base, prior, "cogs", _ACCENT, PT, "cogs_sl", y_label="COGS ($M)")

    # ── SUB-SERVICE LINE ──────────────────────────────────────
    st.markdown('<div class="section-header">COGS by Sub-Service Line</div>', unsafe_allow_html=True)

    sl_opts = sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Service Line", sl_opts, key="cogs_ssl_sl_filter")

    curr_sl  = base[base["service_line_name"] == selected_sl]
    prior_sl = prior[prior["service_line_name"] == selected_sl] if not prior.empty else prior

    cogs_ssl = (curr_sl.groupby("sub_service_line_name")
                .agg(revenue=("revenue","sum"), cogs=("cogs","sum"))
                .reset_index())
    cogs_ssl = cogs_ssl[(cogs_ssl["sub_service_line_name"] != "(blank)") & (cogs_ssl["cogs"] > 0)]

    if cogs_ssl.empty:
        st.info(f"No sub-service line data for {selected_sl}.")
    else:
        ssl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="cogs_ssl_chart")
        dist_chart(cogs_ssl, "sub_service_line_name", "cogs", _ACCENT, PT, ssl_chart, "cogs_ssl")
        inline_trend(ctx, curr_sl, prior_sl, "cogs", _ACCENT, PT, "cogs_ssl",
                     y_label=f"COGS ($M) — {selected_sl}")

    # ── CLIENT ────────────────────────────────────────────────
    st.markdown('<div class="section-header">COGS by Client</div>', unsafe_allow_html=True)

    filtered = clean_for_visuals(df_curr)
    cogs_cl = (filtered.groupby("top_level_parent_customer_name")
               .agg(revenue=("revenue","sum"), cogs=("cogs","sum"))
               .reset_index())
    cogs_cl["pct_rev"] = (cogs_cl["cogs"] / cogs_cl["revenue"].replace(0, float("nan")) * 100).round(1)
    cogs_cl = cogs_cl.sort_values("cogs", ascending=False)

    high_count = (cogs_cl["pct_rev"] > COGS_HIGH_PCT).sum()
    if high_count > 0:
        st.markdown(
            f'<div style="background:rgba(248,113,113,0.07);border:1px solid rgba(248,113,113,0.2);'
            f'border-radius:8px;padding:0.4rem 0.8rem;margin-bottom:0.6rem;'
            f'font-family:DM Mono,monospace;font-size:9px;color:#f87171;">'
            f'⚠ {high_count} client{"s" if high_count > 1 else ""} with COGS >{COGS_HIGH_PCT}% of revenue — '
            f'review cost structure or pricing</div>',
            unsafe_allow_html=True,
        )

    client_view = st.radio("Client view", ["Top 15", "Top 30", "All > $100k"],
                           horizontal=True, key="cogs_client_view")
    if client_view == "All > $100k":
        cl_show = cogs_cl[cogs_cl["cogs"] >= 100_000].copy()
    else:
        cl_show = cogs_cl.head({"Top 15": 15, "Top 30": 30}[client_view]).copy()

    cl_show["_m"]  = cl_show["cogs"] / 1e6
    cl_show = cl_show.sort_values("cogs", ascending=True)

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
    fig_cl.update_layout(**PT, height=max(340, len(cl_show) * 26),
                          margin=dict(l=0, r=130, t=20, b=0))
    fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
    st.plotly_chart(fig_cl, use_container_width=True)

    # Client trend
    prior_filt = clean_for_visuals(df_prior)
    cl_opts = ["All"] + sorted(filtered["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_client = st.selectbox("Client trend", cl_opts, key="cogs_cl_trend_filter")

    if sel_client == "All":
        curr_cl, prior_cl = filtered, prior_filt
    else:
        curr_cl  = filtered[filtered["top_level_parent_customer_name"] == sel_client]
        prior_cl = prior_filt[prior_filt["top_level_parent_customer_name"] == sel_client]

    inline_trend(ctx, curr_cl, prior_cl, "cogs", _ACCENT, PT, "cogs_cl",
                 y_label=f"COGS ($M) — {sel_client}")

    # ── DETAIL TABLE ──────────────────────────────────────────
    st.markdown('<div class="section-header">COGS Detail</div>', unsafe_allow_html=True)

    tbl = (filtered.groupby(["service_line_name","sub_service_line_name","top_level_parent_customer_name"],
                             dropna=False)
           .agg(revenue=("revenue","sum"), cogs=("cogs","sum"))
           .reset_index())
    total = tbl["cogs"].sum()
    tbl["cogs_pct_rev"]   = (tbl["cogs"] / tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    tbl["cogs_pct_total"] = (tbl["cogs"] / total * 100).round(1) if total else 0
    for c in ["revenue","cogs"]:
        tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values(["service_line_name","cogs"], ascending=[True,False])
    tbl.columns = [c.replace("_"," ").title() for c in tbl.columns]

    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":        st.column_config.NumberColumn("Revenue ($M)",   format="$%.2f"),
        "Cogs":           st.column_config.NumberColumn("COGS ($M)",      format="$%.2f"),
        "Cogs Pct Rev":   st.column_config.NumberColumn("COGS % Rev",     format="%.1f%%"),
        "Cogs Pct Total": st.column_config.NumberColumn("COGS % Total",   format="%.1f%%"),
    })
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       "cogs_detail.csv", "text/csv", key="cogs_dl")
