import pandas as pd
from src.db.connection import get_engine
from pathlib import Path

engine = get_engine()

def _run(filename):
    sql = (Path("src/queries") / filename).read_text()
    return pd.read_sql(sql, engine)

def get_revenue(year_from: int = 2022) -> pd.DataFrame:
    df = _run("revenue_by_period.sql")
    df["accounting_period_start_date"] = pd.to_datetime(df["accounting_period_start_date"])
    df = df[df["accounting_period_start_date"].dt.year >= year_from]
    return df

def get_profitability(year_from: int = 2024) -> pd.DataFrame:
    sql = (Path("src/queries") / "profitability.sql").read_text()
    df = pd.read_sql(sql, engine)
    df["accounting_period_start_date"] = pd.to_datetime(df["accounting_period_start_date"])
    df = df[df["accounting_period_start_date"].dt.year >= year_from]
    df = df[df["vertical_name"] != "Internal"]
    df = df[df["revenue_usd"] > 0]
    df["margin_pct"] = (df["gross_profit_usd"] / df["revenue_usd"] * 100).round(1)
    return df

def get_pipeline() -> pd.DataFrame:
    df = _run("pipeline.sql")
    df["service_line"] = df["service_line"].str.split(";")
    df = df.explode("service_line")
    df["service_line"] = df["service_line"].str.strip()
    # flag exploded rows so downstream doesn't double count deals
    df["num_deals_raw"] = df["num_deals"]
    df["num_deals"] = 1  # each exploded row = 1 service line, not N deals
    return df

def get_targets(year_from: int = 2022) -> pd.DataFrame:
    df = _run("targets.sql")
    df["quarter_start_date"] = pd.to_datetime(df["quarter_start_date"])
    df = df[df["quarter_start_date"].dt.year >= year_from]
    return df