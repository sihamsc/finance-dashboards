import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import clean_for_visuals


def render_margin(ctx):
    palette     = ctx["palette"]
    PT          = ctx["PT"]
    df_curr     = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]
    BS = palette["blue_scale"]
    LC = palette["line_current"]

    st.markdown('<div class="section-header">Gross Margin Analysis</div>', unsafe_allow_html=True)

    # Build client data with attributed labor
    lab_cl = (df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
              .sum().reset_index().rename(columns={"labour_cost":"labor"}))
    cl_gm = (clean_for_visuals(df_curr)
             .groupby("top_level_parent_customer_name")
             .agg(revenue=("revenue","sum"),cogs=("cogs","sum"),
                  fixed_cost=("fixed_cost","sum"),gross_margin=("gross_margin","sum"))
             .reset_index())
    cl_gm = cl_gm.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl_gm["labor"]        = cl_gm["labor"].fillna(0)
    cl_gm["contribution"] = cl_gm["gross_margin"] - cl_gm["labor"]
    cl_gm["gm_pct"]       = (cl_gm["gross_margin"]/cl_gm["revenue"].replace(0,float("nan"))*100).round(1)
    cl_gm["cm_pct"]       = (cl_gm["contribution"]/cl_gm["revenue"].replace(0,float("nan"))*100).round(1)
    cl_gm = cl_gm[cl_gm["revenue"]>0].sort_values("revenue",ascending=False)

    # ── Row 1: Bubble + SL bar ────────────────────────────────
    bubble_col, side_col = st.columns([3,2])

    with bubble_col:
        top_n    = st.select_slider("Show top N clients by revenue",
                                    options=[5,10,15,20,25,30], value=15, key="margin_topn")
        cl_plot  = cl_gm.head(top_n).copy()
        cl_plot["_size"] = cl_plot["gross_margin"].clip(lower=0)

        # Quadrant reference values
        med_rev    = cl_plot["revenue"].median()
        med_gm_pct = cl_plot["gm_pct"].median()

        fig = px.scatter(
            cl_plot, x="revenue", y="gm_pct",
            size="_size", size_max=55,
            color="gm_pct", color_continuous_scale=BS,
            hover_name="top_level_parent_customer_name",
            hover_data={"revenue":":,.0f","gm_pct":":.1f","cm_pct":":.1f",
                        "gross_margin":":,.0f","labor":":,.0f","contribution":":,.0f","_size":False},
            title=f"Client GM% vs Revenue — Top {top_n}",
            labels={"revenue":"Revenue ($)","gm_pct":"Gross Margin %","_size":""},
        )

        # Quadrant reference lines
        fig.add_vline(x=med_rev, line_width=1, line_dash="dot", line_color="#2a3045")
        fig.add_hline(y=med_gm_pct, line_width=1, line_dash="dot", line_color="#2a3045")

        # Quadrant labels
        x_max = cl_plot["revenue"].max()
        y_max = cl_plot["gm_pct"].max()
        y_min = cl_plot["gm_pct"].min()
        for text, x, y, color in [
            ("Stars", x_max*0.95, y_max*0.95, "#4ade80"),
            ("Grow",  med_rev*0.05, y_max*0.95, "#60a5fa"),
            ("Volume",x_max*0.95, y_min+(med_gm_pct-y_min)*0.1, "#fb923c"),
            ("Review",med_rev*0.05, y_min+(med_gm_pct-y_min)*0.1, "#f87171"),
        ]:
            fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                               font=dict(size=9, color=color, family="DM Mono"),
                               xanchor="center")

        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        gm_sl = (clean_for_visuals(df_curr)
                 .groupby("service_line_name")
                 .agg(revenue=("revenue","sum"),gm=("gross_margin","sum"))
                 .reset_index())
        gm_sl["gm_pct"] = (gm_sl["gm"]/gm_sl["revenue"].replace(0,float("nan"))*100).round(1)
        gm_sl = gm_sl[gm_sl["revenue"]>0].sort_values("gm_pct",ascending=True)
        fig2 = px.bar(gm_sl, x="gm_pct", y="service_line_name", orientation="h",
                      color="gm_pct", color_continuous_scale=BS,
                      title="GM % by Service Line",
                      labels={"gm_pct":"Gross Margin %","service_line_name":""})
        fig2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        st.plotly_chart(fig2, use_container_width=True)

    # ── GM% monthly trend by service line ────────────────────
    st.markdown('<div class="section-header">GM % Monthly Trend by Service Line</div>', unsafe_allow_html=True)
    mth_sl = (clean_for_visuals(df_curr)
              .groupby(["accounting_period_start_date","service_line_name"])
              .agg(revenue=("revenue","sum"),gm=("gross_margin","sum"))
              .reset_index().sort_values("accounting_period_start_date"))
    mth_sl["gm_pct"] = (mth_sl["gm"]/mth_sl["revenue"].replace(0,float("nan"))*100).round(1)
    fig_t = px.line(mth_sl, x="accounting_period_start_date", y="gm_pct",
                    color="service_line_name", color_discrete_sequence=BS,
                    markers=True,
                    title="GM % Trend — Monthly by Service Line",
                    labels={"accounting_period_start_date":"","gm_pct":"GM %","service_line_name":""})
    fig_t.update_traces(line_width=2)
    fig_t.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
    fig_t.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_t, use_container_width=True)

    # ── Client detail table ───────────────────────────────────
    st.markdown('<div class="section-header">Client Gross Margin Detail ($M)</div>', unsafe_allow_html=True)
    gm_tbl = cl_gm.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        gm_tbl[c] = (gm_tbl[c]/1e6).round(2)
    gm_tbl = gm_tbl.sort_values("gm_pct", ascending=False)
    gm_tbl.columns = [c.replace("_"," ").title() for c in gm_tbl.columns]
    st.dataframe(gm_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":         st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",        format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":       st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":       st.column_config.NumberColumn("CM %",              format="%.1f%%"),
    })
    st.download_button("Download CSV", gm_tbl.to_csv(index=False).encode(),
                       "margin_detail.csv", "text/csv", key="margin_dl")
