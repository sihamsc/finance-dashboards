"""
Labor tab — unified layout:
  Service Line  : distribution (Bar/Tile) → inline trend (Raw/Index)
  Sub-SL        : SL filter → distribution → inline trend
  Client        : bar → client selector → inline trend
  Detail        : table + CSV download
"""

import plotly.graph_objects as go
import streamlit as st

from src.utils.constants import METRIC_COLOR
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m
from src.utils.view_helpers import dist_chart, inline_trend


_ACCENT = METRIC_COLOR["labor"]


def _narrative(ctx):
    labor, labor_py = ctx["labor"], ctx.get("labor_py", 0)
    lab_pct = ctx.get("lab_pct", 0)
    period  = ctx["period_label"]
    dir_    = "up" if labor >= labor_py else "down"
    return (
        f"<b>{period}:</b> Labor cost of <b>{fmt_m(labor)}</b> represents "
        f"<b>{lab_pct:.1f}%</b> of revenue, "
        f"{dir_} <b>{fmt_m(abs(labor - labor_py))}</b> vs prior year."
    )


def _labor_enriched(df_lab, df_rev):
    rev = (df_rev.groupby(
               ["service_line_name","sub_service_line_name","top_level_parent_customer_name"],
               dropna=False)["revenue"]
           .sum().reset_index())
    lab = (df_lab.groupby(
               ["service_line_name","sub_service_line_name","top_level_parent_customer_name"],
               dropna=False)
           .agg(labor=("labour_cost","sum"), total_hours=("total_hours","sum"))
           .reset_index())
    out = lab.merge(rev, on=["service_line_name","sub_service_line_name",
                              "top_level_parent_customer_name"], how="left")
    out["revenue"] = out["revenue"].fillna(0)
    out["labor_pct_rev"] = (out["labor"] / out["revenue"].replace(0,float("nan")) * 100).round(1)
    out["cost_per_hour"] = (out["labor"] / out["total_hours"].replace(0,float("nan"))).round(0)
    return out


def render_labor(ctx):
    PT = ctx["PT"]

    df_curr          = ctx["df_curr"]
    df_lab_curr      = ctx["df_lab_curr"]
    df_lab_prior     = ctx["df_lab_prior"]
    df_curr_decomp   = ctx["df_curr_decomp"]
    df_lab_curr_decomp = ctx["df_lab_curr_decomp"]

    st.markdown(
        f'<div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid {_ACCENT};'
        f'border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">'
        f'{_narrative(ctx)}</div></div>',
        unsafe_allow_html=True,
    )

    lab_base  = clean_for_visuals(df_lab_curr_decomp)
    rev_base  = clean_for_visuals(df_curr_decomp)
    lab_prior = clean_for_visuals(df_lab_prior) if df_lab_prior is not None else lab_base.iloc[0:0]

    enriched     = _labor_enriched(lab_base, rev_base)
    enriched_fil = _labor_enriched(clean_for_visuals(df_lab_curr), clean_for_visuals(df_curr))

    # ── SERVICE LINE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Labor by Service Line</div>', unsafe_allow_html=True)

    lab_sl = (enriched.groupby("service_line_name")
              .agg(labor=("labor","sum"), revenue=("revenue","sum"))
              .reset_index())

    sl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="lab_sl_chart")
    dist_chart(lab_sl, "service_line_name", "labor", _ACCENT, PT, sl_chart, "lab_sl",
               value_label="Labor")
    # Labor uses "labour_cost" column in df_lab; rename to match inline_trend expectation
    lab_base_renamed  = lab_base.rename(columns={"labour_cost": "labor"})
    if "labor" not in lab_base_renamed.columns:
        lab_base_renamed["labor"] = 0
    lab_prior_renamed = lab_prior.rename(columns={"labour_cost": "labor"})
    if "labor" not in lab_prior_renamed.columns:
        lab_prior_renamed["labor"] = 0
    inline_trend(ctx, lab_base_renamed, lab_prior_renamed, "labor", _ACCENT, PT, "lab_sl",
                 y_label="Labor ($M)")

    # ── SUB-SERVICE LINE ──────────────────────────────────────
    st.markdown('<div class="section-header">Labor by Sub-Service Line</div>', unsafe_allow_html=True)

    ssl_options = ["All"] + sorted(enriched["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Service Line", ssl_options, key="lab_ssl_sl_filter")

    ssl_src = enriched if selected_sl == "All" else enriched[enriched["service_line_name"] == selected_sl]
    lab_ssl = (ssl_src.groupby("sub_service_line_name")
               .agg(labor=("labor","sum"), revenue=("revenue","sum"))
               .reset_index())
    lab_ssl = lab_ssl[lab_ssl["sub_service_line_name"] != "(blank)"]

    ssl_chart = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="lab_ssl_chart")
    dist_chart(lab_ssl, "sub_service_line_name", "labor", _ACCENT, PT, ssl_chart, "lab_ssl",
               value_label="Labor")

    curr_ssl_df  = lab_base_renamed  if selected_sl == "All" else lab_base_renamed[lab_base_renamed["service_line_name"] == selected_sl]
    prior_ssl_df = lab_prior_renamed if selected_sl == "All" else lab_prior_renamed[lab_prior_renamed["service_line_name"] == selected_sl]
    inline_trend(ctx, curr_ssl_df, prior_ssl_df, "labor", _ACCENT, PT, "lab_ssl",
                 y_label=f"Labor ($M) — {selected_sl}")

    # ── CLIENT ────────────────────────────────────────────────
    st.markdown('<div class="section-header">Labor by Client</div>', unsafe_allow_html=True)

    lab_cl = (enriched_fil.groupby("top_level_parent_customer_name")
              .agg(labor=("labor","sum"), revenue=("revenue","sum"), total_hours=("total_hours","sum"))
              .reset_index())
    lab_cl["pct_rev"] = (lab_cl["labor"] / lab_cl["revenue"].replace(0,float("nan")) * 100).round(1)
    lab_cl = lab_cl.sort_values("labor", ascending=False)

    client_view = st.radio("Client view", ["Top 15", "Top 30", "All"],
                           horizontal=True, key="lab_client_view")
    n_show = {"Top 15": 15, "Top 30": 30, "All": len(lab_cl)}[client_view]
    cl_show = lab_cl.head(n_show).sort_values("labor", ascending=True)

    cl_show["_m"] = cl_show["labor"] / 1e6
    fig_cl = go.Figure(go.Bar(
        x=cl_show["_m"],
        y=cl_show["top_level_parent_customer_name"],
        orientation="h",
        marker_color=_ACCENT,
        marker_line_width=0,
        text=cl_show.apply(lambda r: f"${r['_m']:.1f}M ({r['pct_rev']:.1f}% rev)", axis=1),
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8", family="DM Sans"),
    ))
    fig_cl.update_layout(**PT, height=max(340, n_show * 26),
                          margin=dict(l=0, r=130, t=20, b=0))
    fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
    st.plotly_chart(fig_cl, use_container_width=True)

    # Client labor trend
    lab_fil_ren  = clean_for_visuals(df_lab_curr).rename(columns={"labour_cost": "labor"})
    lab_pri_ren  = lab_prior.rename(columns={"labour_cost": "labor"})
    cl_opts = ["All"] + sorted(lab_fil_ren["top_level_parent_customer_name"].dropna().unique().tolist())
    sel_client = st.selectbox("Client trend", cl_opts, key="lab_cl_trend_filter")

    if sel_client == "All":
        curr_cl, prior_cl = lab_fil_ren, lab_pri_ren
    else:
        curr_cl  = lab_fil_ren[lab_fil_ren["top_level_parent_customer_name"] == sel_client]
        prior_cl = lab_pri_ren[lab_pri_ren["top_level_parent_customer_name"] == sel_client]

    inline_trend(ctx, curr_cl, prior_cl, "labor", _ACCENT, PT, "lab_cl",
                 y_label=f"Labor ($M) — {sel_client}")

    # ── DETAIL TABLE ──────────────────────────────────────────
    st.markdown('<div class="section-header">Labor Detail</div>', unsafe_allow_html=True)

    tbl = enriched_fil.copy()
    total_lab = tbl["labor"].sum()
    tbl["labor_pct_total"] = (tbl["labor"] / total_lab * 100).round(1) if total_lab else 0
    for c in ["revenue","labor"]:
        tbl[c] = (tbl[c] / 1e6).round(3)
    tbl = tbl.sort_values(["service_line_name","labor"], ascending=[True,False])
    tbl = tbl.rename(columns={
        "service_line_name": "Service Line",
        "sub_service_line_name": "Sub Service Line",
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue",
        "labor": "Labor",
        "total_hours": "Total Hours",
        "labor_pct_rev": "Labor % Rev",
        "labor_pct_total": "Labor % Total",
        "cost_per_hour": "Cost / Hr",
    })
    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":       st.column_config.NumberColumn("Revenue ($M)",  format="$%.3f"),
        "Labor":         st.column_config.NumberColumn("Labor ($M)",    format="$%.3f"),
        "Total Hours":   st.column_config.NumberColumn("Hours",         format="%,.0f"),
        "Cost / Hr":     st.column_config.NumberColumn("Cost / Hr ($)", format="$%.0f"),
        "Labor % Rev":   st.column_config.NumberColumn("Labor % Rev",   format="%.1f%%"),
        "Labor % Total": st.column_config.NumberColumn("Labor % Total", format="%.1f%%"),
    })
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(),
                       "labor_detail.csv", "text/csv", key="labor_dl")
