import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from src.utils.filters import MONTH_MAP, ordered_month_axis_labels
from src.utils.formatters import fmt_m, safe_pct


def _narrative(ctx):
    """Auto-generate a plain-English period summary sentence."""
    rev, rev_py = ctx["rev"], ctx["rev_py"]
    gm_pct, gm_pct_py = ctx["gm_pct"], ctx["gm_pct_py"]
    contrib, contrib_py = ctx["contrib"], ctx["contrib_py"]
    period = ctx["period_label"]

    rev_dir   = "up" if rev >= rev_py else "down"
    rev_delta = abs(rev - rev_py)
    gm_dir    = "improved" if gm_pct >= gm_pct_py else "declined"
    gm_delta  = abs(gm_pct - gm_pct_py)
    cm_dir    = "up" if contrib >= contrib_py else "down"
    cm_delta  = abs(contrib - contrib_py)

    return (
        f"<b>{period}:</b> Revenue is {fmt_m(rev)}, "
        f"{rev_dir} {fmt_m(rev_delta)} vs prior year. "
        f"GM% has {gm_dir} {gm_delta:.1f}pts to {gm_pct:.1f}%. "
        f"Contribution is {cm_dir} {fmt_m(cm_delta)} at {fmt_m(contrib)}."
    )


def _movement_pills(df_curr, df_prior):
    """Find biggest YoY movers by service line and return HTML pills."""
    curr = df_curr.groupby("service_line_name")["revenue"].sum().reset_index()
    prior = df_prior.groupby("service_line_name")["revenue"].sum().reset_index()
    merged = curr.merge(prior, on="service_line_name", suffixes=("_curr","_prior"))
    merged["delta"] = merged["revenue_curr"] - merged["revenue_prior"]
    merged = merged[~merged["service_line_name"].isin(["(blank)","Unassigned"])]

    if merged.empty:
        return ""

    top_pos = merged.nlargest(1, "delta").iloc[0]
    top_neg = merged.nsmallest(1, "delta").iloc[0]

    pills = ""
    if top_pos["delta"] > 0:
        pills += (
            f'<span style="display:inline-block;background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.3);'
            f'border-radius:20px;padding:0.2rem 0.7rem;font-family:DM Mono,monospace;font-size:9px;'
            f'color:#4ade80;margin-right:0.4rem;">'
            f'▲ {top_pos["service_line_name"]} +{fmt_m(top_pos["delta"])}</span>'
        )
    if top_neg["delta"] < 0:
        pills += (
            f'<span style="display:inline-block;background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);'
            f'border-radius:20px;padding:0.2rem 0.7rem;font-family:DM Mono,monospace;font-size:9px;'
            f'color:#f87171;margin-right:0.4rem;">'
            f'▼ {top_neg["service_line_name"]} {fmt_m(top_neg["delta"])}</span>'
        )
    return pills


def render_overview(ctx):
    palette    = ctx["palette"]
    PT         = ctx["PT"]
    rev        = ctx["rev"]
    cogs       = ctx["cogs"]
    fixed_cost = ctx["fixed_cost"]
    labor      = ctx["labor"]
    gm         = ctx["gm"]
    contrib    = ctx["contrib"]
    df_curr    = ctx["df_curr"]
    df_prior   = ctx["df_prior"]
    df_curr_decomp = ctx.get("df_curr_decomp", df_curr)
    is_rolling = ctx["is_rolling"]
    curr_ym    = ctx["curr_ym"]
    prior_ym   = ctx["prior_ym"]
    m_from     = ctx["m_from"]
    m_to       = ctx["m_to"]

    LC  = palette["line_current"]
    LP  = palette["line_prior"]
    WFP = palette["wf_pos"]
    WFN = palette["wf_neg"]
    WFT = palette["wf_total"]
    SC  = palette["series"]

    # ── Narrative bar ─────────────────────────────────────────
    narrative_html = _narrative(ctx)
    pills_html     = _movement_pills(df_curr, df_prior)
    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #d7f34a;'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;margin-bottom:0.4rem;">'
        f'{narrative_html}</div>'
        f'<div>{pills_html}</div></div>',
        unsafe_allow_html=True,
    )

    # ── Row 1: Waterfall + YoY ────────────────────────────────
    col_wf, col_yoy = st.columns(2)

    with col_wf:
        wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","relative","total","relative","total"],
            x=["Revenue","COGS","Fixed Cost","Gross Margin","Labor","Contribution"],
            y=[rev,-cogs,-fixed_cost,None,-labor,None],
            connector={"line":{"color":"#243041"}},
            increasing={"marker":{"color":WFP,"line":{"width":0}}},
            decreasing={"marker":{"color":WFN,"line":{"width":0}}},
            totals={"marker":{"color":WFT,"line":{"width":0}}},
            text=[fmt_m(rev),fmt_m(cogs),fmt_m(fixed_cost),fmt_m(gm),fmt_m(labor),fmt_m(contrib)],
            textfont={"color":"#cbd5e1","size":10,"family":"DM Mono"},
            textposition="outside",
        ))
        wf.update_layout(**PT, title="P&L Bridge — Revenue to Contribution",
                         title_font_color="#cbd5e1", showlegend=False)
        st.plotly_chart(wf, use_container_width=True)

    with col_yoy:
        if is_rolling:
            month_labels  = ordered_month_axis_labels(curr_ym)
            curr_monthly  = df_curr.groupby(["yr","month_num"])["revenue"].sum().reset_index()
            prior_monthly = df_prior.groupby(["yr","month_num"])["revenue"].sum().reset_index()
            rows = []
            for i,(yr,mn) in enumerate(curr_ym):
                val = curr_monthly.loc[(curr_monthly["yr"]==yr)&(curr_monthly["month_num"]==mn),"revenue"]
                rows.append({"order":i,"label":month_labels[i],"Revenue":float(val.iloc[0]) if len(val) else 0,"Period":"Current"})
            for i,(yr,mn) in enumerate(prior_ym):
                val = prior_monthly.loc[(prior_monthly["yr"]==yr)&(prior_monthly["month_num"]==mn),"revenue"]
                rows.append({"order":i,"label":month_labels[i],"Revenue":float(val.iloc[0]) if len(val) else 0,"Period":"Prior Year"})
            yoy_df  = pd.DataFrame(rows)
            x_col   = "label"
            x_order = month_labels
        else:
            months_in_range = list(range(m_from, m_to+1))
            cy = df_curr.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Current"})
            py = df_prior.groupby("month_num")["revenue"].sum().reset_index().rename(columns={"revenue":"Prior Year"})
            base    = pd.DataFrame({"month_num":months_in_range})
            yoy_raw = base.merge(cy,on="month_num",how="left").merge(py,on="month_num",how="left").fillna(0)
            yoy_raw["label"] = yoy_raw["month_num"].map(MONTH_MAP)
            yoy_df  = yoy_raw.melt(id_vars=["month_num","label"],value_vars=["Current","Prior Year"],var_name="Period",value_name="Revenue")
            x_col   = "label"
            x_order = [MONTH_MAP[m] for m in months_in_range]

        fig = px.line(yoy_df, x=x_col, y="Revenue", color="Period", markers=True,
                      color_discrete_map={"Current":LC,"Prior Year":LP},
                      title="Revenue vs Prior Year",
                      labels={x_col:"","Revenue":"Revenue ($)"},
                      category_orders={x_col:x_order})
        fig.update_traces(line_width=2.5)
        fig.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30)
        fig.update_yaxes(tickformat="$,.0f")
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Monthly revenue stacked bar ────────────────────
    st.markdown('<div class="section-header">Monthly Revenue by Service Line</div>', unsafe_allow_html=True)
    rm = (df_curr_decomp[~df_curr_decomp["service_line_name"].isin(["(blank)","Unassigned"])]
          .groupby(["accounting_period_start_date","service_line_name"])["revenue"]
          .sum().reset_index())
    fig_rm = px.bar(rm, x="accounting_period_start_date", y="revenue",
                    color="service_line_name", color_discrete_sequence=SC,
                    title="Monthly Revenue by Service Line",
                    labels={"revenue":"Revenue ($)","accounting_period_start_date":"","service_line_name":""})
    fig_rm.update_traces(marker_line_width=0)
    fig_rm.update_layout(**PT, title_font_color="#cbd5e1", bargap=0.2, xaxis_tickangle=-30)
    fig_rm.update_yaxes(tickformat="$,.0s")
    st.plotly_chart(fig_rm, use_container_width=True)

    # ── Last refreshed ────────────────────────────────────────
    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#2a3045;'
        f'text-align:right;margin-top:0.5rem;">Data loaded: {datetime.now().strftime("%d %b %Y %H:%M")}</div>',
        unsafe_allow_html=True,
    )
