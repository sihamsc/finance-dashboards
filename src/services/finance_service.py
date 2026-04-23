"""
Business logic layer for dashboard-ready transformations.

Keep:
- raw SQL access in src.models.financials
- UI rendering in src.views

Put:
- period filtering / current-prior prep
- headline metrics
- explorer dataframe shaping

here.
"""

from src.utils.formatters import safe_pct
from src.utils.filters import filt, filt_rolling, clean_for_visuals


def build_period_frames(
    df_gm,
    df_lab,
    *,
    is_rolling,
    curr_ym,
    prior_ym,
    selected_year,
    m_from,
    m_to,
    filters,
):
    """
    Returns current/prior GM and labor frames for the selected period.
    """
    if is_rolling:
        df_curr = filt_rolling(df_gm, curr_ym, **filters)
        df_prior = filt_rolling(df_gm, prior_ym, **filters)
        df_lab_curr = filt_rolling(df_lab, curr_ym, **filters)
        df_lab_prior = filt_rolling(df_lab, prior_ym, **filters)
    else:
        df_curr = filt(df_gm, selected_year, m_from, m_to, **filters)
        df_prior = filt(df_gm, selected_year - 1, m_from, m_to, **filters)
        df_lab_curr = filt(df_lab, selected_year, m_from, m_to, **filters)
        df_lab_prior = filt(df_lab, selected_year - 1, m_from, m_to, **filters)

    return {
        "df_curr": df_curr,
        "df_prior": df_prior,
        "df_lab_curr": df_lab_curr,
        "df_lab_prior": df_lab_prior,
    }


def build_headline_metrics(df_curr, df_prior, df_lab_curr, df_lab_prior, excl):
    """
    Build the top-level KPI metrics used in app.py header rows.
    """
    rev = df_curr["revenue"].sum()
    cogs = df_curr["cogs"].sum()
    fixed_cost = df_curr["fixed_cost"].sum()
    labor = df_lab_curr["labour_cost"].sum() if not df_lab_curr.empty else df_curr["labour"].sum()

    gm = rev - cogs - fixed_cost
    contrib = gm - labor

    rev_py = df_prior["revenue"].sum()
    cogs_py = df_prior["cogs"].sum()
    fixed_cost_py = df_prior["fixed_cost"].sum()
    labor_py = df_lab_prior["labour_cost"].sum() if not df_lab_prior.empty else df_prior["labour"].sum()

    gm_py = rev_py - cogs_py - fixed_cost_py
    contrib_py = gm_py - labor_py

    num_clients = df_curr[~df_curr["top_level_parent_customer_name"].isin(excl)]["top_level_parent_customer_name"].nunique()
    clients_py = df_prior[~df_prior["top_level_parent_customer_name"].isin(excl)]["top_level_parent_customer_name"].nunique()

    return {
        "rev": rev,
        "cogs": cogs,
        "fixed_cost": fixed_cost,
        "labor": labor,
        "gm": gm,
        "contrib": contrib,
        "rev_py": rev_py,
        "cogs_py": cogs_py,
        "fixed_cost_py": fixed_cost_py,
        "labor_py": labor_py,
        "gm_py": gm_py,
        "contrib_py": contrib_py,
        "num_clients": num_clients,
        "clients_py": clients_py,
        "gm_pct": safe_pct(gm, rev),
        "cm_pct": safe_pct(contrib, rev),
        "gm_pct_py": safe_pct(gm_py, rev_py),
        "cm_pct_py": safe_pct(contrib_py, rev_py),
        "fc_pct": safe_pct(fixed_cost, rev),
        "fc_pct_py": safe_pct(fixed_cost_py, rev_py),
        "lab_pct": safe_pct(labor, rev),
        "lab_pct_py": safe_pct(labor_py, rev_py),
    }


def build_explorer_detail(df_curr_in, df_lab_curr_in):
    """
    Build one detailed dataframe at:
      service line × sub service line × client

    Includes core P&L fields and all major % ratios.
    """
    gm_detail = (
        df_curr_in.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            fixed_cost=("fixed_cost", "sum"),
            gross_margin=("gross_margin", "sum"),
        )
        .reset_index()
    )

    labor_detail = (
        df_lab_curr_in.groupby(
            ["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
            dropna=False,
        )["labour_cost"]
        .sum()
        .reset_index()
        .rename(columns={"labour_cost": "labor"})
    )

    detail = gm_detail.merge(
        labor_detail,
        on=["service_line_name", "sub_service_line_name", "top_level_parent_customer_name"],
        how="left",
    )

    detail["labor"] = detail["labor"].fillna(0)
    detail["contribution"] = detail["gross_margin"] - detail["labor"]

    detail["gm_pct"] = (detail["gross_margin"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["cm_pct"] = (detail["contribution"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["cogs_pct"] = (detail["cogs"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["fixed_cost_pct"] = (detail["fixed_cost"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)
    detail["labor_pct"] = (detail["labor"] / detail["revenue"].replace(0, float("nan")) * 100).round(1)

    return detail


def build_clean_explorer_detail(df_curr_in, df_lab_curr_in):
    """
    Explorer detail, but stripped of '(blank)' / Unassigned rows for visuals.
    """
    return clean_for_visuals(build_explorer_detail(df_curr_in, df_lab_curr_in))