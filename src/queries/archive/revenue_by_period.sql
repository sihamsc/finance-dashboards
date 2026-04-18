SELECT
    accounting_period_name,
    accounting_period_start_date,
    COALESCE(service_line_name, 'Unassigned') AS service_line_name,
    COALESCE(vertical_name, 'Unassigned')     AS vertical_name,
    COALESCE(top_level_parent_customer_name, 'Unassigned') AS customer_name,
    -SUM(amount_usd) AS revenue_usd
FROM core.rpt_project_revenue_and_costs
WHERE account_type_id = 'Income'
  AND accounting_period_is_posted = TRUE
GROUP BY 1,2,3,4,5
ORDER BY accounting_period_start_date