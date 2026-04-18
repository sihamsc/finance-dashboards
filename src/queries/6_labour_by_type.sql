SELECT
    COUNT(*) AS row_count,
    MIN(accounting_period_start_date) AS min_period,
    MAX(accounting_period_start_date) AS max_period
FROM core.fact_sd_timesheet_cost
WHERE accounting_period_is_posted = TRUE
  AND accounting_period_start_date >= DATE '2024-01-01';