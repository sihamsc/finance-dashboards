import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice, remove_service_line_filters
from src.utils.formatters import pct_text
from src.utils.helpers import service_line_selector_block

def render_cogs(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">COGS Decomposition</div>', unsafe_allow_html=True)

    df_service_view = clean_for_visuals(df_curr_decomp)

    col_csl, col_ccl = st.columns(2)

    with col_csl:
        cogs_sl = clean_for_visuals(df_curr_decomp).groupby("service_line_name").agg(revenue=("revenue", "sum"), cogs=("cogs", "sum")).reset_index()
        cogs_sl["pct_of_rev"] = (cogs_sl["cogs"] / cogs_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        cogs_sl = cogs_sl[cogs_sl["cogs"] > 0].sort_values("cogs", ascending=True)

        fig = px.bar(
            cogs_sl,
            x="cogs",
            y="service_line_name",
            orientation="h",
            color="cogs",
            color_continuous_scale=BS,
            text=cogs_sl["pct_of_rev"].map(pct_text),
            title="COGS by Service Line",
            labels={"cogs": "COGS ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_ccl:
        cogs_cl = clean_for_visuals(df_curr).groupby("top_level_parent_customer_name").agg(revenue=("revenue", "sum"), cogs=("cogs", "sum")).reset_index()
        cogs_cl["pct_of_rev"] = (cogs_cl["cogs"] / cogs_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(cogs_cl), 15)
        start_rank = st.select_slider("Show client ranks", options=start_options, value=1, key="cogs_client_rank")
        cogs_cl_window, end_rank, total_clients = rank_window_slice(cogs_cl, "cogs", start_rank, 15)

        fig = px.bar(
            cogs_cl_window,
            x="cogs",
            y="top_level_parent_customer_name",
            orientation="h",
            color="cogs",
            color_continuous_scale=BS,
            text=cogs_cl_window["pct_of_rev"].map(pct_text),
            title=f"COGS by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"cogs": "COGS ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">COGS Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_service_view,
        selected_metric_col="cogs",
        revenue_col="revenue",
        title_prefix="COGS",
        color_scale=BS,
        percent_label="COGS % Rev",
        selector_key="cogs_sl_selector",
        PT=PT,
    )