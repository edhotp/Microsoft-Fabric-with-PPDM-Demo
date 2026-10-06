-- Example queries for the data agent da_zava_asset_context (data source: lh_zava_ai, SQL analytics endpoint).
-- Add each pair under "Example queries" for the Lakehouse source: the comment line is the question.

-- Which wells lost production because of incident INC-MY-001 and how much?
SELECT well_id, SUM(lost_boe_gross) AS lost_boe_gross, SUM(lost_boe_net_wi) AS lost_boe_net_wi,
       MAX(business_publication_id) AS business_publication_id
FROM ai.loss_allocation
WHERE incident_id = 'INC-MY-001'
GROUP BY well_id
ORDER BY well_id;

-- Which equipment caused incident INC-MY-001 and how long was it down?
SELECT incident_id, equipment_id, incident_category, event_count, equipment_downtime_hours, business_publication_id
FROM ai.incident
WHERE incident_id = 'INC-MY-001';

-- Why was the oil value for well MY_B_W001 on 2025-09-20 selected?
SELECT well_id, business_date, commodity, decision_status, selected_source_system, selected_value_std,
       candidate_count, reason, candidates_json, authority_policy_version, business_publication_id
FROM ai.source_decision
WHERE well_id = 'MY_B_W001' AND business_date = '2025-09-20' AND commodity = 'Oil';

-- How many wellbores and completions does well DZ_A_W001 have, and what are its aliases?
SELECT well_id, well_name, asset_id, wellbore_count, completion_count, alias_list, business_publication_id
FROM ai.well
WHERE well_id = 'DZ_A_W001';

-- What did well MY_A_W001 produce on 2025-09-16?
SELECT well_id, business_date, oil_bbl, gas_mscf, water_bbl, gross_boe, net_wi_boe, is_complete,
       business_publication_id
FROM ai.reporting_stream_daily
WHERE well_id = 'MY_A_W001' AND business_date = '2025-09-16';

-- Which SSOT publication does the AI layer serve?
SELECT publication_id, batch_id, dataset_version, authority_policy_version, mapping_version, period_start,
       period_end, gross_boe_total, net_wi_boe_total, as_of_utc
FROM ai.publication;
