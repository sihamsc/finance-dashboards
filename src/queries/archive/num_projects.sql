SELECT
    accounting_period_name,
    accounting_period_start_date,
    COALESCE(service_line_name, 'Unassigned') AS service_line_name,
    COALESCE(vertical_name, 'Unassigned')     AS vertical_name,
    COUNT(DISTINCT project_number)             AS num_projects,
    COUNT(DISTINCT top_level_parent_customer_id) AS num_clients
FROM core.rpt_project_revenue_and_costs
WHERE account_type_id = 'Income'
AND accounting_period_is_posted = TRUE
GROUP BY 1,2,3,4
ORDER BY accounting_period_start_date