import pandas as pd
from src.models.financials import get_gross_margin

if __name__ == "__main__":

    print("\n--- Gross Margin (2025) ---")
    df_gm = get_gross_margin()
    print(f"Rows: {len(df_gm)}")

    totals = df_gm[df_gm["accounting_period_start_date"].dt.year == 2025].agg({
        "revenue":        "sum",
        "cogs":           "sum",
        "labour":         "sum",
        "be_allocation":  "sum",
        "ae_allocation":  "sum",
        "rta_allocation": "sum",
        "gross_margin":   "sum"
    }).round(0)

    print(totals)
    print(f"GM%: {totals['gross_margin']/totals['revenue']*100:.1f}%")
    print(f"Contribution: ${(totals['gross_margin']-totals['labour'])/1e6:.1f}M")
    print(f"CM%: {(totals['gross_margin']-totals['labour'])/totals['revenue']*100:.1f}%")
