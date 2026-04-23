import pandas as pd
from src.services.finance_service import build_headline_metrics

def test_build_headline_metrics_runs():
    df_curr = pd.DataFrame([{"revenue": 100.0, "cogs": 20.0, "fixed_cost": 10.0, "labour": 15.0}])
    df_prior = pd.DataFrame([{"revenue": 80.0, "cogs": 10.0, "fixed_cost": 10.0, "labour": 10.0}])
    df_lab_curr = pd.DataFrame([{"labour_cost": 15.0}])
    df_lab_prior = pd.DataFrame([{"labour_cost": 10.0}])

    out = build_headline_metrics(df_curr, df_prior, df_lab_curr, df_lab_prior)
    assert out["rev"] == 100.0
    assert out["gm"] == 70.0
    assert out["contrib"] == 55.0
