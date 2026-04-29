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
    """Return the headline summary string for the contribution margin card."""
    contrib = ctx["contrib"]
    contrib_py = ctx.get("contrib_py", 0)
    cm_pct = ctx.get("cm_pct", 0)
    period = ctx["period_label"]

    direction = "up" if contrib >= contrib_py else "down"
    delta = abs(contrib - contrib_py)

    return (
        f"<b>{period}:</b> Contribution of <b>{fmt_m(contrib)}</b> "
        f"({cm_pct:.1f}% CM) is {direction} <b>{fmt_m(delta)}</b> vs prior year."
    )


def _build_contribution_frame(df_gm, df_lab):
    """Build a per-entity (SL × SSL × Client) contribution frame by joining GM and labor data."""
    gm = (
        df_gm.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )

    lab = (
        df_lab.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    out = gm.merge(
        lab,
        on=["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
        how="left",
    )

    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    out["gm_pct"] = (
        out["gross_margin"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    out["cm_pct"] = (
        out["contribution"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    out["labor_pct"] = (
        out["labor"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    return out


def _build_monthly_contribution_frame(df_gm, df_lab, group_filters=None):
    """Build a monthly contribution frame (Contribution = GM − Labor) for trend/index charts."""
    gm = df_gm.copy()
    lab = df_lab.copy()

    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                gm = gm[gm[col] == val]
                lab = lab[lab[col] == val]

    gm_m = (
        gm.groupby(["yr", "month_num", "accounting_period_start_date"])
        .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
        .sort_values("accounting_period_start_date")
    )

    lab_m = (
        lab.groupby(["yr", "month_num", "accounting_period_start_date"])["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    out = gm_m.merge(
        lab_m,
        on=["yr", "month_num", "accounting_period_start_date"],
        how="left",
    )

    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    out["contribution_m"] = out["contribution"] / 1e6
    out["cm_pct"] = (
        out["contribution"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    return out


def _combined_contribution_chart(df, title, PT, LC, prior_df=None, month_order=None):
    """Render a dual-axis line chart showing Contribution$ (primary) and CM% (secondary).

    If prior_df is provided, overlays prior-year traces as dimmed dashed lines.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    x_col = "month" if "month" in df.columns else "accounting_period_start_date"

    fig.add_trace(go.Scatter(
        x=df[x_col], y=df["contribution_m"],
        name="Contribution $M", mode="lines+markers", line=dict(width=2.5, color=LC),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df["cm_pct"],
        name="CM %", mode="lines+markers", line=dict(width=2.5, dash="dot", color="#d7f34a"),
    ), secondary_y=True)

    if prior_df is not None:
        px_col = "month" if "month" in prior_df.columns else "accounting_period_start_date"
        fig.add_trace(go.Scatter(
            x=prior_df[px_col], y=prior_df["contribution_m"],
            name="Contribution $M (PY)", mode="lines+markers",
            line=dict(width=1.5, color=LC, dash="dot"), opacity=0.4,
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=prior_df[px_col], y=prior_df["cm_pct"],
            name="CM % (PY)", mode="lines+markers",
            line=dict(width=1.5, dash="dot", color="#d7f34a"), opacity=0.4,
        ), secondary_y=True)

    fig.update_layout(**{
        **PT,
        "title": title, "title_font_color": "#cbd5e1", "height": 340,
        "legend": dict(orientation="h", y=1.12, x=0),
    })
    fig.update_yaxes(title_text="Contribution ($M)", tickprefix="$", ticksuffix="M", secondary_y=False)
    fig.update_yaxes(title_text="CM %", ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    if month_order:
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)

    st.plotly_chart(fig, use_container_width=True)


def _build_index(ctx, curr_gm, curr_lab, prior_gm, prior_lab, metric, group_filters=None):
    """Build monthly PY index DataFrame for Contribution$ or CM% (metric selects column)."""
    curr_monthly = _build_monthly_contribution_frame(curr_gm, curr_lab, group_filters)
    prior_monthly = _build_monthly_contribution_frame(prior_gm, prior_lab, group_filters)
    metric_col = "contribution" if metric == "Contribution $" else "cm_pct"
    return pd.DataFrame(build_index_rows(ctx, curr_monthly, prior_monthly, metric_col))


def _build_client_contribution(df_curr, df_lab_curr):
    """Build a per-client contribution frame by joining GM and labor data at client level."""
    lab_cl = (
        df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    cl = (
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

    cl = cl.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl["labor"] = cl["labor"].fillna(0)
    cl["contribution"] = cl["gross_margin"] - cl["labor"]
    cl["gm_pct"] = (
        cl["gross_margin"] / cl["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    cl["cm_pct"] = (
        cl["contribution"] / cl["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    cl["labor_pct"] = (
        cl["labor"] / cl["revenue"].replace(0, float("nan")) * 100
    ).round(1)

    return cl[cl["revenue"] > 0].sort_values("revenue", ascending=False)


def render_contribution(ctx):
    """Render the Contribution Margin tab.

    Contribution = Gross Margin – Labor.

    Uses two data views from ctx:
      *_decomp    — SL filter unlocked; powers SL/SSL distribution charts.
      df_curr / df_prior / df_lab_* — fully filtered; powers client charts and table.
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]
    df_lab_curr = ctx["df_lab_curr"]
    df_lab_prior = ctx["df_lab_prior"]

    df_curr_decomp = ctx["df_curr_decomp"]
    df_prior_decomp = df_prior          # decomp key is never set; always falls back
    df_lab_curr_decomp = ctx["df_lab_curr_decomp"]
    df_lab_prior_decomp = df_lab_prior  # decomp key is never set; always falls back

    BS = palette["blue_scale"]
    LC = palette["line_current"]
    LP = palette["line_prior"]

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #d7f34a;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">
                {_narrative(ctx)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # *_base: all service lines visible — used for SL/SSL distribution charts.
    # filtered_*: user's full filter applied — used for client charts and detail table.
    base = clean_for_visuals(df_curr_decomp)
    prior_base = clean_for_visuals(df_prior_decomp)
    lab_base = clean_for_visuals(df_lab_curr_decomp)
    prior_lab_base = clean_for_visuals(df_lab_prior_decomp)

    filtered_base = clean_for_visuals(df_curr)
    filtered_prior = clean_for_visuals(df_prior)
    filtered_lab = clean_for_visuals(df_lab_curr)
    filtered_lab_prior = clean_for_visuals(df_lab_prior)

    contrib_base = _build_contribution_frame(base, lab_base)
    client_contrib = _build_client_contribution(df_curr, df_lab_curr)

    # ── Service Line tile chart ───────────────────────────────
    st.markdown('<div class="section-header">Contribution by Service Line</div>', unsafe_allow_html=True)

    cm_sl = (
        contrib_base.groupby("service_line_name")
        .agg(
            revenue=("revenue", "sum"),
            contribution=("contribution", "sum"),
        )
        .reset_index()
    )

    contrib_sl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="contrib_sl_chart_type")
    if contrib_sl_chart_type == "Tile":
        render_treemap(cm_sl, label_col="service_line_name", value_col="contribution", title="", color_scale=BS, value_label="Contribution")
    else:
        render_bar(cm_sl, label_col="service_line_name", value_col="contribution", title="", color_scale=BS, value_label="Contribution")

    # ── Sub Service Line tile chart ───────────────────────────
    st.markdown('<div class="section-header">Contribution by Sub-Service Line</div>', unsafe_allow_html=True)

    ssl_options = ["All"] + sorted(contrib_base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Sub Service Line view", ssl_options, key="contrib_ssl_sl_filter")

    ssl_src = contrib_base if selected_sl == "All" else contrib_base[contrib_base["service_line_name"] == selected_sl]

    cm_ssl = (
        ssl_src.groupby("sub_service_line_name")
        .agg(
            revenue=("revenue", "sum"),
            contribution=("contribution", "sum"),
        )
        .reset_index()
    )
    cm_ssl = cm_ssl[cm_ssl["sub_service_line_name"] != "(blank)"]

    contrib_ssl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="contrib_ssl_chart_type")
    if contrib_ssl_chart_type == "Tile":
        render_treemap(cm_ssl, label_col="sub_service_line_name", value_col="contribution", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Contribution")
    else:
        render_bar(cm_ssl, label_col="sub_service_line_name", value_col="contribution", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Contribution")

    # ── Service Line trends ───────────────────────────────────
    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)

    tcol1, tcol2 = st.columns(2)

    with tcol1:
        trend_sl_opts = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
        trend_sl = st.selectbox("Trend — Service Line", trend_sl_opts, key="contrib_trend_sl")

    trend_ssl_src = base if trend_sl == "All" else base[base["service_line_name"] == trend_sl]

    with tcol2:
        trend_ssl_opts = ["All"] + sorted(trend_ssl_src["sub_service_line_name"].dropna().unique().tolist())
        trend_ssl = st.selectbox("Trend — Sub Service Line", trend_ssl_opts, key="contrib_trend_ssl")

    trend_filters = {
        "service_line_name": trend_sl,
        "sub_service_line_name": trend_ssl,
    }

    contrib_sl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="contrib_sl_trend_mode")

    if contrib_sl_trend_mode == "Raw":
        month_order = ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"] else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"] + 1)]
        service_monthly = _build_monthly_contribution_frame(base, lab_base, trend_filters)
        service_monthly["month"] = service_monthly["month_num"].map(MONTH_MAP)
        prior_service_monthly = _build_monthly_contribution_frame(prior_base, prior_lab_base, trend_filters)
        prior_service_monthly["month"] = prior_service_monthly["month_num"].map(MONTH_MAP)
        _combined_contribution_chart(service_monthly, "", PT, LC, prior_df=prior_service_monthly, month_order=month_order)
    else:
        index_metric = st.radio("Index metric", ["Contribution $", "CM %"], horizontal=True, key="contrib_service_index_metric")
        idx_df = _build_index(ctx, base, lab_base, prior_base, prior_lab_base, index_metric, trend_filters)
        render_index_chart(idx_df, f"vs Prior Year  —  100 = PY  ({index_metric})", PT)

    # ── Client bubble plot ────────────────────────────────────
    st.markdown('<div class="section-header">Client Profitability Matrix</div>', unsafe_allow_html=True)

    top_n = st.select_slider(
        "Show top N clients by revenue",
        options=[5, 10, 15, 20, 25, 30],
        value=15,
        key="contrib_topn",
    )

    cl_plot = client_contrib.head(top_n).copy()

    med_rev = cl_plot["revenue"].median()
    med_cm_pct = cl_plot["cm_pct"].median()

    cl_plot["segment"] = cl_plot.apply(
        lambda row: classify_segment(row, "revenue", "cm_pct", med_rev, med_cm_pct, "Contribution"),
        axis=1,
    )

    segment_colors = {
        "High Rev / High Contribution": "#4ade80",
        "Low Rev / High Contribution": "#60a5fa",
        "High Rev / Low Contribution": "#fb923c",
        "Low Rev / Low Contribution": "#f87171",
    }

    st.markdown(
        f"""
        <div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-top:-0.25rem;margin-bottom:0.75rem;">
            Segment definitions use the median of the selected top {top_n} clients:
            revenue split = <span style="color:#cbd5e1;">{fmt_m(med_rev)}</span>,
            CM% split = <span style="color:#cbd5e1;">{med_cm_pct:.1f}%</span>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig_bub = px.scatter(
        cl_plot,
        x="revenue",
        y="cm_pct",
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
            "labor_pct": ":.1f",
            "segment": True,
        },
        title=f"CM% vs Revenue  —  Top {top_n} Clients",
        labels={
            "revenue": "Revenue ($)",
            "cm_pct": "Contribution %",
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
        y=med_cm_pct,
        line_width=1,
        line_dash="dot",
        line_color="#94a3b8",
        annotation_text=f"Median CM%: {med_cm_pct:.1f}%",
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
    selected_client = st.selectbox("Trend — Client", client_options, key="contrib_client_trend_filter")

    client_filters = {
        "top_level_parent_customer_name": selected_client,
    }

    contrib_cl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="contrib_cl_trend_mode")

    if contrib_cl_trend_mode == "Raw":
        month_order = ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"] else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"] + 1)]
        client_monthly = _build_monthly_contribution_frame(filtered_base, filtered_lab, client_filters)
        client_monthly["month"] = client_monthly["month_num"].map(MONTH_MAP)
        client_prior_monthly = _build_monthly_contribution_frame(filtered_prior, filtered_lab_prior, client_filters)
        client_prior_monthly["month"] = client_prior_monthly["month_num"].map(MONTH_MAP)
        _combined_contribution_chart(client_monthly, f"— {selected_client}", PT, LC, prior_df=client_prior_monthly, month_order=month_order)
    else:
        client_index_metric = st.radio("Index metric", ["Contribution $", "CM %"], horizontal=True, key="contrib_client_index_metric")
        client_idx_df = _build_index(
            ctx, filtered_base, filtered_lab, filtered_prior, filtered_lab_prior,
            client_index_metric, client_filters,
        )
        render_index_chart(client_idx_df, f"— {selected_client}  vs Prior Year  —  100 = PY  ({client_index_metric})", PT)

    # ── Detail table ──────────────────────────────────────────
    st.markdown('<div class="section-header">Client Contribution Detail</div>', unsafe_allow_html=True)

    cm_tbl = client_contrib.copy()

    for c in ["revenue", "cogs", "fixed_cost", "gross_margin", "labor", "contribution"]:
        cm_tbl[c] = (cm_tbl[c] / 1e6).round(2)

    cm_tbl = cm_tbl.sort_values("cm_pct", ascending=False)
    cm_tbl = cm_tbl.rename(columns={
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue",
        "cogs": "COGS",
        "fixed_cost": "Fixed Cost",
        "gross_margin": "Gross Margin",
        "labor": "Labor",
        "contribution": "Contribution",
        "gm_pct": "GM %",
        "cm_pct": "CM %",
        "labor_pct": "Labor % Rev",
    })

    st.dataframe(
        cm_tbl,
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
            "Labor % Rev": st.column_config.NumberColumn("Labor % Rev", format="%.1f%%"),
        },
    )

    st.download_button(
        "Download Contribution Detail CSV",
        cm_tbl.to_csv(index=False).encode(),
        "contribution_detail.csv",
        "text/csv",
        key="cm_dl",
    )