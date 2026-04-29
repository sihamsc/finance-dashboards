import plotly.express as px
import streamlit as st

from src.utils.filters import EXCL
from src.utils.formatters import kpi

def render_pipeline(ctx):
    PT = ctx["PT"]
    palette = ctx["palette"]
    df_pipe = ctx["df_pipe"]

    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)

    dp = df_pipe.drop_duplicates("deal_id")
    if "service_line" in dp.columns:
        dp = dp[~dp["service_line"].isin(EXCL)]

    tp = dp["pipeline_value_usd"].sum()
    td = dp["deal_id"].nunique()
    ad = tp / td if td > 0 else 0

    pk = st.columns(3)
    pk[0].markdown(kpi("Total Pipeline", tp), unsafe_allow_html=True)
    pk[1].markdown(kpi("Active Deals", td, kind="count"), unsafe_allow_html=True)
    pk[2].markdown(kpi("Avg Deal Size", ad), unsafe_allow_html=True)

    col_ps, col_psl = st.columns(2)

    with col_ps:
        ps2 = dp.groupby("deal_pipeline_stage_name").agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum")).reset_index().sort_values("value", ascending=True)
        fig = px.bar(
            ps2,
            x="value",
            y="deal_pipeline_stage_name",
            orientation="h",
            color="value",
            color_continuous_scale=BS,
            title="Pipeline by Stage",
            labels={"value": "Pipeline Value ($)", "deal_pipeline_stage_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1")
        st.plotly_chart(fig, use_container_width=True)

    with col_psl:
        psl = dp.groupby("service_line").agg(deals=("deal_id", "nunique"), value=("pipeline_value_usd", "sum")).reset_index().sort_values("value", ascending=False)
        fig = px.bar(
            psl,
            x="service_line",
            y="value",
            color="value",
            color_continuous_scale=BS,
            title="Pipeline by Service Line",
            labels={"value": "Pipeline Value ($)", "service_line": ""},
        )
        fig.update_layout(**PT, xaxis_tickangle=-45, coloraxis_showscale=False, title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)