import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.utils.charts import (
    build_index_rows,
    build_yoy_trend_df,
    classify_segment,
    render_bar,
    render_index_chart,
    render_treemap,
)
from src.utils.filters import clean_for_visuals, MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m


def _narrative(ctx):
    """Return the headline summary string for the gross margin card."""
    gm = ctx["gm"]
    gm_py = ctx.get("gm_py", 0)
    gm_pct = ctx["gm_pct"]
    gm_pct_py = ctx.get("gm_pct_py", 0)
    period = ctx["period_label"]

    direction = "up" if gm >= gm_py else "down"
    delta = abs(gm - gm_py)

    pct_direction = "improved" if gm_pct >= gm_pct_py else "declined"
    pct_delta = abs(gm_pct - gm_pct_py)

    return (
        f"<b>{period}:</b> Gross margin of <b>{fmt_m(gm)}</b> is "
        f"{direction} <b>{fmt_m(delta)}</b> vs prior year. "
        f"GM% has {pct_direction} <b>{pct_delta:.1f}pts</b> to <b>{gm_pct:.1f}%</b>."
    )


def _monthly_gm_frame(df, group_filters=None):
    """Aggregate monthly gross margin and GM% after applying optional dimension filters."""
    d = df.copy()
    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                d = d[d[col] == val]

    out = (
        d.groupby(["yr", "month_num", "accounting_period_start_date"])
        .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
        .sort_values("accounting_period_start_date")
    )

    out["gross_margin_m"] = out["gross_margin"] / 1e6
    out["gm_pct"] = (
        out["gross_margin"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    return out


def _combined_gm_chart(df, title, PT, LC, prior_df=None, month_order=None):
    """Render a dual-axis line chart showing GM$ (primary) and GM% (secondary) over time.

    If prior_df is provided, overlays prior-year traces as dimmed dashed lines.
    month_order must be supplied alongside prior_df for correct axis ordering.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    x_col = "month" if "month" in df.columns else "accounting_period_start_date"

    fig.add_trace(go.Scatter(
        x=df[x_col], y=df["gross_margin_m"],
        name="GM $M", mode="lines+markers", line=dict(width=2.5, color=LC),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df["gm_pct"],
        name="GM %", mode="lines+markers", line=dict(width=2.5, dash="dot", color="#d7f34a"),
    ), secondary_y=True)

    if prior_df is not None:
        px_col = "month" if "month" in prior_df.columns else "accounting_period_start_date"
        fig.add_trace(go.Scatter(
            x=prior_df[px_col], y=prior_df["gross_margin_m"],
            name="GM $M (PY)", mode="lines+markers",
            line=dict(width=1.5, color=LC, dash="dot"), opacity=0.4,
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=prior_df[px_col], y=prior_df["gm_pct"],
            name="GM % (PY)", mode="lines+markers",
            line=dict(width=1.5, dash="dot", color="#d7f34a"), opacity=0.4,
        ), secondary_y=True)

    fig.update_layout(**{
        **PT,
        "title": title, "title_font_color": "#cbd5e1", "height": 340,
        "legend": dict(orientation="h", y=1.12, x=0),
    })
    fig.update_yaxes(title_text="GM ($M)", tickprefix="$", ticksuffix="M", secondary_y=False)
    fig.update_yaxes(title_text="GM %", ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    if month_order:
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)

    st.plotly_chart(fig, use_container_width=True)


def _build_index(ctx, curr_df, prior_df, metric, group_filters=None):
    """Build monthly PY index DataFrame for either GM$ or GM% (metric parameter selects)."""
    curr_monthly = _monthly_gm_frame(curr_df, group_filters)
    prior_monthly = _monthly_gm_frame(prior_df, group_filters)
    metric_col = "gross_margin" if metric == "GM $" else "gm_pct"
    return pd.DataFrame(build_index_rows(ctx, curr_monthly, prior_monthly, metric_col))


def _build_client_margin(df_curr, df_lab_curr):
    """Join GM data with labor data to produce a per-client margin + contribution frame."""
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
    cl_gm["gm_pct"] = (
        cl_gm["gross_margin"] / cl_gm["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    cl_gm["cm_pct"] = (
        cl_gm["contribution"] / cl_gm["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    return cl_gm[cl_gm["revenue"] > 0].sort_values("revenue", ascending=False)


def render_margin(ctx):
    """Render the Gross Margin tab.

    Uses two data views from ctx:
      df_curr_decomp / df_prior  — SL filter unlocked; powers distribution charts.
      df_curr / df_prior         — fully filtered; powers client bubble, trends, and table.
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]
    df_lab_curr = ctx["df_lab_curr"]

    df_curr_decomp = ctx["df_curr_decomp"]
    df_prior_decomp = df_prior  # decomp key is never set; always falls back to df_prior

    BS = palette["blue_scale"]
    LC = palette["line_current"]
    LP = palette["line_prior"]

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #4ade80;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">
                {_narrative(ctx)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # base/prior_base: all service lines visible — used for SL/SSL distribution charts.
    # filtered_base/filtered_prior: user's full filter applied — used for client charts.
    base = clean_for_visuals(df_curr_decomp)
    prior_base = clean_for_visuals(df_prior_decomp)

    filtered_base = clean_for_visuals(df_curr)
    filtered_prior = clean_for_visuals(df_prior)

    cl_gm = _build_client_margin(df_curr, df_lab_curr)

    # ── Service Line tile chart ───────────────────────────────
    st.markdown('<div class="section-header">Gross Margin by Service Line</div>', unsafe_allow_html=True)

    gm_sl = (
        base.groupby("service_line_name")
        .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
    )

    margin_sl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="margin_sl_chart_type")
    if margin_sl_chart_type == "Tile":
        render_treemap(gm_sl, label_col="service_line_name", value_col="gross_margin", title="", color_scale=BS, value_label="Gross Margin")
    else:
        render_bar(gm_sl, label_col="service_line_name", value_col="gross_margin", title="", color_scale=BS, value_label="Gross Margin")

    # ── Sub Service Line tile chart ───────────────────────────
    st.markdown('<div class="section-header">Gross Margin by Sub-Service Line</div>', unsafe_allow_html=True)

    ssl_options = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Sub Service Line view", ssl_options, key="margin_ssl_sl_filter")

    ssl_src = base if selected_sl == "All" else base[base["service_line_name"] == selected_sl]

    gm_ssl = (
        ssl_src.groupby("sub_service_line_name")
        .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
    )
    gm_ssl = gm_ssl[gm_ssl["sub_service_line_name"] != "(blank)"]

    margin_ssl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="margin_ssl_chart_type")
    if margin_ssl_chart_type == "Tile":
        render_treemap(gm_ssl, label_col="sub_service_line_name", value_col="gross_margin", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Gross Margin")
    else:
        render_bar(gm_ssl, label_col="sub_service_line_name", value_col="gross_margin", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Gross Margin")

    # ── Service Line trends ───────────────────────────────────
    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)

    tcol1, tcol2 = st.columns(2)

    with tcol1:
        trend_sl_opts = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
        trend_sl = st.selectbox("Trend — Service Line", trend_sl_opts, key="margin_trend_sl")

    trend_ssl_src = base if trend_sl == "All" else base[base["service_line_name"] == trend_sl]

    with tcol2:
        trend_ssl_opts = ["All"] + sorted(trend_ssl_src["sub_service_line_name"].dropna().unique().tolist())
        trend_ssl = st.selectbox("Trend — Sub Service Line", trend_ssl_opts, key="margin_trend_ssl")

    trend_filters = {
        "service_line_name": trend_sl,
        "sub_service_line_name": trend_ssl,
    }

    margin_sl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="margin_sl_trend_mode")

    if margin_sl_trend_mode == "Raw":
        month_order = ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"] else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"] + 1)]
        service_monthly = _monthly_gm_frame(base, trend_filters)
        service_monthly["month"] = service_monthly["month_num"].map(MONTH_MAP)
        prior_monthly = _monthly_gm_frame(prior_base, trend_filters)
        prior_monthly["month"] = prior_monthly["month_num"].map(MONTH_MAP)
        _combined_gm_chart(service_monthly, "", PT, LC, prior_df=prior_monthly, month_order=month_order)
    else:
        index_metric = st.radio("Index metric", ["GM $", "GM %"], horizontal=True, key="margin_service_index_metric")
        idx_df = _build_index(ctx, base, prior_base, index_metric, trend_filters)
        render_index_chart(idx_df, f"vs Prior Year  —  100 = PY  ({index_metric})", PT)

    # ── Client bubble plot ────────────────────────────────────
    st.markdown('<div class="section-header">Client Profitability Matrix</div>', unsafe_allow_html=True)

    top_n = st.select_slider(
        "Show top N clients by revenue",
        options=[5, 10, 15, 20, 25, 30],
        value=15,
        key="margin_topn",
    )

    cl_plot = cl_gm.head(top_n).copy()

    med_rev = cl_plot["revenue"].median()
    med_gm_pct = cl_plot["gm_pct"].median()

    cl_plot["segment"] = cl_plot.apply(
        lambda row: classify_segment(row, "revenue", "gm_pct", med_rev, med_gm_pct, "Margin"),
        axis=1,
    )

    segment_colors = {
        "High Rev / High Margin": "#4ade80",
        "Low Rev / High Margin": "#60a5fa",
        "High Rev / Low Margin": "#fb923c",
        "Low Rev / Low Margin": "#f87171",
    }

    st.markdown(
        f"""
        <div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-top:-0.25rem;margin-bottom:0.75rem;">
            Segment definitions use the median of the selected top {top_n} clients:
            revenue split = <span style="color:#cbd5e1;">{fmt_m(med_rev)}</span>,
            GM% split = <span style="color:#cbd5e1;">{med_gm_pct:.1f}%</span>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig_bub = px.scatter(
        cl_plot,
        x="revenue",
        y="gm_pct",
        color="segment",
        color_discrete_map=segment_colors,
        text="top_level_parent_customer_name",
        hover_name="top_level_parent_customer_name",
        hover_data={
            "revenue": ":,.0f",
            "gm_pct": ":.1f",
            "cm_pct": ":.1f",
            "gross_margin": ":,.0f",
            "labor": ":,.0f",
            "contribution": ":,.0f",
            "segment": True,
        },
        title=f"GM% vs Revenue  —  Top {top_n} Clients",
        labels={
            "revenue": "Revenue ($)",
            "gm_pct": "Gross Margin %",
            "segment": "Segment",
        },
    )

    fig_bub.update_traces(
        marker=dict(size=13, opacity=0.88, line=dict(width=1, color="#0b0f16")),
        textposition="top center",
        textfont=dict(size=9, color="#cbd5e1", family="DM Sans"),
    )

    fig_bub.add_vline(
        x=med_rev,
        line_width=1,
        line_dash="dot",
        line_color="#94a3b8",
        annotation_text=f"Median revenue: {fmt_m(med_rev)}",
        annotation_position="top",
    )

    fig_bub.add_hline(
        y=med_gm_pct,
        line_width=1,
        line_dash="dot",
        line_color="#94a3b8",
        annotation_text=f"Median GM%: {med_gm_pct:.1f}%",
        annotation_position="right",
    )

    fig_bub.update_layout(
        **PT,
        title_font_color="#cbd5e1",
        height=520,
        legend_title_text="Segment",
    )

    fig_bub.update_xaxes(tickformat="$,.0s")
    fig_bub.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_bub, use_container_width=True)

    # ── Client trends ─────────────────────────────────────────
    st.markdown('<div class="section-header">Client Trend</div>', unsafe_allow_html=True)

    client_options = ["All"] + sorted(filtered_base["top_level_parent_customer_name"].dropna().unique().tolist())
    selected_client = st.selectbox("Trend — Client", client_options, key="margin_client_trend_filter")

    client_filters = {
        "top_level_parent_customer_name": selected_client,
    }

    margin_cl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="margin_cl_trend_mode")

    if margin_cl_trend_mode == "Raw":
        month_order = ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"] else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"] + 1)]
        client_monthly = _monthly_gm_frame(filtered_base, client_filters)
        client_monthly["month"] = client_monthly["month_num"].map(MONTH_MAP)
        client_prior_monthly = _monthly_gm_frame(filtered_prior, client_filters)
        client_prior_monthly["month"] = client_prior_monthly["month_num"].map(MONTH_MAP)
        _combined_gm_chart(client_monthly, f"— {selected_client}", PT, LC, prior_df=client_prior_monthly, month_order=month_order)
    else:
        client_index_metric = st.radio("Index metric", ["GM $", "GM %"], horizontal=True, key="margin_client_index_metric")
        client_idx_df = _build_index(ctx, filtered_base, filtered_prior, client_index_metric, client_filters)
        render_index_chart(client_idx_df, f"— {selected_client}  vs Prior Year  —  100 = PY  ({client_index_metric})", PT)

    # ── Detail table ──────────────────────────────────────────
    st.markdown('<div class="section-header">Client Margin Detail</div>', unsafe_allow_html=True)

    gm_tbl = cl_gm.copy()

    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        gm_tbl[c] = (gm_tbl[c] / 1e6).round(2)

    gm_tbl = gm_tbl.sort_values("gm_pct", ascending=False)
    gm_tbl = gm_tbl.rename(columns={
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue",
        "cogs": "COGS",
        "fixed_cost": "Fixed Cost",
        "gross_margin": "Gross Margin",
        "labor": "Labor",
        "contribution": "Contribution",
        "gm_pct": "GM %",
        "cm_pct": "CM %",
    })

    st.dataframe(
        gm_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "COGS": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "Fixed Cost": st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
            "Gross Margin": st.column_config.NumberColumn("GM ($M)", format="$%.2f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.2f"),
            "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
            "GM %": st.column_config.NumberColumn("GM %", format="%.1f%%"),
            "CM %": st.column_config.NumberColumn("CM %", format="%.1f%%"),
        },
    )

    st.download_button(
        "Download Margin Detail CSV",
        gm_tbl.to_csv(index=False).encode(),
        "margin_detail.csv",
        "text/csv",
        key="margin_dl",
    )