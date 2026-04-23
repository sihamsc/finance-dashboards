import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice
from src.utils.formatters import pct_text, safe_pct, kpi
from src.utils.helpers import service_line_selector_block

def render_labor(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]
    df_lab_prior = ctx["df_lab_prior"]
    rev = ctx["rev"]

    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Labor Overview</div>', unsafe_allow_html=True)

    total_labor = df_lab_curr["labour_cost"].sum()
    total_labor_py = df_lab_prior["labour_cost"].sum()
    total_hours = df_lab_curr["total_hours"].sum()
    avg_hr = total_labor / total_hours if total_hours > 0 else 0

    lk = st.columns(4)
    lk[0].markdown(kpi("Total Labor", total_labor, total_labor - total_labor_py, "vs PY"), unsafe_allow_html=True)
    lk[1].markdown(kpi("Labor % Rev", safe_pct(total_labor, rev), kind="pct"), unsafe_allow_html=True)
    lk[2].markdown(kpi("Total Hours", total_hours, kind="count"), unsafe_allow_html=True)
    lk[3].markdown(kpi("Avg Cost/hr", avg_hr, kind="dollar"), unsafe_allow_html=True)

    col_lsl, col_lcl = st.columns(2)

    with col_lsl:
        labor_sl = clean_for_visuals(df_lab_curr).groupby("service_line_name").agg(labor=("labour_cost", "sum")).reset_index()
        rev_sl = clean_for_visuals(df_curr).groupby("service_line_name")["revenue"].sum().reset_index()
        labor_sl = labor_sl.merge(rev_sl, on="service_line_name", how="left")
        labor_sl["pct_of_rev"] = (labor_sl["labor"] / labor_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        labor_sl = labor_sl[labor_sl["labor"] > 0].sort_values("labor", ascending=True)

        fig = px.bar(
            labor_sl,
            x="labor",
            y="service_line_name",
            orientation="h",
            color="labor",
            color_continuous_scale=BS,
            text=labor_sl["pct_of_rev"].map(pct_text),
            title="Labor by Service Line",
            labels={"labor": "Labor ($)", "service_line_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_lcl:
        labor_cl = clean_for_visuals(df_lab_curr).groupby("top_level_parent_customer_name").agg(labor=("labour_cost", "sum")).reset_index()
        rev_cl = clean_for_visuals(df_curr).groupby("top_level_parent_customer_name")["revenue"].sum().reset_index()
        labor_cl = labor_cl.merge(rev_cl, on="top_level_parent_customer_name", how="left")
        labor_cl["pct_of_rev"] = (labor_cl["labor"] / labor_cl["revenue"].replace(0, float("nan")) * 100).round(1)

        start_options = rank_window_options(len(labor_cl), 15)
        start_rank = st.select_slider("Show client ranks", options=start_options, value=1, key="labor_client_rank")
        labor_cl_window, end_rank, total_clients = rank_window_slice(labor_cl, "labor", start_rank, 15)

        fig = px.bar(
            labor_cl_window,
            x="labor",
            y="top_level_parent_customer_name",
            orientation="h",
            color="labor",
            color_continuous_scale=BS,
            text=labor_cl_window["pct_of_rev"].map(pct_text),
            title=f"Labor by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"labor": "Labor ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Labor Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)

    labor_drill_base = (
        df_lab_curr.merge(
            df_curr[["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name", "revenue"]]
            .groupby(
                ["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
                as_index=False
            )["revenue"].sum(),
            on=["yr", "month_num", "service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            how="left"
        )
    )
    labor_drill_base["revenue"] = labor_drill_base["revenue"].fillna(0)
    labor_drill_base["labor_value"] = labor_drill_base["labour_cost"]

    service_line_selector_block(
        agg_df=labor_drill_base,
        selected_metric_col="labor_value",
        revenue_col="revenue",
        title_prefix="Labor",
        color_scale=BS,
        percent_label="Labor % Rev",
        selector_key="labor_sl_selector",
        PT=PT,
    )