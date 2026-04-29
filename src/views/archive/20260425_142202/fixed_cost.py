import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice
from src.utils.formatters import pct_text, fmt_m
from src.utils.helpers import service_line_selector_block


def render_fixed_cost(ctx):
    palette    = ctx["palette"]
    PT         = ctx["PT"]
    df_curr    = ctx["df_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    fixed_cost = ctx["fixed_cost"]

    BS = palette["blue_scale"]
    DC = palette["donut"]

    # ── Methodology info card ─────────────────────────────────
    be_total  = df_curr["be_allocation"].sum()
    ae_total  = df_curr["ae_allocation"].sum()
    rta_total = df_curr["rta_allocation"].sum()
    st.markdown(
        f'<div style="background:#0a0d14;border:1px solid #1b2230;border-left:3px solid #60a5fa;'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;letter-spacing:0.12em;'
        f'text-transform:uppercase;margin-bottom:0.4rem;">Allocation Methodology</div>'
        f'<div style="font-family:DM Sans,sans-serif;font-size:11px;color:#9ca3af;line-height:1.6;">'
        f'<b style="color:#cbd5e1;">Brand Effect {fmt_m(be_total)}</b> — allocated proportionally by client BE revenue share / 12 months &nbsp;|&nbsp; '
        f'<b style="color:#cbd5e1;">AE Synd {fmt_m(ae_total)}</b> — proportional by AE revenue share &nbsp;|&nbsp; '
        f'<b style="color:#cbd5e1;">RTA {fmt_m(rta_total)}</b> — proportional by RTA revenue share'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Fixed Cost Split</div>', unsafe_allow_html=True)

    # ── Donut + FC% trend ────────────────────────────────────
    col_don, col_trend = st.columns(2)

    with col_don:
        asp = pd.DataFrame({
            "Type":  ["Brand Effect","AE Synd","RTA"],
            "Amount":[be_total, ae_total, rta_total],
        })
        asp = asp[asp["Amount"]>0]
        fig_d = px.pie(asp, names="Type", values="Amount", hole=0.68,
                       title="Fixed Cost Split — Brand Effect / AE Synd / RTA",
                       color="Type",
                       color_discrete_map={"Brand Effect":DC[0],"AE Synd":DC[1],"RTA":DC[2]})
        fig_d.update_layout(**PT, title_font_color="#cbd5e1", legend_title_text="")
        fig_d.add_annotation(text=fmt_m(fixed_cost), x=0.5, y=0.5, showarrow=False,
                             font=dict(size=20,color="#f8fafc",family="DM Sans"))
        st.plotly_chart(fig_d, use_container_width=True)

    with col_trend:
        # Fixed Cost % of Revenue monthly — should fall as revenue grows
        mth = (df_curr_decomp.groupby("accounting_period_start_date")
               .agg(revenue=("revenue","sum"),fc=("fixed_cost","sum"))
               .reset_index().sort_values("accounting_period_start_date"))
        mth["fc_pct"] = (mth["fc"]/mth["revenue"].replace(0,float("nan"))*100).round(1)
        fig_t = px.area(mth, x="accounting_period_start_date", y="fc_pct",
                        title="Fixed Cost % of Revenue — Monthly",
                        labels={"accounting_period_start_date":"","fc_pct":"FC %"},
                        color_discrete_sequence=[DC[0]])
        fig_t.update_traces(line_width=2)
        fig_t.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig_t.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_t, use_container_width=True)

    # ── Top 5 allocation recipients ───────────────────────────
    st.markdown('<div class="section-header">Fixed Cost Decomposition</div>', unsafe_allow_html=True)
    fc_cl_all = (clean_for_visuals(df_curr)
                 .groupby("top_level_parent_customer_name")
                 .agg(revenue=("revenue","sum"),fixed_cost=("fixed_cost","sum"))
                 .reset_index().sort_values("fixed_cost",ascending=False))
    top5 = fc_cl_all.head(5)
    top5_html = " &nbsp;|&nbsp; ".join([
        f'<b style="color:#cbd5e1;">{r["top_level_parent_customer_name"][:20]}</b> {fmt_m(r["fixed_cost"])}'
        for _,r in top5.iterrows()
    ])
    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.8rem;">'
        f'LARGEST ALLOCATION RECIPIENTS — {top5_html}</div>',
        unsafe_allow_html=True,
    )

    col_fsl, col_fcl = st.columns(2)

    with col_fsl:
        fc_ssl = (clean_for_visuals(df_curr_decomp)
                  .groupby("sub_service_line_name")
                  .agg(revenue=("revenue","sum"),fixed_cost=("fixed_cost","sum"))
                  .reset_index())
        fc_ssl = fc_ssl[fc_ssl["sub_service_line_name"]!="(blank)"]
        fc_ssl["pct_of_rev"] = (fc_ssl["fixed_cost"]/fc_ssl["revenue"].replace(0,float("nan"))*100).round(1)
        fc_ssl = fc_ssl[fc_ssl["fixed_cost"]>0].sort_values("fixed_cost",ascending=True)
        fig = px.bar(fc_ssl, x="fixed_cost", y="sub_service_line_name", orientation="h",
                     color="fixed_cost", color_continuous_scale=BS,
                     text=fc_ssl["pct_of_rev"].map(pct_text),
                     title="Fixed Cost by Sub Service Line",
                     labels={"fixed_cost":"Fixed Cost ($)","sub_service_line_name":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_fcl:
        start_options = rank_window_options(len(fc_cl_all),15)
        start_rank    = st.select_slider("Show client ranks", options=start_options, value=1, key="fc_client_rank")
        fc_cl_window, end_rank, total_clients = rank_window_slice(fc_cl_all,"fixed_cost",start_rank,15)
        fc_cl_window["pct_of_rev"] = (fc_cl_window["fixed_cost"]/fc_cl_window["revenue"].replace(0,float("nan"))*100).round(1)
        fig = px.bar(fc_cl_window, x="fixed_cost", y="top_level_parent_customer_name", orientation="h",
                     color="fixed_cost", color_continuous_scale=BS,
                     text=fc_cl_window["pct_of_rev"].map(pct_text),
                     title=f"Fixed Cost by Client — ranks {start_rank}–{min(end_rank,total_clients)}",
                     labels={"fixed_cost":"Fixed Cost ($)","top_level_parent_customer_name":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=420)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Fixed Cost Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=clean_for_visuals(df_curr_decomp),
        selected_metric_col="fixed_cost",
        revenue_col="revenue",
        title_prefix="Fixed Cost",
        color_scale=BS,
        percent_label="Fixed Cost % Rev",
        selector_key="fc_sl_selector",
        PT=PT,
    )
