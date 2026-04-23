import plotly.express as px
import streamlit as st

from src.utils.formatters import safe_pct, kpi

def render_targets(ctx):
    PT = ctx["PT"]
    palette = ctx["palette"]
    df_tgt = ctx["df_tgt"]
    selected_year = ctx["selected_year"]
    rev = ctx["rev"]

    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Targets vs Actuals</div>', unsafe_allow_html=True)

    dty = df_tgt[df_tgt["yr"] == selected_year].copy()
    tt = dty["target_usd"].sum() if not dty.empty else 0
    vt = rev - tt
    ptt = safe_pct(rev, tt) if tt not in (0, None) else 0

    tk = st.columns(4)
    tk[0].markdown(kpi(f"{selected_year} Target", tt), unsafe_allow_html=True)
    tk[1].markdown(kpi("Actual Revenue", rev, vt, "vs Target"), unsafe_allow_html=True)
    tk[2].markdown(kpi("Attainment %", ptt, kind="pct"), unsafe_allow_html=True)
    tk[3].markdown(kpi("Teams", dty["team_primary_name"].nunique() if not dty.empty else 0, kind="count"), unsafe_allow_html=True)

    col_qt, col_ta = st.columns(2)

    with col_qt:
        if not dty.empty:
            qt = (
                dty.assign(ql="Q" + dty["quarter_start_date"].dt.quarter.astype(str))
                .groupby(["ql", "quarter_start_date"], as_index=False)["target_usd"]
                .sum()
                .sort_values("quarter_start_date")
            )
            fig = px.bar(
                qt,
                x="ql",
                y="target_usd",
                color="target_usd",
                color_continuous_scale=BS,
                title="Quarterly Targets",
                labels={"target_usd": "Target ($M)", "ql": "Quarter"},
                category_orders={"ql": qt["ql"].tolist()},
            )
            fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No target data for {selected_year}. Targets only from Q1 2025.")

    with col_ta:
        if not dty.empty:
            ta = dty.groupby("team_primary_name")["target_usd"].sum().reset_index().sort_values("target_usd", ascending=True)
            fig = px.bar(
                ta,
                x="target_usd",
                y="team_primary_name",
                orientation="h",
                color="target_usd",
                color_continuous_scale=BS,
                title="Annual Target by Team",
                labels={"target_usd": "Annual Target ($M)", "team_primary_name": ""},
            )
            fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
            st.plotly_chart(fig, use_container_width=True)