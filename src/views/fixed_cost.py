import pandas as pd
import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice
from src.utils.formatters import pct_text, fmt_m
from src.utils.helpers import service_line_selector_block

def render_fixed_cost(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    fixed_cost = ctx["fixed_cost"]

    BS = palette["blue_scale"]
    DC = palette["donut"]

    st.markdown('<div class="section-header">Fixed Cost Split</div>', unsafe_allow_html=True)

    asp = pd.DataFrame({
        "Type": ["Brand Effect", "AE Synd", "RTA"],
        "Amount": [
            df_curr["be_allocation"].sum(),
            df_curr["ae_allocation"].sum(),
            df_curr["rta_allocation"].sum(),
        ],
    })
    asp = asp[asp["Amount"] > 0]

    fig_donut = px.pie(
        asp,
        names="Type",
        values="Amount",
        hole=0.68,
        title="Fixed Cost Split — Brand Effect / AE Synd / RTA",
        color="Type",
        color_discrete_map={"Brand Effect": DC[0], "AE Synd": DC[1], "RTA": DC[2]},
    )
    fig_donut.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
    fig_donut.add_annotation(
        text=fmt_m(fixed_cost),
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="#f8fafc", family="DM Sans"),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown('<div class="section-header">Fixed Cost Decomposition</div>', unsafe_allow_html=True)
    col_fsl, col_fcl = st.columns(2)

    with col_fsl:
        fc_sl = clean_for_visuals(df_curr).groupby("service_line_name").agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum")).reset_index()
        fc_sl["pct_of_rev"] = (fc_sl["fixed_cost"] / fc_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        fc_sl = fc_sl[fc_sl["fixed_cost"] > 0].sort_values("fixed_cost", ascending=True)

        fig = px.bar(
            fc_sl,
            x="fixed_cost",
            y="service_line_name",
            orientation="h",
            color="fixed_cost",
            color_continuous_scale=BS,
            text=fc_sl["pct_of_rev"].map(pct_text),
            title="Fixed Cost by Service Line",
            labels={"fixed_cost": "Fixed Cost ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_fcl:
        fc_cl = clean_for_visuals(df_curr).groupby("top_level_parent_customer_name").agg(revenue=("revenue", "sum"), fixed_cost=("fixed_cost", "sum")).reset_index()
        fc_cl["pct_of_rev"] = (fc_cl["fixed_cost"] / fc_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(fc_cl), 15)
        start_rank = st.select_slider("Show client ranks", options=start_options, value=1, key="fc_client_rank")
        fc_cl_window, end_rank, total_clients = rank_window_slice(fc_cl, "fixed_cost", start_rank, 15)

        fig = px.bar(
            fc_cl_window,
            x="fixed_cost",
            y="top_level_parent_customer_name",
            orientation="h",
            color="fixed_cost",
            color_continuous_scale=BS,
            text=fc_cl_window["pct_of_rev"].map(pct_text),
            title=f"Fixed Cost by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"fixed_cost": "Fixed Cost ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Fixed Cost Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_curr,
        selected_metric_col="fixed_cost",
        revenue_col="revenue",
        title_prefix="Fixed Cost",
        color_scale=BS,
        percent_label="Fixed Cost % Rev",
        selector_key="fc_sl_selector",
        PT=PT,
    )