-- Labour split by client and service line
-- Uses timesheet_internal_cost from fact_sd_timesheet_cost
-- which exactly matches the NULL account_type_id rows in rpt_project_revenue_and_costs
-- Join key: netsuite_project_id = project_id (one dominant service line per project)

WITH project_dimensions AS (
    -- One row per project — pick the dominant service line (highest revenue)
    SELECT DISTINCT ON (project_id)
        project_id,
        service_line_name,
        sub_service_line_name,
        vertical_name,
        customer_id
    FROM core.rpt_project_revenue_and_costs
    WHERE accounting_period_is_posted = TRUE
    AND account_type_id = 'Income'
    ORDER BY project_id, amount ASC
),

periods AS (
    SELECT DISTINCT
        accounting_period_id,
        accounting_period_name,
        accounting_period_start_date
    FROM core.rpt_project_revenue_and_costs
    WHERE accounting_period_is_posted = TRUE
)

SELECT
    EXTRACT(YEAR FROM p.accounting_period_start_date)::int    AS yr,
    p.accounting_period_name,
    p.accounting_period_start_date,
    COALESCE(c.top_level_parent_customer_name, 'Unassigned')  AS top_level_parent_customer_name,
    COALESCE(d.service_line_name, '(blank)')                  AS service_line_name,
    COALESCE(d.sub_service_line_name, '(blank)')              AS sub_service_line_name,
    COALESCE(d.vertical_name, '(blank)')                      AS vertical_name,
    ROUND(SUM(t.timesheet_internal_cost)::numeric, 2)         AS labour_cost,
    ROUND(SUM(t.actual_hours)::numeric, 1)                    AS total_hours
FROM core.fact_sd_timesheet_cost t
LEFT JOIN project_dimensions d  ON t.netsuite_project_id  = d.project_id
LEFT JOIN core.dim_customers c  ON d.customer_id          = c.customer_id
LEFT JOIN periods p             ON t.accounting_period_id = p.accounting_period_id
WHERE t.accounting_period_is_posted = TRUE
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY p.accounting_period_start_date, labour_cost DESC
