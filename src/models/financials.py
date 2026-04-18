import pandas as pd
from sqlalchemy import text, create_engine
from src.db.connection import get_engine
from pathlib import Path

engine = get_engine()

BASE_DIR   = Path(__file__).resolve().parent.parent.parent
QUERIES_DIR = BASE_DIR / "src" / "queries"

def _run(filename):
    sql = (QUERIES_DIR / filename).read_text()
    with engine.connect() as conn:
        conn.execute(text("SET statement_timeout = '60s'"))
        return pd.read_sql(text(sql), conn)

def get_gross_margin(year_from: int = 2024) -> pd.DataFrame:
    df = _run("5_gross_margin.sql")
    df["accounting_period_start_date"] = pd.to_datetime(df["accounting_period_start_date"])
    df = df[df["accounting_period_start_date"].dt.year >= year_from]
    return df

def get_labour(year_from: int = 2024) -> pd.DataFrame:
    df = _run("6_labour_by_type.sql")
    df["accounting_period_start_date"] = pd.to_datetime(df["accounting_period_start_date"])
    df = df[df["accounting_period_start_date"].dt.year >= year_from]
    return df

def get_pipeline() -> pd.DataFrame:
    return _run("7_pipeline.sql")

def get_targets() -> pd.DataFrame:
    df = _run("8_targets.sql")
    df["quarter_start_date"] = pd.to_datetime(df["quarter_start_date"])
    return df
