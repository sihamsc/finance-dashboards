WITH revenue_and_cos AS (
    SELECT
        accounting_period_name,
        accounting_period_start_date,
        COALESCE(service_line_name, 'Unassigned') AS service_line_name,
        COALESCE(vertical_name, 'Unassigned')     AS vertical_name,
        project_id,
        accounting_period_id,
        -SUM(CASE WHEN account_type_id = 'Income' THEN amount_usd ELSE 0 END) AS revenue_usd,
         SUM(CASE WHEN account_type_id = 'COGS'   THEN amount_usd ELSE 0 END) AS cos_usd
    FROM core.rpt_project_revenue_and_costs
    WHERE accounting_period_is_posted = TRUE
    GROUP BY 1,2,3,4,5,6
),
people AS (
    SELECT
        netsuite_project_id,
        accounting_period_id,
        SUM(timesheet_external_cost) AS people_cost_usd
    FROM core.fact_sd_timesheet_cost
    WHERE accounting_period_is_posted = TRUE
    GROUP BY 1,2
),
joined AS (
    SELECT
        r.accounting_period_name,
        r.accounting_period_start_date,
        r.service_line_name,
        r.vertical_name,
        r.revenue_usd,
        r.cos_usd,
        COALESCE(p.people_cost_usd, 0) AS people_cost_usd
    FROM revenue_and_cos r
    LEFT JOIN people p
        ON  r.project_id           = p.netsuite_project_id
        AND r.accounting_period_id = p.accounting_period_id
)
SELECT
    accounting_period_name,
    accounting_period_start_date,
    service_line_name,
    vertical_name,
    SUM(revenue_usd)                             AS revenue_usd,
    SUM(cos_usd)                                 AS cos_usd,
    SUM(people_cost_usd)                         AS people_cost_usd,
    SUM(cos_usd) + SUM(people_cost_usd)          AS total_cost_usd,
    SUM(revenue_usd) - SUM(cos_usd) - SUM(people_cost_usd) AS gross_profit_usd
FROM joined
GROUP BY 1,2,3,4
ORDER BY accounting_period_start_date