import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m


def render_contribution(ctx):
    palette     = ctx["palette"]
    PT          = ctx["PT"]
    df_curr     = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]
    BS = palette["blue_scale"]
    SC = palette["series"]

    st.markdown('<div class="section-header">Contribution Analysis</div>', unsafe_allow_html=True)

    # Build client data
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
    cl_gm["labor_pct"]    = (cl_gm["labor"]/cl_gm["revenue"].replace(0,float("nan"))*100).round(1)
    cl_gm = cl_gm[cl_gm["revenue"]>0].sort_values("revenue",ascending=False)

    # ── Row 1: Bubble + CM% by SL ────────────────────────────
    bubble_col, side_col = st.columns([3,2])

    with bubble_col:
        top_n_cm = st.select_slider("Show top N clients by revenue",
                                    options=[5,10,15,20,25,30], value=15, key="contrib_topn")
        cl_plot  = cl_gm.head(top_n_cm).copy()
        cl_plot["_size"] = cl_plot["contribution"].clip(lower=0)

        med_rev   = cl_plot["revenue"].median()
        med_cm_pct= cl_plot["cm_pct"].median()

        fig = px.scatter(
            cl_plot, x="revenue", y="cm_pct",
            size="_size", size_max=55,
            color="cm_pct", color_continuous_scale=BS,
            hover_name="top_level_parent_customer_name",
            hover_data={"revenue":":,.0f","gm_pct":":.1f","cm_pct":":.1f",
                        "gross_margin":":,.0f","labor":":,.0f","contribution":":,.0f","_size":False},
            title=f"Client Contribution — Top {top_n_cm} by Revenue",
            labels={"revenue":"Revenue ($)","cm_pct":"Contribution %","_size":""},
        )

        # Quadrant lines + labels
        fig.add_vline(x=med_rev, line_width=1, line_dash="dot", line_color="#2a3045")
        fig.add_hline(y=med_cm_pct, line_width=1, line_dash="dot", line_color="#2a3045")
        x_max = cl_plot["revenue"].max()
        y_max = cl_plot["cm_pct"].max()
        y_min = cl_plot["cm_pct"].min()
        for text, x, y, color in [
            ("Stars", x_max*0.95, y_max*0.95, "#4ade80"),
            ("Grow",  med_rev*0.05, y_max*0.95, "#60a5fa"),
            ("Volume",x_max*0.95, y_min+(med_cm_pct-y_min)*0.1, "#fb923c"),
            ("Review",med_rev*0.05, y_min+(med_cm_pct-y_min)*0.1, "#f87171"),
        ]:
            fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                               font=dict(size=9, color=color, family="DM Mono"),
                               xanchor="center")

        # GM% annotation left of each bubble
        for _, row in cl_plot.iterrows():
            fig.add_annotation(
                x=row["revenue"], y=row["cm_pct"],
                text=f"GM {row['gm_pct']:.0f}%",
                showarrow=False, xanchor="right", xshift=-10,
                font=dict(size=8, color="#6b7280", family="DM Mono"),
            )

        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        cm_sl = clean_for_visuals(df_curr).groupby("service_line_name").agg(
            revenue=("revenue","sum"),gm=("gross_margin","sum")).reset_index()
        lab_sl = (clean_for_visuals(df_lab_curr).groupby("service_line_name")["labour_cost"]
                  .sum().reset_index().rename(columns={"labour_cost":"labor"}))
        cm_sl  = cm_sl.merge(lab_sl, on="service_line_name", how="left")
        cm_sl["labor"]        = cm_sl["labor"].fillna(0)
        cm_sl["contribution"] = cm_sl["gm"] - cm_sl["labor"]
        cm_sl["cm_pct"]       = (cm_sl["contribution"]/cm_sl["revenue"].replace(0,float("nan"))*100).round(1)
        cm_sl = cm_sl[cm_sl["revenue"]>0].sort_values("cm_pct",ascending=True)
        fig2 = px.bar(cm_sl, x="cm_pct", y="service_line_name", orientation="h",
                      color="cm_pct", color_continuous_scale=BS,
                      title="Contribution % by Service Line",
                      labels={"cm_pct":"Contribution %","service_line_name":""})
        fig2.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        st.plotly_chart(fig2, use_container_width=True)

    # ── CM% vs GM% scatter — labor intensity ─────────────────
    st.markdown('<div class="section-header">CM% vs GM% — Labor Intensity View</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-family:DM Mono,monospace;font-size:9px;color:#4a5570;margin-bottom:0.6rem;">'
        'Gap between dot and the 45° line = labor as % of revenue. '
        'Clients far below the line are labor-intensive.</p>',
        unsafe_allow_html=True,
    )
    scatter_df = cl_gm.copy()
    fig_s = px.scatter(
        scatter_df, x="gm_pct", y="cm_pct",
        size="revenue", size_max=40,
        color="labor_pct", color_continuous_scale=["#4ade80","#fb923c","#f87171"],
        range_color=[0, scatter_df["labor_pct"].quantile(0.9)],
        hover_name="top_level_parent_customer_name",
        hover_data={"gm_pct":":.1f","cm_pct":":.1f","labor_pct":":.1f","revenue":":,.0f"},
        title="CM% vs GM% — colour = Labor % of Revenue",
        labels={"gm_pct":"Gross Margin %","cm_pct":"Contribution %","labor_pct":"Labor % Rev"},
    )
    # 45° reference line
    min_v = min(scatter_df["gm_pct"].min(), scatter_df["cm_pct"].min())
    max_v = max(scatter_df["gm_pct"].max(), scatter_df["cm_pct"].max())
    fig_s.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
                    line=dict(color="#2a3045",width=1,dash="dot"))
    fig_s.add_annotation(x=(min_v+max_v)/2, y=(min_v+max_v)/2+3,
                         text="GM% = CM% (zero labor)", showarrow=False,
                         font=dict(size=8,color="#2a3045",family="DM Mono"))
    fig_s.update_layout(**PT, title_font_color="#cbd5e1", height=480)
    fig_s.update_xaxes(ticksuffix="%"); fig_s.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_s, use_container_width=True)

    # ── Contribution bridge by service line ───────────────────
    st.markdown('<div class="section-header">Contribution Bridge — GM to CM by Service Line</div>', unsafe_allow_html=True)
    bridge_df = cm_sl.copy().sort_values("contribution", ascending=False)
    fig_br = go.Figure()
    for _, row in bridge_df.iterrows():
        sl = row["service_line_name"]
        gm_v  = row["gm"]
        lab_v = row["labor"]
        cm_v  = row["contribution"]
        fig_br.add_trace(go.Bar(
            name=sl,
            x=[sl, sl, sl],
            y=[gm_v, -lab_v, cm_v],
            # grouped trick — use waterfall instead
        ))

    # Use a proper waterfall per SL displayed as grouped bars
    sls = bridge_df["service_line_name"].tolist()
    fig_br2 = go.Figure()
    colours_pos = [SC[i % len(SC)] for i in range(len(sls))]
    for i, row in bridge_df.iterrows():
        sl = row["service_line_name"]
        fig_br2.add_trace(go.Bar(
            name=sl,
            x=["Gross Margin","Labor","Contribution"],
            y=[row["gm"], row["labor"], row["contribution"]],
            marker_color=[colours_pos[list(bridge_df["service_line_name"]).index(sl)]]*3,
            marker_line_width=0,
            showlegend=True,
        ))
    fig_br2.update_layout(**PT, barmode="group",
                          title="GM → Labor → Contribution by Service Line",
                          title_font_color="#cbd5e1",
                          legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#cbd5e1",size=9)),
                          height=380)
    fig_br2.update_yaxes(tickformat="$,.0s")
    st.plotly_chart(fig_br2, use_container_width=True)

    # ── Client detail table ───────────────────────────────────
    st.markdown('<div class="section-header">Client Contribution Detail ($M)</div>', unsafe_allow_html=True)
    cm_tbl = cl_gm.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        cm_tbl[c] = (cm_tbl[c]/1e6).round(2)
    cm_tbl = cm_tbl.sort_values("cm_pct", ascending=False)
    cm_tbl.columns = [c.replace("_"," ").title() for c in cm_tbl.columns]
    st.dataframe(cm_tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":         st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",        format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":       st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":       st.column_config.NumberColumn("CM %",              format="%.1f%%"),
        "Labor Pct":    st.column_config.NumberColumn("Labor % Rev",       format="%.1f%%"),
    })
    st.download_button("Download CSV", cm_tbl.to_csv(index=False).encode(),
                       "contribution_detail.csv","text/csv",key="cm_dl")
