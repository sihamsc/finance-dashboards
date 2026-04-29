"""
Profitability tab — merges Gross Margin and Contribution into one view.

Toggle at the top switches between:
  Gross Margin   — GM%, COGS, Fixed Cost decomposition
  Contribution   — CM%, Labor efficiency view

Both modes share the same layout:
  1. Narrative headline
  2. Service Line distribution (Bar / Treemap toggle at tab level)
  3. Sub-Service Line distribution (filtered by SL)
  4. Monthly trend (dual-axis: $ + %)
  5. Client profitability matrix (scatter with contextual quadrant labels)
  6. Client trend
  7. Detail table + CSV download
"""

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
from src.utils.constants import GM_SEGMENT_DISPLAY, CM_SEGMENT_DISPLAY, SEGMENT_COLORS, TOP_N_OPTIONS, TOP_N_DEFAULT
from src.utils.filters import clean_for_visuals, MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m


# ─────────────────────────────────────────────────────────────
# Shared data builders
# ─────────────────────────────────────────────────────────────

def _monthly_gm_frame(df, group_filters=None):
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
    out["gm_pct"] = (out["gross_margin"] / out["revenue"].replace(0, float("nan")) * 100).round(1)
    return out


def _monthly_cm_frame(df_gm, df_lab, group_filters=None):
    gm = df_gm.copy()
    lab = df_lab.copy()
    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                gm  = gm[gm[col]   == val]
                lab = lab[lab[col]  == val]
    gm_m = (
        gm.groupby(["yr", "month_num", "accounting_period_start_date"])
        .agg(revenue=("revenue", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
        .sort_values("accounting_period_start_date")
    )
    lab_m = (
        lab.groupby(["yr", "month_num", "accounting_period_start_date"])["labour_cost"]
        .sum().reset_index().rename(columns={"labour_cost": "labor"})
    )
    out = gm_m.merge(lab_m, on=["yr", "month_num", "accounting_period_start_date"], how="left")
    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    out["contribution_m"] = out["contribution"] / 1e6
    out["cm_pct"] = (out["contribution"] / out["revenue"].replace(0, float("nan")) * 100).round(1)
    return out


def _client_gm(df_curr, df_lab_curr):
    lab_cl = (
        df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
        .sum().reset_index().rename(columns={"labour_cost": "labor"})
    )
    cl = (
        clean_for_visuals(df_curr)
        .groupby("top_level_parent_customer_name")
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"),
             fixed_cost=("fixed_cost", "sum"), gross_margin=("gross_margin", "sum"))
        .reset_index()
    )
    cl = cl.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl["labor"] = cl["labor"].fillna(0)
    cl["contribution"] = cl["gross_margin"] - cl["labor"]
    cl["gm_pct"] = (cl["gross_margin"] / cl["revenue"].replace(0, float("nan")) * 100).round(1)
    cl["cm_pct"] = (cl["contribution"] / cl["revenue"].replace(0, float("nan")) * 100).round(1)
    return cl[cl["revenue"] > 0].sort_values("revenue", ascending=False)


def _contribution_frame(df_gm, df_lab):
    gm = (
        df_gm.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        ).agg(revenue=("revenue","sum"), cogs=("cogs","sum"),
              fixed_cost=("fixed_cost","sum"), gross_margin=("gross_margin","sum"))
        .reset_index()
    )
    lab = (
        df_lab.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )["labour_cost"].sum().reset_index().rename(columns={"labour_cost": "labor"})
    )
    out = gm.merge(lab, on=["service_line_name","sub_service_line_name","top_level_parent_customer_name"], how="left")
    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    return out


# ─────────────────────────────────────────────────────────────
# Dual-axis trend charts
# ─────────────────────────────────────────────────────────────

def _gm_chart(df, title, PT, LC, prior_df=None, month_order=None):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = "month" if "month" in df.columns else "accounting_period_start_date"
    fig.add_trace(go.Scatter(x=df[x], y=df["gross_margin_m"], name="GM $M",
                             mode="lines+markers", line=dict(width=2.5, color=LC)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df[x], y=df["gm_pct"], name="GM %",
                             mode="lines+markers", line=dict(width=2.5, dash="dot", color="#d7f34a")), secondary_y=True)
    if prior_df is not None:
        px_ = "month" if "month" in prior_df.columns else "accounting_period_start_date"
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df["gross_margin_m"], name="GM $M (PY)",
                                 mode="lines+markers", line=dict(width=1.5, color=LC, dash="dot"), opacity=0.4), secondary_y=False)
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df["gm_pct"], name="GM % (PY)",
                                 mode="lines+markers", line=dict(width=1.5, dash="dot", color="#d7f34a"), opacity=0.4), secondary_y=True)
    fig.update_layout(**{**PT, "title": title, "title_font_color": "#cbd5e1", "height": 340,
                         "legend": dict(orientation="h", y=1.12, x=0)})
    fig.update_yaxes(title_text="GM ($M)", tickprefix="$", ticksuffix="M", secondary_y=False)
    fig.update_yaxes(title_text="GM %", ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    if month_order:
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)
    st.plotly_chart(fig, use_container_width=True)


def _cm_chart(df, title, PT, LC, prior_df=None, month_order=None):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = "month" if "month" in df.columns else "accounting_period_start_date"
    fig.add_trace(go.Scatter(x=df[x], y=df["contribution_m"], name="Contribution $M",
                             mode="lines+markers", line=dict(width=2.5, color=LC)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df[x], y=df["cm_pct"], name="CM %",
                             mode="lines+markers", line=dict(width=2.5, dash="dot", color="#d7f34a")), secondary_y=True)
    if prior_df is not None:
        px_ = "month" if "month" in prior_df.columns else "accounting_period_start_date"
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df["contribution_m"], name="CM $M (PY)",
                                 mode="lines+markers", line=dict(width=1.5, color=LC, dash="dot"), opacity=0.4), secondary_y=False)
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df["cm_pct"], name="CM % (PY)",
                                 mode="lines+markers", line=dict(width=1.5, dash="dot", color="#d7f34a"), opacity=0.4), secondary_y=True)
    fig.update_layout(**{**PT, "title": title, "title_font_color": "#cbd5e1", "height": 340,
                         "legend": dict(orientation="h", y=1.12, x=0)})
    fig.update_yaxes(title_text="Contribution ($M)", tickprefix="$", ticksuffix="M", secondary_y=False)
    fig.update_yaxes(title_text="CM %", ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    if month_order:
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Index helpers
# ─────────────────────────────────────────────────────────────

def _gm_index(ctx, curr_df, prior_df, metric, group_filters=None):
    curr_m = _monthly_gm_frame(curr_df, group_filters)
    prior_m = _monthly_gm_frame(prior_df, group_filters)
    col = "gross_margin" if metric == "GM $" else "gm_pct"
    return pd.DataFrame(build_index_rows(ctx, curr_m, prior_m, col))


def _cm_index(ctx, curr_gm, curr_lab, prior_gm, prior_lab, metric, group_filters=None):
    curr_m = _monthly_cm_frame(curr_gm, curr_lab, group_filters)
    prior_m = _monthly_cm_frame(prior_gm, prior_lab, group_filters)
    col = "contribution" if metric == "Contribution $" else "cm_pct"
    return pd.DataFrame(build_index_rows(ctx, curr_m, prior_m, col))


# ─────────────────────────────────────────────────────────────
# Bubble chart
# ─────────────────────────────────────────────────────────────

def _bubble(cl_plot, y_col, y_label, segment_display, med_rev, med_y, title, PT):
    cl_plot = cl_plot.copy()
    cl_plot["_segment"] = cl_plot["segment"].map(segment_display).fillna(cl_plot["segment"])

    med_rev_str = fmt_m(med_rev)
    med_y_str   = f"{med_y:.1f}%"

    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.75rem;">'
        f'Median splits: revenue = <span style="color:#cbd5e1">{med_rev_str}</span> &nbsp;|&nbsp; '
        f'{y_label} = <span style="color:#cbd5e1">{med_y_str}</span>. &nbsp;&nbsp;'
        f'<span style="color:#4ade80">■</span> Stars — Protect &nbsp;'
        f'<span style="color:#60a5fa">■</span> Rising — Scale &nbsp;'
        f'<span style="color:#fb923c">■</span> Volume — Fix Margin &nbsp;'
        f'<span style="color:#f87171">■</span> At Risk — Review'
        f'</div>',
        unsafe_allow_html=True,
    )

    fig = px.scatter(
        cl_plot, x="revenue", y=y_col,
        color="_segment", color_discrete_map=SEGMENT_COLORS,
        text="top_level_parent_customer_name",
        hover_name="top_level_parent_customer_name",
        hover_data={"revenue": ":,.0f", "gm_pct": ":.1f", "cm_pct": ":.1f",
                    "gross_margin": ":,.0f", "labor": ":,.0f", "contribution": ":,.0f", "_segment": False},
        title=title,
        labels={"revenue": "Revenue ($)", y_col: y_label, "_segment": "Segment"},
    )
    fig.update_traces(
        marker=dict(size=13, opacity=0.88, line=dict(width=1, color="#0b0f16")),
        textposition="top center",
        textfont=dict(size=9, color="#cbd5e1", family="DM Sans"),
    )
    fig.add_vline(x=med_rev, line_width=1, line_dash="dot", line_color="#94a3b8",
                  annotation_text=f"Median: {med_rev_str}", annotation_position="top",
                  annotation_font=dict(size=9, color="#6b7280", family="DM Mono"))
    fig.add_hline(y=med_y, line_width=1, line_dash="dot", line_color="#94a3b8",
                  annotation_text=f"Median: {med_y_str}", annotation_position="right",
                  annotation_font=dict(size=9, color="#6b7280", family="DM Mono"))
    fig.update_layout(**PT, title_font_color="#cbd5e1", height=520, legend_title_text="Segment")
    fig.update_xaxes(tickformat="$,.0s")
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# GM sections
# ─────────────────────────────────────────────────────────────

def _render_gm(ctx, chart_type):
    palette, PT = ctx["palette"], ctx["PT"]
    df_curr      = ctx["df_curr"]
    df_prior     = ctx["df_prior"]
    df_lab_curr  = ctx["df_lab_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    df_prior_decomp = df_prior

    BS = palette["blue_scale"]
    LC = palette["line_current"]

    base         = clean_for_visuals(df_curr_decomp)
    prior_base   = clean_for_visuals(df_prior_decomp)
    filtered     = clean_for_visuals(df_curr)
    filtered_pri = clean_for_visuals(df_prior)
    cl_gm        = _client_gm(df_curr, df_lab_curr)

    # ── SL distribution ──────────────────────────────────────
    st.markdown('<div class="section-header">Gross Margin by Service Line</div>', unsafe_allow_html=True)
    gm_sl = (base.groupby("service_line_name")
             .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
             .reset_index())
    if chart_type == "Treemap":
        render_treemap(gm_sl, "service_line_name", "gross_margin", "", BS, "Gross Margin")
    else:
        render_bar(gm_sl, "service_line_name", "gross_margin", "", BS, "Gross Margin")

    # ── SSL distribution ─────────────────────────────────────
    st.markdown('<div class="section-header">Gross Margin by Sub-Service Line</div>', unsafe_allow_html=True)
    ssl_options = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Filter by Service Line", ssl_options, key="profit_gm_ssl_sl")
    ssl_src = base if selected_sl == "All" else base[base["service_line_name"] == selected_sl]
    gm_ssl = (ssl_src.groupby("sub_service_line_name")
              .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
              .reset_index())
    gm_ssl = gm_ssl[gm_ssl["sub_service_line_name"] != "(blank)"]
    lbl = f"— {selected_sl}" if selected_sl != "All" else ""
    if chart_type == "Treemap":
        render_treemap(gm_ssl, "sub_service_line_name", "gross_margin", lbl, BS, "Gross Margin")
    else:
        render_bar(gm_ssl, "sub_service_line_name", "gross_margin", lbl, BS, "Gross Margin")

    # ── Monthly trend ────────────────────────────────────────
    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        trend_sl = st.selectbox("Service Line", ["All"]+sorted(base["service_line_name"].dropna().unique().tolist()), key="profit_gm_trend_sl")
    ssl_src2 = base if trend_sl == "All" else base[base["service_line_name"] == trend_sl]
    with tc2:
        trend_ssl = st.selectbox("Sub Service Line", ["All"]+sorted(ssl_src2["sub_service_line_name"].dropna().unique().tolist()), key="profit_gm_trend_ssl")
    trend_f = {"service_line_name": trend_sl, "sub_service_line_name": trend_ssl}
    trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="profit_gm_trend_mode")
    if trend_mode == "Raw":
        month_order = (ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"]
                       else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"]+1)])
        curr_m = _monthly_gm_frame(base, trend_f)
        curr_m["month"] = curr_m["month_num"].map(MONTH_MAP)
        pri_m = _monthly_gm_frame(prior_base, trend_f)
        pri_m["month"] = pri_m["month_num"].map(MONTH_MAP)
        _gm_chart(curr_m, "", PT, LC, prior_df=pri_m, month_order=month_order)
    else:
        idx_metric = st.radio("Index metric", ["GM $", "GM %"], horizontal=True, key="profit_gm_idx_metric")
        idx_df = _gm_index(ctx, base, prior_base, idx_metric, trend_f)
        render_index_chart(idx_df, f"vs Prior Year — 100 = PY ({idx_metric})", PT)

    # ── Client bubble ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Profitability Matrix</div>', unsafe_allow_html=True)
    top_n = st.select_slider("Top N clients", options=TOP_N_OPTIONS, value=TOP_N_DEFAULT, key="profit_gm_topn")
    cl_plot = cl_gm.head(top_n).copy()
    med_rev    = cl_plot["revenue"].median()
    med_gm_pct = cl_plot["gm_pct"].median()
    cl_plot["segment"] = cl_plot.apply(
        lambda r: classify_segment(r, "revenue", "gm_pct", med_rev, med_gm_pct, "Margin"), axis=1
    )
    _bubble(cl_plot, "gm_pct", "Gross Margin %", GM_SEGMENT_DISPLAY, med_rev, med_gm_pct,
            f"GM% vs Revenue — Top {top_n} Clients", PT)

    # ── Client trend ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Trend</div>', unsafe_allow_html=True)
    cl_opts = ["All"] + sorted(filtered["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_cl = st.selectbox("Client", cl_opts, key="profit_gm_cl_trend")
    cl_f = {"top_level_parent_customer_name": sel_cl}
    cl_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="profit_gm_cl_mode")
    if cl_mode == "Raw":
        month_order = (ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"]
                       else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"]+1)])
        cm2 = _monthly_gm_frame(filtered, cl_f)
        cm2["month"] = cm2["month_num"].map(MONTH_MAP)
        pm2 = _monthly_gm_frame(filtered_pri, cl_f)
        pm2["month"] = pm2["month_num"].map(MONTH_MAP)
        _gm_chart(cm2, f"— {sel_cl}", PT, LC, prior_df=pm2, month_order=month_order)
    else:
        idx_m = st.radio("Index metric", ["GM $", "GM %"], horizontal=True, key="profit_gm_cl_idx")
        idx_df2 = _gm_index(ctx, filtered, filtered_pri, idx_m, cl_f)
        render_index_chart(idx_df2, f"— {sel_cl}  vs Prior Year — 100 = PY ({idx_m})", PT)

    # ── Detail table ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Margin Detail</div>', unsafe_allow_html=True)
    tbl = cl_gm.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values("gm_pct", ascending=False).rename(columns={
        "top_level_parent_customer_name": "Client", "revenue": "Revenue",
        "cogs": "COGS", "fixed_cost": "Fixed Cost", "gross_margin": "Gross Margin",
        "labor": "Labor", "contribution": "Contribution", "gm_pct": "GM %", "cm_pct": "CM %",
    })
    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",    format="$%.2f"),
        "COGS":         st.column_config.NumberColumn("COGS ($M)",       format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",         format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",      format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("CM ($M)",         format="$%.2f"),
        "GM %":         st.column_config.NumberColumn("GM %",            format="%.1f%%"),
        "CM %":         st.column_config.NumberColumn("CM %",            format="%.1f%%"),
    })
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       "margin_detail.csv", "text/csv", key="profit_gm_dl")


# ─────────────────────────────────────────────────────────────
# CM sections
# ─────────────────────────────────────────────────────────────

def _render_cm(ctx, chart_type):
    palette, PT   = ctx["palette"], ctx["PT"]
    df_curr       = ctx["df_curr"]
    df_prior      = ctx["df_prior"]
    df_lab_curr   = ctx["df_lab_curr"]
    df_lab_prior  = ctx["df_lab_prior"]
    df_curr_decomp      = ctx["df_curr_decomp"]
    df_prior_decomp     = df_prior
    df_lab_curr_decomp  = ctx["df_lab_curr_decomp"]
    df_lab_prior_decomp = df_lab_prior

    BS = palette["blue_scale"]
    LC = palette["line_current"]

    base         = clean_for_visuals(df_curr_decomp)
    prior_base   = clean_for_visuals(df_prior_decomp)
    lab_base     = clean_for_visuals(df_lab_curr_decomp)
    prior_lab    = clean_for_visuals(df_lab_prior_decomp)
    filtered     = clean_for_visuals(df_curr)
    filtered_pri = clean_for_visuals(df_prior)
    filtered_lab = clean_for_visuals(df_lab_curr)
    filt_lab_pri = clean_for_visuals(df_lab_prior)

    contrib_base = _contribution_frame(base, lab_base)
    cl_contrib   = _client_gm(df_curr, df_lab_curr)  # already has contribution column

    # ── SL distribution ──────────────────────────────────────
    st.markdown('<div class="section-header">Contribution by Service Line</div>', unsafe_allow_html=True)
    cm_sl = (contrib_base.groupby("service_line_name")
             .agg(revenue=("revenue","sum"), contribution=("contribution","sum"))
             .reset_index())
    if chart_type == "Treemap":
        render_treemap(cm_sl, "service_line_name", "contribution", "", BS, "Contribution")
    else:
        render_bar(cm_sl, "service_line_name", "contribution", "", BS, "Contribution")

    # ── SSL distribution ─────────────────────────────────────
    st.markdown('<div class="section-header">Contribution by Sub-Service Line</div>', unsafe_allow_html=True)
    ssl_options = ["All"] + sorted(contrib_base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Filter by Service Line", ssl_options, key="profit_cm_ssl_sl")
    ssl_src = contrib_base if selected_sl == "All" else contrib_base[contrib_base["service_line_name"] == selected_sl]
    cm_ssl = (ssl_src.groupby("sub_service_line_name")
              .agg(revenue=("revenue","sum"), contribution=("contribution","sum"))
              .reset_index())
    cm_ssl = cm_ssl[cm_ssl["sub_service_line_name"] != "(blank)"]
    lbl = f"— {selected_sl}" if selected_sl != "All" else ""
    if chart_type == "Treemap":
        render_treemap(cm_ssl, "sub_service_line_name", "contribution", lbl, BS, "Contribution")
    else:
        render_bar(cm_ssl, "sub_service_line_name", "contribution", lbl, BS, "Contribution")

    # ── Monthly trend ────────────────────────────────────────
    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        trend_sl = st.selectbox("Service Line", ["All"]+sorted(base["service_line_name"].dropna().unique().tolist()), key="profit_cm_trend_sl")
    ssl_src2 = base if trend_sl == "All" else base[base["service_line_name"] == trend_sl]
    with tc2:
        trend_ssl = st.selectbox("Sub Service Line", ["All"]+sorted(ssl_src2["sub_service_line_name"].dropna().unique().tolist()), key="profit_cm_trend_ssl")
    trend_f = {"service_line_name": trend_sl, "sub_service_line_name": trend_ssl}
    trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="profit_cm_trend_mode")
    if trend_mode == "Raw":
        month_order = (ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"]
                       else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"]+1)])
        curr_m = _monthly_cm_frame(base, lab_base, trend_f)
        curr_m["month"] = curr_m["month_num"].map(MONTH_MAP)
        pri_m = _monthly_cm_frame(prior_base, prior_lab, trend_f)
        pri_m["month"] = pri_m["month_num"].map(MONTH_MAP)
        _cm_chart(curr_m, "", PT, LC, prior_df=pri_m, month_order=month_order)
    else:
        idx_metric = st.radio("Index metric", ["Contribution $", "CM %"], horizontal=True, key="profit_cm_idx_metric")
        idx_df = _cm_index(ctx, base, lab_base, prior_base, prior_lab, idx_metric, trend_f)
        render_index_chart(idx_df, f"vs Prior Year — 100 = PY ({idx_metric})", PT)

    # ── Client bubble ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Profitability Matrix</div>', unsafe_allow_html=True)
    top_n = st.select_slider("Top N clients", options=TOP_N_OPTIONS, value=TOP_N_DEFAULT, key="profit_cm_topn")
    cl_plot = cl_contrib.head(top_n).copy()
    med_rev    = cl_plot["revenue"].median()
    med_cm_pct = cl_plot["cm_pct"].median()
    cl_plot["segment"] = cl_plot.apply(
        lambda r: classify_segment(r, "revenue", "cm_pct", med_rev, med_cm_pct, "Contribution"), axis=1
    )
    _bubble(cl_plot, "cm_pct", "Contribution %", CM_SEGMENT_DISPLAY, med_rev, med_cm_pct,
            f"CM% vs Revenue — Top {top_n} Clients", PT)

    # ── Client trend ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Trend</div>', unsafe_allow_html=True)
    cl_opts = ["All"] + sorted(filtered["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_cl = st.selectbox("Client", cl_opts, key="profit_cm_cl_trend")
    cl_f = {"top_level_parent_customer_name": sel_cl}
    cl_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="profit_cm_cl_mode")
    if cl_mode == "Raw":
        month_order = (ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"]
                       else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"]+1)])
        cm2 = _monthly_cm_frame(filtered, filtered_lab, cl_f)
        cm2["month"] = cm2["month_num"].map(MONTH_MAP)
        pm2 = _monthly_cm_frame(filtered_pri, filt_lab_pri, cl_f)
        pm2["month"] = pm2["month_num"].map(MONTH_MAP)
        _cm_chart(cm2, f"— {sel_cl}", PT, LC, prior_df=pm2, month_order=month_order)
    else:
        idx_m = st.radio("Index metric", ["Contribution $", "CM %"], horizontal=True, key="profit_cm_cl_idx")
        idx_df2 = _cm_index(ctx, filtered, filtered_lab, filtered_pri, filt_lab_pri, idx_m, cl_f)
        render_index_chart(idx_df2, f"— {sel_cl}  vs Prior Year — 100 = PY ({idx_m})", PT)

    # ── Detail table ────────────────────────────────────────
    st.markdown('<div class="section-header">Client Contribution Detail</div>', unsafe_allow_html=True)
    tbl = cl_contrib.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values("cm_pct", ascending=False).rename(columns={
        "top_level_parent_customer_name": "Client", "revenue": "Revenue",
        "cogs": "COGS", "fixed_cost": "Fixed Cost", "gross_margin": "Gross Margin",
        "labor": "Labor", "contribution": "Contribution", "gm_pct": "GM %", "cm_pct": "CM %",
    })
    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",    format="$%.2f"),
        "COGS":         st.column_config.NumberColumn("COGS ($M)",       format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)", format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",         format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",      format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("CM ($M)",         format="$%.2f"),
        "GM %":         st.column_config.NumberColumn("GM %",            format="%.1f%%"),
        "CM %":         st.column_config.NumberColumn("CM %",            format="%.1f%%"),
    })
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       "contribution_detail.csv", "text/csv", key="profit_cm_dl")


# ─────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────

def render_profitability(ctx):
    """Render the combined Profitability tab (Gross Margin + Contribution).

    A top toggle switches between views.
    A single chart-type toggle controls Treemap vs Bar for all distribution sections.
    """
    gm      = ctx["gm"]
    gm_py   = ctx["gm_py"]
    gm_pct  = ctx["gm_pct"]
    gm_pct_py = ctx["gm_pct_py"]
    contrib = ctx["contrib"]
    contrib_py = ctx["contrib_py"]
    cm_pct  = ctx["cm_pct"]
    cm_pct_py = ctx["cm_pct_py"]
    period  = ctx["period_label"]

    gm_dir  = "improved" if gm_pct >= gm_pct_py else "declined"
    cm_dir  = "improved" if cm_pct >= cm_pct_py else "declined"

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #4ade80;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">
                <b>{period}:</b>
                &nbsp; GM = <b>{fmt_m(gm)}</b> ({gm_pct:.1f}%, {gm_dir} {abs(gm_pct-gm_pct_py):.1f}pts vs PY)
                &nbsp;|&nbsp;
                Contribution = <b>{fmt_m(contrib)}</b> ({cm_pct:.1f}% CM, {cm_dir} {abs(cm_pct-cm_pct_py):.1f}pts vs PY)
                &nbsp;|&nbsp;
                Labor drag = <b>{(gm_pct - cm_pct):.1f}pts</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Top-level controls in one row ─────────────────────────
    ctl1, ctl2 = st.columns([3, 1])
    with ctl1:
        metric_mode = st.radio(
            "Metric",
            ["Gross Margin", "Contribution"],
            horizontal=True,
            key="profit_metric_mode",
        )
    with ctl2:
        chart_type = st.radio(
            "Chart",
            ["Bar", "Treemap"],
            horizontal=True,
            key="profit_chart_type",
        )

    st.divider()

    if metric_mode == "Gross Margin":
        _render_gm(ctx, chart_type)
    else:
        _render_cm(ctx, chart_type)