"""
Profitability tab — Gross Margin and Contribution in one view.

Top toggle switches between metrics.
Both modes follow the same unified layout:
  Service Line  : distribution (Bar/Tile) → inline trend (Raw/Index)
  Sub-SL        : SL filter → distribution → inline trend
  Client        : matrix (scatter) → client selector → inline trend
  Detail        : table + CSV download
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
    render_index_chart,
)
from src.utils.constants import (
    GM_SEGMENT_DISPLAY, CM_SEGMENT_DISPLAY, SEGMENT_COLORS,
    TOP_N_OPTIONS, TOP_N_DEFAULT, METRIC_COLOR,
)
from src.utils.filters import clean_for_visuals, MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m
from src.utils.view_helpers import dist_chart, inline_trend


_GM_ACCENT = METRIC_COLOR["gross_margin"]
_CM_ACCENT = METRIC_COLOR["contribution"]


# ─────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────

def _monthly_gm(df, group_filters=None):
    d = df.copy()
    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                d = d[d[col] == val]
    out = (d.groupby(["yr","month_num","accounting_period_start_date"])
           .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
           .reset_index().sort_values("accounting_period_start_date"))
    out["gross_margin_m"] = out["gross_margin"] / 1e6
    out["gm_pct"] = (out["gross_margin"] / out["revenue"].replace(0,float("nan")) * 100).round(1)
    return out


def _monthly_cm(df_gm, df_lab, group_filters=None):
    gm = df_gm.copy()
    lab = df_lab.copy()
    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                gm  = gm[gm[col]  == val]
                lab = lab[lab[col] == val]
    gm_m = (gm.groupby(["yr","month_num","accounting_period_start_date"])
            .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
            .reset_index().sort_values("accounting_period_start_date"))
    lab_m = (lab.groupby(["yr","month_num","accounting_period_start_date"])["labour_cost"]
             .sum().reset_index().rename(columns={"labour_cost":"labor"}))
    out = gm_m.merge(lab_m, on=["yr","month_num","accounting_period_start_date"], how="left")
    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    out["contribution_m"] = out["contribution"] / 1e6
    out["cm_pct"] = (out["contribution"] / out["revenue"].replace(0,float("nan")) * 100).round(1)
    return out


def _client_frame(df_curr, df_lab_curr):
    lab_cl = (df_lab_curr.groupby("top_level_parent_customer_name")["labour_cost"]
              .sum().reset_index().rename(columns={"labour_cost":"labor"}))
    cl = (clean_for_visuals(df_curr)
          .groupby("top_level_parent_customer_name")
          .agg(revenue=("revenue","sum"), cogs=("cogs","sum"),
               fixed_cost=("fixed_cost","sum"), gross_margin=("gross_margin","sum"))
          .reset_index())
    cl = cl.merge(lab_cl, on="top_level_parent_customer_name", how="left")
    cl["labor"] = cl["labor"].fillna(0)
    cl["contribution"] = cl["gross_margin"] - cl["labor"]
    cl["gm_pct"] = (cl["gross_margin"] / cl["revenue"].replace(0,float("nan")) * 100).round(1)
    cl["cm_pct"] = (cl["contribution"] / cl["revenue"].replace(0,float("nan")) * 100).round(1)
    return cl[cl["revenue"] > 0].sort_values("revenue", ascending=False)


def _contrib_sl_frame(df_gm, df_lab):
    gm = (df_gm.groupby(["service_line_name","sub_service_line_name",
                          "top_level_parent_customer_name"], dropna=False)
          .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
          .reset_index())
    lab = (df_lab.groupby(["service_line_name","sub_service_line_name",
                            "top_level_parent_customer_name"], dropna=False)["labour_cost"]
           .sum().reset_index().rename(columns={"labour_cost":"labor"}))
    out = gm.merge(lab, on=["service_line_name","sub_service_line_name",
                              "top_level_parent_customer_name"], how="left")
    out["labor"] = out["labor"].fillna(0)
    out["contribution"] = out["gross_margin"] - out["labor"]
    return out


# ─────────────────────────────────────────────────────────────
# Dual-axis monthly charts (GM / CM)
# ─────────────────────────────────────────────────────────────

def _dual_chart(df, metric_col, pct_col, metric_label, pct_label, title, PT, accent, prior_df=None, month_order=None):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = "month" if "month" in df.columns else "accounting_period_start_date"
    fig.add_trace(go.Scatter(x=df[x], y=df[f"{metric_col}_m"], name=f"{metric_label} $M",
                             mode="lines+markers", line=dict(width=2.5, color=accent)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df[x], y=df[pct_col], name=pct_label,
                             mode="lines+markers", line=dict(width=2.5, dash="dot", color="#d7f34a")), secondary_y=True)
    if prior_df is not None:
        px_ = "month" if "month" in prior_df.columns else "accounting_period_start_date"
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df[f"{metric_col}_m"],
                                 name=f"{metric_label} $M (PY)", mode="lines+markers",
                                 line=dict(width=1.5, color=accent, dash="dot"), opacity=0.4), secondary_y=False)
        fig.add_trace(go.Scatter(x=prior_df[px_], y=prior_df[pct_col],
                                 name=f"{pct_label} (PY)", mode="lines+markers",
                                 line=dict(width=1.5, dash="dot", color="#d7f34a"), opacity=0.4), secondary_y=True)
    fig.update_layout(**{**PT, "title": title, "title_font_color": "#cbd5e1", "height": 340,
                         "legend": dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)",
                                        font=dict(color="#cbd5e1", size=10))})
    fig.update_yaxes(title_text=f"{metric_label} ($M)", tickprefix="$", ticksuffix="M", secondary_y=False)
    fig.update_yaxes(title_text=pct_label, ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    if month_order:
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)
    st.plotly_chart(fig, use_container_width=True)


def _inline_dual_trend(ctx, curr_gm, prior_gm, curr_lab, prior_lab, metric, accent, PT, key_prefix):
    """Render Raw (dual-axis) / Index trend inline."""
    trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True,
                          key=f"{key_prefix}_trend")
    is_gm = metric == "gm"
    month_order = (ordered_month_axis_labels(ctx["curr_ym"]) if ctx["is_rolling"]
                   else [MONTH_MAP[m] for m in range(ctx["m_from"], ctx["m_to"]+1)])
    if trend_mode == "Raw":
        if is_gm:
            curr_m = _monthly_gm(curr_gm)
            curr_m["month"] = curr_m["month_num"].map(MONTH_MAP)
            pri_m  = _monthly_gm(prior_gm)
            pri_m["month"] = pri_m["month_num"].map(MONTH_MAP)
            _dual_chart(curr_m, "gross_margin", "gm_pct", "Gross Margin", "GM %",
                        "", PT, accent, prior_df=pri_m, month_order=month_order)
        else:
            curr_m = _monthly_cm(curr_gm, curr_lab)
            curr_m["month"] = curr_m["month_num"].map(MONTH_MAP)
            pri_m  = _monthly_cm(prior_gm, prior_lab)
            pri_m["month"] = pri_m["month_num"].map(MONTH_MAP)
            _dual_chart(curr_m, "contribution", "cm_pct", "Contribution", "CM %",
                        "", PT, accent, prior_df=pri_m, month_order=month_order)
    else:
        if is_gm:
            curr_agg = curr_gm.groupby(["yr","month_num"])["gross_margin"].sum().reset_index()
            pri_agg  = prior_gm.groupby(["yr","month_num"])["gross_margin"].sum().reset_index()
            idx_df   = pd.DataFrame(build_index_rows(ctx, curr_agg, pri_agg, "gross_margin"))
        else:
            curr_m = _monthly_cm(curr_gm, curr_lab)
            pri_m  = _monthly_cm(prior_gm, prior_lab)
            curr_agg = curr_m[["yr","month_num","contribution"]].copy()
            pri_agg  = pri_m[["yr","month_num","contribution"]].copy()
            idx_df = pd.DataFrame(build_index_rows(ctx, curr_agg, pri_agg, "contribution"))
        render_index_chart(idx_df, "vs Prior Year — 100 = PY", PT)


# ─────────────────────────────────────────────────────────────
# Client bubble
# ─────────────────────────────────────────────────────────────

def _bubble(cl_plot, y_col, y_label, segment_display, med_rev, med_y, top_n, PT):
    cl_plot = cl_plot.copy()
    cl_plot["_segment"] = cl_plot["segment"].map(segment_display).fillna(cl_plot["segment"])

    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.75rem;">'
        f'Median splits: revenue = <span style="color:#cbd5e1">{fmt_m(med_rev)}</span> &nbsp;|&nbsp; '
        f'{y_label} = <span style="color:#cbd5e1">{med_y:.1f}%</span>. &nbsp;&nbsp;'
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
        title=f"{y_label} vs Revenue — Top {top_n} Clients",
        labels={"revenue": "Revenue ($)", y_col: y_label, "_segment": "Segment"},
    )
    fig.update_traces(
        marker=dict(size=13, opacity=0.88, line=dict(width=1, color="#0b0f16")),
        textposition="top center",
        textfont=dict(size=9, color="#cbd5e1", family="DM Sans"),
    )
    fig.add_vline(x=med_rev, line_width=1, line_dash="dot", line_color="#94a3b8",
                  annotation_text=f"Median: {fmt_m(med_rev)}", annotation_position="top",
                  annotation_font=dict(size=9, color="#6b7280", family="DM Mono"))
    fig.add_hline(y=med_y, line_width=1, line_dash="dot", line_color="#94a3b8",
                  annotation_text=f"Median: {med_y:.1f}%", annotation_position="right",
                  annotation_font=dict(size=9, color="#6b7280", family="DM Mono"))
    fig.update_layout(**PT if isinstance(PT, dict) else {}, title_font_color="#cbd5e1",
                      height=520, legend_title_text="Segment")
    fig.update_xaxes(tickformat="$,.0s")
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Section renderers (shared layout for GM and CM)
# ─────────────────────────────────────────────────────────────

def _render_sections(ctx, chart_type, metric, accent):
    """Render SL → SSL → Client → Detail for either 'gm' or 'cm'."""
    is_gm = metric == "gm"
    metric_col   = "gross_margin"   if is_gm else "contribution"
    metric_label = "Gross Margin"   if is_gm else "Contribution"
    pct_col      = "gm_pct"         if is_gm else "cm_pct"
    segment_map  = GM_SEGMENT_DISPLAY if is_gm else CM_SEGMENT_DISPLAY

    df_curr       = ctx["df_curr"]
    df_prior      = ctx["df_prior"]
    df_lab_curr   = ctx["df_lab_curr"]
    df_lab_prior  = ctx["df_lab_prior"]
    df_curr_decomp      = ctx["df_curr_decomp"]
    df_prior_decomp     = df_prior
    df_lab_curr_decomp  = ctx["df_lab_curr_decomp"]
    df_lab_prior_decomp = df_lab_prior
    PT = ctx["PT"]

    base      = clean_for_visuals(df_curr_decomp)
    prior_base = clean_for_visuals(df_prior_decomp)
    lab_base  = clean_for_visuals(df_lab_curr_decomp)
    lab_prior = clean_for_visuals(df_lab_prior_decomp)
    filtered  = clean_for_visuals(df_curr)
    filt_pri  = clean_for_visuals(df_prior)

    # Build SL-level aggregation for distribution
    if is_gm:
        sl_agg = (base.groupby("service_line_name")
                  .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
                  .reset_index())
    else:
        cf = _contrib_sl_frame(base, lab_base)
        sl_agg = (cf.groupby("service_line_name")
                  .agg(revenue=("revenue","sum"), contribution=("contribution","sum"))
                  .reset_index())

    cl_frame = _client_frame(df_curr, df_lab_curr)

    # ── SERVICE LINE ─────────────────────────────────────────
    st.markdown(f'<div class="section-header">{metric_label} by Service Line</div>',
                unsafe_allow_html=True)
    dist_chart(sl_agg, "service_line_name", metric_col, accent, PT, chart_type,
               f"profit_{metric}_sl", value_label=metric_label)
    _inline_dual_trend(ctx, base, prior_base, lab_base, lab_prior, metric, accent, PT,
                       f"profit_{metric}_sl")

    # ── SUB-SERVICE LINE ─────────────────────────────────────
    st.markdown(f'<div class="section-header">{metric_label} by Sub-Service Line</div>',
                unsafe_allow_html=True)
    sl_opts = sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Service Line", sl_opts, key=f"profit_{metric}_ssl_sl")

    if is_gm:
        ssl_src = base[base["service_line_name"] == selected_sl]
        ssl_agg = (ssl_src.groupby("sub_service_line_name")
                   .agg(revenue=("revenue","sum"), gross_margin=("gross_margin","sum"))
                   .reset_index())
    else:
        cf_ssl = _contrib_sl_frame(
            base[base["service_line_name"] == selected_sl],
            lab_base[lab_base["service_line_name"] == selected_sl],
        )
        ssl_agg = (cf_ssl.groupby("sub_service_line_name")
                   .agg(revenue=("revenue","sum"), contribution=("contribution","sum"))
                   .reset_index())
    ssl_agg = ssl_agg[ssl_agg["sub_service_line_name"] != "(blank)"]

    if ssl_agg.empty:
        st.info(f"No sub-service line data for {selected_sl}.")
    else:
        dist_chart(ssl_agg, "sub_service_line_name", metric_col, accent, PT, chart_type,
                   f"profit_{metric}_ssl", value_label=metric_label)
        curr_sl_gm  = base[base["service_line_name"] == selected_sl]
        pri_sl_gm   = prior_base[prior_base["service_line_name"] == selected_sl]
        curr_sl_lab = lab_base[lab_base["service_line_name"] == selected_sl]
        pri_sl_lab  = lab_prior[lab_prior["service_line_name"] == selected_sl]
        _inline_dual_trend(ctx, curr_sl_gm, pri_sl_gm, curr_sl_lab, pri_sl_lab, metric, accent, PT,
                           f"profit_{metric}_ssl")

    # ── CLIENT MATRIX ────────────────────────────────────────
    st.markdown(f'<div class="section-header">Client Profitability Matrix</div>',
                unsafe_allow_html=True)
    top_n = st.select_slider("Top N clients", options=TOP_N_OPTIONS, value=TOP_N_DEFAULT,
                              key=f"profit_{metric}_topn")
    cl_plot = cl_frame.head(top_n).copy()
    med_rev = cl_plot["revenue"].median()
    med_pct = cl_plot[pct_col].median()
    cl_plot["segment"] = cl_plot.apply(
        lambda r: classify_segment(r, "revenue", pct_col, med_rev, med_pct,
                                   "Margin" if is_gm else "Contribution"), axis=1
    )
    _bubble(cl_plot, pct_col, f"{'Gross Margin' if is_gm else 'Contribution'} %",
            segment_map, med_rev, med_pct, top_n, PT)

    # Client trend
    cl_opts = ["All"] + sorted(filtered["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_cl = st.selectbox("Client trend", cl_opts, key=f"profit_{metric}_cl")
    if sel_cl == "All":
        curr_cl_gm, pri_cl_gm, curr_cl_lab, pri_cl_lab = filtered, filt_pri, clean_for_visuals(df_lab_curr), clean_for_visuals(df_lab_prior)
    else:
        curr_cl_gm  = filtered[filtered["top_level_parent_customer_name"] == sel_cl]
        pri_cl_gm   = filt_pri[filt_pri["top_level_parent_customer_name"] == sel_cl]
        curr_cl_lab = clean_for_visuals(df_lab_curr)
        curr_cl_lab = curr_cl_lab[curr_cl_lab["top_level_parent_customer_name"] == sel_cl]
        pri_cl_lab  = clean_for_visuals(df_lab_prior)
        pri_cl_lab  = pri_cl_lab[pri_cl_lab["top_level_parent_customer_name"] == sel_cl]
    _inline_dual_trend(ctx, curr_cl_gm, pri_cl_gm, curr_cl_lab, pri_cl_lab, metric, accent, PT,
                       f"profit_{metric}_cl")

    # ── DETAIL TABLE ─────────────────────────────────────────
    st.markdown(f'<div class="section-header">Client {metric_label} Detail</div>',
                unsafe_allow_html=True)
    tbl = cl_frame.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values(pct_col, ascending=False).rename(columns={
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue", "cogs": "COGS", "fixed_cost": "Fixed Cost",
        "gross_margin": "Gross Margin", "labor": "Labor", "contribution": "Contribution",
        "gm_pct": "GM %", "cm_pct": "CM %",
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
    fname = "margin_detail.csv" if is_gm else "contribution_detail.csv"
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       fname, "text/csv", key=f"profit_{metric}_dl")


# ─────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────

def render_profitability(ctx):
    """Render the combined Profitability tab (Gross Margin + Contribution)."""
    gm, gm_py   = ctx["gm"], ctx["gm_py"]
    gm_pct      = ctx["gm_pct"]
    gm_pct_py   = ctx["gm_pct_py"]
    contrib     = ctx["contrib"]
    contrib_py  = ctx["contrib_py"]
    cm_pct      = ctx["cm_pct"]
    cm_pct_py   = ctx["cm_pct_py"]
    period      = ctx["period_label"]

    gm_dir = "improved" if gm_pct >= gm_pct_py else "declined"
    cm_dir = "improved" if cm_pct >= cm_pct_py else "declined"

    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid {_GM_ACCENT};'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'<b>{period}:</b>'
        f' &nbsp; GM = <b>{fmt_m(gm)}</b> ({gm_pct:.1f}%, {gm_dir} {abs(gm_pct-gm_pct_py):.1f}pts vs PY)'
        f' &nbsp;|&nbsp; Contribution = <b>{fmt_m(contrib)}</b> ({cm_pct:.1f}% CM, {cm_dir} {abs(cm_pct-cm_pct_py):.1f}pts)'
        f' &nbsp;|&nbsp; Labor drag = <b>{(gm_pct - cm_pct):.1f}pts</b>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    ctl1, ctl2 = st.columns([3, 1])
    with ctl1:
        metric_mode = st.radio("Metric", ["Gross Margin", "Contribution"],
                               horizontal=True, key="profit_metric_mode")
    with ctl2:
        chart_type = st.radio("Chart", ["Bar", "Tile"],
                              horizontal=True, key="profit_chart_type")

    st.divider()

    if metric_mode == "Gross Margin":
        _render_sections(ctx, chart_type, "gm", _GM_ACCENT)
    else:
        _render_sections(ctx, chart_type, "cm", _CM_ACCENT)
