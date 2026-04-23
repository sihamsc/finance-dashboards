import streamlit as st
import plotly.express as px

from src.services.finance_service import build_clean_explorer_detail
from src.utils.helpers import waterfall_for_slice
from src.utils.formatters import kpi


def render_explorer(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]
    df_curr = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]

    BS = palette["blue_scale"]
    WFP = palette["wf_pos"]
    WFN = palette["wf_neg"]
    WFT = palette["wf_total"]

    st.markdown('<div class="section-header">Insight Explorer</div>', unsafe_allow_html=True)

    explorer_detail = build_clean_explorer_detail(df_curr, df_lab_curr)

    metric_options = {
        "Revenue": "revenue",
        "COGS": "cogs",
        "Fixed Cost": "fixed_cost",
        "Labor": "labor",
        "Gross Margin": "gross_margin",
        "Contribution": "contribution",
    }
    level_options = {
        "Service Line": "service_line_name",
        "Sub Service Line": "sub_service_line_name",
        "Client": "top_level_parent_customer_name",
    }

    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        explorer_metric_label = st.selectbox("Metric", list(metric_options.keys()), key="explorer_metric")
    with ctrl2:
        explorer_level_label = st.selectbox("View Level", list(level_options.keys()), key="explorer_level")
    with ctrl3:
        explorer_mode = st.radio("Mode", ["Explore", "Compare"], horizontal=True, key="explorer_mode")
    with ctrl4:
        explorer_top_n = st.select_slider("Top N", options=[10, 15, 20, 25, 30, 50], value=15, key="explorer_topn")

    metric_col = metric_options[explorer_metric_label]
    level_col = level_options[explorer_level_label]

    drill1, drill2, drill3, drill4 = st.columns(4)

    with drill1:
        exp_service = st.selectbox(
            "Service Line Drill",
            ["All"] + sorted(explorer_detail["service_line_name"].dropna().unique().tolist()),
            key="explorer_service",
        )

    exp_df = explorer_detail.copy()
    if exp_service != "All":
        exp_df = exp_df[exp_df["service_line_name"] == exp_service]

    with drill2:
        ssl_options = ["All"] + sorted(exp_df["sub_service_line_name"].dropna().unique().tolist())
        exp_ssl = st.selectbox("Sub Service Line Drill", ssl_options, key="explorer_ssl")

    if exp_ssl != "All":
        exp_df = exp_df[exp_df["sub_service_line_name"] == exp_ssl]

    with drill3:
        client_options = ["All"] + sorted(exp_df["top_level_parent_customer_name"].dropna().unique().tolist())
        exp_client = st.selectbox("Client Drill", client_options, key="explorer_client")

    if exp_client != "All":
        exp_df = exp_df[exp_df["top_level_parent_customer_name"] == exp_client]

    with drill4:
        search_text = st.text_input("Search", value="", key="explorer_search")

    if search_text.strip():
        txt = search_text.strip().lower()
        mask = (
            exp_df["service_line_name"].str.lower().str.contains(txt, na=False) |
            exp_df["sub_service_line_name"].str.lower().str.contains(txt, na=False) |
            exp_df["top_level_parent_customer_name"].str.lower().str.contains(txt, na=False)
        )
        exp_df = exp_df[mask]

    grouped = (
        exp_df.groupby(level_col)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            labor=("labor", "sum"),
            gross_margin=("gross_margin", "sum"),
            contribution=("contribution", "sum"),
        )
        .reset_index()
    )

    grouped["gm_pct"] = (grouped["gross_margin"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["cm_pct"] = (grouped["contribution"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["cogs_pct"] = (grouped["cogs"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["fixed_cost_pct"] = (grouped["fixed_cost"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)
    grouped["labor_pct"] = (grouped["labor"] / grouped["revenue"].replace(0, float("nan")) * 100).round(1)

    ratio_map = {
        "revenue": None,
        "cogs": "cogs_pct",
        "fixed_cost": "fixed_cost_pct",
        "labor": "labor_pct",
        "gross_margin": "gm_pct",
        "contribution": "cm_pct",
    }
    ratio_col = ratio_map[metric_col]

    chart_df = grouped.sort_values(metric_col, ascending=False).head(explorer_top_n).copy()

    main_col, side_col = st.columns([3, 2])

    with main_col:
        main_fig = px.bar(
            chart_df.sort_values(metric_col, ascending=True),
            x=metric_col,
            y=level_col,
            orientation="h",
            color=metric_col,
            color_continuous_scale=BS,
            text=chart_df.sort_values(metric_col, ascending=True)[ratio_col].map(lambda x: "" if str(x) == "nan" else f"{x:.1f}%") if ratio_col else None,
            title=f"{explorer_metric_label} by {explorer_level_label}",
            labels={metric_col: f"{explorer_metric_label} ($)", level_col: ""},
        )
        if ratio_col:
            main_fig.update_traces(textposition="outside")
        main_fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=520)
        main_fig.update_xaxes(tickformat="$,.0s")
        st.plotly_chart(main_fig, use_container_width=True)

    selected_entity = None
    selected_row = None

    with side_col:
        if explorer_mode == "Explore":
            entity_options = chart_df[level_col].tolist() if not chart_df.empty else []
            if entity_options:
                selected_entity = st.selectbox("Selected Slice", entity_options, key="explorer_entity")
                selected_row = grouped[grouped[level_col] == selected_entity].iloc[0]
                cards = st.columns(2)
                cards[0].markdown(kpi(explorer_metric_label, selected_row[metric_col]), unsafe_allow_html=True)
                cards[1].markdown(kpi("Revenue", selected_row["revenue"]), unsafe_allow_html=True)
                cards[0].markdown(kpi("GM %", selected_row["gm_pct"], kind="pct"), unsafe_allow_html=True)
                cards[1].markdown(kpi("CM %", selected_row["cm_pct"], kind="pct"), unsafe_allow_html=True)
            else:
                st.info("No data for current explorer selection.")
        else:
            entity_options = grouped[level_col].tolist()
            if len(entity_options) >= 2:
                cmp_a = st.selectbox("Compare A", entity_options, key="explorer_cmp_a")
                cmp_b = st.selectbox("Compare B", [x for x in entity_options if x != cmp_a], key="explorer_cmp_b")
                row_a = grouped[grouped[level_col] == cmp_a].iloc[0]
                row_b = grouped[grouped[level_col] == cmp_b].iloc[0]
                a, b = st.columns(2)
                a.markdown(kpi(cmp_a[:18], row_a[metric_col]), unsafe_allow_html=True)
                b.markdown(kpi(cmp_b[:18], row_b[metric_col]), unsafe_allow_html=True)
                a.markdown(kpi("GM %", row_a["gm_pct"], kind="pct"), unsafe_allow_html=True)
                b.markdown(kpi("GM %", row_b["gm_pct"], kind="pct"), unsafe_allow_html=True)
            else:
                st.info("Need at least two slices to compare.")

    if explorer_mode == "Explore" and selected_entity is not None:
        st.markdown('<div class="section-header">Selected Slice Bridge</div>', unsafe_allow_html=True)
        st.plotly_chart(
            waterfall_for_slice(selected_row, f"{selected_entity} — P&L Bridge", PT, WFP, WFN, WFT),
            use_container_width=True,
        )
