/*
    Zava Energy SSOT workshop - validasi sumber Azure SQL (read-only)
    Jalankan setelah memuat batch dengan `python -m workshop load`.
    Ganti nilai @batch_id sesuai batch yang ingin diperiksa.
*/
SET NOCOUNT ON;
DECLARE @batch_id varchar(10) = 'B0';

-- 1. Status batch: hanya batch SEALED yang boleh diambil oleh pipeline Fabric
SELECT batch_id, parent_batch_id, dataset_version, state, period_start, period_end, sealed_at_utc
FROM ctl.source_batch
ORDER BY sealed_at_utc;

-- 2. Rekonsiliasi row count per entitas terhadap manifest ctl.batch_entity
DECLARE @sql nvarchar(max) = N'';
SELECT @sql = @sql + N'
SELECT ''' + c.entity_name + N''' AS entity_name, COUNT_BIG(*) AS actual_rows
FROM ' + QUOTENAME(c.source_schema) + N'.' + QUOTENAME(c.source_table) + N'
WHERE batch_id = @b UNION ALL'
FROM ctl.entity_config AS c
WHERE c.enabled = 1 AND c.entity_kind <> 'CONTROL'
ORDER BY c.ordinal;
SET @sql = LEFT(@sql, LEN(@sql) - LEN(N' UNION ALL'));
SET @sql = N'WITH actual AS (' + @sql + N')
SELECT m.entity_name, m.row_count AS expected_rows, a.actual_rows,
       CASE WHEN m.row_count = a.actual_rows THEN ''OK'' ELSE ''MISMATCH'' END AS status
FROM ctl.batch_entity AS m
JOIN actual AS a ON a.entity_name = m.entity_name
WHERE m.batch_id = @b
ORDER BY m.entity_name;';
EXEC sys.sp_executesql @sql, N'@b varchar(10)', @b = @batch_id;

-- 3. Gambaran sumber produksi per sistem (perhatikan perbedaan satuan & nama kolom IQ)
SELECT 'SRC_DZ_PROD' AS source_system, commodity, unit, COUNT(*) AS rows_in_batch
FROM src_dz.production_report WHERE batch_id = @batch_id GROUP BY commodity, unit
UNION ALL
SELECT 'SRC_MY_PROD', commodity, unit, COUNT(*)
FROM src_my.production_report WHERE batch_id = @batch_id GROUP BY commodity, unit
UNION ALL
SELECT 'SRC_MY_OPS', commodity, unit, COUNT(*)
FROM src_my.production_provisional WHERE batch_id = @batch_id GROUP BY commodity, unit
UNION ALL
SELECT 'SRC_IQ_PROD', product, qty_unit, COUNT(*)
FROM src_iq.daily_volumes WHERE batch_id = @batch_id GROUP BY product, qty_unit
ORDER BY source_system, commodity;

-- 4. Source authority register yang berlaku untuk batch ini
SELECT policy_version, domain, source_system, scope, priority, eligible_status, valid_from, valid_to, owner_role
FROM ref.source_authority
WHERE batch_id = @batch_id
ORDER BY domain, scope, priority;

-- 5. Fixture insiden INC-MY-001 (hanya ada di B0)
SELECT e.incident_id, COUNT(DISTINCT e.event_id) AS downtime_events,
       SUM(DATEDIFF(MINUTE, e.start_utc, e.end_utc)) / 60.0 AS equipment_downtime_hours,
       (SELECT COUNT(DISTINCT l.well_ref) FROM src_my.loss_allocation AS l
         WHERE l.batch_id = @batch_id
           AND l.event_id IN (SELECT event_id FROM src_my.downtime_event
                              WHERE batch_id = @batch_id AND incident_id = 'INC-MY-001')) AS affected_wells
FROM src_my.downtime_event AS e
WHERE e.batch_id = @batch_id AND e.incident_id = 'INC-MY-001'
GROUP BY e.incident_id;
