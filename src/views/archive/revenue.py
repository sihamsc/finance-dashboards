import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice, remove_service_line_filters, EXCL
from src.utils.helpers import service_line_selector_block

def render_revenue(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    df_lab_curr = ctx["df_lab_curr"]

    SC = palette["series"]
    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Revenue Decomposition</div>', unsafe_allow_html=True)

    df_service_view = clean_for_visuals(df_curr_decomp)

    col_rsl, col_rcl = st.columns(2)

    with col_rsl:
        rv_sl = clean_for_visuals(df_curr_decomp).groupby("service_line_name")["revenue"].sum().reset_index()
        rv_sl = rv_sl[rv_sl["revenue"] > 0].sort_values("revenue", ascending=True)

        fig = px.bar(
            rv_sl,
            x="revenue",
            y="service_line_name",
            orientation="h",
            color="service_line_name",
            color_discrete_sequence=SC,
            title="Revenue by Service Line",
            labels={"revenue": "Revenue ($)", "service_line_name": ""},
        )
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**PT, showlegend=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_rcl:
        rv_cl = clean_for_visuals(df_curr).groupby("top_level_parent_customer_name")["revenue"].sum().reset_index()
        start_options = rank_window_options(len(rv_cl), 15)
        start_rank = st.select_slider("Show client ranks", options=start_options, value=1, key="rev_client_rank")
        rv_cl_window, end_rank, total_clients = rank_window_slice(rv_cl, "revenue", start_rank, 15)

        fig = px.bar(
            rv_cl_window,
            x="revenue",
            y="top_level_parent_customer_name",
            orientation="h",
            color="revenue",
            color_continuous_scale=BS,
            title=f"Revenue by Client — ranks {start_rank}–{min(end_rank, total_clients)}",
            labels={"revenue": "Revenue ($)", "top_level_parent_customer_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Revenue Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=df_service_view,
        selected_metric_col="revenue",
        revenue_col="revenue",
        title_prefix="Revenue",
        color_scale=BS,
        percent_label="Share of Revenue",
        selector_key="rev_sl_selector",
        PT=PT,
    )

    st.markdown('<div class="section-header">Revenue Detail — Service Line × Sub Service Line ($M)</div>', unsafe_allow_html=True)
    lab_join = (
        df_lab_curr.groupby(["service_line_name", "sub_service_line_name"])["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )
    rv_tbl = (
        df_curr.groupby(["service_line_name", "sub_service_line_name"], dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
            clients=("top_level_parent_customer_name", lambda s: s[~s.isin(EXCL)].nunique()),
        )
        .reset_index()
    )
    rv_tbl = rv_tbl.merge(lab_join, on=["service_line_name", "sub_service_line_name"], how="left")
    rv_tbl["labor"] = rv_tbl["labor"].fillna(0)
    rv_tbl["contribution"] = rv_tbl["gross_margin"] - rv_tbl["labor"]
    rv_tbl["gm_pct"] = (rv_tbl["gross_margin"] / rv_tbl["revenue"].replace(0, float("nan")) * 100).round(1)
    rv_tbl["cm_pct"] = (rv_tbl["contribution"] / rv_tbl["revenue"].replace(0, float("nan")) * 100).round(1)

    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        rv_tbl[c] = (rv_tbl[c] / 1e6).round(2)

    rv_tbl = rv_tbl.sort_values(["service_line_name", "revenue"], ascending=[True, False])
    rv_tbl.columns = [c.replace("_", " ").title() for c in rv_tbl.columns]

    st.dataframe(
        rv_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Cogs": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "Gm Pct": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "Cm Pct": st.column_config.NumberColumn("CM %", format="%.1f%%"),
            "Clients": st.column_config.NumberColumn("Clients", format="%d"),
        },
    )