import streamlit as st
import plotly.express as px
import pandas as pd
from src.models.financials import get_revenue, get_profitability, get_pipeline, get_targets

st.set_page_config(page_title="MarketCast Finance Dashboard", layout="wide")
st.title("MarketCast Finance Dashboard")

# ── Load data ─────────────────────────────────────────────────
@st.cache_data
def load_data():
    rev = get_revenue(year_from=2022)  # load 2 years back for YoY
    return {
        "revenue":       rev,
        "profitability": get_profitability(),
        "pipeline":      get_pipeline(),
        "targets":       get_targets(),
    }

data = load_data()

# ── Sidebar filters ───────────────────────────────────────────
st.sidebar.header("Filters")

years = sorted(data["revenue"]["accounting_period_start_date"].dt.year.unique(), reverse=True)
selected_year = st.sidebar.selectbox("Year", years, index=years.index(2025) if 2025 in years else 0)

service_lines = ["All"] + sorted(data["revenue"]["service_line_name"].dropna().unique().tolist())
selected_sl = st.sidebar.selectbox("Service Line", service_lines)

verticals = ["All"] + sorted(data["revenue"]["vertical_name"].dropna().unique().tolist())
selected_vertical = st.sidebar.selectbox("Vertical", verticals)

# ── Filter helper ─────────────────────────────────────────────
def filter_df(df, date_col="accounting_period_start_date"):
    df = df[df[date_col].dt.year == selected_year]
    if selected_sl != "All" and "service_line_name" in df.columns:
        df = df[df["service_line_name"] == selected_sl]
    if selected_vertical != "All" and "vertical_name" in df.columns:
        df = df[df["vertical_name"] == selected_vertical]
    return df

def filter_prior(df, date_col="accounting_period_start_date"):
    df = df[df[date_col].dt.year == selected_year - 1]
    if selected_sl != "All" and "service_line_name" in df.columns:
        df = df[df["service_line_name"] == selected_sl]
    if selected_vertical != "All" and "vertical_name" in df.columns:
        df = df[df["vertical_name"] == selected_vertical]
    return df

# ── Apply filters ─────────────────────────────────────────────
rev_filtered   = filter_df(data["revenue"])
rev_prior      = filter_prior(data["revenue"])
prof_filtered  = filter_df(data["profitability"])
pipe_df        = data["pipeline"]
tgt_df         = data["targets"]

# ── KPI cards ─────────────────────────────────────────────────
total_revenue  = rev_filtered["revenue_usd"].sum()
prior_revenue  = rev_prior["revenue_usd"].sum()
rev_delta      = total_revenue - prior_revenue
total_cos      = prof_filtered["cos_usd"].sum()
total_people   = prof_filtered["people_cost_usd"].sum()
total_profit   = prof_filtered["gross_profit_usd"].sum()
avg_margin     = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
num_clients    = rev_filtered["customer_name"].nunique()
total_pipeline = (
    pipe_df
    .drop_duplicates(subset=["deal_pipeline_stage_name", "owner_full_name", "num_deals_raw"])
    ["pipeline_value_usd"].sum()
)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Total Revenue",  f"${total_revenue/1e6:.1f}M", delta=f"${rev_delta/1e6:.1f}M vs LY")
col2.metric("COS",            f"${total_cos/1e6:.1f}M")
col3.metric("People Cost",    f"${total_people/1e6:.1f}M")
col4.metric("Gross Profit",   f"${total_profit/1e6:.1f}M")
col5.metric("Avg Margin",     f"{avg_margin:.1f}%")
col6.metric("Active Clients", f"{num_clients}")
col7.metric("Pipeline",       f"${total_pipeline/1e6:.1f}M")

st.divider()

# ── Row 1: Revenue this year vs last year ─────────────────────
st.subheader("Revenue: This Year vs Last Year")
rev_cy = (
    rev_filtered
    .groupby("accounting_period_start_date")["revenue_usd"]
    .sum().reset_index()
    .rename(columns={"revenue_usd": "Current Year"})
)
rev_py = (
    rev_prior
    .groupby("accounting_period_start_date")["revenue_usd"]
    .sum().reset_index()
    .rename(columns={"revenue_usd": "Prior Year"})
)
# align on month number for overlay
rev_cy["month"] = rev_cy["accounting_period_start_date"].dt.month
rev_py["month"] = rev_py["accounting_period_start_date"].dt.month
rev_yoy = rev_cy.merge(rev_py[["month", "Prior Year"]], on="month", how="left")
fig_yoy = px.line(
    rev_yoy.melt(id_vars=["accounting_period_start_date", "month"],
                 value_vars=["Current Year", "Prior Year"],
                 var_name="Period", value_name="Revenue"),
    x="accounting_period_start_date",
    y="Revenue",
    color="Period",
    markers=True,
    labels={"Revenue": "Revenue (USD)", "accounting_period_start_date": "Month"},
)
fig_yoy.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_yoy, use_container_width=True)

st.divider()

# ── Row 2: Revenue by Month | Revenue by Vertical ─────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Revenue by Month")
    rev_monthly = (
        rev_filtered
        .groupby(["accounting_period_start_date", "service_line_name"])["revenue_usd"]
        .sum().reset_index()
    )
    fig = px.bar(
        rev_monthly,
        x="accounting_period_start_date",
        y="revenue_usd",
        color="service_line_name",
        labels={"revenue_usd": "Revenue (USD)", "accounting_period_start_date": "Month"},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Revenue by Vertical")
    rev_vertical = (
        rev_filtered
        .groupby("vertical_name")["revenue_usd"]
        .sum().reset_index()
        .sort_values("revenue_usd", ascending=False)
        .head(10)
    )
    fig2 = px.bar(
        rev_vertical,
        x="revenue_usd",
        y="vertical_name",
        orientation="h",
        labels={"revenue_usd": "Revenue (USD)", "vertical_name": "Vertical"},
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 3: Top clients | Clients over time ────────────────────
col_e, col_f = st.columns(2)

with col_e:
    st.subheader("Top 15 Clients by Revenue")
    top_clients = (
        rev_filtered
        .groupby("customer_name")["revenue_usd"]
        .sum().reset_index()
        .sort_values("revenue_usd", ascending=False)
        .head(15)
    )
    fig_clients = px.bar(
        top_clients,
        x="revenue_usd",
        y="customer_name",
        orientation="h",
        labels={"revenue_usd": "Revenue (USD)", "customer_name": "Client"},
    )
    fig_clients.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_clients, use_container_width=True)

with col_f:
    st.subheader("Active Clients Over Time")
    clients_over_time = (
        data["revenue"]
        .groupby("accounting_period_start_date")["customer_name"]
        .nunique().reset_index()
        .rename(columns={"customer_name": "num_clients"})
    )
    fig_cot = px.line(
        clients_over_time,
        x="accounting_period_start_date",
        y="num_clients",
        markers=True,
        labels={"num_clients": "Number of Clients", "accounting_period_start_date": "Month"},
    )
    fig_cot.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_cot, use_container_width=True)

st.divider()

# ── Row 4: Margin by service line | Pipeline ──────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Gross Margin % by Service Line")
    margin_sl = (
        prof_filtered
        .groupby("service_line_name")
        .agg(revenue=("revenue_usd", "sum"), cost=("total_cost_usd", "sum"))
        .reset_index()
    )
    margin_sl["margin_pct"] = (
        (margin_sl["revenue"] - margin_sl["cost"]) / margin_sl["revenue"] * 100
    ).round(1)
    margin_sl = margin_sl[margin_sl["revenue"] > 0].sort_values("margin_pct", ascending=False)
    fig3 = px.bar(
        margin_sl,
        x="service_line_name",
        y="margin_pct",
        labels={"margin_pct": "Margin %", "service_line_name": "Service Line"},
        color="margin_pct",
        color_continuous_scale="RdYlGn",
    )
    fig3.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Pipeline by Stage")
    pipe_stage = (
        pipe_df
        .drop_duplicates(subset=["deal_pipeline_stage_name", "owner_full_name", "num_deals_raw"])
        .groupby("deal_pipeline_stage_name")["pipeline_value_usd"]
        .sum().reset_index()
        .sort_values("pipeline_value_usd", ascending=False)
    )
    fig4 = px.funnel(
        pipe_stage,
        x="pipeline_value_usd",
        y="deal_pipeline_stage_name",
        labels={"pipeline_value_usd": "Pipeline Value (USD)", "deal_pipeline_stage_name": "Stage"},
    )
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Row 5: Cost breakdown ─────────────────────────────────────
st.subheader("Cost Breakdown: COS vs People by Service Line")
cost_breakdown = (
    prof_filtered
    .groupby("service_line_name")
    .agg(cos=("cos_usd", "sum"), people=("people_cost_usd", "sum"))
    .reset_index()
    .melt(id_vars="service_line_name", value_vars=["cos", "people"],
          var_name="cost_type", value_name="amount")
)
cost_breakdown["cost_type"] = cost_breakdown["cost_type"].map(
    {"cos": "Cost of Sales", "people": "People Cost"}
)
fig5 = px.bar(
    cost_breakdown,
    x="service_line_name",
    y="amount",
    color="cost_type",
    barmode="stack",
    labels={"amount": "Cost (USD)", "service_line_name": "Service Line", "cost_type": "Cost Type"},
)
fig5.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Row 6: Targets ────────────────────────────────────────────
st.subheader("Quarterly Targets by Team")
fig6 = px.bar(
    tgt_df,
    x="quarter_start_date",
    y="target_usd",
    color="team_primary_name",
    barmode="group",
    labels={"target_usd": "Target (USD)", "quarter_start_date": "Quarter"},
)
st.plotly_chart(fig6, use_container_width=True)