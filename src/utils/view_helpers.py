"""
Reusable UI building-blocks for the per-metric detail tabs.

inline_trend   — Bar/Tile distribution + inline Raw/Index trend toggle.
                 Used by Revenue, COGS, Fixed Cost, Labor, and Profitability
                 so every tab has an identical section structure.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.charts import build_index_rows, build_yoy_trend_df, render_treemap, render_index_chart
from src.utils.filters import MONTH_MAP


def inline_trend(
    ctx,
    curr_df,
    prior_df,
    value_col,
    accent,
    pt,
    key_prefix,
    y_label=None,
    height=300,
):
    """Render a Raw / Index trend toggle directly under a distribution chart.

    Parameters
    ----------
    ctx         : the shared context dict (needs is_rolling, curr_ym, etc.)
    curr_df     : row-level current-period dataframe (already filtered/sliced)
    prior_df    : row-level prior-year dataframe
    value_col   : column to aggregate (e.g. "revenue", "cogs", "labour_cost")
    accent      : hex color for the current-year line
    pt          : base Plotly layout dict
    key_prefix  : unique string prefix for Streamlit widget keys
    y_label     : axis label override (defaults to "{value_col} ($M)")
    height      : chart height in pixels
    """
    lp = "#475569"   # slate-600 — consistent muted prior-year color across all tabs
    y_label = y_label or f"{value_col.replace('_', ' ').title()} ($M)"

    trend_mode = st.radio(
        "View",
        ["Raw", "Index (100 = PY)"],
        horizontal=True,
        key=f"{key_prefix}_trend_mode",
    )

    if trend_mode == "Raw":
        yoy_df, month_order = build_yoy_trend_df(ctx, curr_df, prior_df, value_col)
        m_col = f"{value_col}_m"
        fig = px.line(
            yoy_df,
            x="month",
            y=m_col,
            color="Period",
            markers=True,
            color_discrete_map={"Current": accent, "Prior Year": lp},
            labels={"month": "", m_col: y_label},
            category_orders={"month": month_order},
        )
        fig.update_traces(line_width=2.5)
        fig.update_layout(
            **pt,
            height=height,
            xaxis_tickangle=-30,
            legend=dict(
                orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1", size=10),
            ),
        )
        fig.update_yaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig, use_container_width=True)
    else:
        curr_m  = curr_df.groupby(["yr", "month_num"])[value_col].sum().reset_index()
        prior_m = prior_df.groupby(["yr", "month_num"])[value_col].sum().reset_index()
        idx_df  = pd.DataFrame(build_index_rows(ctx, curr_m, prior_m, value_col))
        render_index_chart(idx_df, "vs Prior Year — 100 = PY", pt)


def dist_chart(df, label_col, value_col, accent, pt, chart_type, key_suffix, value_label=None):
    """Render a distribution chart (Bar or Treemap) for the current period.

    Parameters
    ----------
    chart_type  : "Bar" or "Treemap"
    key_suffix  : unique Streamlit key suffix
    """
    value_label = value_label or value_col.replace("_", " ").title()
    d = df[df[value_col] > 0].copy() if value_col in df.columns else df.copy()

    if d.empty:
        st.info(f"No {value_label.lower()} data available.")
        return

    if chart_type == "Treemap":
        # Reuse charts.render_treemap but we need a color_scale — use a two-stop scale
        # anchored on the accent color so the treemap matches the tab's color identity.
        from src.utils.charts import render_treemap
        # Build a minimal two-stop scale from near-black to accent
        cs = [[0.0, "#07090e"], [1.0, accent]]
        render_treemap(d, label_col, value_col, "", cs, value_label)
    else:
        total = d[value_col].sum()
        d["_pct"] = (d[value_col] / total * 100).round(1) if total else 0
        d["_m"]   = (d[value_col] / 1e6).round(2)
        d = d.sort_values(value_col, ascending=True)
        bar_colors = [accent if v >= 0 else "#f87171" for v in d[value_col]]

        fig = go.Figure(go.Bar(
            x=d["_m"],
            y=d[label_col],
            orientation="h",
            marker_color=bar_colors,
            marker_line_width=0,
            text=d.apply(lambda r: f"${r['_m']:.1f}M  ({r['_pct']:.1f}%)", axis=1),
            textposition="outside",
            textfont=dict(family="DM Sans", size=11, color="#94a3b8"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color="#94a3b8", size=11),
            margin=dict(l=0, r=110, t=20, b=0),
            height=max(240, len(d) * 36 + 50),
            xaxis=dict(tickprefix="$", ticksuffix="M", gridcolor="#141924",
                       linecolor="#1b2230", tickfont=dict(color="#cbd5e1"), zeroline=False),
            yaxis=dict(gridcolor="#141924", linecolor="#1b2230",
                       tickfont=dict(color="#cbd5e1"), zeroline=False),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"dist_{key_suffix}")
