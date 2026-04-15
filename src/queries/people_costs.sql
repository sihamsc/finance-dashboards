SELECT
    accounting_period_start_date,
    netsuite_project_number,
    SUM(actual_hours)            AS total_hours,
    SUM(timesheet_external_cost) AS people_cost_external_usd,
    SUM(timesheet_internal_cost) AS people_cost_internal_usd
FROM core.fact_sd_timesheet_cost
WHERE accounting_period_is_posted = TRUE
GROUP BY 1,2
ORDER BY accounting_period_start_date