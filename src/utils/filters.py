import pandas as pd

MONTH_MAP = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}
MONTH_NAMES = [MONTH_MAP[i] for i in range(1, 13)]
EXCL = ["Unassigned", "(blank)"]

def clean_for_visuals(df, client_col="top_level_parent_customer_name"):
    d = df.copy()
    for col in ["service_line_name", "sub_service_line_name", "vertical_name"]:
        if col in d.columns:
            d = d[d[col] != "(blank)"]
    if client_col in d.columns:
        d = d[~d[client_col].isin(EXCL)]
    return d

def apply_dim_filters(d, selected_sl, selected_ssl, selected_vertical, selected_customer):
    if selected_sl != "All":
        d = d[d["service_line_name"] == selected_sl]
    if selected_ssl != "All":
        d = d[d["sub_service_line_name"] == selected_ssl]
    if selected_vertical != "All":
        d = d[d["vertical_name"] == selected_vertical]
    if selected_customer != "All":
        d = d[d["top_level_parent_customer_name"] == selected_customer]
    return d

def filt(data, year, m1, m2, selected_sl, selected_ssl, selected_vertical, selected_customer):
    d = data[(data["yr"] == year) & (data["month_num"] >= m1) & (data["month_num"] <= m2)].copy()
    return apply_dim_filters(d, selected_sl, selected_ssl, selected_vertical, selected_customer)

def rolling_ym(base_year, end_month):
    start_month = (end_month % 12) + 1
    if start_month == 1:
        return [(base_year, m) for m in range(1, 13)]
    return (
        [(base_year - 1, m) for m in range(start_month, 13)] +
        [(base_year, m) for m in range(1, end_month + 1)]
    )

def filt_rolling(data, ym_list, selected_sl, selected_ssl, selected_vertical, selected_customer):
    if not ym_list:
        return pd.DataFrame(columns=data.columns)

    mask = pd.Series(False, index=data.index)
    for yr, mn in ym_list:
        mask |= ((data["yr"] == yr) & (data["month_num"] == mn))

    d = data[mask].copy()
    return apply_dim_filters(d, selected_sl, selected_ssl, selected_vertical, selected_customer)

def ordered_month_axis_labels(ym_list):
    return [MONTH_MAP[m] for _, m in ym_list]

def rank_window_slice(df, sort_col, start_rank, window_size=15):
    d = df.sort_values(sort_col, ascending=False).reset_index(drop=True).copy()
    d["rank"] = d.index + 1
    end_rank = start_rank + window_size - 1
    return d[(d["rank"] >= start_rank) & (d["rank"] <= end_rank)].copy(), end_rank, len(d)

def rank_window_options(n_items, window_size=15):
    if n_items <= 0:
        return [1]
    return list(range(1, n_items + 1, window_size))