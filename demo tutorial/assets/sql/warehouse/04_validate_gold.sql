/*
    PIEP SSOT workshop - validasi Gold (Fabric Warehouse wh_piep_gold), read-only.
    Bandingkan hasil dengan assets/expected/expected-results-standard.json.
*/

-- 1. Publikasi yang berlaku (harus tepat satu baris)
SELECT * FROM ops.vw_current_publication;

-- 2. Riwayat siklus publikasi (QUALITY_FAILED, SUPERSEDED, PUBLISHED, ...)
SELECT * FROM ops.vw_publication_history ORDER BY COALESCE(PublishedAtUtc, DecidedAtUtc, StagedAtUtc);
SELECT PublicationId, EventType, Actor, Detail, EventAtUtc FROM ops.publication_event ORDER BY EventAtUtc;

-- 3. Gold hanya berisi satu PublicationId
SELECT 'fact_production_daily' AS TableName, COUNT(DISTINCT PublicationId) AS Publications, COUNT_BIG(*) AS RowsInGold
FROM gold.fact_production_daily
UNION ALL SELECT 'dim_well', COUNT(DISTINCT PublicationId), COUNT_BIG(*) FROM gold.dim_well
UNION ALL SELECT 'fact_loss_allocation', COUNT(DISTINCT PublicationId), COUNT_BIG(*) FROM gold.fact_loss_allocation;

-- 4. Kontrol total vs manifest (selisih harus 0)
SELECT p.PublicationId,
       CAST(JSON_VALUE(p.ControlTotalsJson, '$.GrossBoe') AS decimal(19,6)) AS ManifestGrossBoe,
       (SELECT SUM(GrossBoe) FROM gold.fact_production_daily) AS GoldGrossBoe,
       CAST(JSON_VALUE(p.ControlTotalsJson, '$.NetWiBoe') AS decimal(19,6)) AS ManifestNetWiBoe,
       (SELECT SUM(NetWiBoe) FROM gold.fact_production_daily) AS GoldNetWiBoe
FROM ops.vw_current_publication AS p;

-- 5. Produksi per negara (gross dan net WI) - jawaban kunci UC01
SELECT a.CountryName, SUM(f.GrossBoe) AS GrossBoe, SUM(f.NetWiBoe) AS NetWiBoe,
       CAST(100.0 * SUM(f.IsComplete) / COUNT(*) AS decimal(5,2)) AS CompletenessPct
FROM gold.fact_production_daily AS f
JOIN gold.dim_asset AS a ON a.AssetKey = f.AssetKey
GROUP BY a.CountryName
ORDER BY a.CountryName;

-- 6. Fixture insiden INC-MY-001 (expected: 10 sumur, 4,000 BOE gross, 1,600 BOE net WI, USD 177,080 gross)
SELECT i.IncidentId, COUNT(DISTINCT l.WellKey) AS AffectedWells, SUM(l.LostBoeGross) AS LostBoeGross,
       SUM(l.LostBoeNetWi) AS LostBoeNetWi, SUM(l.ValueUsdGross) AS ValueUsdGross, SUM(l.ValueUsdNetWi) AS ValueUsdNetWi
FROM gold.fact_loss_allocation AS l
JOIN gold.dim_incident AS i ON i.IncidentKey = l.IncidentKey
WHERE i.IncidentId = 'INC-MY-001'
GROUP BY i.IncidentId;

SELECT i.IncidentId, SUM(d.DurationHours) AS EquipmentDowntimeHours
FROM gold.fact_downtime_event AS d
JOIN gold.dim_incident AS i ON i.IncidentKey = d.IncidentKey
WHERE i.IncidentId = 'INC-MY-001'
GROUP BY i.IncidentId;

-- 7. Keputusan otoritas sumber (S1/S2): sumur MY_B_W001, 2025-09-20, Oil
SELECT DecisionId, WellId, BusinessDate, Commodity, DecisionStatus, SelectedSourceSystem, SelectedRevision,
       SelectedValueStd, CandidateCount, Reason, CandidatesJson
FROM gold.source_decision
WHERE WellId = 'MY_B_W001' AND BusinessDate = '2025-09-20' AND Commodity = 'Oil';

-- 8. Bukti kualitas batch terakhir yang gagal (Q1) dan status konsumen
SELECT BatchId, Stage, Status, BlockerCount, WarningCount, InfoCount, Message
FROM ops.quality_evidence ORDER BY BatchId, UpdatedAtUtc;
SELECT BatchId, RuleId, Severity, SUM(IssueCount) AS Issues
FROM ops.dq_issue_summary GROUP BY BatchId, RuleId, Severity ORDER BY BatchId, RuleId;
SELECT PublicationId, Consumer, Status, Detail, UpdatedAtUtc FROM ops.consumer_status ORDER BY UpdatedAtUtc;
