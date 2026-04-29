import plotly.graph_objects as go
import streamlit as st

from src.utils.charts import render_bar, render_treemap
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m, pct_text


def _narrative(ctx):
    """Return the headline summary string for the labor card."""
    labor = ctx["labor"]
    labor_py = ctx.get("labor_py", 0)
    lab_pct = ctx.get("lab_pct", 0)
    period = ctx["period_label"]

    direction = "up" if labor >= labor_py else "down"
    delta = abs(labor - labor_py)

    return (
        f"<b>{period}:</b> Labor cost of <b>{fmt_m(labor)}</b> represents "
        f"<b>{lab_pct:.1f}%</b> of revenue, "
        f"{direction} <b>{fmt_m(delta)}</b> vs prior year."
    )


def _labor_with_revenue(df_lab, df_rev):
    """Join labor data with revenue data and add labor% rev and cost-per-hour columns."""
    revenue = (
        df_rev.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )["revenue"]
        .sum()
        .reset_index()
    )

    labor = (
        df_lab.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(
            labor=("labour_cost", "sum"),
            total_hours=("total_hours", "sum"),
        )
        .reset_index()
    )

    out = labor.merge(
        revenue,
        on=["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
        how="left",
    )

    out["revenue"] = out["revenue"].fillna(0)
    out["labor_pct_rev"] = (
        out["labor"] / out["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    out["cost_per_hour"] = (
        out["labor"] / out["total_hours"].replace(0, float("nan"))
    ).round(0)

    return out


def render_labor(ctx):
    """Render the Labor tab.

    Uses two data views from ctx:
      *_decomp  — SL filter unlocked; powers SL/SSL distribution charts.
      df_curr / df_lab_curr — fully filtered; powers client bar and detail table.
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    df_curr = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    df_lab_curr_decomp = ctx["df_lab_curr_decomp"]

    BS = palette["blue_scale"]

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #fb923c;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">
                {_narrative(ctx)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # *_base: all service lines visible — used for SL/SSL distribution charts.
    # *_filtered: user's full filter applied — used for client bar and detail table.
    lab_base = clean_for_visuals(df_lab_curr_decomp)
    rev_base = clean_for_visuals(df_curr_decomp)

    lab_filtered = clean_for_visuals(df_lab_curr)
    rev_filtered = clean_for_visuals(df_curr)

    lab_enriched = _labor_with_revenue(lab_base, rev_base)
    lab_enriched_filtered = _labor_with_revenue(lab_filtered, rev_filtered)

    # ── Service Line tile chart ───────────────────────────────
    st.markdown('<div class="section-header">Labor by Service Line</div>', unsafe_allow_html=True)

    labor_sl = (
        lab_enriched.groupby("service_line_name")
        .agg(labor=("labor", "sum"), revenue=("revenue", "sum"))
        .reset_index()
    )

    labor_sl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="labor_sl_chart_type")
    if labor_sl_chart_type == "Tile":
        render_treemap(labor_sl, label_col="service_line_name", value_col="labor", title="", color_scale=BS, value_label="Labor")
    else:
        render_bar(labor_sl, label_col="service_line_name", value_col="labor", title="", color_scale=BS, value_label="Labor")

    # ── Sub Service Line tile chart, directly below SL chart ───
    st.markdown('<div class="section-header">Labor by Sub-Service Line</div>', unsafe_allow_html=True)

    ssl_options = ["All"] + sorted(lab_enriched["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Sub Service Line view", ssl_options, key="labor_ssl_sl_filter")

    ssl_src = lab_enriched if selected_sl == "All" else lab_enriched[lab_enriched["service_line_name"] == selected_sl]

    labor_ssl = (
        ssl_src.groupby("sub_service_line_name")
        .agg(labor=("labor", "sum"), revenue=("revenue", "sum"))
        .reset_index()
    )
    labor_ssl = labor_ssl[labor_ssl["sub_service_line_name"] != "(blank)"]

    labor_ssl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="labor_ssl_chart_type")
    if labor_ssl_chart_type == "Tile":
        render_treemap(labor_ssl, label_col="sub_service_line_name", value_col="labor", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Labor")
    else:
        render_bar(labor_ssl, label_col="sub_service_line_name", value_col="labor", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="Labor")

    # ── Client bar ────────────────────────────────────────────
    st.markdown('<div class="section-header">Labor by Client</div>', unsafe_allow_html=True)

    labor_cl = (
        lab_enriched_filtered.groupby("top_level_parent_customer_name")
        .agg(
            labor=("labor", "sum"),
            revenue=("revenue", "sum"),
            total_hours=("total_hours", "sum"),
        )
        .reset_index()
    )

    labor_cl["pct_of_rev"] = (
        labor_cl["labor"] / labor_cl["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    labor_cl = labor_cl.sort_values("labor", ascending=False)

    client_view = st.radio(
        "Client view",
        ["Top 15", "Top 30", "All"],
        horizontal=True,
        key="labor_client_view",
    )

    n_show = {"Top 15": 15, "Top 30": 30, "All": len(labor_cl)}[client_view]
    labor_cl_show = labor_cl.head(n_show).sort_values("labor", ascending=True)

    fig = go.Figure(go.Bar(
        x=labor_cl_show["labor"],
        y=labor_cl_show["top_level_parent_customer_name"],
        orientation="h",
        marker_color="#fb923c",
        marker_line_width=0,
        text=labor_cl_show["pct_of_rev"].map(pct_text),
        textposition="outside",
    ))

    fig.update_layout(
        **PT,
        title=f"— {client_view}",
        title_font_color="#cbd5e1",
        height=max(400, n_show * 26),
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(tickformat="$,.0s")

    st.plotly_chart(fig, use_container_width=True)

    # ── Detail table ──────────────────────────────────────────
    st.markdown(
        '<div class="section-header">Labor Detail</div>',
        unsafe_allow_html=True,
    )

    labor_tbl = lab_enriched_filtered.copy()
    total_labor = labor_tbl["labor"].sum()

    labor_tbl["labor_pct_total"] = (
        labor_tbl["labor"] / total_labor * 100 if total_labor else 0
    ).round(1)

    for c in ["revenue", "labor"]:
        labor_tbl[c] = (labor_tbl[c] / 1e6).round(3)

    labor_tbl = labor_tbl.sort_values(["service_line_name", "labor"], ascending=[True, False])
    labor_tbl = labor_tbl.rename(columns={
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

    st.dataframe(
        labor_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.3f"),
            "Labor": st.column_config.NumberColumn("Labor ($M)", format="$%.3f"),
            "Total Hours": st.column_config.NumberColumn("Hours", format="%,.0f"),
            "Cost / Hr": st.column_config.NumberColumn("Cost / Hr ($)", format="$%.0f"),
            "Labor % Rev": st.column_config.NumberColumn("Labor % Rev", format="%.1f%%"),
            "Labor % Total": st.column_config.NumberColumn("Labor % Total", format="%.1f%%"),
        },
    )

    st.download_button(
        "Download Labor Detail CSV",
        labor_tbl.to_csv(index=False).encode(),
        "labor_detail.csv",
        "text/csv",
        key="labor_dl",
    )