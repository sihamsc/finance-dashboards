WITH fixed_costs AS (
    SELECT 2022 AS yr, 10158000 AS fixed_cost_be, 938000 AS fixed_cost_ae, 833000 AS fixed_cost_rta
    UNION ALL SELECT 2023, 10158000, 938000, 833000
    UNION ALL SELECT 2024, 10158000, 938000, 833000
    UNION ALL SELECT 2025, 10158000, 938000, 833000
    UNION ALL SELECT 2026, 10158000, 938000, 833000
),

-- Single scan of the source table
detail AS (
    SELECT
        EXTRACT(YEAR FROM r.accounting_period_start_date)::int AS yr,
        r.accounting_period_name,
        r.accounting_period_start_date,
        r.service_line_name,
        r.sub_service_line_name,
        r.vertical_name,
        COALESCE(c.top_level_parent_customer_name, 'Unassigned') AS top_level_parent_customer_name,
        r.account_type_id,
        r.amount
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.accounting_period_is_posted = TRUE
),

-- Monthly base metrics per (period × client × vertical × SL × sub_SL)
base AS (
    SELECT
        yr,
        accounting_period_name,
        accounting_period_start_date,
        service_line_name,
        sub_service_line_name,
        vertical_name,
        top_level_parent_customer_name,
        -SUM(CASE WHEN account_type_id = 'Income' THEN amount ELSE 0 END) AS revenue,
         SUM(CASE WHEN account_type_id = 'COGS'   THEN amount ELSE 0 END) AS cogs,
         SUM(CASE WHEN account_type_id IS NULL     THEN amount ELSE 0 END) AS labour
    FROM detail
    GROUP BY 1,2,3,4,5,6,7
),

-- Annual revenue per client/SL for the three fixed-cost sub-service-lines
annual_alloc_rev AS (
    SELECT
        yr,
        top_level_parent_customer_name,
        vertical_name,
        service_line_name,
        sub_service_line_name,
        -SUM(amount) AS annual_rev
    FROM detail
    WHERE account_type_id = 'Income'
      AND sub_service_line_name IN ('Brand Effect', 'Ad Effect', 'Ad Solutions RTA')
    GROUP BY 1,2,3,4,5
),

-- Annual totals per sub-SL type (denominator for allocation ratio)
annual_totals AS (
    SELECT yr, sub_service_line_name, SUM(annual_rev) AS tot_rev
    FROM annual_alloc_rev
    GROUP BY 1,2
),

-- Distinct periods for monthly expansion of annual allocations
periods AS (
    SELECT DISTINCT yr, accounting_period_name, accounting_period_start_date
    FROM detail
),

-- Expand each client's annual allocation to one row per month
monthly_alloc AS (
    SELECT
        p.accounting_period_name,
        p.accounting_period_start_date,
        ar.top_level_parent_customer_name,
        ar.vertical_name,
        ar.service_line_name,
        ar.sub_service_line_name,
        CASE ar.sub_service_line_name
            WHEN 'Brand Effect'     THEN (ar.annual_rev / NULLIF(t.tot_rev, 0)) * f.fixed_cost_be  / 12
            WHEN 'Ad Effect'        THEN (ar.annual_rev / NULLIF(t.tot_rev, 0)) * f.fixed_cost_ae  / 12
            WHEN 'Ad Solutions RTA' THEN (ar.annual_rev / NULLIF(t.tot_rev, 0)) * f.fixed_cost_rta / 12
        END AS allocation
    FROM annual_alloc_rev ar
    JOIN annual_totals t ON ar.yr = t.yr AND ar.sub_service_line_name = t.sub_service_line_name
    JOIN fixed_costs f   ON ar.yr = f.yr
    JOIN periods p       ON ar.yr = p.yr
)

SELECT
    b.accounting_period_name,
    b.accounting_period_start_date,
    b.top_level_parent_customer_name,
    b.vertical_name,
    b.service_line_name,
    b.sub_service_line_name,
    b.revenue,
    b.cogs,
    b.labour,
    -- BE/AE/RTA are mutually exclusive by sub_service_line; a row carries at most one
    COALESCE(CASE WHEN b.sub_service_line_name = 'Brand Effect'     THEN m.allocation END, 0) AS be_allocation,
    COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Effect'        THEN m.allocation END, 0) AS ae_allocation,
    COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Solutions RTA' THEN m.allocation END, 0) AS rta_allocation,
    b.revenue
        - b.cogs
        - COALESCE(CASE WHEN b.sub_service_line_name = 'Brand Effect'     THEN m.allocation END, 0)
        - COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Effect'        THEN m.allocation END, 0)
        - COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Solutions RTA' THEN m.allocation END, 0) AS gross_margin,
    CASE WHEN b.revenue = 0 THEN NULL
         ELSE ROUND(
             ((b.revenue
                 - b.cogs
                 - COALESCE(CASE WHEN b.sub_service_line_name = 'Brand Effect'     THEN m.allocation END, 0)
                 - COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Effect'        THEN m.allocation END, 0)
                 - COALESCE(CASE WHEN b.sub_service_line_name = 'Ad Solutions RTA' THEN m.allocation END, 0)
             ) / NULLIF(b.revenue, 0) * 100)::numeric, 1)
    END AS gm_pct
FROM base b
LEFT JOIN monthly_alloc m
    ON  b.accounting_period_name         = m.accounting_period_name
    AND b.top_level_parent_customer_name = m.top_level_parent_customer_name
    AND b.vertical_name                  = m.vertical_name
    AND b.service_line_name              = m.service_line_name
    AND b.sub_service_line_name          = m.sub_service_line_name
ORDER BY b.accounting_period_start_date