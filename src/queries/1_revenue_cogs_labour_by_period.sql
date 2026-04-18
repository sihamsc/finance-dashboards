SELECT
    r.accounting_period_name,
    r.accounting_period_start_date,
    r.service_line_name,
    r.sub_service_line_name,
    r.vertical_name,
    c.top_level_parent_customer_name,

    -- Revenue: Income rows, negated (credits are stored as negative)
    -SUM(CASE WHEN r.account_type_id = 'Income' THEN r.amount ELSE 0 END) AS revenue,

    -- COGS: direct project costs
    SUM(CASE WHEN r.account_type_id = 'COGS' THEN r.amount ELSE 0 END)   AS cogs,

    -- Labour: rows where account_type_id is NULL
    SUM(CASE WHEN r.account_type_id IS NULL THEN r.amount ELSE 0 END)     AS labour

FROM core.rpt_project_revenue_and_costs r
LEFT JOIN core.dim_customers c
    ON r.customer_id = c.customer_id
WHERE r.accounting_period_is_posted = TRUE
GROUP BY 1,2,3,4,5,6
ORDER BY r.accounting_period_start_date, c.top_level_parent_customer_name