import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m

def render_overview(ctx):
    palette = ctx["palette"]
    PT = ctx["PT"]

    rev = ctx["rev"]
    cogs = ctx["cogs"]
    fixed_cost = ctx["fixed_cost"]
    labor = ctx["labor"]
    gm = ctx["gm"]
    contrib = ctx["contrib"]

    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]
    is_rolling = ctx["is_rolling"]
    curr_ym = ctx["curr_ym"]
    prior_ym = ctx["prior_ym"]
    m_from = ctx["m_from"]
    m_to = ctx["m_to"]

    LC = palette["line_current"]
    LP = palette["line_prior"]
    WFP = palette["wf_pos"]
    WFN = palette["wf_neg"]
    WFT = palette["wf_total"]

    col_wf, col_yoy = st.columns(2)

    with col_wf:
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total", "relative", "total"],
            x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labor", "Contribution"],
            y=[rev, -cogs, -fixed_cost, None, -labor, None],
            connector={"line": {"color": "#243041"}},
            increasing={"marker": {"color": WFP, "line": {"width": 0}}},
            decreasing={"marker": {"color": WFN, "line": {"width": 0}}},
            totals={"marker": {"color": WFT, "line": {"width": 0}}},
            text=[fmt_m(rev), fmt_m(cogs), fmt_m(fixed_cost), fmt_m(gm), fmt_m(labor), fmt_m(contrib)],
            textfont={"color": "#cbd5e1", "size": 10, "family": "DM Mono"},
            textposition="outside",
        ))
        wf.update_layout(**PT, title="P&L Bridge — Revenue to Contribution", title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(wf, use_container_width=True)

    with col_yoy:
        if is_rolling:
            month_labels = ordered_month_axis_labels(curr_ym)

            curr_monthly = df_curr.groupby(["yr", "month_num"])["revenue"].sum().reset_index()
            prior_monthly = df_prior.groupby(["yr", "month_num"])["revenue"].sum().reset_index()

            rows = []
            for i, (yr, mn) in enumerate(curr_ym):
                val = curr_monthly.loc[
                    (curr_monthly["yr"] == yr) & (curr_monthly["month_num"] == mn),
                    "revenue"
                ]
                rows.append({"order": i, "label": month_labels[i], "Revenue": float(val.iloc[0]) if len(val) else 0, "Period": "Current"})

            for i, (yr, mn) in enumerate(prior_ym):
                val = prior_monthly.loc[
                    (prior_monthly["yr"] == yr) & (prior_monthly["month_num"] == mn),
                    "revenue"
                ]
                rows.append({"order": i, "label": month_labels[i], "Revenue": float(val.iloc[0]) if len(val) else 0, "Period": "Prior Year"})

            yoy_df = pd.DataFrame(rows)
            x_col = "label"
            x_order = month_labels
        else:
            months_in_range = list(range(m_from, m_to + 1))
            cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Current"})
            py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Prior Year"})
            base = pd.DataFrame({"month_num": months_in_range})
            yoy_raw = base.merge(cy, on="month_num", how="left").merge(py, on="month_num", how="left").fillna(0)
            yoy_raw["label"] = yoy_raw["month_num"].map(MONTH_MAP)
            yoy_df = yoy_raw.melt(
                id_vars=["month_num", "label"],
                value_vars=["Current", "Prior Year"],
                var_name="Period",
                value_name="Revenue",
            )
            x_col = "label"
            x_order = [MONTH_MAP[m] for m in months_in_range]

        fig = px.line(
            yoy_df,
            x=x_col,
            y="Revenue",
            color="Period",
            markers=True,
            color_discrete_map={"Current": LC, "Prior Year": LP},
            title="Revenue vs Prior Year",
            labels={x_col: "", "Revenue": "Revenue ($)"},
            category_orders={x_col: x_order},
        )
        fig.update_traces(line_width=2.5)
        fig.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig.update_yaxes(tickformat="$,.0f")
        st.plotly_chart(fig, use_container_width=True)