from src.models.financials import get_revenue, get_profitability, get_pipeline, get_targets
from pathlib import Path
import pandas as pd
from src.db.connection import get_engine

engine = get_engine()

if __name__ == "__main__":
    print("\n--- Profitability with People Costs (2024+) ---")
    sql = (Path("src/queries") / "profitability.sql").read_text()
    df = pd.read_sql(sql, engine)
    df["accounting_period_start_date"] = pd.to_datetime(df["accounting_period_start_date"])
    df = df[df["accounting_period_start_date"].dt.year >= 2024]
    df = df[df["revenue_usd"] > 0]
    print(df.head(10))