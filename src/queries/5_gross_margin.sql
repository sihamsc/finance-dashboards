WITH fixed_costs AS (
    SELECT 2022 AS yr, 10158000 AS fixed_cost_be, 938000 AS fixed_cost_ae, 833000 AS fixed_cost_rta
    UNION ALL SELECT 2023, 10158000, 938000, 833000
    UNION ALL SELECT 2024, 10158000, 938000, 833000
    UNION ALL SELECT 2025, 10158000, 938000, 833000
    UNION ALL SELECT 2026, 10158000, 938000, 833000
),

base AS (
    SELECT
        r.accounting_period_name,
        r.accounting_period_start_date,
        r.service_line_name,
        r.sub_service_line_name,
        r.vertical_name,
        COALESCE(c.top_level_parent_customer_name, 'Unassigned') AS top_level_parent_customer_name,
        -SUM(CASE WHEN r.account_type_id = 'Income' THEN r.amount ELSE 0 END) AS revenue,
         SUM(CASE WHEN r.account_type_id = 'COGS'   THEN r.amount ELSE 0 END) AS cogs,
         SUM(CASE WHEN r.account_type_id IS NULL     THEN r.amount ELSE 0 END) AS labour
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.accounting_period_is_posted = TRUE
    GROUP BY 1,2,3,4,5,6
),

be_rev AS (
    SELECT
        EXTRACT(YEAR FROM r.accounting_period_start_date)::int AS yr,
        COALESCE(c.top_level_parent_customer_name, 'Unassigned') AS top_level_parent_customer_name,
        r.vertical_name,
        r.service_line_name,
        r.sub_service_line_name,
        -SUM(r.amount) AS annual_be_rev
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.account_type_id = 'Income'
      AND r.sub_service_line_name = 'Brand Effect'
      AND r.accounting_period_is_posted = TRUE
    GROUP BY 1,2,3,4,5
),

tot_be AS (
    SELECT yr, SUM(annual_be_rev) AS tot_be_rev
    FROM be_rev GROUP BY 1
),

ae_rev AS (
    SELECT
        EXTRACT(YEAR FROM r.accounting_period_start_date)::int AS yr,
        COALESCE(c.top_level_parent_customer_name, 'Unassigned') AS top_level_parent_customer_name,
        r.vertical_name,
        r.service_line_name,
        r.sub_service_line_name,
        -SUM(r.amount) AS annual_ae_rev
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.account_type_id = 'Income'
      AND r.sub_service_line_name = 'Ad Effect'
      AND r.accounting_period_is_posted = TRUE
    GROUP BY 1,2,3,4,5
),

tot_ae AS (
    SELECT yr, SUM(annual_ae_rev) AS tot_ae_rev
    FROM ae_rev GROUP BY 1
),

rta_rev AS (
    SELECT
        EXTRACT(YEAR FROM r.accounting_period_start_date)::int AS yr,
        COALESCE(c.top_level_parent_customer_name, 'Unassigned') AS top_level_parent_customer_name,
        r.vertical_name,
        r.service_line_name,
        r.sub_service_line_name,
        -SUM(r.amount) AS annual_rta_rev
    FROM core.rpt_project_revenue_and_costs r
    LEFT JOIN core.dim_customers c ON r.customer_id = c.customer_id
    WHERE r.account_type_id = 'Income'
      AND r.sub_service_line_name = 'Ad Solutions RTA'
      AND r.accounting_period_is_posted = TRUE
    GROUP BY 1,2,3,4,5
),

tot_rta AS (
    SELECT yr, SUM(annual_rta_rev) AS tot_rta_rev
    FROM rta_rev GROUP BY 1
),

periods AS (
    SELECT DISTINCT
        EXTRACT(YEAR FROM accounting_period_start_date)::int AS yr,
        accounting_period_name,
        accounting_period_start_date
    FROM core.rpt_project_revenue_and_costs
    WHERE accounting_period_is_posted = TRUE
),

be_alloc AS (
    SELECT
        p.accounting_period_name,
        p.accounting_period_start_date,
        b.top_level_parent_customer_name,
        b.vertical_name,
        b.service_line_name,
        b.sub_service_line_name,
        (b.annual_be_rev / NULLIF(t.tot_be_rev, 0)) * f.fixed_cost_be / 12 AS be_allocation
    FROM be_rev b
    JOIN tot_be t      ON b.yr = t.yr
    JOIN fixed_costs f ON b.yr = f.yr
    JOIN periods p     ON b.yr = p.yr
),

ae_alloc AS (
    SELECT
        p.accounting_period_name,
        p.accounting_period_start_date,
        b.top_level_parent_customer_name,
        b.vertical_name,
        b.service_line_name,
        b.sub_service_line_name,
        (b.annual_ae_rev / NULLIF(t.tot_ae_rev, 0)) * f.fixed_cost_ae / 12 AS ae_allocation
    FROM ae_rev b
    JOIN tot_ae t      ON b.yr = t.yr
    JOIN fixed_costs f ON b.yr = f.yr
    JOIN periods p     ON b.yr = p.yr
),

rta_alloc AS (
    SELECT
        p.accounting_period_name,
        p.accounting_period_start_date,
        b.top_level_parent_customer_name,
        b.vertical_name,
        b.service_line_name,
        b.sub_service_line_name,
        (b.annual_rta_rev / NULLIF(t.tot_rta_rev, 0)) * f.fixed_cost_rta / 12 AS rta_allocation
    FROM rta_rev b
    JOIN tot_rta t     ON b.yr = t.yr
    JOIN fixed_costs f ON b.yr = f.yr
    JOIN periods p     ON b.yr = p.yr
)

SELECT
    COALESCE(b.accounting_period_name,         be.accounting_period_name,
             ae.accounting_period_name,         rta.accounting_period_name)  AS accounting_period_name,
    COALESCE(b.accounting_period_start_date,   be.accounting_period_start_date,
             ae.accounting_period_start_date,  rta.accounting_period_start_date) AS accounting_period_start_date,
    COALESCE(b.top_level_parent_customer_name, be.top_level_parent_customer_name,
             ae.top_level_parent_customer_name,rta.top_level_parent_customer_name) AS top_level_parent_customer_name,
    COALESCE(b.vertical_name,                  be.vertical_name,
             ae.vertical_name,                 rta.vertical_name)            AS vertical_name,
    COALESCE(b.service_line_name,              be.service_line_name,
             ae.service_line_name,             rta.service_line_name)        AS service_line_name,
    COALESCE(b.sub_service_line_name,          be.sub_service_line_name,
             ae.sub_service_line_name,         rta.sub_service_line_name)    AS sub_service_line_name,
    COALESCE(b.revenue, 0) AS revenue,
    COALESCE(b.cogs,    0) AS cogs,
    COALESCE(b.labour,  0) AS labour,
    COALESCE(be.be_allocation,   0) AS be_allocation,
    COALESCE(ae.ae_allocation,   0) AS ae_allocation,
    COALESCE(rta.rta_allocation, 0) AS rta_allocation,
    COALESCE(b.revenue, 0)
        - COALESCE(b.cogs,             0)
        - COALESCE(be.be_allocation,   0)
        - COALESCE(ae.ae_allocation,   0)
        - COALESCE(rta.rta_allocation, 0) AS gross_margin,
    CASE WHEN COALESCE(b.revenue, 0) = 0 THEN NULL
         ELSE ROUND(
             ((COALESCE(b.revenue, 0)
                 - COALESCE(b.cogs,             0)
                 - COALESCE(be.be_allocation,   0)
                 - COALESCE(ae.ae_allocation,   0)
                 - COALESCE(rta.rta_allocation, 0)
             ) / NULLIF(b.revenue, 0) * 100)::numeric, 1)
    END AS gm_pct
FROM base b
FULL OUTER JOIN be_alloc be
    ON  b.accounting_period_name         = be.accounting_period_name
    AND b.top_level_parent_customer_name = be.top_level_parent_customer_name
    AND b.vertical_name                  = be.vertical_name
    AND b.service_line_name              = be.service_line_name
    AND b.sub_service_line_name          = be.sub_service_line_name
FULL OUTER JOIN ae_alloc ae
    ON  COALESCE(b.accounting_period_name,         be.accounting_period_name)         = ae.accounting_period_name
    AND COALESCE(b.top_level_parent_customer_name, be.top_level_parent_customer_name) = ae.top_level_parent_customer_name
    AND COALESCE(b.vertical_name,                  be.vertical_name)                  = ae.vertical_name
    AND COALESCE(b.service_line_name,              be.service_line_name)               = ae.service_line_name
    AND COALESCE(b.sub_service_line_name,          be.sub_service_line_name)           = ae.sub_service_line_name
FULL OUTER JOIN rta_alloc rta
    ON  COALESCE(b.accounting_period_name,         be.accounting_period_name,         ae.accounting_period_name)         = rta.accounting_period_name
    AND COALESCE(b.top_level_parent_customer_name, be.top_level_parent_customer_name, ae.top_level_parent_customer_name) = rta.top_level_parent_customer_name
    AND COALESCE(b.vertical_name,                  be.vertical_name,                  ae.vertical_name)                  = rta.vertical_name
    AND COALESCE(b.service_line_name,              be.service_line_name,              ae.service_line_name)               = rta.service_line_name
    AND COALESCE(b.sub_service_line_name,          be.sub_service_line_name,          ae.sub_service_line_name)           = rta.sub_service_line_name
ORDER BY accounting_period_start_date
