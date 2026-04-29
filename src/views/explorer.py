"""
Insight Explorer — src/views/explorer.py

Three modes:
  Portfolio View   — heatmap (per-col scaled, $ then %) with level + top-N filter
  Comparison       — entity picker + delta cards + horizontal P&L flow diagram + radar
  Scatter Analysis — level radio + X/Y axis selectors + segment scatter
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

from src.services.finance_service import build_clean_explorer_detail
from src.utils.constants import (
    GM_LOW_PCT, CM_NEGATIVE, COGS_FLAG_PCT, LABOR_HIGH_PCT, CM_STRONG_PCT,
    CONC_TOP1, CONC_TOP3,
)
from src.utils.formatters import kpi, fmt_m, safe_pct, pct_text
from src.utils.helpers import waterfall_for_slice
from src.utils.filters import clean_for_visuals

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
_CSS = """
<style>
/* Signal flags */
.ex-flags { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:1rem; }
.ex-flag {
    display:inline-flex; align-items:center; gap:5px;
    padding:0.3rem 0.8rem; border-radius:6px;
    font-family:'DM Mono',monospace; font-size:9px;
    letter-spacing:0.06em; font-weight:500;
}
.ex-flag-red   { background:rgba(248,113,113,0.1); border:1px solid rgba(248,113,113,0.25); color:#f87171; }
.ex-flag-amber { background:rgba(251,146,60,0.1);  border:1px solid rgba(251,146,60,0.25);  color:#fb923c; }
.ex-flag-green { background:rgba(74,222,128,0.1);  border:1px solid rgba(74,222,128,0.25);  color:#4ade80; }
.ex-flag-blue  { background:rgba(96,165,250,0.1);  border:1px solid rgba(96,165,250,0.25);  color:#60a5fa; }

/* Compare cards */
.ex-card { background:#0a0d14; border:1px solid #1b2230; border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.3rem; }
.ex-card-label { font-family:'DM Mono',monospace; font-size:8px; letter-spacing:0.15em; text-transform:uppercase; color:#3a4560; margin-bottom:0.3rem; }
.ex-card-value { font-size:15px; font-weight:700; color:#f0f2f8; letter-spacing:-0.02em; line-height:1.1; }

/* P&L flow diagram */
.plflow {
    display:flex; align-items:center; gap:0;
    background:#070a10; border:1px solid #1b2230;
    border-radius:12px; padding:1rem 1.2rem;
    margin:0.8rem 0 1rem; overflow-x:auto;
}
.plflow-node {
    flex:0 0 auto; text-align:center;
    background:#0d1220; border:1px solid #1b2230;
    border-radius:10px; padding:0.7rem 0.9rem;
    min-width:100px;
}
.plflow-node-label {
    font-family:'DM Mono',monospace; font-size:8px;
    letter-spacing:0.12em; text-transform:uppercase;
    color:#4a5570; margin-bottom:0.35rem;
}
.plflow-node-a { font-family:'DM Sans',sans-serif; font-size:13px; font-weight:700; color:#f0f2f8; }
.plflow-node-b { font-family:'DM Mono',monospace; font-size:10px; color:#6b7280; margin-top:0.15rem; }
.plflow-node-delta { font-family:'DM Mono',monospace; font-size:11px; font-weight:700; margin-top:0.3rem; }
.plflow-delta-pos { color:#4ade80; }
.plflow-delta-neg { color:#f87171; }
.plflow-arrow {
    flex:0 0 auto; display:flex; flex-direction:column;
    align-items:center; padding:0 4px;
}
.plflow-arrow-op {
    font-family:'DM Mono',monospace; font-size:9px;
    color:#3a4560; margin-bottom:2px;
}
.plflow-arrow-line {
    width:28px; height:1px; background:#1b2230; position:relative;
}
.plflow-arrow-line::after {
    content:'›'; position:absolute; right:-5px; top:-8px;
    color:#2a3a50; font-size:14px;
}
.plflow-total {
    border-color:#2a3a50 !important;
    background:linear-gradient(135deg,#0d1626,#0a1020) !important;
}

/* Section header */
.ex-section {
    font-family:'DM Mono',monospace; font-size:8px; letter-spacing:0.2em;
    text-transform:uppercase; color:#3a4560; margin:1.2rem 0 0.5rem;
    padding-bottom:0.4rem; border-bottom:1px solid #111827;
}
.ex-divider { border:none; border-top:1px solid #0f1520; margin:1rem 0; }
</style>
"""

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
LEVEL_OPTIONS = {
    "Service Line":     "service_line_name",
    "Sub Service Line": "sub_service_line_name",
    "Client":           "top_level_parent_customer_name",
}
SCATTER_AXIS_OPTIONS = {
    "Revenue ($)":      "revenue",
    "Gross Margin ($)": "gross_margin",
    "Contribution ($)": "contribution",
    "GM %":             "gm_pct",
    "CM %":             "cm_pct",
    "COGS % Rev":       "cogs_pct",
    "Fixed Cost % Rev": "fixed_cost_pct",
    "Labor % Rev":      "labor_pct",
}
SEGMENT_COLORS = {
    "High / High": "#4ade80",
    "Low / High":  "#60a5fa",
    "High / Low":  "#fb923c",
    "Low / Low":   "#f87171",
}

# Heatmap column definitions — order: $ cols first, % cols after
# Each: (col_key, display_label, is_money)
# All columns share the same blue-scale colorscale (Blues-dark).
# Scaling is applied INDEPENDENTLY per column — min/max normalised within the column.
# This means Revenue and GM% are each scaled 0→1 within their own range,
# so a "dark blue" cell always means high for THAT column regardless of units.
HEATMAP_COLS = [
    ("revenue",      "Revenue",      True),
    ("gross_margin", "Gross Margin", True),
    ("contribution", "Contribution", True),
    ("cogs",         "COGS",         True),
    ("labor",        "Labor",        True),
    ("fixed_cost",   "Fixed Cost",   True),
    ("gm_pct",       "GM %",         False),
    ("cm_pct",       "CM %",         False),
    ("cogs_pct",     "COGS % Rev",   False),
    ("labor_pct",    "Labor % Rev",  False),
]

# Single shared colorscale — dark = high value within each column's own range
_HM_COLORSCALE = [
    [0.0, "#07090e"],
    [0.3, "#0d1626"],
    [0.6, "#1e3a5f"],
    [0.8, "#3b82f6"],
    [1.0, "#93c5fd"],
]

# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────
def _add_ratios(df):
    """Add percentage columns (GM%, CM%, COGS% Rev, FC% Rev, Labor% Rev) to df in-place."""
    rv = df["revenue"].replace(0, float("nan"))
    df["gm_pct"]         = (df["gross_margin"] / rv * 100).round(1)
    df["cm_pct"]         = (df["contribution"] / rv * 100).round(1)
    df["cogs_pct"]       = (df["cogs"]         / rv * 100).round(1)
    df["fixed_cost_pct"] = (df["fixed_cost"]   / rv * 100).round(1)
    df["labor_pct"]      = (df["labor"]        / rv * 100).round(1)
    return df


def _group(exp_df, level_col):
    """Aggregate the explorer detail frame to the requested grouping level and add ratios."""
    g = (exp_df.groupby(level_col)
         .agg(revenue=("revenue","sum"), cogs=("cogs","sum"),
              fixed_cost=("fixed_cost","sum"), labor=("labor","sum"),
              gross_margin=("gross_margin","sum"), contribution=("contribution","sum"))
         .reset_index())
    return _add_ratios(g)


def _axis_only():
    """Return Plotly axis style dict for the dark dashboard theme."""
    return dict(gridcolor="#141924", linecolor="#1b2230",
                tickcolor="#1b2230", tickfont=dict(color="#cbd5e1"))


def _base_layout(title="", height=420):
    """Return a base Plotly layout dict for explorer charts (transparent bg, dark axes)."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#94a3b8", size=11),
        title=title, title_font_color="#cbd5e1", title_font_size=11,
        margin=dict(l=0, r=0, t=40, b=0), height=height,
        xaxis=_axis_only(), yaxis=_axis_only(),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=10)),
    )


def _detail_table(df, level_col, key_suffix=""):
    """Render a formatted detail table and CSV download button for the explorer."""
    tbl = df.copy()
    for c in ["revenue","cogs","fixed_cost","gross_margin","labor","contribution"]:
        if c in tbl.columns:
            tbl[c] = (tbl[c] / 1e6).round(2)
    tbl = tbl.sort_values("revenue", ascending=False)
    tbl.columns = [c.replace("_"," ").title() for c in tbl.columns]
    st.dataframe(tbl, use_container_width=True, hide_index=True, column_config={
        "Revenue":      st.column_config.NumberColumn("Revenue ($M)",      format="$%.2f"),
        "Cogs":         st.column_config.NumberColumn("COGS ($M)",         format="$%.2f"),
        "Fixed Cost":   st.column_config.NumberColumn("Fixed Cost ($M)",   format="$%.2f"),
        "Gross Margin": st.column_config.NumberColumn("GM ($M)",           format="$%.2f"),
        "Labor":        st.column_config.NumberColumn("Labor ($M)",        format="$%.2f"),
        "Contribution": st.column_config.NumberColumn("Contribution ($M)", format="$%.2f"),
        "Gm Pct":       st.column_config.NumberColumn("GM %",              format="%.1f%%"),
        "Cm Pct":       st.column_config.NumberColumn("CM %",              format="%.1f%%"),
        "Labor Pct":    st.column_config.NumberColumn("Labor % Rev",       format="%.1f%%"),
        "Cogs Pct":     st.column_config.NumberColumn("COGS % Rev",        format="%.1f%%"),
    })
    st.download_button(
        "Download CSV", tbl.to_csv(index=False).encode(),
        "explorer_detail.csv", "text/csv",
        key=f"ex_dl_{level_col}_{key_suffix}",
    )


def _signal_flags(grouped, level_col):
    """Render auto-generated anomaly signal pills above a portfolio view.

    Thresholds (hard-coded):
      >30% revenue in one entity → concentration red flag
      >60% in top 3             → concentration amber flag
      CM% < 0                   → negative contribution red flag
      GM% < 20%                 → low margin amber flag
      COGS% > 65%               → high COGS amber flag
      Labor% > 40%              → high labor blue flag
      CM% > 50%                 → strong contribution green flag
    """
    flags = []
    total_rev = grouped["revenue"].sum()
    top1_pct  = safe_pct(grouped.iloc[0]["revenue"], total_rev) if len(grouped) > 0 else 0
    top3_pct  = safe_pct(grouped.head(3)["revenue"].sum(), total_rev)

    if top1_pct > CONC_TOP1:
        flags.append(("red",   f"Concentration — top entity = {top1_pct:.0f}% of revenue (>{CONC_TOP1}% threshold)"))
    elif top3_pct > CONC_TOP3:
        flags.append(("amber", f"Concentration — top 3 = {top3_pct:.0f}% of revenue (>{CONC_TOP3}% threshold)"))
    for _, r in grouped[grouped["cm_pct"] < CM_NEGATIVE].iterrows():
        flags.append(("red",   f"Negative CM — {str(r[level_col])[:25]} ({r['cm_pct']:.1f}%)"))
    for _, r in grouped[(grouped["gm_pct"] < GM_LOW_PCT) & (grouped["gm_pct"] >= 0)].head(2).iterrows():
        flags.append(("amber", f"Low GM — {str(r[level_col])[:25]} ({r['gm_pct']:.1f}%, <{GM_LOW_PCT}% threshold)"))
    for _, r in grouped[grouped["cogs_pct"] > COGS_FLAG_PCT].head(2).iterrows():
        flags.append(("amber", f"High COGS — {str(r[level_col])[:25]} ({r['cogs_pct']:.1f}% rev, >{COGS_FLAG_PCT}% threshold)"))
    for _, r in grouped[grouped["labor_pct"] > LABOR_HIGH_PCT].head(2).iterrows():
        flags.append(("blue",  f"High Labor — {str(r[level_col])[:25]} ({r['labor_pct']:.0f}% rev, >{LABOR_HIGH_PCT}% threshold)"))
    for _, r in grouped[grouped["cm_pct"] > CM_STRONG_PCT].head(2).iterrows():
        flags.append(("green", f"Strong CM — {str(r[level_col])[:25]} ({r['cm_pct']:.0f}%, >{CM_STRONG_PCT}% threshold)"))
    if not flags:
        flags.append(("blue", "No material anomalies detected for current selection"))

    css_map  = {"red":"ex-flag-red","amber":"ex-flag-amber","green":"ex-flag-green","blue":"ex-flag-blue"}
    icon_map = {"red":"▲","amber":"◆","green":"✓","blue":"○"}
    pills    = "".join([
        f'<span class="ex-flag {css_map[c]}"><span>{icon_map[c]}</span>{t}</span>'
        for c, t in flags
    ])
    st.markdown(f'<div class="ex-flags">{pills}</div>', unsafe_allow_html=True)


def _top_n_filter(grouped, level_col, key_prefix):
    """Top N radio. Returns sliced dataframe."""
    n_total = len(grouped)
    options = []
    for n in [15, 30]:
        if n < n_total:
            options.append(f"Top {n}")
    options.append("All")

    sel = st.radio("Show", options, horizontal=True, key=f"{key_prefix}_topn")
    if sel == "All":
        return grouped
    n = int(sel.replace("Top ", ""))
    return grouped.head(n)


# ─────────────────────────────────────────────────────────────
# MODE: Portfolio View — heatmap only, per-col scaled
# ─────────────────────────────────────────────────────────────
def _mode_portfolio(exp_df, df_curr):
    """Render the Portfolio View mode — per-column normalised heatmap with signal flags."""
    st.markdown('<div class="ex-section">Filters</div>', unsafe_allow_html=True)
    level_label = st.radio(
        "Group by", list(LEVEL_OPTIONS.keys()), horizontal=True, key="pv_level",
    )
    level_col = LEVEL_OPTIONS[level_label]

    grouped = _group(exp_df, level_col)
    grouped = grouped[grouped["revenue"] > 0].sort_values("revenue", ascending=False)

    if grouped.empty:
        st.info("No data for current filters.")
        return

    # Top-N filter only makes sense at Client level (SL/SSL have few rows)
    grouped_show = _top_n_filter(grouped, level_col, "pv") if level_label == "Client" else grouped

    # ── Key signals ───────────────────────────────────────────
    st.markdown('<div class="ex-section">Key Signals</div>', unsafe_allow_html=True)
    _signal_flags(grouped_show, level_col)

    # ── Heatmap scale mode ────────────────────────────────────
    hm_col1, hm_col2 = st.columns([3, 1])
    with hm_col1:
        st.markdown('<div class="ex-section">P&L Heatmap</div>', unsafe_allow_html=True)
    with hm_col2:
        scale_mode = st.radio("Scale", ["Per Column", "By Type"], horizontal=True, key="pv_hm_scale")

    if scale_mode == "Per Column":
        scale_help = "Each column independently normalised 0→1. Darker = higher within that column."
    else:
        scale_help = ("$ columns normalised together; % columns normalised together. "
                      "Darker = higher relative to all columns of that type.")
    st.markdown(
        f'<p style="font-family:DM Mono,monospace;font-size:9px;color:#4a5570;margin-bottom:0.6rem;">'
        f'{scale_help} Rows sorted by revenue.</p>',
        unsafe_allow_html=True,
    )

    entities  = grouped_show[level_col].tolist()
    col_keys  = [c for (c, _, _) in HEATMAP_COLS if c in grouped_show.columns]
    col_labels= [lbl for (c, lbl, _) in HEATMAP_COLS if c in grouped_show.columns]
    col_money = {c: m for (c, _, m) in HEATMAP_COLS}
    n_rows    = len(entities)
    n_cols    = len(col_keys)

    # Build z matrix (n_rows × n_cols)
    z_matrix   = []
    raw_matrix = []

    for row_i, entity in enumerate(entities):
        z_matrix.append([])
        raw_matrix.append([])

    if scale_mode == "Per Column":
        for col_i, col_key in enumerate(col_keys):
            raw_col = grouped_show[col_key].fillna(0).tolist()
            col_min = min(raw_col)
            col_max = max(raw_col)
            col_rng = col_max - col_min if col_max != col_min else 1.0
            for row_i, val in enumerate(raw_col):
                z_matrix[row_i].append((val - col_min) / col_rng)
                raw_matrix[row_i].append(val)
    else:
        # "By Type": $ cols share one normalisation range; % cols share another
        money_cols = [c for c in col_keys if col_money.get(c, False)]
        pct_cols   = [c for c in col_keys if not col_money.get(c, False)]
        money_max = max((grouped_show[c].fillna(0).max() for c in money_cols), default=1.0) or 1.0
        pct_max   = max((grouped_show[c].fillna(0).max() for c in pct_cols),   default=1.0) or 1.0
        for col_i, col_key in enumerate(col_keys):
            raw_col  = grouped_show[col_key].fillna(0).tolist()
            divisor  = money_max if col_money.get(col_key, False) else pct_max
            for row_i, val in enumerate(raw_col):
                z_matrix[row_i].append(max(0.0, val / divisor))
                raw_matrix[row_i].append(val)

    # Build annotation text matrix — raw values, formatted
    annotations = []
    for row_i, entity in enumerate(entities):
        for col_i, col_key in enumerate(col_keys):
            raw = raw_matrix[row_i][col_i]
            txt = fmt_m(raw) if col_money[col_key] else f"{raw:.1f}%"
            annotations.append(dict(
                x=col_labels[col_i],
                y=entity,
                text=f"<b>{txt}</b>",
                showarrow=False,
                font=dict(size=15, family="DM Mono", color="#f0f2f8"),
                xref="x", yref="y",
            ))

    # Hover text matrix — one formatted string per cell
    hover_matrix = []
    for row_i in range(n_rows):
        hover_row = []
        for col_i, col_key in enumerate(col_keys):
            raw = raw_matrix[row_i][col_i]
            hover_row.append(fmt_m(raw) if col_money[col_key] else f"{raw:.1f}%")
        hover_matrix.append(hover_row)

    fig_hm = go.Figure(go.Heatmap(
        z=z_matrix,
        x=col_labels,
        y=entities,
        colorscale=_HM_COLORSCALE,
        zmin=0, zmax=1,
        showscale=False,
        customdata=hover_matrix,
        hovertemplate="<b>%{y}</b> — %{x}<br>%{customdata}<extra></extra>",
    ))

    fig_hm.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#94a3b8", size=11),
        title="P&L Heatmap — each column independently scaled",
        title_font_color="#cbd5e1", title_font_size=11,
        annotations=annotations,
        margin=dict(l=0, r=0, t=80, b=0),
        height=max(320, n_rows * 44 + 100),
        xaxis=dict(
            side="top",
            tickfont=dict(color="#cbd5e1", size=10, family="DM Mono"),
            linecolor="#1b2230", tickcolor="#1b2230",
            tickangle=0,
        ),
        yaxis=dict(
            tickfont=dict(color="#cbd5e1", size=10),
            linecolor="#1b2230", autorange="reversed",
        ),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    # ── Detail table ──────────────────────────────────────────
    st.markdown('<div class="ex-section">Full Detail ($M)</div>', unsafe_allow_html=True)
    _detail_table(grouped_show, level_col, key_suffix="pv")


# ─────────────────────────────────────────────────────────────
# MODE: Comparison
# ─────────────────────────────────────────────────────────────
def _pl_flow_html(row_a, row_b, ent_a, ent_b):
    """
    Build horizontal P&L flow diagram showing A vs B delta at each step.
    Revenue → (−COGS) → (−Fixed Cost) → Gross Margin → (−Labor) → Contribution
    """
    steps = [
        ("Revenue",      "revenue",      None,          False),
        ("COGS",         "cogs",         "− COGS",      True),   # cost: lower is better for A
        ("Fixed Cost",   "fixed_cost",   "− Fixed Cost",True),
        ("Gross Margin", "gross_margin", "= GM",        False),
        ("Labor",        "labor",        "− Labor",     True),
        ("Contribution", "contribution", "= CM",        False),
    ]
    totals = {"gross_margin", "contribution"}

    nodes_html = ""
    for j, (label, col, arrow_label, is_cost) in enumerate(steps):
        va    = row_a[col]
        vb    = row_b[col]
        diff  = va - vb
        # For cost lines: A being lower = positive for A → flip sign for display
        delta = -diff if is_cost else diff
        is_total = col in totals

        delta_cls = "plflow-delta-pos" if delta > 0 else "plflow-delta-neg" if delta < 0 else ""
        delta_str = f"{'+'if delta>0 else ''}{fmt_m(delta)}"
        node_cls  = "plflow-node plflow-total" if is_total else "plflow-node"

        node_html = (
            f'<div class="{node_cls}">'
            f'<div class="plflow-node-label">{label}</div>'
            f'<div class="plflow-node-a">{fmt_m(va)}</div>'
            f'<div class="plflow-node-b">{fmt_m(vb)}</div>'
            f'<div class="plflow-node-delta {delta_cls}">{delta_str}</div>'
            f'</div>'
        )

        if j > 0 and arrow_label:
            nodes_html += (
                f'<div class="plflow-arrow">'
                f'<div class="plflow-arrow-op">{arrow_label}</div>'
                f'<div class="plflow-arrow-line"></div>'
                f'</div>'
            )
        nodes_html += node_html

    legend_html = (
        f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#4a5570;margin-top:0.6rem;">'
        f'Top row = <span style="color:#cbd5e1">{str(ent_a)[:30]}</span> &nbsp;|&nbsp; '
        f'Middle row = <span style="color:#6b7280">{str(ent_b)[:30]}</span> &nbsp;|&nbsp; '
        f'Bottom row = delta (green = A outperforms B, red = B outperforms A). '
        f'For cost lines, positive delta means A has lower cost.</div>'
    )

    return f'<div class="plflow">{nodes_html}</div>{legend_html}'


def _mode_compare(exp_df, ctx):
    """Render the Comparison mode — side-by-side delta cards, P&L flow diagram, and radar."""
    # ── Entity selector — level first, then pick two ──────────
    st.markdown('<div class="ex-section">Select Entities to Compare</div>', unsafe_allow_html=True)
    level_label = st.radio(
        "Compare by", list(LEVEL_OPTIONS.keys()), horizontal=True, key="cmp_level",
    )
    level_col = LEVEL_OPTIONS[level_label]

    grouped_all = _group(exp_df, level_col)
    grouped_all = grouped_all[grouped_all["revenue"] > 0].sort_values("revenue", ascending=False)
    entity_list = grouped_all[level_col].tolist()

    if len(entity_list) < 2:
        st.info("Need at least 2 entities. Adjust filters.")
        return

    cc1, cc2 = st.columns(2)
    with cc1:
        ent_a = st.selectbox("Entity A", entity_list, index=0, key="cmp_a")
    with cc2:
        remaining = [x for x in entity_list if x != ent_a]
        ent_b = st.selectbox("Entity B", remaining, index=0, key="cmp_b")

    row_a = grouped_all[grouped_all[level_col] == ent_a].iloc[0]
    row_b = grouped_all[grouped_all[level_col] == ent_b].iloc[0]

    # ── Delta summary cards ───────────────────────────────────
    st.markdown('<div class="ex-section">Metric Summary — A vs B</div>', unsafe_allow_html=True)
    compare_metrics = [
        ("Revenue",      "revenue",      "money"),
        ("Gross Margin", "gross_margin", "money"),
        ("GM %",         "gm_pct",       "pct"),
        ("Contribution", "contribution", "money"),
        ("CM %",         "cm_pct",       "pct"),
        ("Labor",        "labor",        "money"),
    ]
    hcols = st.columns(len(compare_metrics))
    for i, (lbl, col, kind) in enumerate(compare_metrics):
        va, vb  = row_a[col], row_b[col]
        diff    = va - vb
        va_s    = f"{va:.1f}%" if kind == "pct" else fmt_m(va)
        vb_s    = f"{vb:.1f}%" if kind == "pct" else fmt_m(vb)
        diff_s  = f"{diff:+.1f}pts" if kind == "pct" else f"{'+'if diff>=0 else ''}{fmt_m(diff)}"
        clr     = "#4ade80" if diff >= 0 else "#f87171"
        hcols[i].markdown(
            f'<div class="ex-card">'
            f'<div class="ex-card-label">{lbl}</div>'
            f'<div class="ex-card-value">{va_s}</div>'
            f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-top:2px;">{vb_s}</div>'
            f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{clr};margin-top:4px;">{diff_s} A vs B</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Side-by-side waterfalls ───────────────────────────────
    st.markdown('<div class="ex-section">P&L Bridge — Side by Side</div>', unsafe_allow_html=True)
    WFP = ctx["palette"]["wf_pos"]
    WFN = ctx["palette"]["wf_neg"]
    WFT = ctx["palette"]["wf_total"]
    PT  = ctx["PT"]
    wa, wb = st.columns(2)
    with wa:
        st.plotly_chart(
            waterfall_for_slice(row_a, f"{str(ent_a)[:30]} — P&L", PT, WFP, WFN, WFT),
            use_container_width=True,
        )
    with wb:
        st.plotly_chart(
            waterfall_for_slice(row_b, f"{str(ent_b)[:30]} — P&L", PT, WFP, WFN, WFT),
            use_container_width=True,
        )

    # ── Horizontal P&L flow diagram ───────────────────────────
    st.markdown('<div class="ex-section">P&L Flow — A vs B Delta</div>', unsafe_allow_html=True)
    st.markdown(_pl_flow_html(row_a, row_b, ent_a, ent_b), unsafe_allow_html=True)

    # ── Radar ─────────────────────────────────────────────────
    st.markdown('<div class="ex-section">% Metric Profile</div>', unsafe_allow_html=True)
    radar_metrics = ["gm_pct", "cm_pct", "cogs_pct", "fixed_cost_pct", "labor_pct"]
    radar_labels  = ["GM %", "CM %", "COGS %", "Fixed Cost %", "Labor %"]
    radar_max     = max(80, max(
        [row_a[m] for m in radar_metrics] + [row_b[m] for m in radar_metrics]
    ) + 10)

    radar_fig = go.Figure()
    colours = ["#60a5fa", "#fb923c"]
    for idx, (ent, row) in enumerate([(ent_a, row_a), (ent_b, row_b)]):
        vals   = [row[m] for m in radar_metrics]
        closed = vals + [vals[0]]
        lbls   = radar_labels + [radar_labels[0]]
        radar_fig.add_trace(go.Scatterpolar(
            r=closed, theta=lbls, fill="toself",
            fillcolor=colours[idx],
            name=str(ent)[:32],
            line=dict(color=colours[idx], width=2.5),
            opacity=0.75,
        ))
    radar_fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, radar_max],
                tickfont=dict(color="#94a3b8", size=11, family="DM Mono"),
                ticksuffix="%",
                gridcolor="#243041",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e2e8f0", size=13, family="DM Sans"),
                gridcolor="#243041",
                rotation=90,
                direction="clockwise",
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#94a3b8"),
        legend=dict(
            font=dict(color="#cbd5e1", size=11, family="DM Sans"),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="top", y=-0.08,
            xanchor="center", x=0.5,
        ),
        title=dict(text="% Metric Profile", font=dict(color="#cbd5e1", size=12, family="DM Sans")),
        margin=dict(l=90, r=90, t=70, b=70),
        height=480,
    )
    st.plotly_chart(radar_fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# MODE: Scatter Analysis
# ─────────────────────────────────────────────────────────────
def _classify_segment(row, med_x, med_y, x_col, y_col):
    """Return a quadrant label (High/High, Low/High, etc.) based on median splits."""
    high_x = row[x_col] >= med_x
    high_y = row[y_col] >= med_y
    if high_x and high_y:    return "High / High"
    if not high_x and high_y: return "Low / High"
    if high_x and not high_y: return "High / Low"
    return "Low / Low"


def _mode_scatter(exp_df, PT):
    """Render the Scatter Analysis mode — configurable X/Y axes with quadrant segmentation."""
    # ── Controls — level first (own row), axes below ──────────
    st.markdown('<div class="ex-section">Group By</div>', unsafe_allow_html=True)
    level_label = st.radio(
        "Group by", list(LEVEL_OPTIONS.keys()), horizontal=True, key="sc_level",
    )

    st.markdown('<div class="ex-section">Axes & Display</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([3, 3, 1])
    with sc1:
        x_label = st.selectbox(
            "X Axis", list(SCATTER_AXIS_OPTIONS.keys()),
            index=list(SCATTER_AXIS_OPTIONS.keys()).index("Revenue ($)"),
            key="scatter_x",
        )
    with sc2:
        y_label = st.selectbox(
            "Y Axis", list(SCATTER_AXIS_OPTIONS.keys()),
            index=list(SCATTER_AXIS_OPTIONS.keys()).index("GM %"),
            key="scatter_y",
        )
    with sc3:
        top_n = st.select_slider("Top N", options=[5,10,15,20,25,30], value=15, key="scatter_topn")

    level_col = LEVEL_OPTIONS[level_label]
    x_col     = SCATTER_AXIS_OPTIONS[x_label]
    y_col     = SCATTER_AXIS_OPTIONS[y_label]

    grouped = _group(exp_df, level_col)
    grouped = grouped[grouped["revenue"] > 0].sort_values("revenue", ascending=False)

    if grouped.empty:
        st.info("No data for current filters.")
        return

    cl_plot = grouped.head(top_n).copy()

    for c in [x_col, y_col]:
        if c not in cl_plot.columns:
            st.warning(f"Column '{c}' not available.")
            return

    med_x = cl_plot[x_col].median()
    med_y = cl_plot[y_col].median()

    cl_plot["segment"] = cl_plot.apply(
        lambda r: _classify_segment(r, med_x, med_y, x_col, y_col), axis=1
    )

    x_is_money = x_col in ("revenue","gross_margin","contribution","cogs","fixed_cost","labor")
    y_is_money = y_col in ("revenue","gross_margin","contribution","cogs","fixed_cost","labor")
    x_med_str  = fmt_m(med_x)   if x_is_money else f"{med_x:.1f}%"
    y_med_str  = fmt_m(med_y)   if y_is_money else f"{med_y:.1f}%"

    # Segment definition callout
    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#6b7280;margin-bottom:0.75rem;">'
        f'Quadrant splits use median of top {top_n} {level_label}s: &nbsp;'
        f'{x_label} = <span style="color:#cbd5e1">{x_med_str}</span> &nbsp;|&nbsp; '
        f'{y_label} = <span style="color:#cbd5e1">{y_med_str}</span>. &nbsp;&nbsp;'
        f'<span style="color:#4ade80">■</span> High / High = Stars &nbsp;'
        f'<span style="color:#60a5fa">■</span> Low / High = Grow &nbsp;'
        f'<span style="color:#fb923c">■</span> High / Low = Volume &nbsp;'
        f'<span style="color:#f87171">■</span> Low / Low = Review'
        f'</div>',
        unsafe_allow_html=True,
    )

    fig_sc = px.scatter(
        cl_plot, x=x_col, y=y_col,
        color="segment", color_discrete_map=SEGMENT_COLORS,
        text=level_col,
        hover_name=level_col,
        hover_data={
            c: (":.1f%" if "pct" in c else ":,.0f")
            for c in ["gm_pct","cm_pct","cogs_pct","labor_pct",
                      "revenue","gross_margin","contribution"]
            if c in cl_plot.columns
        },
        title=f"{y_label} vs {x_label} — Top {top_n} {level_label}s",
        labels={x_col: x_label, y_col: y_label, "segment": "Segment"},
    )
    fig_sc.update_traces(
        marker=dict(size=13, opacity=0.88, line=dict(width=1, color="#0b0f16")),
        textposition="top center",
        textfont=dict(size=9, color="#cbd5e1", family="DM Sans"),
    )
    fig_sc.add_vline(
        x=med_x, line_width=1, line_dash="dot", line_color="#94a3b8",
        annotation_text=f"Median: {x_med_str}",
        annotation_position="top",
        annotation_font=dict(size=9, color="#6b7280", family="DM Mono"),
    )
    fig_sc.add_hline(
        y=med_y, line_width=1, line_dash="dot", line_color="#94a3b8",
        annotation_text=f"Median: {y_med_str}",
        annotation_position="right",
        annotation_font=dict(size=9, color="#6b7280", family="DM Mono"),
    )
    fig_sc.update_layout(**PT, title_font_color="#cbd5e1", height=560, legend_title_text="Segment")
    fig_sc.update_xaxes(
        tickformat="$,.0s" if x_is_money else ".1f",
        ticksuffix=""      if x_is_money else "%",
        title=x_label,
    )
    fig_sc.update_yaxes(
        tickformat="$,.0s" if y_is_money else ".1f",
        ticksuffix=""      if y_is_money else "%",
        title=y_label,
    )
    st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown('<div class="ex-section">Full Detail ($M)</div>', unsafe_allow_html=True)
    _detail_table(cl_plot, level_col, key_suffix="scatter")


# ─────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────
def render_explorer(ctx):
    """Render the Insight Explorer tab.

    Three modes selectable via a top radio:
      Portfolio View   — heatmap of all entities with per-column normalised colour scale
                         and auto-generated anomaly signal flags.
      Comparison       — pick two entities, compare delta cards, P&L flow diagram, and radar.
      Scatter Analysis — configurable X/Y axes with quadrant segmentation and detail table.

    All three modes share the same aggregated explorer dataset built by
    build_clean_explorer_detail (gross margin joined with labor).
    """
    palette     = ctx["palette"]
    PT          = ctx["PT"]
    df_curr     = ctx["df_curr"]
    df_lab_curr = ctx["df_lab_curr"]

    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Build full explorer dataset ───────────────────────────
    exp_df = build_clean_explorer_detail(df_curr, df_lab_curr)

    # ── Mode selector ─────────────────────────────────────────
    ex_mode = st.radio(
        "Mode",
        ["Portfolio View", "Comparison", "Scatter Analysis"],
        horizontal=True, key="ex_mode_top", label_visibility="collapsed",
    )
    st.markdown('<hr class="ex-divider">', unsafe_allow_html=True)

    # ── Dispatch — each mode owns its own filters ─────────────
    if ex_mode == "Portfolio View":
        _mode_portfolio(exp_df, df_curr)

    elif ex_mode == "Comparison":
        _mode_compare(exp_df, ctx)

    elif ex_mode == "Scatter Analysis":
        _mode_scatter(exp_df, PT)