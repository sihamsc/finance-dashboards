SELECT
    deal_id,
    deal_pipeline_stage_name,
    COALESCE(vertical, 'Unassigned')     AS vertical,
    COALESCE(service_line, 'Unassigned') AS service_line,
    owner_full_name,
    deal_amount_usd                       AS pipeline_value_usd
FROM core.rpt_hubspot_line_report
WHERE is_deal_deleted = FALSE
  AND LOWER(deal_pipeline_stage_name) NOT IN ('closed won', 'closed lost')
  AND deal_amount_usd IS NOT NULL