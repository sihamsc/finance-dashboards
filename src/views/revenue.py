"""
Revenue tab:
  1. Deterministic headline
  2. Tile chart — Service Line
  3. Service Line selector → Sub Service Line tile chart
  4. Monthly revenue trend
  5. Monthly revenue index vs prior year, where 100 = prior year
  6. Client bar chart — Top 15 / Top 30 / All > $100k
  7. Detail table — Service Line | Sub Service Line | Client | Revenue $M | Revenue %
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.charts import build_index_rows, build_yoy_trend_df, render_bar, render_index_chart
from src.utils.filters import clean_for_visuals, MONTH_MAP


def render_tile_chart(df_tiles, label_col, value_col, title, color_scale, key_suffix, PT):
    """Render a Plotly treemap tile chart. Also imported and used by fixed_cost.py.

    key_suffix is appended to the Streamlit widget key to prevent duplicate-key errors
    when the same chart type is rendered more than once on a page.
    """
    d = df_tiles.copy()
    total = d[value_col].sum()

    if total == 0 or d.empty:
        st.info(f"No data available for {title}.")
        return

    d["_pct"] = (d[value_col] / total * 100).round(1).fillna(0)
    d["_val_m"] = (d[value_col] / 1e6).round(2)
    d["_label"] = d[label_col]
    d["_parent"] = "Total"
    d = d[d[value_col] > 0]

    fig = go.Figure(go.Treemap(
        labels=d["_label"].tolist() + ["Total"],
        parents=["Total"] * len(d) + [""],
        values=d[value_col].tolist() + [total],
        customdata=list(zip(d["_val_m"], d["_pct"])),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "$%{customdata[0]:.2f}M<br>"
            "%{customdata[1]:.1f}% of total"
            "<extra></extra>"
        ),
        texttemplate="<b>%{label}</b><br>$%{customdata[0]:.1f}M<br>%{customdata[1]:.1f}%",
        textfont=dict(family="DM Sans", size=12, color="#f0f2f8"),
        marker=dict(
            colorscale=color_scale,
            colors=d[value_col].tolist() + [total],
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

    st.plotly_chart(fig, use_container_width=True, key=f"tile_{key_suffix}")


def _narrative(ctx):
    """Return the headline summary string for the revenue card."""
    rev = ctx["rev"]
    rev_py = ctx["rev_py"]
    period = ctx["period_label"]
    df_curr = ctx["df_curr"]

    rev_dir = "up" if rev >= rev_py else "down"
    rev_delta = abs(rev - rev_py)

    sl_grp = (
        clean_for_visuals(ctx.get("df_curr_decomp", df_curr))
        .groupby("service_line_name")["revenue"]
        .sum()
    )

    top_sl = sl_grp.idxmax() if not sl_grp.empty else "—"
    top_sl_pct = (sl_grp.max() / rev * 100) if rev > 0 and not sl_grp.empty else 0

    return (
        f"<b>{period}:</b> Revenue of <b>${rev/1e6:.1f}M</b> is "
        f"{rev_dir} <b>${rev_delta/1e6:.1f}M</b> vs prior year. "
        f"<b>{top_sl}</b> is the largest contributor at "
        f"<b>{top_sl_pct:.0f}%</b> of total revenue."
    )


def _build_filtered_monthly_trend(df_base, trend_sl, trend_ssl):
    """Aggregate monthly revenue after optionally filtering by SL and Sub-SL."""
    trend_df = df_base.copy()

    if trend_sl != "All":
        trend_df = trend_df[trend_df["service_line_name"] == trend_sl]

    if trend_ssl != "All":
        trend_df = trend_df[trend_df["sub_service_line_name"] == trend_ssl]

    monthly = (
        trend_df.groupby(["yr", "month_num", "accounting_period_start_date"])["revenue"]
        .sum()
        .reset_index()
        .sort_values("accounting_period_start_date")
    )

    monthly["revenue_m"] = monthly["revenue"] / 1e6

    return monthly


def _build_revenue_index(ctx, df_curr_view, df_prior_view, trend_sl, trend_ssl):
    """Build the monthly revenue index DataFrame (100 = same as prior year)."""
    is_rolling = ctx["is_rolling"]
    curr_ym = ctx["curr_ym"]
    prior_ym = ctx["prior_ym"]
    m_from = ctx["m_from"]
    m_to = ctx["m_to"]

    curr_monthly = _build_filtered_monthly_trend(df_curr_view, trend_sl, trend_ssl)
    prior_monthly = _build_filtered_monthly_trend(df_prior_view, trend_sl, trend_ssl)

    rows = []

    if is_rolling:
        month_pairs = list(zip(curr_ym, prior_ym))

        for i, ((cy, cm), (py, pm)) in enumerate(month_pairs):
            curr_val = curr_monthly.loc[
                (curr_monthly["yr"] == cy) & (curr_monthly["month_num"] == cm),
                "revenue",
            ]
            prior_val = prior_monthly.loc[
                (prior_monthly["yr"] == py) & (prior_monthly["month_num"] == pm),
                "revenue",
            ]

            c = float(curr_val.iloc[0]) if len(curr_val) else 0
            p = float(prior_val.iloc[0]) if len(prior_val) else 0

            rows.append({
                "order": i,
                "month": MONTH_MAP[cm],
                "current": c,
                "prior": p,
                "index": (c / p * 100) if p else None,
            })

    else:
        for i, m in enumerate(range(m_from, m_to + 1)):
            curr_val = curr_monthly.loc[curr_monthly["month_num"] == m, "revenue"]
            prior_val = prior_monthly.loc[prior_monthly["month_num"] == m, "revenue"]

            c = float(curr_val.iloc[0]) if len(curr_val) else 0
            p = float(prior_val.iloc[0]) if len(prior_val) else 0

            rows.append({
                "order": i,
                "month": MONTH_MAP[m],
                "current": c,
                "prior": p,
                "index": (c / p * 100) if p else None,
            })

    return pd.DataFrame(rows)


def render_revenue(ctx):
    """Render the Revenue tab.

    Sections:
      1. Narrative headline
      2. Service Line treemap
      3. Sub Service Line treemap (filtered by selected SL)
      4. Monthly revenue trend with SL/SSL filter
      5. Monthly revenue index vs prior year
      6. Client bar chart (Top 15 / Top 30 / All > $100k)
      7. Client concentration treemap (Top 10 + Other)
      8. Client monthly trend + PY index
      9. Detail table with CSV download
    """
    palette = ctx["palette"]
    PT = ctx["PT"]

    df_curr = ctx["df_curr"]
    df_curr_decomp = ctx["df_curr_decomp"]
    # decomp prior key is never set in context; falls back to df_prior
    df_prior_decomp = ctx.get("df_prior_decomp", ctx["df_prior"])

    BS = palette["blue_scale"]
    LC = palette["line_current"]
    LP = palette["line_prior"]

    st.markdown(
        f"""
        <div style="background:#0b0f16;border:1px solid #18202d;border-left:3px solid #60a5fa;
                    border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:12px;color:#cbd5e1;">
                {_narrative(ctx)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Revenue by Service Line</div>', unsafe_allow_html=True)


    base_decomp = clean_for_visuals(df_curr_decomp)

    sl_data = (
        base_decomp.groupby("service_line_name")["revenue"]
        .sum()
        .reset_index()
    )
    sl_data = sl_data[sl_data["revenue"] > 0]

    rev_sl_chart_type = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="rev_sl_chart_type")
    if rev_sl_chart_type == "Tile":
        render_tile_chart(sl_data, "service_line_name", "revenue", "", BS, "rev_sl", PT)
    else:
        # YoY grouped bar — current vs prior year side by side
        prior_sl_data = (
            clean_for_visuals(ctx.get("df_prior_decomp", ctx["df_prior"]))
            .groupby("service_line_name")["revenue"].sum().reset_index()
            .rename(columns={"revenue": "revenue_py"})
        )
        sl_yoy = sl_data.merge(prior_sl_data, on="service_line_name", how="left").fillna(0)
        sl_yoy["rev_m"]    = sl_yoy["revenue"]    / 1e6
        sl_yoy["rev_py_m"] = sl_yoy["revenue_py"] / 1e6
        sl_yoy = sl_yoy.sort_values("revenue", ascending=True)
        fig_sl_yoy = go.Figure()
        fig_sl_yoy.add_trace(go.Bar(
            y=sl_yoy["service_line_name"], x=sl_yoy["rev_py_m"],
            name="Prior Year", orientation="h",
            marker_color=LP, marker_line_width=0, opacity=0.55,
        ))
        fig_sl_yoy.add_trace(go.Bar(
            y=sl_yoy["service_line_name"], x=sl_yoy["rev_m"],
            name="Current", orientation="h",
            marker_color=LC, marker_line_width=0,
        ))
        fig_sl_yoy.update_layout(**PT, barmode="group", title_font_color="#cbd5e1",
                                  height=max(280, len(sl_yoy)*48+60),
                                  legend=dict(orientation="h", y=1.05, bgcolor="rgba(0,0,0,0)",
                                              font=dict(color="#cbd5e1", size=10)))
        fig_sl_yoy.update_xaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_sl_yoy, use_container_width=True)

    st.markdown('<div class="section-header">Revenue by Sub-Service Line</div>', unsafe_allow_html=True)

    sl_options = sorted(base_decomp["service_line_name"].dropna().unique().tolist())

    selected_sl = st.selectbox(
        "Filter by Service Line",
        sl_options,
        key="rev_sl_filter",
    )

    ssl_src = base_decomp[base_decomp["service_line_name"] == selected_sl]

    ssl_data = (
        ssl_src.groupby("sub_service_line_name")["revenue"]
        .sum()
        .reset_index()
    )
    ssl_data = ssl_data[ssl_data["revenue"] > 0]

    if ssl_data.empty:
        st.info(f"No sub service line data for {selected_sl}.")
    else:
        rev_ssl_chart_type = st.radio("Chart type", ["Bar", "Tile"], horizontal=True, key="rev_ssl_chart_type")
        if rev_ssl_chart_type == "Tile":
            render_tile_chart(ssl_data, "sub_service_line_name", "revenue", f"— {selected_sl}", BS, "rev_ssl", PT)
        else:
            render_bar(ssl_data, label_col="sub_service_line_name", value_col="revenue", title=f"— {selected_sl}", color_scale=BS, value_label="Revenue")

    st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)

    trend_base = clean_for_visuals(df_curr_decomp)
    trend_prior_base = clean_for_visuals(df_prior_decomp)

    tcol1, tcol2 = st.columns(2)

    with tcol1:
        trend_sl_opts = ["All"] + sorted(trend_base["service_line_name"].dropna().unique().tolist())
        trend_sl = st.selectbox("Trend — Service Line", trend_sl_opts, key="rev_trend_sl")

    trend_ssl_src = trend_base if trend_sl == "All" else trend_base[trend_base["service_line_name"] == trend_sl]

    with tcol2:
        trend_ssl_opts = ["All"] + sorted(trend_ssl_src["sub_service_line_name"].dropna().unique().tolist())
        trend_ssl = st.selectbox("Trend — Sub Service Line", trend_ssl_opts, key="rev_trend_ssl")

    rev_sl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="rev_sl_trend_mode")

    if rev_sl_trend_mode == "Raw":
        # Filter both current and prior by the same SL/SSL selectors
        curr_filt = trend_base.copy()
        prior_filt = trend_prior_base.copy()
        if trend_sl != "All":
            curr_filt = curr_filt[curr_filt["service_line_name"] == trend_sl]
            prior_filt = prior_filt[prior_filt["service_line_name"] == trend_sl]
        if trend_ssl != "All":
            curr_filt = curr_filt[curr_filt["sub_service_line_name"] == trend_ssl]
            prior_filt = prior_filt[prior_filt["sub_service_line_name"] == trend_ssl]

        yoy_df, month_order = build_yoy_trend_df(ctx, curr_filt, prior_filt, "revenue")
        fig_trend = px.line(
            yoy_df, x="month", y="revenue_m", color="Period",
            color_discrete_map={"Current": LC, "Prior Year": LP},
            markers=True, title="",
            labels={"month": "", "revenue_m": "Revenue ($M)"},
            category_orders={"month": month_order},
        )
        fig_trend.update_traces(line_width=2.5)
        fig_trend.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30, height=320)
        fig_trend.update_yaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        idx_df = _build_revenue_index(ctx, trend_base, trend_prior_base, trend_sl, trend_ssl)
        render_index_chart(idx_df, "vs Prior Year  —  100 = PY", PT)

    st.markdown('<div class="section-header">Revenue by Client</div>', unsafe_allow_html=True)

    rv_cl = (
        clean_for_visuals(df_curr)
        .groupby("top_level_parent_customer_name")["revenue"]
        .sum()
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    total_rev = rv_cl["revenue"].sum()
    top5_pct = (rv_cl.head(5)["revenue"].sum() / total_rev * 100) if total_rev > 0 else 0
    top10_pct = (rv_cl.head(10)["revenue"].sum() / total_rev * 100) if total_rev > 0 else 0
    n_clients = len(rv_cl)

    st.markdown(
        f"""
        <div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.5rem;">
            CONCENTRATION — Top 5 clients = <span style="color:#cbd5e1">{top5_pct:.0f}%</span> of revenue
            &nbsp;|&nbsp; Top 10 = <span style="color:#cbd5e1">{top10_pct:.0f}%</span>
            &nbsp;|&nbsp; Total clients: <span style="color:#cbd5e1">{n_clients}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    client_view = st.radio(
        "Client view",
        ["Top 15", "Top 30", "All > $100k"],
        horizontal=True,
        key="rev_client_view",
    )

    if client_view == "All > $100k":
        rv_cl_show = rv_cl[rv_cl["revenue"] >= 100_000].copy()
    else:
        n_show = {"Top 15": 15, "Top 30": 30}[client_view]
        rv_cl_show = rv_cl.head(n_show).copy()

    rv_cl_show["revenue_m"] = rv_cl_show["revenue"] / 1e6
    rv_cl_show = rv_cl_show.sort_values("revenue_m", ascending=True)

    fig_cl = px.bar(
        rv_cl_show,
        x="revenue_m",
        y="top_level_parent_customer_name",
        orientation="h",
        color="revenue_m",
        color_continuous_scale=BS,
        title=f"— {client_view}",
        labels={"revenue_m": "Revenue ($M)", "top_level_parent_customer_name": ""},
    )
    fig_cl.update_layout(
        **PT,
        coloraxis_showscale=False,
        title_font_color="#cbd5e1",
        height=max(380, len(rv_cl_show) * 24),
    )
    fig_cl.update_yaxes(categoryorder="total ascending")
    fig_cl.update_xaxes(tickprefix="$", ticksuffix="M")
    st.plotly_chart(fig_cl, use_container_width=True)


    # ── Client concentration tile — Top 10 + Other ─────────────
    st.markdown('<div class="section-header">Client Concentration</div>', unsafe_allow_html=True)

    top10_clients = rv_cl.head(10).copy()
    other_revenue = rv_cl.iloc[10:]["revenue"].sum()

    tile_clients = top10_clients.copy()

    if other_revenue > 0:
        tile_clients = pd.concat(
            [
                tile_clients,
                pd.DataFrame({
                    "top_level_parent_customer_name": ["Other"],
                    "revenue": [other_revenue],
                }),
            ],
            ignore_index=True,
        )

    rev_conc_chart_type = st.radio("Chart type", ["Tile", "Bar"], horizontal=True, key="rev_conc_chart_type")
    if rev_conc_chart_type == "Tile":
        render_tile_chart(tile_clients, "top_level_parent_customer_name", "revenue", "Top 10 + Other", BS, "rev_client_top10_other", PT)
    else:
        render_bar(tile_clients, label_col="top_level_parent_customer_name", value_col="revenue", title="Top 10 + Other", color_scale=BS, value_label="Revenue")

    # ── Client monthly trend + PY index ────────────────────────
    st.markdown('<div class="section-header">Client Trend</div>', unsafe_allow_html=True)

    client_trend_base = clean_for_visuals(df_curr_decomp)
    client_prior_base = clean_for_visuals(df_prior_decomp)

    client_options = ["All"] + sorted(
        client_trend_base["top_level_parent_customer_name"].dropna().unique().tolist()
    )

    selected_client = st.selectbox(
        "Trend — Client",
        client_options,
        key="rev_client_trend_filter",
    )

    client_trend_df = client_trend_base.copy()
    client_prior_df = client_prior_base.copy()

    if selected_client != "All":
        client_trend_df = client_trend_df[
            client_trend_df["top_level_parent_customer_name"] == selected_client
        ]
        client_prior_df = client_prior_df[
            client_prior_df["top_level_parent_customer_name"] == selected_client
        ]

    client_mth = (
        client_trend_df.groupby("accounting_period_start_date")["revenue"]
        .sum()
        .reset_index()
        .sort_values("accounting_period_start_date")
    )
    client_mth["revenue_m"] = client_mth["revenue"] / 1e6

    rev_cl_trend_mode = st.radio("View", ["Raw", "Index (100 = PY)"], horizontal=True, key="rev_cl_trend_mode")

    if rev_cl_trend_mode == "Raw":
        cl_yoy_df, cl_month_order = build_yoy_trend_df(ctx, client_trend_df, client_prior_df, "revenue")
        fig_client_trend = px.line(
            cl_yoy_df, x="month", y="revenue_m", color="Period",
            color_discrete_map={"Current": LC, "Prior Year": LP},
            markers=True, title=f"— {selected_client}",
            labels={"month": "", "revenue_m": "Revenue ($M)"},
            category_orders={"month": cl_month_order},
        )
        fig_client_trend.update_traces(line_width=2.5)
        fig_client_trend.update_layout(**PT, title_font_color="#cbd5e1", xaxis_tickangle=-30, height=320)
        fig_client_trend.update_yaxes(tickprefix="$", ticksuffix="M")
        st.plotly_chart(fig_client_trend, use_container_width=True)
    else:
        curr_m = client_trend_df.groupby(["yr", "month_num"])["revenue"].sum().reset_index()
        prior_m = client_prior_df.groupby(["yr", "month_num"])["revenue"].sum().reset_index()
        client_idx_df = pd.DataFrame(build_index_rows(ctx, curr_m, prior_m, "revenue"))
        render_index_chart(client_idx_df, f"— {selected_client}  vs Prior Year  —  100 = PY", PT)


    st.markdown(
        '<div class="section-header">Revenue Detail</div>',
        unsafe_allow_html=True,
    )

    rv_tbl = (
        clean_for_visuals(df_curr)
        .groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(revenue=("revenue", "sum"))
        .reset_index()
    )

    total_rev_tbl = rv_tbl["revenue"].sum()
    rv_tbl["rev_pct"] = (rv_tbl["revenue"] / total_rev_tbl * 100).round(1)
    rv_tbl["revenue"] = (rv_tbl["revenue"] / 1e6).round(2)
    rv_tbl = rv_tbl.sort_values(["service_line_name", "revenue"], ascending=[True, False])
    rv_tbl.columns = [c.replace("_", " ").title() for c in rv_tbl.columns]

    st.dataframe(
        rv_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue ($M)", format="$%.2f"),
            "Rev Pct": st.column_config.NumberColumn("Revenue %", format="%.1f%%"),
        },
    )

    st.download_button(
        "Download CSV",
        rv_tbl.to_csv(index=False).encode(),
        "revenue_detail.csv",
        "text/csv",
        key="rev_dl",
    )