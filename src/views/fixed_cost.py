"""
Fixed Cost tab — refactored layout:
  1. Deterministic headline
  2. Tile chart — Service Line (Fixed Cost $M + % of total)
  3. Donut — Brand Effect / AE Synd / RTA split (keep, remove redundant bar)
  4. Client bar chart (Top 15 / 30 / All radio)
  5. Detail table
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m, pct_text
from src.views.revenue import render_tile_chart


def _narrative(ctx):
    """Return the headline summary string for the fixed cost card."""
    fixed_cost = ctx["fixed_cost"]
    rev        = ctx["rev"]
    fc_py      = ctx.get("fixed_cost_py", 0)
    period     = ctx["period_label"]
    fc_pct     = (fixed_cost / rev * 100) if rev > 0 else 0
    dir_       = "up" if fixed_cost >= fc_py else "down"
    delta_m    = abs(fixed_cost - fc_py)
    return (
        f"<b>{period}:</b> Fixed costs of <b>{fmt_m(fixed_cost)}</b> represent "
        f"<b>{fc_pct:.1f}%</b> of revenue, "
        f"{dir_} <b>{fmt_m(delta_m)}</b> vs prior year."
    )


def render_fixed_cost(ctx):
    """Render the Fixed Cost tab.

    Fixed cost = BE allocation + AE Synd allocation + RTA allocation,
    each proportionally allocated to clients by their revenue share.

    Sections:
      1. Narrative headline + allocation methodology card
      2. Service Line treemap
      3. Allocation type donut (BE / AE / RTA) + FC% monthly area trend
      4. Client bar chart (Top 15 / Top 30 / All)
      5. Detail table with CSV download
    """
    palette        = ctx["palette"]
    PT             = ctx["PT"]
    df_curr        = ctx["df_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    fixed_cost     = ctx["fixed_cost"]

    BS = palette["blue_scale"]
    DC = palette["donut"]

    # ── 1. Headline ───────────────────────────────────────────────
    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #a78bfa;'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'{_narrative(ctx)}</div></div>',
        unsafe_allow_html=True,
    )

    # Methodology info card
    be_total  = df_curr["be_allocation"].sum()
    ae_total  = df_curr["ae_allocation"].sum()
    rta_total = df_curr["rta_allocation"].sum()
    st.markdown(
        f'<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #60a5fa;'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
        f'text-transform:uppercase;margin-bottom:0.4rem;">Allocation Methodology</div>'
        f'<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;line-height:1.6;">'
        f'<b style="color:#cbd5e1;">Brand Effect {fmt_m(be_total)}</b> — allocated proportionally by client BE revenue share / 12 months'
        f' &nbsp;|&nbsp; <b style="color:#cbd5e1;">AE Synd {fmt_m(ae_total)}</b> — proportional by AE revenue share'
        f' &nbsp;|&nbsp; <b style="color:#cbd5e1;">RTA {fmt_m(rta_total)}</b> — proportional by RTA revenue share'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── 2. Service Line tile chart ───────────────────────────────
    st.markdown('<div class="section-header">Fixed Cost by Service Line</div>', unsafe_allow_html=True)
    fc_sl = (
        clean_for_visuals(df_curr_decomp)
        .groupby("service_line_name")
        .agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum"))
        .reset_index()
    )
    fc_sl = fc_sl[fc_sl["fixed_cost"] > 0]
    render_tile_chart(fc_sl, "service_line_name", "fixed_cost", "", BS, "fc_sl", PT)

    # ── 3. Donut + FC% trend (side by side) ──────────────────────
    st.markdown('<div class="section-header">Allocation Type Split</div>', unsafe_allow_html=True)
    col_don, col_trend = st.columns(2)

    with col_don:
        asp = pd.DataFrame({
            "Type":   ["Brand Effect", "AE Synd", "RTA"],
            "Amount": [be_total, ae_total, rta_total],
        })
        asp = asp[asp["Amount"] > 0]
        fig_d = px.pie(
            asp, names="Type", values="Amount", hole=0.68,
            title="BE / AE Synd / RTA",
            color="Type",
            color_discrete_map={"Brand Effect": DC[0], "AE Synd": DC[1], "RTA": DC[2]},
        )
        fig_d.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fig_d.add_annotation(
            text=fmt_m(fixed_cost), x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="#f8fafc", family="DM Sans"),
        )
        st.plotly_chart(fig_d, use_container_width=True)

    with col_trend:
        mth = (
            df_curr_decomp
            .groupby("accounting_period_start_date")
            .agg(revenue=("revenue", "sum"), fc=("fixed_cost", "sum"))
            .reset_index()
            .sort_values("accounting_period_start_date")
        )
        mth["fc_pct"] = (mth["fc"] / mth["revenue"].replace(0, float("nan")) * 100).round(1)
        fig_t = px.area(
            mth, x="accounting_period_start_date", y="fc_pct",
            title="FC % of Revenue",
            labels={"accounting_period_start_date": "", "fc_pct": "FC %"},
            color_discrete_sequence=[DC[0]],
        )
        fig_t.update_traces(line_width=2)
        fig_t.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig_t.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_t, use_container_width=True)

    # ── 4. Top allocation recipients bar ──────────────────────────
    st.markdown('<div class="section-header">Fixed Cost by Client</div>', unsafe_allow_html=True)

    fc_cl_all = (
        clean_for_visuals(df_curr)
        .groupby("top_level_parent_customer_name")
        .agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum"))
        .reset_index()
        .sort_values("fixed_cost", ascending=False)
    )
    fc_cl_all["pct_of_rev"] = (
        fc_cl_all["fixed_cost"] / fc_cl_all["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    # Top 5 recipients inline
    top5 = fc_cl_all.head(5)
    top5_html = " &nbsp;|&nbsp; ".join([
        f'<b style="color:#cbd5e1;">{r["top_level_parent_customer_name"][:20]}</b> {fmt_m(r["fixed_cost"])}'
        for _, r in top5.iterrows()
    ])
    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.5rem;">'
        f'LARGEST RECIPIENTS — {top5_html}</div>',
        unsafe_allow_html=True,
    )

    client_view = st.radio("Client view", ["Top 15", "Top 30", "All"], horizontal=True, key="fc_client_view")
    n_show = {"Top 15": 15, "Top 30": 30, "All": len(fc_cl_all)}[client_view]
    fc_cl_show = fc_cl_all.head(n_show).sort_values("fixed_cost", ascending=True)

    fig_cl = px.bar(
        fc_cl_show, x="fixed_cost", y="top_level_parent_customer_name", orientation="h",
        color="fixed_cost", color_continuous_scale=BS,
        text=fc_cl_show["pct_of_rev"].map(pct_text),
        title=f"— {client_view}",
        labels={"fixed_cost": "Fixed Cost ($)", "top_level_parent_customer_name": ""},
    )
    fig_cl.update_traces(textposition="outside")
    fig_cl.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1",
                         height=max(380, n_show * 26))
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig_cl, use_container_width=True)

    # ── 5. Detail table ───────────────────────────────────────────
    st.markdown('<div class="section-header">Fixed Cost Detail</div>', unsafe_allow_html=True)
    fc_tbl = (
        clean_for_visuals(df_curr)
        .groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum"))
        .reset_index()
    )
    total_fc = fc_tbl["fixed_cost"].sum()
    fc_tbl["fc_pct_rev"] = (fc_tbl["fixed_cost"] / fc_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    fc_tbl["fc_pct_tot"] = (fc_tbl["fixed_cost"] / total_fc * 100).round(1)
    for c in ["revenue", "fixed_cost"]:
        fc_tbl[c] = (fc_tbl[c] / 1e6).round(2)
    fc_tbl = fc_tbl.sort_values(["service_line_name", "fixed_cost"], ascending=[True, False])
    fc_tbl.columns = [c.replace("_", " ").title() for c in fc_tbl.columns]

    st.dataframe(
        fc_tbl, use_container_width=True, hide_index=True,
        column_config={
            "Revenue":      st.column_config.NumberColumn("Revenue ($M)",    format="$%.2f"),
            "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Fc Pct Rev":   st.column_config.NumberColumn("FC % Rev",        format="%.1f%%"),
            "Fc Pct Tot":   st.column_config.NumberColumn("FC % Total",      format="%.1f%%"),
        },
    )
    st.download_button(
        "Download CSV", fc_tbl.to_csv(index=False).encode(),
        "fixed_cost_detail.csv", "text/csv", key="fc_dl",
    )
