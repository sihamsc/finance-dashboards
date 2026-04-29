# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dashboard
streamlit run app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_finance_service.py

# Install dependencies (uses uv)
uv sync

# Docker build and run
docker build -t finance-dashboards .
docker run -p 8080:8080 finance-dashboards
```

## Environment / Secrets

Database credentials are loaded from `.env` (local) or Streamlit secrets (deployed). Required vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. The app connects to a PostgreSQL database via SQLAlchemy + psycopg2.

## Architecture

This is a single-page multi-tab Streamlit dashboard for financial P&L analysis. The data flow is:

```
PostgreSQL DB
  → src/models/financials.py   (raw SQL via src/queries/*.sql)
  → app.py load_data()         (@st.cache_data, runs once)
  → src/services/finance_service.py  (period slicing + metric aggregation)
  → src/views/*.py             (one render_*() function per tab)
```

**`app.py`** is the entry point and owns the full sidebar (time filters + theme picker). It builds two sets of period-filtered frames on every rerun — `period_frames` (respects all filters) and `decomp_period_frames` (SL/Sub-SL filters unlocked, for distribution charts). A `context` dict packages all shared state and is passed into every view's `render_*()` function.

**`src/services/finance_service.py`** is the business logic layer. `build_period_frames()` handles both standard (year + month range) and Rolling 12M modes. `build_headline_metrics()` computes all top-level KPIs. `build_explorer_detail()` / `build_clean_explorer_detail()` produce the client × SL × sub-SL detail table.

**`src/views/`** — one file per tab. Each exports a single `render_*(context)` function. Views must not do period slicing themselves; they consume pre-built frames from `context`. The `decomp_*` frames exist specifically so distribution charts (treemaps, waterfalls) show full SL breakdowns even when a SL filter is active.

**`src/utils/`**:
- `filters.py` — `filt()` / `filt_rolling()` for period slicing; `EXCL` = `["Unassigned", "(blank)"]`; `clean_for_visuals()` strips blank-labelled rows before charting
- `theme.py` — `get_theme_palette(name)` returns colour dict; `PT` is the global Plotly layout base; `plotly_layout(**overrides)` safely deep-merges overrides
- `charts.py` — reusable Plotly helpers: `render_treemap`, `render_index_chart`, `build_yoy_trend_df`, `build_index_rows`, `classify_segment`
- `formatters.py` — `kpi()` returns HTML for a metric card; `fmt_m()` formats dollar values in $M

**`src/models/financials.py`** maps to numbered SQL files in `src/queries/`. The primary dataset is `5_gross_margin.sql` (revenue, cogs, labour, allocations per client/SL/month). Labour by client comes from `9_labour_by_client_service_line.sql` and is kept separate because it has different granularity.

## Key domain concepts

- **Fixed Cost** = `be_allocation + ae_allocation + rta_allocation` (computed in `app.py` load_data)
- **Gross Margin** = `Revenue – COGS – Fixed Cost`
- **Contribution** = `Gross Margin – Labor`
- Prior-year comparison is always the same time window one year back
- `df_curr_decomp` / `df_lab_curr_decomp` exist so decomposition charts always show the full SL split; use `remove_service_line_filters()` from `filters.py` when building charts that should ignore SL sidebar selection

## Tests

Tests live in `tests/` and use pytest. They test pure business logic in `src/services/` and `src/utils/` only — no database, no Streamlit. The `build_headline_metrics()` signature requires an `excl` argument (list of excluded client names, typically `EXCL` from `filters.py`).