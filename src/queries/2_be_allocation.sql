WITH fixed_costs AS (
    SELECT 2022 AS yr, 1000 AS fixed_cost_be
    UNION ALL SELECT 2023, 1000
    UNION ALL SELECT 2024, 1000
    UNION ALL SELECT 2025, 1000
    UNION ALL SELECT 2026, 1000
),

be_revenue_by_customer AS (
    -- Group by top_level_parent_customer_name not customer_id
    -- This consolidates Disney subsidiaries into one Disney row
    SELECT
        EXTRACT(YEAR FROM accounting_period_start_date)::int AS yr,
        c.top_level_parent_customer_name,
        r.vertical_name,
        r.service_line_name,
        r.sub_service_line_name,
        -SUM(r.amount) AS annual_be_rev
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.account_type_id = 'Income'
      AND r.sub_service_line_name = 'Brand Effect'
      AND r.accounting_period_is_posted = TRUE
    GROUP BY 1, 2, 3, 4, 5
),

tot_be_revenue AS (
    SELECT yr, SUM(annual_be_rev) AS tot_be_rev
    FROM be_revenue_by_customer
    GROUP BY 1
),

allocation AS (
    SELECT
        b.yr,
        b.top_level_parent_customer_name,
        b.vertical_name,
        b.service_line_name,
        b.sub_service_line_name,
        b.annual_be_rev,
        t.tot_be_rev,
        f.fixed_cost_be,
        ROUND(
            ((b.annual_be_rev / NULLIF(t.tot_be_rev, 0)) * f.fixed_cost_be / 12)::numeric,
            2
        ) AS be_allocation_per_month
    FROM be_revenue_by_customer b
    JOIN tot_be_revenue t ON b.yr = t.yr
    JOIN fixed_costs f     ON b.yr = f.yr
),

periods AS (
    SELECT DISTINCT
        EXTRACT(YEAR FROM accounting_period_start_date)::int AS yr,
        accounting_period_name,
        accounting_period_start_date
    FROM core.rpt_project_revenue_and_costs
    WHERE accounting_period_is_posted = TRUE
)

SELECT
    p.yr,
    p.accounting_period_name,
    p.accounting_period_start_date,
    a.top_level_parent_customer_name,
    a.vertical_name,
    a.service_line_name,
    a.sub_service_line_name,
    a.annual_be_rev,
    a.tot_be_rev          AS annual_tot_be_rev,
    a.fixed_cost_be,
    a.be_allocation_per_month
FROM allocation a
JOIN periods p ON a.yr = p.yr
ORDER BY p.accounting_period_start_date DESC