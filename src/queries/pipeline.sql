SELECT
    deal_pipeline_stage_name,
    COALESCE(vertical, 'Unassigned')     AS vertical,
    COALESCE(service_line, 'Unassigned') AS service_line,
    owner_full_name,
    COUNT(DISTINCT deal_id)   AS num_deals,
    SUM(deal_amount_usd)      AS pipeline_value_usd
FROM core.rpt_hubspot_line_report
WHERE is_deal_deleted = FALSE
  AND LOWER(deal_pipeline_stage_name) NOT IN ('closed won', 'closed lost')
GROUP BY 1,2,3,4
ORDER BY pipeline_value_usd DESC NULLS LAST