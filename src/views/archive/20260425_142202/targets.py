import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.formatters import safe_pct, kpi, fmt_m


def render_targets(ctx):
    PT            = ctx["PT"]
    palette       = ctx["palette"]
    df_tgt        = ctx["df_tgt"]
    selected_year = ctx["selected_year"]
    rev           = ctx["rev"]
    m_to          = ctx.get("m_to", 12)
    BS = palette["blue_scale"]
    LC = palette["line_current"]

    st.markdown('<div class="section-header">Targets vs Actuals</div>', unsafe_allow_html=True)

    dty          = df_tgt[df_tgt["yr"]==selected_year].copy()
    tt           = dty["target_usd"].sum() if not dty.empty else 0
    vt           = rev - tt
    ptt          = safe_pct(rev, tt) if tt not in (0,None) else 0
    months_left  = max(12 - m_to, 0)
    remaining    = max(tt - rev, 0)
    monthly_need = remaining / months_left if months_left > 0 else 0

    # KPI row
    tk = st.columns(4)
    tk[0].markdown(kpi(f"{selected_year} Target", tt),              unsafe_allow_html=True)
    tk[1].markdown(kpi("Actual Revenue", rev, vt, "vs Target"),     unsafe_allow_html=True)
    tk[2].markdown(kpi("Attainment %", ptt, kind="pct"),            unsafe_allow_html=True)
    tk[3].markdown(kpi("Teams", dty["team_primary_name"].nunique() if not dty.empty else 0, kind="count"), unsafe_allow_html=True)

    # Remaining year card
    if tt > 0 and months_left > 0:
        colour = "#4ade80" if rev >= tt else "#fb923c"
        st.markdown(
            f'<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid {colour};'
            f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
            f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:0.3rem;">Remaining Year</div>'
            f'<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;">'
            f'<b style="color:#cbd5e1;">{fmt_m(remaining)}</b> still needed in '
            f'<b style="color:#cbd5e1;">{months_left}</b> remaining months &nbsp;|&nbsp; '
            f'Requires <b style="color:{colour}">{fmt_m(monthly_need)}/month</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    if dty.empty:
        st.info(f"No target data for {selected_year}. Targets only from Q1 2025.")
    else:
        # ── Quarterly pacing — target vs actual on same chart ─
        st.markdown('<div class="section-header">Quarterly Pacing — Target vs Actual</div>', unsafe_allow_html=True)

        qt = (dty.assign(ql="Q"+dty["quarter_start_date"].dt.quarter.astype(str))
              .groupby(["ql","quarter_start_date"],as_index=False)["target_usd"]
              .sum().sort_values("quarter_start_date"))

        # Rough quarterly actual split — prorate annual by quarter
        # If detailed quarterly actuals are not available, show annual attainment line
        fig_pace = go.Figure()
        fig_pace.add_trace(go.Bar(
            x=qt["ql"], y=qt["target_usd"],
            name="Target", marker_color="#1e3a5f", marker_line_width=0,
        ))
        # Flat actual line across quarters (total actual / 4)
        actual_per_q = rev / 4
        fig_pace.add_trace(go.Scatter(
            x=qt["ql"], y=[actual_per_q]*len(qt),
            name="Actual (avg per Q)", mode="lines+markers",
            line=dict(color=LC, width=2), marker=dict(size=6),
        ))
        # Attainment % annotation
        for _, r in qt.iterrows():
            attainment = safe_pct(actual_per_q, r["target_usd"])
            fig_pace.add_annotation(
                x=r["ql"], y=r["target_usd"],
                text=f"{attainment:.0f}%",
                showarrow=False, yshift=12,
                font=dict(size=9, color="#d7f34a", family="DM Mono"),
            )
        fig_pace.update_layout(**PT, title="Quarterly Target vs Actual Revenue",
                               title_font_color="#cbd5e1", bargap=0.35,
                               legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#cbd5e1",size=10)))
        fig_pace.update_yaxes(tickformat="$,.0s")
        st.plotly_chart(fig_pace, use_container_width=True)

        # ── Team charts ────────────────────────────────────────
        col_qt, col_ta = st.columns(2)

        with col_qt:
            fig = px.bar(qt, x="ql", y="target_usd", color="target_usd",
                         color_continuous_scale=BS,
                         title="Quarterly Targets by Quarter",
                         labels={"target_usd":"Target ($M)","ql":"Quarter"},
                         category_orders={"ql":qt["ql"].tolist()})
            fig.update_layout(**PT, coloraxis_showscale=False,
                              title_font_color="#cbd5e1", showlegend=False)
            fig.update_yaxes(tickformat="$,.0s")
            st.plotly_chart(fig, use_container_width=True)

        with col_ta:
            ta = (dty.groupby("team_primary_name")["target_usd"].sum()
                  .reset_index().sort_values("target_usd",ascending=True))
            fig2 = px.bar(ta, x="target_usd", y="team_primary_name", orientation="h",
                          color="target_usd", color_continuous_scale=BS,
                          title="Annual Target by Team",
                          labels={"target_usd":"Annual Target ($M)","team_primary_name":""})
            fig2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            fig2.update_xaxes(tickformat="$,.0s")
            st.plotly_chart(fig2, use_container_width=True)

        # ── Detail table ────────────────────────────────────────
        st.markdown('<div class="section-header">Target Detail</div>', unsafe_allow_html=True)
        ttbl = dty.copy()
        ttbl["target_usd"] = (ttbl["target_usd"]/1e6).round(2)
        ttbl.columns = [c.replace("_"," ").title() for c in ttbl.columns]
        st.dataframe(ttbl, use_container_width=True, hide_index=True,
                     column_config={"Target Usd":st.column_config.NumberColumn("Target ($M)",format="$%.2f")})
        st.download_button("Download CSV", ttbl.to_csv(index=False).encode(),
                           "targets.csv","text/csv",key="tgt_dl")

    # ── Data gap flags ────────────────────────────────────────
    st.markdown(
        '<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #fb923c;'
        'border-radius:12px;padding:0.7rem 1rem;margin-top:1rem;">'
        '<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
        'text-transform:uppercase;margin-bottom:0.4rem;">Data Gaps</div>'
        '<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;line-height:1.7;">'
        '⚠ Targets loaded from Q1 2025 only — prior years not available in DB<br>'
        '⚠ 2026 budget not yet loaded — upload required for forward-looking view<br>'
        '⚠ Team → Service Line mapping not available — quarterly actuals cannot be split by SL vs target'
        '</div></div>',
        unsafe_allow_html=True,
    )
