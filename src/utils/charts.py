import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.filters import MONTH_MAP, ordered_month_axis_labels


def render_treemap(df, label_col, value_col, title, color_scale, value_label, key=None):
    """Render a Plotly treemap of value_col broken down by label_col.

    Rows where value_col <= 0 are excluded so the treemap only shows
    positive contributions. Hover shows both $M value and % of total.
    """
    d = df[df[value_col] > 0].copy()

    if d.empty:
        st.info(f"No {value_label.lower()} data available.")
        return

    total = d[value_col].sum()
    d["_pct_total"] = (d[value_col] / total * 100).round(1)
    d["_value_m"] = (d[value_col] / 1e6).round(2)

    fig = go.Figure(go.Treemap(
        labels=d[label_col].tolist() + ["Total"],
        parents=["Total"] * len(d) + [""],
        values=d[value_col].tolist() + [total],
        customdata=list(zip(d["_value_m"], d["_pct_total"])),
        hovertemplate=(
            "<b>%{label}</b><br>"
            f"{value_label}: $%{{customdata[0]:.2f}}M<br>"
            "%{customdata[1]:.1f}% of total"
            "<extra></extra>"
        ),
        texttemplate="<b>%{label}</b><br>$%{customdata[0]:.1f}M<br>%{customdata[1]:.1f}%",
        textfont=dict(family="DM Sans", size=12, color="#f0f2f8"),
        marker=dict(
            colors=d[value_col].tolist() + [total],
            colorscale=color_scale,
            showscale=False,
            line=dict(width=2, color="#07090e"),
        ),
        root_color="rgba(0,0,0,0)",
        branchvalues="total",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#94a3b8", size=11),
        title=title,
        title_font_color="#cbd5e1",
        margin=dict(l=0, r=0, t=40, b=0),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_bar(df, label_col, value_col, title, color_scale, value_label, key=None):
    """Render a horizontal bar chart of value_col broken down by label_col.

    Positive bars use the theme accent colour; negative bars use red.
    """
    d = df.copy()

    if d.empty:
        st.info(f"No {value_label.lower()} data available.")
        return

    total = d[value_col].sum()
    d["_pct_total"] = (d[value_col] / total * 100).round(1) if total else 0
    d["_value_m"] = (d[value_col] / 1e6).round(2)
    d = d.sort_values(value_col, ascending=True)

    accent = color_scale[-1] if color_scale else "#7aa2f7"
    bar_colors = [accent if v >= 0 else "#f87171" for v in d[value_col]]

    fig = go.Figure(go.Bar(
        x=d["_value_m"],
        y=d[label_col],
        orientation="h",
        marker_color=bar_colors,
        marker_line_width=0,
        text=d.apply(lambda r: f"${r['_value_m']:.1f}M  ({r['_pct_total']:.1f}%)", axis=1),
        textposition="outside",
        textfont=dict(family="DM Sans", size=11, color="#94a3b8"),
        customdata=list(zip(d["_value_m"], d["_pct_total"])),
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"{value_label}: $%{{customdata[0]:.2f}}M<br>"
            "%{customdata[1]:.1f}% of total"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#94a3b8", size=11),
        title=title,
        title_font_color="#cbd5e1",
        margin=dict(l=0, r=100, t=40, b=0),
        height=max(280, len(d) * 36 + 60),
        xaxis=dict(
            tickprefix="$",
            ticksuffix="M",
            gridcolor="#141924",
            linecolor="#1b2230",
            tickcolor="#1b2230",
            tickfont=dict(color="#cbd5e1"),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#141924",
            linecolor="#1b2230",
            tickcolor="#1b2230",
            tickfont=dict(color="#cbd5e1"),
            zeroline=False,
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_index_chart(idx_df, title, PT, key=None):
    """Render a line chart of month-over-month index values vs prior year.

    Expects idx_df to have columns: month, index (where 100 = same as PY).
    Y-axis is always anchored at 0 with a 100 reference line.
    """
    fig = px.line(
        idx_df,
        x="month",
        y="index",
        markers=True,
        title=title,
        labels={"month": "", "index": "Index"},
        category_orders={"month": idx_df["month"].tolist()},
        color_discrete_sequence=["#d7f34a"],
    )
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="#94a3b8",
        annotation_text="100 = PY",
        annotation_position="top left",
    )
    fig.update_traces(line_width=2.5)
    fig.update_layout(**PT, title_font_color="#cbd5e1", height=300)
    idx_max = idx_df["index"].max(skipna=True) if idx_df["index"].notna().any() else 150
    fig.update_yaxes(range=[0, max(150, idx_max * 1.15)])
    st.plotly_chart(fig, use_container_width=True, key=key)


def build_index_rows(ctx, curr_monthly, prior_monthly, metric_col):
    """Build monthly PY-index rows. Returns list of dicts for pd.DataFrame()."""
    is_rolling = ctx["is_rolling"]
    m_from = ctx["m_from"]
    m_to = ctx["m_to"]

    rows = []

    if is_rolling:
        for i, ((cy, cm), (py, pm)) in enumerate(zip(ctx["curr_ym"], ctx["prior_ym"])):
            c = _monthly_value(curr_monthly, metric_col, yr=cy, month_num=cm)
            p = _monthly_value(prior_monthly, metric_col, yr=py, month_num=pm)
            rows.append(_index_row(i, MONTH_MAP[cm], c, p))
    else:
        for i, m in enumerate(range(m_from, m_to + 1)):
            c = _monthly_value(curr_monthly, metric_col, month_num=m)
            p = _monthly_value(prior_monthly, metric_col, month_num=m)
            rows.append(_index_row(i, MONTH_MAP[m], c, p))

    return rows


def classify_segment(row, x_col, y_col, med_x, med_y, metric_name):
    """Return a quadrant label for a row based on median splits of x_col and y_col.

    Produces four segments using the provided medians as thresholds:
      "High Rev / High {metric_name}", "Low Rev / High {metric_name}", etc.
    Designed for use via df.apply(lambda row: classify_segment(...), axis=1).
    """
    high_x = row[x_col] >= med_x
    high_y = row[y_col] >= med_y
    if high_x and high_y:
        return f"High Rev / High {metric_name}"
    if not high_x and high_y:
        return f"Low Rev / High {metric_name}"
    if high_x and not high_y:
        return f"High Rev / Low {metric_name}"
    return f"Low Rev / Low {metric_name}"


def build_yoy_trend_df(ctx, curr_df, prior_df, value_col):
    """Build a melted current + prior-year monthly DataFrame for a two-line trend chart.

    curr_df / prior_df must have yr and month_num columns (raw row-level data).
    Handles both standard (m_from→m_to) and rolling-12M modes.

    Returns (df, month_order):
      df has columns: month (string label), Period ('Current'/'Prior Year'),
                      value_col (raw), {value_col}_m ($M scaled).
      month_order is the ordered list of month labels for category_orders.
    """
    is_rolling = ctx["is_rolling"]
    m_from = ctx["m_from"]
    m_to = ctx["m_to"]

    curr_agg = curr_df.groupby(["yr", "month_num"])[value_col].sum().reset_index()
    prior_agg = prior_df.groupby(["yr", "month_num"])[value_col].sum().reset_index()

    rows = []

    if is_rolling:
        labels = ordered_month_axis_labels(ctx["curr_ym"])
        for i, ((cy, cm_n), (py, pm_n)) in enumerate(zip(ctx["curr_ym"], ctx["prior_ym"])):
            c = curr_agg.loc[(curr_agg["yr"] == cy) & (curr_agg["month_num"] == cm_n), value_col]
            p = prior_agg.loc[(prior_agg["yr"] == py) & (prior_agg["month_num"] == pm_n), value_col]
            rows.append({"month": labels[i], "Period": "Current",    value_col: float(c.iloc[0]) if len(c) else 0})
            rows.append({"month": labels[i], "Period": "Prior Year", value_col: float(p.iloc[0]) if len(p) else 0})
        month_order = labels
    else:
        for m in range(m_from, m_to + 1):
            c = curr_agg.loc[curr_agg["month_num"] == m, value_col]
            p = prior_agg.loc[prior_agg["month_num"] == m, value_col]
            rows.append({"month": MONTH_MAP[m], "Period": "Current",    value_col: float(c.iloc[0]) if len(c) else 0})
            rows.append({"month": MONTH_MAP[m], "Period": "Prior Year", value_col: float(p.iloc[0]) if len(p) else 0})
        month_order = [MONTH_MAP[m] for m in range(m_from, m_to + 1)]

    df = pd.DataFrame(rows)
    df[f"{value_col}_m"] = df[value_col] / 1e6
    return df, month_order


def _monthly_value(df, col, month_num, yr=None):
    mask = df["month_num"] == month_num
    if yr is not None:
        mask &= df["yr"] == yr
    val = df.loc[mask, col]
    return float(val.iloc[0]) if len(val) else 0


def _index_row(order, month, c, p):
    return {
        "order": order,
        "month": month,
        "current": c,
        "prior": p,
        "index": (c / p * 100) if p else None,
    }