SELECT
    quarter_start_date,
    quarter_end_date,
    team_primary_name,
    SUM(target_amount_usd) AS target_usd
FROM core.fact_hubspot_targets
GROUP BY 1, 2, 3
ORDER BY 1, 3 DESC
