"""
Pipeline tab — deal pipeline overview and coverage vs annual target.

Sections:
  1. KPI row: total pipeline, deal count, avg deal size, coverage, remaining-target cover
  2. Remaining-year run-rate card (how much revenue is still needed and at what monthly pace)
  3. Pipeline by stage (horizontal bar)
  4. Pipeline by service line (vertical bar)
  5. Pipeline by vertical (conditional — only shown if 'vertical' column exists)
  6. Pipeline detail table with CSV download
"""

import plotly.express as px
import streamlit as st

from src.utils.filters import EXCL
from src.utils.formatters import kpi, fmt_m, safe_pct


def render_pipeline(ctx):
    """Render the Pipeline tab.

    Deduplicates deals by deal_id before all aggregations to avoid double-counting
    deals that span multiple rows in the source data.
    """
    PT       = ctx["PT"]
    palette  = ctx["palette"]
    df_pipe  = ctx["df_pipe"]
    df_tgt   = ctx["df_tgt"]
    selected_year = ctx["selected_year"]
    rev      = ctx["rev"]
    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Pipeline Summary</div>', unsafe_allow_html=True)

    dp = df_pipe.drop_duplicates("deal_id")
    if "service_line" in dp.columns:
        dp = dp[~dp["service_line"].isin(EXCL)]

    tp = dp["pipeline_value_usd"].sum()
    td = dp["deal_id"].nunique()
    ad = tp/td if td>0 else 0

    # Annual target for coverage calc
    dty        = df_tgt[df_tgt["yr"]==selected_year]
    ann_target = dty["target_usd"].sum() if not dty.empty else 0
    coverage   = tp/ann_target if ann_target > 0 else 0

    # Pipeline to target gap
    remaining_target = max(ann_target - rev, 0)
    gap_covered      = safe_pct(tp, remaining_target) if remaining_target > 0 else 100.0

    # KPI row
    pk = st.columns(5)
    pk[0].markdown(kpi("Total Pipeline",      tp), unsafe_allow_html=True)
    pk[1].markdown(kpi("Active Deals",        td, kind="count"), unsafe_allow_html=True)
    pk[2].markdown(kpi("Avg Deal Size",        ad), unsafe_allow_html=True)
    pk[3].markdown(kpi("Pipeline Coverage",   coverage, kind="dollar"), unsafe_allow_html=True)
    pk[4].markdown(kpi("Covers Remaining Tgt",gap_covered, kind="pct"), unsafe_allow_html=True)

    # Pipeline → Target link card
    if ann_target > 0:
        m = ctx.get("m_to", 12)
        months_left = max(12 - m, 1)
        monthly_needed = remaining_target / months_left
        st.markdown(
            f'<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #d7f34a;'
            f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
            f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:0.3rem;">Remaining Year</div>'
            f'<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;">'
            f'<b style="color:#cbd5e1;">{fmt_m(remaining_target)}</b> still needed to hit {selected_year} target &nbsp;|&nbsp; '
            f'Requires <b style="color:#cbd5e1;">{fmt_m(monthly_needed)}/month</b> &nbsp;|&nbsp; '
            f'Pipeline covers <b style="color:{"#4ade80" if gap_covered>=100 else "#fb923c"}">{gap_covered:.0f}%</b> of that'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── Charts ────────────────────────────────────────────────
    col_ps, col_psl = st.columns(2)

    with col_ps:
        ps2 = (dp.groupby("deal_pipeline_stage_name")
               .agg(deals=("deal_id","nunique"),value=("pipeline_value_usd","sum"))
               .reset_index().sort_values("value",ascending=True))
        fig = px.bar(ps2, x="value", y="deal_pipeline_stage_name", orientation="h",
                     color="value", color_continuous_scale=BS,
                     title="Pipeline by Stage",
                     labels={"value":"Pipeline Value ($)","deal_pipeline_stage_name":""})
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_psl:
        psl = (dp.groupby("service_line")
               .agg(deals=("deal_id","nunique"),value=("pipeline_value_usd","sum"))
               .reset_index().sort_values("value",ascending=False))
        fig2 = px.bar(psl, x="service_line", y="value", color="value",
                      color_continuous_scale=BS,
                      title="Pipeline by Service Line",
                      labels={"value":"Pipeline Value ($)","service_line":""})
        fig2.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False,
                           title_font_color="#cbd5e1", showlegend=False)
        fig2.update_yaxes(tickformat="$,.0s")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Pipeline by vertical ──────────────────────────────────
    if "vertical" in dp.columns:
        st.markdown('<div class="section-header">Pipeline by Vertical</div>', unsafe_allow_html=True)
        pv = (dp[~dp["vertical"].isin(EXCL)]
              .groupby("vertical")
              .agg(deals=("deal_id","nunique"),value=("pipeline_value_usd","sum"))
              .reset_index().sort_values("value",ascending=True))
        fig3 = px.bar(pv, x="value", y="vertical", orientation="h",
                      color="value", color_continuous_scale=BS,
                      title="Pipeline by Vertical",
                      labels={"value":"Pipeline Value ($)","vertical":""})
        fig3.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        fig3.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Pipeline detail table ─────────────────────────────────
    st.markdown('<div class="section-header">Deal Pipeline Detail</div>', unsafe_allow_html=True)
    ptbl = (dp.groupby(["deal_pipeline_stage_name","service_line","vertical"])
            .agg(deals=("deal_id","nunique"),value=("pipeline_value_usd","sum"))
            .reset_index().sort_values("value",ascending=False))
    ptbl["value"] = (ptbl["value"]/1e6).round(2)
    ptbl.columns  = [c.replace("_"," ").title() for c in ptbl.columns]
    st.dataframe(ptbl, use_container_width=True, hide_index=True,
                 column_config={"Value":st.column_config.NumberColumn("Value ($M)",format="$%.2f")})
    st.download_button("Download CSV", ptbl.to_csv(index=False).encode(),
                       "pipeline_detail.csv","text/csv",key="pipe_dl")

    st.markdown(
        '<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #fb923c;'
        'border-radius:8px;padding:0.6rem 1rem;margin-top:1rem;">'
        '<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
        'text-transform:uppercase;margin-bottom:0.3rem;">Data Gaps</div>'
        '<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;line-height:1.6;">'
        '⚠ Stage names are custom labels (e.g. "Q1 2025") — standard Stage 1–6 mapping pending from Chris/John<br>'
        '⚠ Deal owner / account manager not currently in pipeline data — can\'t split by rep'
        '</div></div>',
        unsafe_allow_html=True,
    )
