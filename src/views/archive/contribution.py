import plotly.express as px
import streamlit as st

from src.utils.filters import clean_for_visuals

def render_contribution(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]
    BS = palette["blue_scale"]

    st.markdown('<div class="section-header">Contribution Analysis</div>', unsafe_allow_html=True)

    lab_cl = (
        df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    cl_gm = (
        clean_for_visuals(df_curr)
        .groupby("top_level_parent_customer_name")
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )
    cl_gm = cl_gm.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl_gm["labor"] = cl_gm["labor"].fillna(0)
    cl_gm["contribution"] = cl_gm["gross_margin"] - cl_gm["labor"]
    cl_gm["gm_pct"] = (cl_gm["gross_margin"] / cl_gm["revenue"].replace(0, float("nan")) * 100).round(1)
    cl_gm["cm_pct"] = (cl_gm["contribution"] / cl_gm["revenue"].replace(0, float("nan")) * 100).round(1)
    cl_gm = cl_gm[cl_gm["revenue"] > 0].sort_values("revenue", ascending=False)

    bubble_col, side_col = st.columns([3, 2])

    with bubble_col:
        top_n_cm = st.select_slider("Show top N clients by revenue", options=[5, 10, 15, 20, 25, 30], value=15, key="contrib_topn")
        cl_cm_plot = cl_gm.head(top_n_cm)

        fig = px.scatter(
            cl_cm_plot,
            x="revenue",
            y="cm_pct",
            size="contribution",
            size_max=48,
            color="cm_pct",
            color_continuous_scale=BS,
            text="top_level_parent_customer_name",
            hover_name="top_level_parent_customer_name",
            hover_data={
                "revenue": ":,.0f",
                "gm_pct": ":.1f",
                "cm_pct": ":.1f",
                "gross_margin": ":,.0f",
                "labor": ":,.0f",
                "contribution": ":,.0f",
            },
            title=f"Client Contribution — Top {top_n_cm} by Revenue",
            labels={"revenue": "Revenue ($)", "cm_pct": "Contribution %", "contribution": "Contribution"},
        )
        fig.update_traces(textposition="top center", textfont=dict(size=9, color="#cbd5e1"))
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        cm_sl = clean_for_visuals(df_curr).groupby("service_line_name").agg(revenue=("revenue", "sum"), gm=("gross_margin", "sum")).reset_index()
        lab_sl_cm = clean_for_visuals(df_lab_curr).groupby("service_line_name")["labour_cost"].sum().reset_index().rename(columns={"labour_cost": "labor"})
        cm_sl = cm_sl.merge(lab_sl_cm, on="service_line_name", how="left")
        cm_sl["labor"] = cm_sl["labor"].fillna(0)
        cm_sl["contribution"] = cm_sl["gm"] - cm_sl["labor"]
        cm_sl["cm_pct"] = (cm_sl["contribution"] / cm_sl["revenue"].replace(0, float("nan")) * 100).round(1)
        cm_sl = cm_sl[cm_sl["revenue"] > 0].sort_values("cm_pct", ascending=True)

        fig = px.bar(
            cm_sl,
            x="cm_pct",
            y="service_line_name",
            orientation="h",
            color="cm_pct",
            color_continuous_scale=BS,
            title="Contribution % by Service Line",
            labels={"cm_pct": "Contribution %", "service_line_name": ""},
        )
        fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        st.plotly_chart(fig, use_container_width=True)