import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from .formatters import fmt_m, pct_text
from .filters import clean_for_visuals

def service_line_selector_block(
    agg_df,
    selected_metric_col,
    revenue_col,
    title_prefix,
    color_scale,
    percent_label,
    selector_key,
    PT,
):
    d = clean_for_visuals(agg_df, client_col="top_level_parent_customer_name")
    sl_options = sorted(d["service_line_name"].dropna().unique().tolist())
    if not sl_options:
        st.info(f"No {title_prefix.lower()} drilldown available for the current selection.")
        return

    selected_service = st.selectbox(
        f"{title_prefix} drilldown — service line",
        sl_options,
        key=selector_key,
    )

    sub = (
        d[d["service_line_name"] == selected_service]
        .groupby("sub_service_line_name", dropna=False)
        .agg(metric=(selected_metric_col, "sum"), revenue=(revenue_col, "sum"))
        .reset_index()
    )
    sub = sub[sub["sub_service_line_name"] != "(blank)"]
    sub["pct_of_rev"] = (sub["metric"] / sub["revenue"].replace(0, float("nan")) * 100).round(1)
    sub = sub.sort_values("metric", ascending=True)

    fig = px.bar(
        sub,
        x="metric",
        y="sub_service_line_name",
        orientation="h",
        color="metric",
        color_continuous_scale=color_scale,
        text=sub["pct_of_rev"].map(pct_text),
        title=f"{title_prefix} — {selected_service}",
        labels={"metric": f"{title_prefix} ($)", "sub_service_line_name": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**PT, coloraxis_showscale=False, title_font_color="#cbd5e1", height=360)
    fig.update_xaxes(tickformat="$,.0s")
    st.plotly_chart(fig, use_container_width=True)

    sub_display = sub.copy()
    sub_display["metric"] = (sub_display["metric"] / 1e6).round(2)
    sub_display["revenue"] = (sub_display["revenue"] / 1e6).round(2)

    metric_col_name = f"{title_prefix} ($M)"
    revenue_col_name = "Revenue ($M)"
    if title_prefix == "Revenue":
        revenue_col_name = "Total Revenue ($M)"

    sub_display = sub_display.rename(columns={
        "sub_service_line_name": "Sub Service Line",
        "metric": metric_col_name,
        "revenue": revenue_col_name,
        "pct_of_rev": percent_label,
    })

    st.dataframe(
        sub_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            metric_col_name: st.column_config.NumberColumn(metric_col_name, format="$%.2f"),
            revenue_col_name: st.column_config.NumberColumn(revenue_col_name, format="$%.2f"),
            percent_label: st.column_config.NumberColumn(percent_label, format="%.1f%%"),
        },
    )


def waterfall_for_slice(row, title, PT, WFP, WFN, WFT):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total", "relative", "total"],
        x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labor", "Contribution"],
        y=[row["revenue"], -row["cogs"], -row["fixed_cost"], None, -row["labor"], None],
        connector={"line": {"color": "#243041"}},
        increasing={"marker": {"color": WFP, "line": {"width": 0}}},
        decreasing={"marker": {"color": WFN, "line": {"width": 0}}},
        totals={"marker": {"color": WFT, "line": {"width": 0}}},
        text=[
            fmt_m(row["revenue"]),
            fmt_m(row["cogs"]),
            fmt_m(row["fixed_cost"]),
            fmt_m(row["gross_margin"]),
            fmt_m(row["labor"]),
            fmt_m(row["contribution"]),
        ],
        textposition="outside",
    ))
    fig.update_layout(**PT, title=title, title_font_color="#cbd5e1", showlegend=False, height=420)
    return fig