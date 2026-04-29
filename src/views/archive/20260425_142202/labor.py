import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice, MONTH_MAP
from src.utils.formatters import pct_text, safe_pct, kpi
from src.utils.helpers import service_line_selector_block


def render_labor(ctx):
    palette            = ctx["palette"]
    PT                 = ctx["PT"]
    df_curr            = ctx["df_curr"]
    df_lab_curr        = ctx["df_lab_curr"]
    df_curr_decomp     = ctx["df_curr_decomp"]
    df_lab_curr_decomp = ctx["df_lab_curr_decomp"]
    df_lab_prior       = ctx["df_lab_prior"]
    rev                = ctx["rev"]
    BS = palette["blue_scale"]
    SC = palette["series"]

    st.markdown('<div class="section-header">Labor Overview</div>', unsafe_allow_html=True)

    total_labor    = df_lab_curr["labour_cost"].sum()
    total_labor_py = df_lab_prior["labour_cost"].sum()
    total_hours    = df_lab_curr["total_hours"].sum()
    avg_hr         = total_labor/total_hours if total_hours > 0 else 0
    implied_fte    = round(total_hours/1920, 1)   # 1,920 hrs = ~1 FTE/year

    lk = st.columns(5)
    lk[0].markdown(kpi("Total Labor", total_labor, total_labor-total_labor_py, "vs PY"), unsafe_allow_html=True)
    lk[1].markdown(kpi("Labor % Rev", safe_pct(total_labor,rev), kind="pct"), unsafe_allow_html=True)
    lk[2].markdown(kpi("Total Hours",  total_hours, kind="count"), unsafe_allow_html=True)
    lk[3].markdown(kpi("Avg Cost/hr",  avg_hr, kind="dollar"), unsafe_allow_html=True)
    lk[4].markdown(kpi("Implied FTE",  implied_fte, kind="count"), unsafe_allow_html=True)

    # ── Row 1: SL bar + Revenue per Labor $ ──────────────────
    col_lsl, col_eff = st.columns(2)

    with col_lsl:
        labor_sl = (clean_for_visuals(df_lab_curr_decomp)
                    .groupby("service_line_name").agg(labor=("labour_cost","sum")).reset_index())
        rev_sl   = (clean_for_visuals(df_curr_decomp)
                    .groupby("service_line_name")["revenue"].sum().reset_index())
        labor_sl = labor_sl.merge(rev_sl, on="service_line_name", how="left")
        labor_sl["pct_of_rev"] = (labor_sl["labor"]/labor_sl["revenue"].replace(0,float("nan"))*100).round(1)
        labor_sl = labor_sl[labor_sl["labor"]>0].sort_values("labor",ascending=True)
        fig = px.bar(labor_sl, x="labor", y="service_line_name", orientation="h",
                     color="labor", color_continuous_scale=BS,
                     text=labor_sl["pct_of_rev"].map(pct_text),
                     title="Labor by Service Line",
                     labels={"labor":"Labor ($)","service_line_name":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_eff:
        # Revenue per $1 of Labor — efficiency metric
        eff = labor_sl.copy()
        eff["rev_per_labor"] = (eff["revenue"]/eff["labor"].replace(0,float("nan"))).round(2)
        eff = eff[eff["rev_per_labor"].notna()].sort_values("rev_per_labor",ascending=True)
        fig_e = px.bar(eff, x="rev_per_labor", y="service_line_name", orientation="h",
                       color="rev_per_labor", color_continuous_scale=BS,
                       title="Revenue per $1 of Labor — Efficiency",
                       labels={"rev_per_labor":"Revenue / $1 Labor","service_line_name":""})
        fig_e.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig_e.update_xaxes(tickprefix="$",tickformat=",.2f")
        st.plotly_chart(fig_e, use_container_width=True)

    # ── Client bar ────────────────────────────────────────────
    st.markdown('<div class="section-header">Labor by Client</div>', unsafe_allow_html=True)
    labor_cl = (clean_for_visuals(df_lab_curr)
                .groupby("top_level_parent_customer_name").agg(labor=("labour_cost","sum")).reset_index())
    rev_cl   = (clean_for_visuals(df_curr)
                .groupby("top_level_parent_customer_name")["revenue"].sum().reset_index())
    labor_cl = labor_cl.merge(rev_cl, on="top_level_parent_customer_name", how="left")
    labor_cl["pct_of_rev"] = (labor_cl["labor"]/labor_cl["revenue"].replace(0,float("nan"))*100).round(1)

    start_options = rank_window_options(len(labor_cl),15)
    start_rank    = st.select_slider("Show client ranks", options=start_options, value=1, key="labor_client_rank")
    lc_win, end_rank, total_clients = rank_window_slice(labor_cl,"labor",start_rank,15)
    fig_cl = px.bar(lc_win, x="labor", y="top_level_parent_customer_name", orientation="h",
                    color="labor", color_continuous_scale=BS,
                    text=lc_win["pct_of_rev"].map(pct_text),
                    title=f"Labor by Client — ranks {start_rank}–{min(end_rank,total_clients)}",
                    labels={"labor":"Labor ($)","top_level_parent_customer_name":""})
    fig_cl.update_traces(textposition="outside")
    fig_cl.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig_cl, use_container_width=True)

    # ── Labor heatmap: top 15 clients × month ────────────────
    st.markdown('<div class="section-header">Labor Cost Heatmap — Client × Month</div>', unsafe_allow_html=True)
    top15_clients = labor_cl.sort_values("labor",ascending=False).head(15)["top_level_parent_customer_name"].tolist()
    heat_src = (df_lab_curr[df_lab_curr["top_level_parent_customer_name"].isin(top15_clients)]
                .groupby(["top_level_parent_customer_name","month_num"])["labour_cost"]
                .sum().reset_index())
    heat_pivot = heat_src.pivot(index="top_level_parent_customer_name",
                                columns="month_num", values="labour_cost").fillna(0)
    heat_pivot.columns = [MONTH_MAP.get(c,str(c)) for c in heat_pivot.columns]
    heat_pivot = heat_pivot.reindex(
        [c for c in heat_pivot.index if c in top15_clients],
        axis=0
    )
    fig_h = px.imshow(
        heat_pivot/1000,
        color_continuous_scale=["#0a0d14","#1e3a5f","#60a5fa","#d7f34a"],
        title="Labor Cost by Client × Month ($k) — top 15 clients",
        labels=dict(x="Month",y="Client",color="Labor ($k)"),
        aspect="auto",
    )
    fig_h.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans",color="#94a3b8"),
        title_font_color="#cbd5e1",
        xaxis=dict(tickfont=dict(color="#cbd5e1")),
        yaxis=dict(tickfont=dict(color="#cbd5e1")),
        coloraxis_colorbar=dict(tickfont=dict(color="#cbd5e1"),title_font=dict(color="#cbd5e1")),
        margin=dict(l=0,r=0,t=40,b=0),
        height=400,
    )
    st.plotly_chart(fig_h, use_container_width=True)

    # ── Sub-SL drilldown ─────────────────────────────────────
    st.markdown('<div class="section-header">Labor Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    labor_drill_base = (
        df_lab_curr_decomp.merge(
            df_curr_decomp[["yr","month_num","service_line_name","sub_service_line_name",
                            "top_level_parent_customer_name","revenue"]]
            .groupby(["yr","month_num","service_line_name","sub_service_line_name",
                      "top_level_parent_customer_name"],as_index=False)["revenue"].sum(),
            on=["yr","month_num","service_line_name","sub_service_line_name",
                "top_level_parent_customer_name"],
            how="left"
        )
    )
    labor_drill_base["revenue"]     = labor_drill_base["revenue"].fillna(0)
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

    # Download
    ld = (clean_for_visuals(df_lab_curr)
          .groupby(["top_level_parent_customer_name","service_line_name","sub_service_line_name"])
          .agg(labour_cost=("labour_cost","sum"),total_hours=("total_hours","sum"))
          .reset_index().sort_values("labour_cost",ascending=False))
    ld["cost_per_hour"] = (ld["labour_cost"]/ld["total_hours"].replace(0,float("nan"))).round(0)
    ld["labour_cost"]   = (ld["labour_cost"]/1e6).round(3)
    ld.columns = [c.replace("_"," ").title() for c in ld.columns]
    st.download_button("Download Labor Detail CSV", ld.to_csv(index=False).encode(),
                       "labor_detail.csv","text/csv",key="lab_dl")
