import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import clean_for_visuals, rank_window_options, rank_window_slice, EXCL
from src.utils.formatters import fmt_m, safe_pct
from src.utils.helpers import service_line_selector_block


def render_revenue(ctx):
    palette       = ctx["palette"]
    PT            = ctx["PT"]
    df_curr       = ctx["df_curr"]
    df_curr_decomp= ctx["df_curr_decomp"]
    df_prior      = ctx["df_prior"]
    df_lab_curr   = ctx["df_lab_curr"]

    SC = palette["series"]
    BS = palette["blue_scale"]
    WFP= palette["wf_pos"]
    WFN= palette["wf_neg"]
    WFT= palette["wf_total"]

    st.markdown('<div class="section-header">Revenue Decomposition</div>', unsafe_allow_html=True)

    # ── Row 1: SL bar + Revenue Mix donut ────────────────────
    col_rsl, col_mix = st.columns(2)

    with col_rsl:
        rv_sl = (clean_for_visuals(df_curr_decomp)
                 .groupby("service_line_name")["revenue"].sum().reset_index())
        rv_sl = rv_sl[rv_sl["revenue"] > 0].sort_values("revenue", ascending=True)
        fig = px.bar(rv_sl, x="revenue", y="service_line_name", orientation="h",
                     color="service_line_name", color_discrete_sequence=SC,
                     title="Revenue by Service Line",
                     labels={"revenue":"Revenue ($)","service_line_name":""})
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**PT, showlegend=False, title_font_color="#cbd5e1", height=420)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with col_mix:
        # Revenue mix donut — % share by SL
        mix_df = rv_sl.copy()
        mix_df["pct"] = (mix_df["revenue"] / mix_df["revenue"].sum() * 100).round(1)
        fig_mix = px.pie(mix_df, names="service_line_name", values="revenue",
                         hole=0.6, title="Revenue Mix — Service Line Share",
                         color_discrete_sequence=SC)
        fig_mix.update_traces(textinfo="label+percent", textfont=dict(size=10, color="#cbd5e1"))
        fig_mix.update_layout(**PT, title_font_color="#cbd5e1", showlegend=False, height=420)
        st.plotly_chart(fig_mix, use_container_width=True)

    # ── YoY Revenue bridge by service line ───────────────────
    st.markdown('<div class="section-header">Revenue Movement vs Prior Year — by Service Line</div>', unsafe_allow_html=True)

    curr_sl  = (clean_for_visuals(df_curr_decomp)
                .groupby("service_line_name")["revenue"].sum().reset_index().rename(columns={"revenue":"curr"}))
    prior_sl = (clean_for_visuals(df_prior)
                .groupby("service_line_name")["revenue"].sum().reset_index().rename(columns={"revenue":"prior"}))
    bridge = curr_sl.merge(prior_sl, on="service_line_name", how="outer").fillna(0)
    bridge["delta"] = bridge["curr"] - bridge["prior"]
    bridge = bridge[bridge["service_line_name"].ne("(blank)")].sort_values("delta", ascending=True)

    colours = ["#f87171" if d < 0 else "#4ade80" for d in bridge["delta"]]
    fig_bridge = go.Figure(go.Bar(
        x=bridge["delta"], y=bridge["service_line_name"],
        orientation="h",
        marker_color=colours, marker_line_width=0,
        text=bridge["delta"].map(lambda v: f"{'+' if v>=0 else ''}{fmt_m(v)}"),
        textposition="outside",
    ))
    fig_bridge.update_layout(**PT, title="Revenue YoY Change by Service Line",
                             title_font_color="#cbd5e1", height=350)
    fig_bridge.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig_bridge, use_container_width=True)

    # ── Row 2: Client bar + concentration ────────────────────
    st.markdown('<div class="section-header">Revenue by Client</div>', unsafe_allow_html=True)

    rv_cl = (clean_for_visuals(df_curr)
             .groupby("top_level_parent_customer_name")["revenue"].sum().reset_index()
             .sort_values("revenue", ascending=False))

    # Concentration stats
    total_rev = rv_cl["revenue"].sum()
    top5_pct  = safe_pct(rv_cl.head(5)["revenue"].sum(), total_rev)
    top10_pct = safe_pct(rv_cl.head(10)["revenue"].sum(), total_rev)
    n_clients = len(rv_cl)

    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.8rem;">'
        f'CONCENTRATION — '
        f'Top 5 clients = <span style="color:#cbd5e1">{top5_pct:.0f}%</span> of revenue &nbsp;|&nbsp; '
        f'Top 10 = <span style="color:#cbd5e1">{top10_pct:.0f}%</span> &nbsp;|&nbsp; '
        f'Total clients: <span style="color:#cbd5e1">{n_clients}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Toggle: Top 15 / Top 30 / All
    client_view = st.radio("Client view", ["Top 15","Top 30","All"], horizontal=True, key="rev_client_view")
    n_show = {"Top 15":15,"Top 30":30,"All":len(rv_cl)}[client_view]
    rv_cl_show = rv_cl.head(n_show).sort_values("revenue", ascending=True)

    fig_cl = px.bar(rv_cl_show, x="revenue", y="top_level_parent_customer_name", orientation="h",
                    color="revenue", color_continuous_scale=BS,
                    title=f"Revenue by Client — {client_view}",
                    labels={"revenue":"Revenue ($)","top_level_parent_customer_name":""})
    fig_cl.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1",
                         height=max(420, n_show * 28))
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig_cl, use_container_width=True)

    # ── Sub-SL drilldown ─────────────────────────────────────
    st.markdown('<div class="section-header">Revenue Drilldown — Sub Service Lines</div>', unsafe_allow_html=True)
    service_line_selector_block(
        agg_df=clean_for_visuals(df_curr_decomp),
        selected_metric_col="revenue",
        revenue_col="revenue",
        title_prefix="Revenue",
        color_scale=BS,
        percent_label="Share of Revenue",
        selector_key="rev_sl_selector",
        PT=PT,
    )

    # ── Detail table ─────────────────────────────────────────
    st.markdown('<div class="section-header">Revenue Detail — Service Line × Sub Service Line ($M)</div>', unsafe_allow_html=True)
    lab_join = (df_lab_curr.groupby(["service_line_name","sub_service_line_name"])["labour_cost"]
                .sum().reset_index().rename(columns={"labour_cost":"labor"}))
    rv_tbl = (df_curr.groupby(["service_line_name","sub_service_line_name"],dropna=False)
              .agg(revenue=("revenue","sum"),cogs=("cogs","sum"),
                   fixed_cost=("fixed_cost","sum"),gross_margin=("gross_margin","sum"),
                   clients=("top_level_parent_customer_name",lambda s:s[~s.isin(EXCL)].nunique()))
              .reset_index())
    rv_tbl = rv_tbl.merge(lab_join, on=["service_line_name","sub_service_line_name"], how="left")
    rv_tbl["labor"]        = rv_tbl["labor"].fillna(0)
    rv_tbl["contribution"] = rv_tbl["gross_margin"] - rv_tbl["labor"]
    rv_tbl["gm_pct"]       = (rv_tbl["gross_margin"]/rv_tbl["revenue"].replace(0,float("nan"))*100).round(1)
    rv_tbl["cm_pct"]       = (rv_tbl["contribution"]/rv_tbl["revenue"].replace(0,float("nan"))*100).round(1)
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        rv_tbl[c] = (rv_tbl[c]/1e6).round(2)
    rv_tbl = rv_tbl.sort_values(["service_line_name","revenue"],ascending=[True,False])
    rv_tbl.columns = [c.replace("_"," ").title() for c in rv_tbl.columns]
    st.dataframe(rv_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":         st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",        format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":       st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":       st.column_config.NumberColumn("CM %",              format="%.1f%%"),
        "Clients":      st.column_config.NumberColumn("Clients",           format="%d"),
    })
    # Download
    st.download_button("Download CSV", rv_tbl.to_csv(index=False).encode(),
                       "revenue_detail.csv", "text/csv", key="rev_dl")
