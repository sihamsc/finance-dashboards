"""
Overview tab:
  - Deterministic headline narrative
  - Service line and client movement pills
  - P&L waterfall bridge
  - Monthly revenue: current vs prior year
  - Dual service-line radar:
      * raw $M profile
      * indexed 0–100 profile
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from src.utils.charts import build_index_rows, render_index_chart
from src.utils.filters import MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m


def _narrative(ctx):
    """Return the one-sentence headline summary for the overview card."""
    rev, rev_py = ctx["rev"], ctx["rev_py"]
    gm_pct, gm_pct_py = ctx["gm_pct"], ctx["gm_pct_py"]
    contrib, contrib_py = ctx["contrib"], ctx["contrib_py"]
    period = ctx["period_label"]

    rev_dir = "up" if rev >= rev_py else "down"
    gm_dir = "improved" if gm_pct >= gm_pct_py else "declined"
    contrib_dir = "up" if contrib >= contrib_py else "down"

    return (
        f"<b>{period}:</b> Revenue is {fmt_m(rev)}, "
        f"{rev_dir} {fmt_m(abs(rev - rev_py))} vs prior year. "
        f"GM% has {gm_dir} {abs(gm_pct - gm_pct_py):.1f}pts to {gm_pct:.1f}%. "
        f"Contribution is {contrib_dir} {fmt_m(abs(contrib - contrib_py))} at {fmt_m(contrib)}."
    )


def _pill(label, name, delta):
    """Return a single green (positive) or red (negative) HTML movement pill."""
    if delta >= 0:
        return (
            f'<span style="display:inline-block;background:rgba(74,222,128,0.1);'
            f'border:1px solid rgba(74,222,128,0.3);border-radius:20px;padding:0.2rem 0.7rem;'
            f'font-family:DM Mono,monospace;font-size:9px;color:#4ade80;margin-right:0.4rem;">'
            f'▲ {label}: {name} +{fmt_m(delta)}</span>'
        )

    return (
        f'<span style="display:inline-block;background:rgba(248,113,113,0.1);'
        f'border:1px solid rgba(248,113,113,0.3);border-radius:20px;padding:0.2rem 0.7rem;'
        f'font-family:DM Mono,monospace;font-size:9px;color:#f87171;margin-right:0.4rem;">'
        f'▼ {label}: {name} {fmt_m(delta)}</span>'
    )


def _movement_pills(df_curr, df_prior, group_col, label):
    """Return HTML string of the top gaining and top losing entity for group_col."""
    curr = df_curr.groupby(group_col)["revenue"].sum().reset_index()
    prior = df_prior.groupby(group_col)["revenue"].sum().reset_index()

    merged = curr.merge(prior, on=group_col, how="outer", suffixes=("_curr", "_prior")).fillna(0)
    merged["delta"] = merged["revenue_curr"] - merged["revenue_prior"]
    merged = merged[~merged[group_col].isin(["(blank)", "Unassigned"])]

    if merged.empty:
        return ""

    top_pos = merged.nlargest(1, "delta").iloc[0]
    top_neg = merged.nsmallest(1, "delta").iloc[0]

    pills = ""
    if top_pos["delta"] > 0:
        pills += _pill(label, top_pos[group_col], top_pos["delta"])
    if top_neg["delta"] < 0:
        pills += _pill(label, top_neg[group_col], top_neg["delta"])

    return pills


def _build_yoy_monthly_df(ctx):
    """Build monthly revenue data for the current vs prior-year line chart.

    Returns (df, x_col, x_order) where x_col is the column to use as the
    x-axis and x_order is the list of labels in the correct display order.
    Handles both rolling-12M and standard full-year / YTD modes.
    """
    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]
    is_rolling = ctx["is_rolling"]
    curr_ym = ctx["curr_ym"]
    prior_ym = ctx["prior_ym"]
    m_from = ctx["m_from"]
    m_to = ctx["m_to"]

    if is_rolling:
        month_labels = ordered_month_axis_labels(curr_ym)

        curr_monthly = df_curr.groupby(["yr", "month_num"])["revenue"].sum().reset_index()
        prior_monthly = df_prior.groupby(["yr", "month_num"])["revenue"].sum().reset_index()

        rows = []

        for i, (yr, mn) in enumerate(curr_ym):
            val = curr_monthly.loc[
                (curr_monthly["yr"] == yr) & (curr_monthly["month_num"] == mn),
                "revenue",
            ]
            rows.append({
                "order": i,
                "label": month_labels[i],
                "Revenue": float(val.iloc[0]) / 1e6 if len(val) else 0,
                "Period": "Current",
            })

        for i, (yr, mn) in enumerate(prior_ym):
            val = prior_monthly.loc[
                (prior_monthly["yr"] == yr) & (prior_monthly["month_num"] == mn),
                "revenue",
            ]
            rows.append({
                "order": i,
                "label": month_labels[i],
                "Revenue": float(val.iloc[0]) / 1e6 if len(val) else 0,
                "Period": "Prior Year",
            })

        return pd.DataFrame(rows), "label", month_labels

    months_in_range = list(range(m_from, m_to + 1))

    cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Current"})
    py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue": "Prior Year"})

    base = pd.DataFrame({"month_num": months_in_range})
    yoy_raw = base.merge(cy, on="month_num", how="left").merge(py, on="month_num", how="left").fillna(0)

    yoy_raw["label"] = yoy_raw["month_num"].map(MONTH_MAP)
    yoy_raw["Current"] = yoy_raw["Current"] / 1e6
    yoy_raw["Prior Year"] = yoy_raw["Prior Year"] / 1e6

    yoy_df = yoy_raw.melt(
        id_vars=["month_num", "label"],
        value_vars=["Current", "Prior Year"],
        var_name="Period",
        value_name="Revenue",
    )

    return yoy_df, "label", [MONTH_MAP[m] for m in months_in_range]


def _build_radar_data(ctx):
    """Aggregate revenue, COGS, fixed cost, labor, GM, and contribution by service line.

    Uses the decomp frame (SL filter unlocked) so all service lines appear on the radar
    regardless of the current SL filter selection.
    """
    df_curr_decomp = ctx["df_curr_decomp"]
    df_lab_curr_decomp = ctx.get("df_lab_curr_decomp", ctx["df_lab_curr"])

    base = df_curr_decomp[
        ~df_curr_decomp["service_line_name"].isin(["(blank)", "Unassigned"])
    ].copy()

    radar = (
        base.groupby("service_line_name")
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )

    labor = (
        df_lab_curr_decomp[
            ~df_lab_curr_decomp["service_line_name"].isin(["(blank)", "Unassigned"])
        ]
        .groupby("service_line_name")["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    radar = radar.merge(labor, on="service_line_name", how="left")
    radar["labor"] = radar["labor"].fillna(0)
    radar["contribution"] = radar["gross_margin"] - radar["labor"]

    return radar


def _radar_chart(radar_df, selected_sl, mode, cfo_colors, PT):
    """Render a polar/radar chart for service-line P&L profiles.

    mode="raw"     — values in $M, radial axis has dollar prefix.
    mode="indexed" — each metric normalised 0–100 within its column max,
                     so shapes are comparable across different-scale metrics.
    selected_sl    — highlights a single service line; "All" shows all equally.
    """
    metric_map = {
        "Revenue": "revenue",
        "COGS": "cogs",
        "Fixed Cost": "fixed_cost",
        "Labor": "labor",
        "Gross Margin": "gross_margin",
        "Contribution": "contribution",
    }

    labels = list(metric_map.keys())
    fig = go.Figure()

    for idx, row in radar_df.iterrows():
        sl = row["service_line_name"]
        color = cfo_colors[idx % len(cfo_colors)]

        if mode == "raw":
            values = [row[col] / 1e6 for col in metric_map.values()]
            title = "Raw $M Profile"
            radialaxis = dict(
                visible=True,
                gridcolor="#1b2230",
                tickfont=dict(color="#94a3b8", size=9),
                tickprefix="$",
                ticksuffix="M",
            )
            hover_unit = "$M"
        else:
            values = []
            for col in metric_map.values():
                max_val = radar_df[col].abs().max()
                values.append((abs(row[col]) / max_val * 100) if max_val else 0)

            title = "Indexed Profile"
            radialaxis = dict(
                visible=True,
                range=[0, 100],
                gridcolor="#1b2230",
                tickfont=dict(color="#94a3b8", size=9),
            )
            hover_unit = "index"

        values = values + [values[0]]
        theta = labels + [labels[0]]

        is_selected = selected_sl == "All" or selected_sl == sl

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=theta,
            name=sl,
            legendgroup=sl,
            showlegend=(mode == "raw"),
            line=dict(
                color=color,
                width=3.5 if is_selected else 1,
            ),
            fill="toself" if is_selected else None,
            fillcolor=color if is_selected else None,
            opacity=0.82 if is_selected else 0.08,
            hovertemplate=(
                f"<b>{sl}</b><br>"
                "%{theta}: %{r:.2f} " + hover_unit +
                "<extra></extra>"
            ),
        ))

    fig.update_layout(**{
        **PT,
        "title": dict(text=title, font=dict(color="#cbd5e1", size=13, family="DM Sans")),
        "polar": dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis={
                **radialaxis,
                "gridcolor": "#243041",
                "tickfont": {**radialaxis.get("tickfont", {}), "size": 10, "color": "#94a3b8"},
            },
            angularaxis=dict(
                gridcolor="#243041",
                tickfont=dict(color="#e2e8f0", size=13, family="DM Sans"),
                rotation=90,
                direction="clockwise",
            ),
        ),
        "legend": dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#cbd5e1", size=11, family="DM Sans"),
            bgcolor="rgba(0,0,0,0)",
        ),
        "margin": dict(l=80, r=80, t=60, b=90),
        "height": 600,
        "showlegend": True,
    })

    return fig


def render_overview(ctx):
    """Render the Overview tab.

    Sections:
      0. Business filters (SL / Sub-SL / Vertical / Client) — Overview-only, inline
      1. Narrative headline + SL/client movement pills
      2. P&L waterfall bridge (Revenue → Contribution)
      3. Monthly revenue vs prior year line chart
      4. Service-line radar: raw $M profile and indexed (0–100) profile side by side
      5. Service-line summary table
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    # ── Business filters — only visible on this tab ───────────────
    df_gm_yr = ctx["df_gm_curr_yr"]
    excl = ctx.get("EXCL", [])

    fc1, fc2, fc3, fc4 = st.columns(4)

    sl_opts = ["All"] + sorted([x for x in df_gm_yr["service_line_name"].unique() if x != "(blank)"])
    with fc1:
        selected_sl = st.selectbox("Service Line", sl_opts, key="ov_sl")

    ssl_pool = df_gm_yr if selected_sl == "All" else df_gm_yr[df_gm_yr["service_line_name"] == selected_sl]
    ssl_opts = ["All"] + sorted([x for x in ssl_pool["sub_service_line_name"].unique() if x != "(blank)"])
    with fc2:
        selected_ssl = st.selectbox("Sub Service Line", ssl_opts, key="ov_ssl")

    v_pool = ssl_pool if selected_ssl == "All" else ssl_pool[ssl_pool["sub_service_line_name"] == selected_ssl]
    v_opts = ["All"] + sorted([x for x in v_pool["vertical_name"].unique() if x != "(blank)"])
    with fc3:
        selected_vertical = st.selectbox("Vertical", v_opts, key="ov_vertical")

    c_pool = v_pool if selected_vertical == "All" else v_pool[v_pool["vertical_name"] == selected_vertical]
    c_opts = ["All"] + sorted([x for x in c_pool["top_level_parent_customer_name"].unique() if x not in excl])
    with fc4:
        st.selectbox("Client", c_opts, key="ov_customer")

    st.divider()

    rev = ctx["rev"]
    cogs = ctx["cogs"]
    fixed_cost = ctx["fixed_cost"]
    labor = ctx["labor"]
    gm = ctx["gm"]
    contrib = ctx["contrib"]
    gm_pct = ctx["gm_pct"]
    cm_pct = ctx["cm_pct"]

    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]

    WFP = palette["wf_pos"]
    WFN = palette["wf_neg"]
    WFT = palette["wf_total"]
    LC = palette["line_current"]
    LP = palette["line_prior"]

    # More CFO-friendly than neon / rainbow.
    cfo_colors = [
        "#d7f34a",  # MarketCast accent
        "#60a5fa",  # soft blue
        "#94a3b8",  # slate
        "#a78bfa",  # muted violet
        "#fbbf24",  # amber
        "#34d399",  # green
        "#f87171",  # red
    ]

    narrative_html = _narrative(ctx)
    service_pills = _movement_pills(df_curr, df_prior, "service_line_name", "SL")
    client_pills = _movement_pills(df_curr, df_prior, "top_level_parent_customer_name", "Client")

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #d7f34a;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;margin-bottom:0.45rem;">
                {narrative_html}
            </div>
            <div>{service_pills}{client_pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">P&L Bridge — Current Period</div>', unsafe_allow_html=True)
    wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total", "relative", "total"],
        x=["Revenue", "COGS", "Fixed Cost", "Gross Margin", "Labor", "Contribution"],
        y=[rev, -cogs, -fixed_cost, None, -labor, None],
        connector={"line": {"color": "#243041"}},
        increasing={"marker": {"color": WFP, "line": {"width": 0}}},
        decreasing={"marker": {"color": WFN, "line": {"width": 0}}},
        totals={"marker": {"color": WFT, "line": {"width": 0}}},
        text=[
            fmt_m(rev),
            fmt_m(cogs),
            fmt_m(fixed_cost),
            f"{fmt_m(gm)} ({gm_pct:.1f}%)",
            fmt_m(labor),
            f"{fmt_m(contrib)} ({cm_pct:.1f}%)",
        ],
        textfont={"color": "#cbd5e1", "size": 10, "family": "DM Mono"},
        textposition="outside",
    ))
    wf.update_layout(**PT, title="", showlegend=False, height=360)
    st.plotly_chart(wf, use_container_width=True, key="ov_pl_bridge")

    st.markdown('<div class="section-header">Revenue Performance</div>', unsafe_allow_html=True)

    ov_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="ov_trend_mode")

    if ov_trend_mode == "Raw":
        yoy_df, x_col, x_order = _build_yoy_monthly_df(ctx)
        fig_yoy = px.line(
            yoy_df,
            x=x_col,
            y="Revenue",
            color="Period",
            markers=True,
            color_discrete_map={"Current": LC, "Prior Year": LP},
            title="",
            labels={x_col: "", "Revenue": "Revenue ($M)"},
            category_orders={x_col: x_order},
        )
        fig_yoy.update_traces(line_width=2.5)
        fig_yoy.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig_yoy.update_yaxes(tickprefix="$", ticksuffix="M", tickformat=",.1f")
        st.plotly_chart(fig_yoy, use_container_width=True, key="ov_rev_raw_trend")
    else:
        curr_m = ctx["df_curr"].groupby(["yr", "month_num"])["revenue"].sum().reset_index()
        prior_m = ctx["df_prior"].groupby(["yr", "month_num"])["revenue"].sum().reset_index()
        idx_df = pd.DataFrame(build_index_rows(ctx, curr_m, prior_m, "revenue"))
        render_index_chart(idx_df, "Revenue Index vs Prior Year — 100 = Same as PY", PT, key="ov_rev_idx_trend")

    st.markdown('<div class="section-header">Service Line Profile</div>', unsafe_allow_html=True)

    radar_df = _build_radar_data(ctx)

    selected_sl = st.selectbox(
        "Highlight service line",
        ["All"] + sorted(radar_df["service_line_name"].dropna().unique().tolist()),
        key="overview_radar_highlight",
    )

    radar_col1, radar_col2 = st.columns(2)

    with radar_col1:
        fig_raw = _radar_chart(radar_df, selected_sl, "raw", cfo_colors, PT)
        st.plotly_chart(fig_raw, use_container_width=True, key="ov_radar_raw")

    with radar_col2:
        fig_idx = _radar_chart(radar_df, selected_sl, "indexed", cfo_colors, PT)
        st.plotly_chart(fig_idx, use_container_width=True, key="ov_radar_idx")

    radar_table = radar_df.copy()
    for c in ["revenue", "cogs", "fixed_cost", "labor", "gross_margin", "contribution"]:
        radar_table[c] = (radar_table[c] / 1e6).round(2)

    radar_table = radar_table.rename(columns={
        "service_line_name": "Service Line",
        "revenue": "Revenue",
        "cogs": "COGS",
        "fixed_cost": "Fixed Cost",
        "labor": "Labor",
        "gross_margin": "Gross Margin",
        "contribution": "Contribution",
    })

    st.dataframe(
        radar_table[
            ["Service Line", "Revenue", "COGS", "Fixed Cost", "Labor", "Gross Margin", "Contribution"]
        ].sort_values("Revenue", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "COGS": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        },
    )

    st.markdown(
        f"""
        <div style="font-family:DM Mono,monospace;font-size:8px;color:#2a3045;
                    text-align:right;margin-top:0.5rem;">
            Data loaded: {datetime.now().strftime("%d %b %Y %H:%M")}
        </div>
        """,
        unsafe_allow_html=True,
    )