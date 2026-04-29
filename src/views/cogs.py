import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.charts import build_index_rows, build_yoy_trend_df, render_bar, render_index_chart, render_treemap
from src.utils.filters import clean_for_visuals
from src.utils.formatters import fmt_m, pct_text


def _narrative(ctx):
    """Return the headline summary string for the COGS card."""
    cogs = ctx["cogs"]
    cogs_py = ctx.get("cogs_py", 0)
    rev = ctx["rev"]
    period = ctx["period_label"]

    cogs_pct = (cogs / rev * 100) if rev > 0 else 0
    direction = "up" if cogs >= cogs_py else "down"
    delta = abs(cogs - cogs_py)

    return (
        f"<b>{period}:</b> COGS of <b>{fmt_m(cogs)}</b> represents "
        f"<b>{cogs_pct:.1f}%</b> of revenue, "
        f"{direction} <b>{fmt_m(delta)}</b> vs prior year."
    )


def _monthly_trend(df, value_col, group_filters=None):
    """Aggregate value_col by month, optionally filtering by group_filters dict."""
    d = df.copy()

    if group_filters:
        for col, val in group_filters.items():
            if val != "All":
                d = d[d[col] == val]

    out = (
        d.groupby(["yr", "month_num", "accounting_period_start_date"])[value_col]
        .sum()
        .reset_index()
        .sort_values("accounting_period_start_date")
    )
    out[f"{value_col}_m"] = out[value_col] / 1e6
    return out


def _build_index(ctx, curr_df, prior_df, value_col, group_filters=None):
    """Build monthly PY index DataFrame (100 = same as prior year) for value_col."""
    curr_monthly = _monthly_trend(curr_df, value_col, group_filters)
    prior_monthly = _monthly_trend(prior_df, value_col, group_filters)
    return pd.DataFrame(build_index_rows(ctx, curr_monthly, prior_monthly, value_col))


def render_cogs(ctx):
    """Render the COGS tab.

    Uses two data views from ctx:
      df_curr_decomp / df_prior  — SL filter unlocked; powers distribution charts.
      df_curr / df_prior         — fully filtered; powers client charts and detail table.
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    df_curr = ctx["df_curr"]
    df_prior = ctx["df_prior"]
    df_curr_decomp = ctx["df_curr_decomp"]
    df_prior_decomp = df_prior  # decomp key is never set; always falls back to df_prior

    BS = palette["blue_scale"]
    LC = palette["line_current"]
    LP = palette["line_prior"]

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #f87171;
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

    # ── Service Line tile chart ───────────────────────────────
    st.markdown('<div class="section-header">COGS by Service Line</div>', unsafe_allow_html=True)

    cogs_sl = (
        base.groupby("service_line_name")
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
        .reset_index()
    )

    cogs_sl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="cogs_sl_chart_type")
    if cogs_sl_chart_type == "Tile":
        render_treemap(cogs_sl, label_col="service_line_name", value_col="cogs", title="", color_scale=BS, value_label="COGS")
    else:
        render_bar(cogs_sl, label_col="service_line_name", value_col="cogs", title="", color_scale=BS, value_label="COGS")

    # ── Sub Service Line tile chart, directly below SL chart ───
    st.markdown('<div class="section-header">COGS by Sub-Service Line</div>', unsafe_allow_html=True)

    ssl_options = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
    selected_sl = st.selectbox("Sub Service Line view", ssl_options, key="cogs_ssl_sl_filter")

    ssl_src = base if selected_sl == "All" else base[base["service_line_name"] == selected_sl]

    cogs_ssl = (
        ssl_src.groupby("sub_service_line_name")
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
        .reset_index()
    )
    cogs_ssl = cogs_ssl[cogs_ssl["sub_service_line_name"] != "(blank)"]

    cogs_ssl_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="cogs_ssl_chart_type")
    if cogs_ssl_chart_type == "Tile":
        render_treemap(cogs_ssl, label_col="sub_service_line_name", value_col="cogs", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="COGS")
    else:
        render_bar(cogs_ssl, label_col="sub_service_line_name", value_col="cogs", title=f"— {'All' if selected_sl == 'All' else selected_sl}", color_scale=BS, value_label="COGS")

    # ── Monthly COGS trend ────────────────────────────────────
    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)

    tcol1, tcol2 = st.columns(2)
    with tcol1:
        trend_sl_opts = ["All"] + sorted(base["service_line_name"].dropna().unique().tolist())
        trend_sl = st.selectbox("Trend — Service Line", trend_sl_opts, key="cogs_trend_sl")

    trend_ssl_src = base if trend_sl == "All" else base[base["service_line_name"] == trend_sl]

    with tcol2:
        trend_ssl_opts = ["All"] + sorted(trend_ssl_src["sub_service_line_name"].dropna().unique().tolist())
        trend_ssl = st.selectbox("Trend — Sub Service Line", trend_ssl_opts, key="cogs_trend_ssl")

    trend_filters = {
        "service_line_name": trend_sl,
        "sub_service_line_name": trend_ssl,
    }

    cogs_sl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="cogs_sl_trend_mode")

    if cogs_sl_trend_mode == "Raw":
        curr_filt = base.copy()
        prior_filt = prior_base.copy()
        for col, val in trend_filters.items():
            if val != "All":
                curr_filt = curr_filt[curr_filt[col] == val]
                prior_filt = prior_filt[prior_filt[col] == val]

        yoy_df, month_order = build_yoy_trend_df(ctx, curr_filt, prior_filt, "cogs")
        fig_trend = px.line(
            yoy_df, x="month", y="cogs_m", color="Period",
            color_discrete_map={"Current": LC, "Prior Year": LP},
            markers=True, title="",
            labels={"month": "", "cogs_m": "COGS ($M)"},
            category_orders={"month": month_order},
        )
        fig_trend.update_traces(line_width=2.5)
        fig_trend.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30, height=320)
        fig_trend.update_yaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        idx_df = _build_index(ctx, base, prior_base, "cogs", trend_filters)
        render_index_chart(idx_df, "vs Prior Year  —  100 = PY", PT)

    # ── Client bar ────────────────────────────────────────────
    st.markdown('<div class="section-header">COGS by Client</div>', unsafe_allow_html=True)


    cogs_cl = (
        filtered_base.groupby("top_level_parent_customer_name")
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
        .reset_index()
    )
    cogs_cl["pct_of_rev"] = (
        cogs_cl["cogs"] / cogs_cl["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    cogs_cl = cogs_cl.sort_values("cogs", ascending=False)

    high_count = (cogs_cl["pct_of_rev"] > 60).sum()
    if high_count > 0:
        st.markdown(
            f"""
            <div style="font-family:DM Mono,monospace;font-size:9px;color:#f87171;margin-bottom:0.5rem;">
                ⚠ {high_count} client{"s" if high_count > 1 else ""} with COGS >60% of revenue
            </div>
            """,
            unsafe_allow_html=True,
        )

    client_view = st.radio(
        "Client view",
        ["Top 15", "Top 30", "All > $100k"],
        horizontal=True,
        key="cogs_client_view",
    )

    if client_view == "All > $100k":
        cogs_cl_show = cogs_cl[cogs_cl["cogs"] >= 100_000].copy()
    else:
        n_show = {"Top 15": 15, "Top 30": 30}[client_view]
        cogs_cl_show = cogs_cl.head(n_show).copy()

    cogs_cl_show["cogs_m"] = cogs_cl_show["cogs"] / 1e6
    cogs_cl_show = cogs_cl_show.sort_values("cogs_m", ascending=True)

    fig_cl = go.Figure(go.Bar(
        x=cogs_cl_show["cogs_m"],
        y=cogs_cl_show["top_level_parent_customer_name"],
        orientation="h",
        marker_color="#4c78a8",
        marker_line_width=0,
        text=cogs_cl_show["pct_of_rev"].map(pct_text),
        textposition="outside",
    ))
    fig_cl.update_layout(
        **PT,
        title=f"— {client_view}",
        title_font_color="#cbd5e1",
        height=max(400, len(cogs_cl_show) * 24),
    )
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
    st.plotly_chart(fig_cl, use_container_width=True)

    # ── Client concentration ──────────────────────────────────
    st.markdown('<div class="section-header">Client Concentration</div>', unsafe_allow_html=True)

    top10_clients = cogs_cl.head(10).copy()
    other_cogs = cogs_cl.iloc[10:]["cogs"].sum()

    tile_clients = top10_clients.copy()

    if other_cogs > 0:
        tile_clients = pd.concat(
            [
                tile_clients,
                pd.DataFrame({
                    "top_level_parent_customer_name": ["Other"],
                    "cogs": [other_cogs],
                }),
            ],
            ignore_index=True,
        )

    cogs_conc_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="cogs_conc_chart_type")
    if cogs_conc_chart_type == "Tile":
        render_treemap(tile_clients, label_col="top_level_parent_customer_name", value_col="cogs", title="Top 10 + Other", color_scale=BS, value_label="COGS")
    else:
        render_bar(tile_clients, label_col="top_level_parent_customer_name", value_col="cogs", title="Top 10 + Other", color_scale=BS, value_label="COGS")

    # ── Client trend ──────────────────────────────────────────
    st.markdown('<div class="section-header">Client Trend</div>', unsafe_allow_html=True)

    client_options = ["All"] + sorted(filtered_base["top_level_parent_customer_name"].dropna().unique().tolist())

    selected_client = st.selectbox(
        "Trend — Client",
        client_options,
        key="cogs_client_trend_filter",
    )

    client_filters = {
        "top_level_parent_customer_name": selected_client,
    }

    cogs_cl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="cogs_cl_trend_mode")

    if cogs_cl_trend_mode == "Raw":
        curr_cl = filtered_base if selected_client == "All" else filtered_base[filtered_base["top_level_parent_customer_name"] == selected_client]
        prior_cl = filtered_prior if selected_client == "All" else filtered_prior[filtered_prior["top_level_parent_customer_name"] == selected_client]

        cl_yoy_df, cl_month_order = build_yoy_trend_df(ctx, curr_cl, prior_cl, "cogs")
        fig_client_trend = px.line(
            cl_yoy_df, x="month", y="cogs_m", color="Period",
            color_discrete_map={"Current": LC, "Prior Year": LP},
            markers=True, title=f"— {selected_client}",
            labels={"month": "", "cogs_m": "COGS ($M)"},
            category_orders={"month": cl_month_order},
        )
        fig_client_trend.update_traces(line_width=2.5)
        fig_client_trend.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30, height=320)
        fig_client_trend.update_yaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_client_trend, use_container_width=True)
    else:
        client_idx_df = _build_index(ctx, filtered_base, filtered_prior, "cogs", client_filters)
        render_index_chart(client_idx_df, f"— {selected_client}  vs Prior Year  —  100 = PY", PT)

    # ── Detail table ──────────────────────────────────────────
    st.markdown(
        '<div class="section-header">COGS Detail</div>',
        unsafe_allow_html=True,
    )

    cogs_tbl = (
        filtered_base.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(revenue=("revenue", "sum"), cogs=("cogs", "sum"))
        .reset_index()
    )

    total_cogs = cogs_tbl["cogs"].sum()
    cogs_tbl["cogs_pct_rev"] = (
        cogs_tbl["cogs"] / cogs_tbl["revenue"].replace(0, float("nan")) * 100
    ).round(1)
    cogs_tbl["cogs_pct_total"] = (
        cogs_tbl["cogs"] / total_cogs * 100 if total_cogs else 0
    ).round(1)

    for c in ["revenue", "cogs"]:
        cogs_tbl[c] = (cogs_tbl[c] / 1e6).round(2)

    cogs_tbl = cogs_tbl.sort_values(["service_line_name", "cogs"], ascending=[True, False])
    cogs_tbl = cogs_tbl.rename(columns={
        "service_line_name": "Service Line",
        "sub_service_line_name": "Sub Service Line",
        "top_level_parent_customer_name": "Client",
        "revenue": "Revenue",
        "cogs": "COGS",
        "cogs_pct_rev": "COGS % Rev",
        "cogs_pct_total": "COGS % Total",
    })

    st.dataframe(
        cogs_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "COGS": st.column_config.NumberColumn("COGS ($M)", format="$%.2f"),
            "COGS % Rev": st.column_config.NumberColumn("COGS % Rev", format="%.1f%%"),
            "COGS % Total": st.column_config.NumberColumn("COGS % Total", format="%.1f%%"),
        },
    )

    st.download_button(
        "Download COGS Detail CSV",
        cogs_tbl.to_csv(index=False).encode(),
        "cogs_detail.csv",
        "text/csv",
        key="cogs_dl",
    )