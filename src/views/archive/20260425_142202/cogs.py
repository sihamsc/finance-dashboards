import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice
from src.utils.formatters import pct_text
from src.utils.helpers import service_line_selector_block


def render_cogs(ctx):
    palette       = ctx["palette"]
    PT            = ctx["PT"]
    df_curr       = ctx["df_curr"]
    df_curr_decomp= ctx["df_curr_decomp"]
    BS = palette["blue_scale"]
    SC = palette["series"]

    st.markdown('<div class="section-header">COGS Decomposition</div>', unsafe_allow_html=True)

    # ── Row 1: SL bar + COGS% trend ──────────────────────────
    col_csl, col_trend = st.columns(2)

    with col_csl:
        cogs_sl = (clean_for_visuals(df_curr_decomp)
                   .groupby("service_line_name")
                   .agg(revenue=("revenue","sum"),cogs=("cogs","sum"))
                   .reset_index())
        cogs_sl["pct_of_rev"] = (cogs_sl["cogs"]/cogs_sl["revenue"].replace(0,float("nan"))*100).round(1)
        cogs_sl = cogs_sl[cogs_sl["cogs"]>0].sort_values("cogs",ascending=True)
        fig = px.bar(cogs_sl, x="cogs", y="service_line_name", orientation="h",
                     color="cogs", color_continuous_scale=BS,
                     text=cogs_sl["pct_of_rev"].map(pct_text),
                     title="COGS by Service Line",
                     labels={"cogs":"COGS ($)","service_line_name":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_trend:
        # COGS % of revenue monthly trend — key ratio for CFO
        mth = (df_curr_decomp.groupby("accounting_period_start_date")
               .agg(revenue=("revenue","sum"),cogs=("cogs","sum"))
               .reset_index().sort_values("accounting_period_start_date"))
        mth["cogs_pct"] = (mth["cogs"]/mth["revenue"].replace(0,float("nan"))*100).round(1)
        fig_t = px.area(mth, x="accounting_period_start_date", y="cogs_pct",
                        title="COGS % of Revenue — Monthly Trend",
                        labels={"accounting_period_start_date":"","cogs_pct":"COGS %"},
                        color_discrete_sequence=["#f87171"])
        fig_t.update_traces(line_width=2)
        fig_t.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30, height=420)
        fig_t.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_t, use_container_width=True)

    # ── Dual-axis: Revenue bar + COGS% line by SL ────────────
    st.markdown('<div class="section-header">Revenue vs COGS % by Service Line</div>', unsafe_allow_html=True)
    dual = (clean_for_visuals(df_curr_decomp)
            .groupby("service_line_name")
            .agg(revenue=("revenue","sum"),cogs=("cogs","sum"))
            .reset_index())
    dual["cogs_pct"] = (dual["cogs"]/dual["revenue"].replace(0,float("nan"))*100).round(1)
    dual = dual[dual["revenue"]>0].sort_values("revenue",ascending=False)

    fig_dual = go.Figure()
    fig_dual.add_trace(go.Bar(
        x=dual["service_line_name"], y=dual["revenue"],
        name="Revenue", marker_color=SC[0], marker_line_width=0, opacity=0.85,
    ))
    fig_dual.add_trace(go.Scatter(
        x=dual["service_line_name"], y=dual["cogs_pct"],
        name="COGS %", yaxis="y2",
        line=dict(color="#f87171",width=2), mode="lines+markers",
    ))
    fig_dual.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans",color="#94a3b8",size=11),
        title="Revenue vs COGS % by Service Line", title_font_color="#cbd5e1",
        xaxis=dict(gridcolor="#141924",linecolor="#1b2230",tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title="Revenue ($)",tickformat="$,.0s",gridcolor="#141924",
                   linecolor="#1b2230",tickfont=dict(color="#cbd5e1")),
        yaxis2=dict(title="COGS %",overlaying="y",side="right",
                    tickfont=dict(color="#f87171"),ticksuffix="%",
                    gridcolor="rgba(0,0,0,0)"),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#cbd5e1",size=10)),
        margin=dict(l=0,r=40,t=40,b=0), height=380,
    )
    st.plotly_chart(fig_dual, use_container_width=True)

    # ── Client bar with high-COGS flag ────────────────────────
    st.markdown('<div class="section-header">COGS by Client</div>', unsafe_allow_html=True)
    cogs_cl = (clean_for_visuals(df_curr)
               .groupby("top_level_parent_customer_name")
               .agg(revenue=("revenue","sum"),cogs=("cogs","sum"))
               .reset_index())
    cogs_cl["pct_of_rev"] = (cogs_cl["cogs"]/cogs_cl["revenue"].replace(0,float("nan"))*100).round(1)

    start_options = rank_window_options(len(cogs_cl),15)
    start_rank    = st.select_slider("Show client ranks", options=start_options, value=1, key="cogs_client_rank")
    cogs_cl_window, end_rank, total_clients = rank_window_slice(cogs_cl,"cogs",start_rank,15)

    # Flag clients where COGS > 60% of revenue in red
    colours = ["#f87171" if p > 60 else "#4c78a8" for p in cogs_cl_window["pct_of_rev"]]
    fig_cl = go.Figure(go.Bar(
        x=cogs_cl_window["cogs"],
        y=cogs_cl_window["top_level_parent_customer_name"],
        orientation="h",
        marker_color=colours, marker_line_width=0,
        text=cogs_cl_window["pct_of_rev"].map(pct_text),
        textposition="outside",
        name="",
    ))
    fig_cl.update_layout(**PT, title=f"COGS by Client — ranks {start_rank}–{min(end_rank,total_clients)} (red = COGS >60% rev)",
                         title_font_color="#cbd5e1", height=420)
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig_cl, use_container_width=True)

    # ── Sub-SL drilldown ─────────────────────────────────────
    st.markdown('<div class="section-header">COGS Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=clean_for_visuals(df_curr_decomp),
        selected_metric_col="cogs",
        revenue_col="revenue",
        title_prefix="COGS",
        color_scale=BS,
        percent_label="COGS % Rev",
        selector_key="cogs_sl_selector",
        PT=PT,
    )
