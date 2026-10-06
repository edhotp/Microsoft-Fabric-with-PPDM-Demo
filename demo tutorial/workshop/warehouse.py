"""Gold contract for Fabric Warehouse and generator for the Warehouse T-SQL scripts.

The Spark notebook nb_05 writes the same tables (plus PublicationId) to the Lakehouse `serve` schema.
tests/test_notebooks_spark.py checks that both sides match column by column.
"""

from __future__ import annotations

from workshop.contracts import AUTHORITY_POLICY_VERSION, KPI_CONTRACT_VERSION, MAPPING_VERSION

LAKEHOUSE = "lh_piep_core"

V = "decimal(19,6)"
M = "decimal(19,4)"


def _cols(spec: str) -> tuple[tuple[str, str, bool], ...]:
    result = []
    for token in spec.split():
        name, sql_type = token.split(":")
        nullable = sql_type.endswith("?")
        result.append((name, sql_type.rstrip("?").replace("V", V).replace("M", M), nullable))
    return tuple(result)


GOLD_TABLES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "dim_date": _cols("DateKey:int Date:date Year:int MonthNumber:int MonthName:varchar(3) YearMonth:varchar(7) "
                      "MonthStart:date DayOfMonth:int DaysInMonth:int"),
    "dim_asset": _cols("AssetKey:bigint AssetId:varchar(10) AssetName:varchar(100) CountryCode:varchar(2) "
                       "CountryName:varchar(100) FacilityId:varchar(20)?"),
    "dim_well": _cols("WellKey:bigint WellId:varchar(20) WellName:varchar(100) AssetKey:bigint AssetId:varchar(10) "
                      "CountryCode:varchar(2) StreamId:varchar(30) WellboreCount:int CompletionCount:int "
                      "AliasList:varchar(1000)? WellStatus:varchar(20)"),
    "dim_equipment": _cols("EquipmentKey:bigint EquipmentId:varchar(20) EquipmentName:varchar(100) "
                           "EquipmentType:varchar(40) FacilityId:varchar(20) AssetKey:bigint AssetId:varchar(10) "
                           "CountryCode:varchar(2)"),
    "dim_incident": _cols("IncidentKey:bigint IncidentId:varchar(30) IncidentCategory:varchar(30) EventCount:int"),
    "dim_scenario": _cols("ScenarioKey:bigint ScenarioId:varchar(20) ScenarioName:varchar(100)"),
    "dim_cost_category": _cols("CostCategoryKey:bigint CostCategory:varchar(30)"),
    "fact_production_daily": _cols(
        "DateKey:int WellKey:bigint AssetKey:bigint StreamId:varchar(30) OilBbl:V? GasMscf:V? WaterBbl:V? "
        "GrossBoe:V? WiShare:decimal(9,6)? NetWiBoe:V? ObservationCount:int ExpectedObservationCount:int "
        "IsComplete:int RetractedCount:int SelectedSources:varchar(200)? MaxRevision:int?"),
    "fact_target_daily": _cols("DateKey:int AssetKey:bigint ScenarioKey:bigint TargetOilBbl:V? TargetGasMscf:V? "
                               "TargetBoe:V?"),
    "fact_operating_cost_monthly": _cols(
        "MonthDateKey:int AssetKey:bigint CostCategoryKey:bigint CurrencyCode:varchar(3) AmountLocal:M "
        "UsdPerUnit:decimal(18,9) AmountUsd:M ClosingStatus:varchar(20) CostId:varchar(30)"),
    "fact_downtime_event": _cols(
        "EventId:varchar(30) IncidentKey:bigint EquipmentKey:bigint AssetKey:bigint StartDateKey:int "
        "StartUtc:datetime2(6) EndUtc:datetime2(6) DurationHours:decimal(9,3) Reason:varchar(120)"),
    "fact_loss_allocation": _cols(
        "LossId:varchar(40) DateKey:int WellKey:bigint AssetKey:bigint IncidentKey:bigint EquipmentKey:bigint "
        "EventId:varchar(30) LostOilBbl:V LostGasMscf:V LostBoeGross:V WiShare:decimal(9,6) LostBoeNetWi:V "
        "ValueUsdGross:M ValueUsdNetWi:M"),
    "master_wellbore": _cols("WellboreId:varchar(30) WellId:varchar(20) WellboreName:varchar(100)"),
    "master_completion": _cols("CompletionId:varchar(40) WellboreId:varchar(30) StreamId:varchar(30) "
                               "CompletionName:varchar(100)"),
    "source_decision": _cols(
        "DecisionId:varchar(64) CanonicalKey:varchar(80) StreamId:varchar(30) WellId:varchar(20) BusinessDate:date "
        "Commodity:varchar(10) CandidateCount:int DecisionStatus:varchar(30) SelectedSourceSystem:varchar(30)? "
        "SelectedObservationId:varchar(32)? SelectedRevision:int? SelectedValueStd:V? Reason:varchar(400)? "
        "CandidatesJson:varchar(4000)? AuthorityPolicyVersion:varchar(20)"),
}

PRIMARY_KEYS = {
    "dim_date": "DateKey", "dim_asset": "AssetKey", "dim_well": "WellKey", "dim_equipment": "EquipmentKey",
    "dim_incident": "IncidentKey", "dim_scenario": "ScenarioKey", "dim_cost_category": "CostCategoryKey",
}

OPS_TABLES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "publication": _cols(
        "PublicationId:varchar(30) BatchId:varchar(10) ParentBatchId:varchar(10)? DatasetVersion:varchar(30)? "
        "AuthorityPolicyVersion:varchar(20)? MappingVersion:varchar(30)? KpiContractVersion:varchar(20)? "
        "UomFactorVersion:varchar(20)? PeriodStart:date? PeriodEnd:date? ControlTotalsJson:varchar(4000)? "
        "BlockerCount:int WarningCount:int InfoCount:int Status:varchar(30) StagedAtUtc:datetime2(6)? "
        "DecidedBy:varchar(256)? DecidedAtUtc:datetime2(6)? DecisionComment:varchar(1000)? "
        "PublishedAtUtc:datetime2(6)? SupersededBy:varchar(30)? RunId:varchar(100)?"),
    "publication_event": _cols("PublicationId:varchar(30) EventType:varchar(40) Actor:varchar(256) "
                               "Detail:varchar(4000)? EventAtUtc:datetime2(6)"),
    "authorized_approver": _cols("ApproverUpn:varchar(256) ApproverRole:varchar(100) DataDomain:varchar(30) "
                                 "IsActive:bit"),
    "kpi_contract": _cols("KpiId:varchar(20) KpiName:varchar(100) Definition:varchar(1000) Unit:varchar(20) "
                          "Grain:varchar(100) DataOwner:varchar(100) SourceColumn:varchar(200) "
                          "ContractVersion:varchar(20)"),
    "quality_evidence": _cols("BatchId:varchar(10) Stage:varchar(30) Status:varchar(40) PublicationId:varchar(30)? "
                              "BlockerCount:int WarningCount:int InfoCount:int Message:varchar(4000)? "
                              "RunId:varchar(100)? UpdatedAtUtc:datetime2(6)? SyncedAtUtc:datetime2(6)"),
    "dq_issue_summary": _cols("BatchId:varchar(10) Stage:varchar(30) RuleId:varchar(10) Severity:varchar(10) "
                              "IssueCount:int SyncedAtUtc:datetime2(6)"),
    "consumer_status": _cols("PublicationId:varchar(30) Consumer:varchar(60) Status:varchar(30) "
                             "Detail:varchar(1000)? UpdatedAtUtc:datetime2(6)"),
}

KPI_CONTRACT = [
    ("KPI-01", "Gross production (BOE)", "Oil bbl + Gas Mscf / 6 for the selected authoritative value of each "
     "stream-day", "BOE", "Reporting stream x day", "Production Reporting", "fact_production_daily.GrossBoe"),
    ("KPI-02", "Net WI production (BOE)", "Gross BOE x working interest effective on the business date",
     "BOE", "Reporting stream x day", "Production Reporting", "fact_production_daily.NetWiBoe"),
    ("KPI-03", "Target achievement (%)", "Gross BOE / Target BOE for the same asset and dates", "%",
     "Asset x day", "Planning (RKAP)", "fact_target_daily.TargetBoe"),
    ("KPI-04", "Data completeness (%)", "Stream-days with Oil, Gas and Water / all stream-days in period", "%",
     "Reporting stream x day", "Data Management", "fact_production_daily.IsComplete"),
    ("KPI-05", "Production loss (BOE)", "Approved loss allocation, gross and net WI", "BOE",
     "Well x day x event", "Operations", "fact_loss_allocation.LostBoeGross"),
    ("KPI-06", "Opex (USD)", "Closing operating cost converted with the approved monthly FX rate", "USD",
     "Asset x month x category", "Finance", "fact_operating_cost_monthly.AmountUsd"),
    ("KPI-07", "Equipment downtime (hours)", "Sum of downtime event duration", "hours", "Event",
     "Operations", "fact_downtime_event.DurationHours"),
]


def _ddl_columns(columns, with_publication: bool) -> str:
    lines = [f"    [{name}] {sql_type} {'NULL' if nullable else 'NOT NULL'}" for name, sql_type, nullable in columns]
    if with_publication:
        lines.append("    [PublicationId] varchar(30) NOT NULL")
    return ",\n".join(lines)


def _create(schema: str, table: str, columns, with_publication: bool) -> str:
    return (f"IF OBJECT_ID(N'{schema}.{table}', N'U') IS NULL\n"
            f"CREATE TABLE [{schema}].[{table}] (\n{_ddl_columns(columns, with_publication)}\n);\nGO\n")


def column_list(table: str) -> str:
    return ", ".join(f"[{name}]" for name, _, _ in GOLD_TABLES[table]) + ", [PublicationId]"


def render_objects() -> str:
    parts = ["-- Generated by `python -m workshop render-warehouse` from workshop/warehouse.py. Do not edit by hand.",
             "-- Target: Fabric Warehouse wh_piep_gold (same workspace as lh_piep_core). Safe to re-run.", ""]
    for schema in ("stg", "gold", "ops"):
        parts.append(f"IF SCHEMA_ID(N'{schema}') IS NULL EXEC(N'CREATE SCHEMA [{schema}]');\nGO")
    parts.append("\n-- stg: kandidat publikasi (beberapa PublicationId); gold: satu publikasi yang disetujui")
    for table, columns in GOLD_TABLES.items():
        parts.append(_create("stg", table, columns, True))
        parts.append(_create("gold", table, columns, True))
    parts.append("-- ops: manifest publikasi, approval, bukti kualitas, dan status konsumen")
    for table, columns in OPS_TABLES.items():
        parts.append(_create("ops", table, columns, False))
    parts.append("-- Constraint informatif (NOT ENFORCED) membantu optimizer dan relasi semantic model")
    for table, key in PRIMARY_KEYS.items():
        name = f"PK_gold_{table}"
        parts.append(f"IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'{name}')\n"
                     f"    ALTER TABLE [gold].[{table}] ADD CONSTRAINT [{name}] PRIMARY KEY NONCLUSTERED ([{key}]) "
                     f"NOT ENFORCED;\nGO")
    parts.append("IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'PK_ops_publication')\n"
                 "    ALTER TABLE [ops].[publication] ADD CONSTRAINT [PK_ops_publication] PRIMARY KEY NONCLUSTERED "
                 "([PublicationId]) NOT ENFORCED;\nGO")
    parts.append("""CREATE OR ALTER VIEW ops.vw_current_publication AS
SELECT p.PublicationId, p.BatchId, p.DatasetVersion, p.AuthorityPolicyVersion, p.MappingVersion,
       p.KpiContractVersion, p.PeriodStart, p.PeriodEnd, p.DecidedBy AS ApprovedBy, p.DecidedAtUtc AS ApprovedAtUtc,
       p.PublishedAtUtc, p.ControlTotalsJson
FROM ops.publication AS p
WHERE p.Status = 'PUBLISHED';
GO
""")
    parts.append("""CREATE OR ALTER VIEW ops.vw_publication_history AS
SELECT PublicationId, BatchId, Status, BlockerCount, WarningCount, InfoCount, StagedAtUtc, DecidedBy, DecidedAtUtc,
       DecisionComment, PublishedAtUtc, SupersededBy, AuthorityPolicyVersion, MappingVersion
FROM ops.publication;
GO
""")
    return "\n".join(parts) + "\n"


def _lake(table: str) -> str:
    return f"{LAKEHOUSE}.serve.{table}"


def render_procedures() -> str:
    tables = list(GOLD_TABLES)
    count_union = "\n        UNION ALL ".join(
        f"SELECT '{t}' AS TableName, COUNT_BIG(*) AS ActualRows FROM {_lake(t)} WHERE PublicationId = @PublicationId"
        for t in tables)
    stage_copy = "\n".join(
        f"        DELETE FROM stg.{t} WHERE PublicationId = @PublicationId;\n"
        f"        INSERT INTO stg.{t} ({column_list(t)})\n"
        f"        SELECT {column_list(t)} FROM {_lake(t)} WHERE PublicationId = @PublicationId;"
        for t in tables)
    publish_copy = "\n".join(
        f"        DELETE FROM gold.{t};\n"
        f"        INSERT INTO gold.{t} ({column_list(t)})\n"
        f"        SELECT {column_list(t)} FROM stg.{t} WHERE PublicationId = @PublicationId;"
        for t in tables)
    return f"""-- Generated by `python -m workshop render-warehouse` from workshop/warehouse.py. Do not edit by hand.
-- Prosedur siklus publikasi SSOT: stage -> approve -> publish, plus bukti kualitas dan status konsumen.

CREATE OR ALTER PROCEDURE ops.usp_stage_candidate
    @PublicationId varchar(30),
    @RunId varchar(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(6) = SYSUTCDATETIME();

    IF EXISTS (SELECT 1 FROM ops.publication WHERE PublicationId = @PublicationId AND Status = 'PUBLISHED')
    BEGIN
        SELECT @PublicationId AS PublicationId, 'ALREADY_PUBLISHED' AS Result;
        RETURN;
    END;
    IF (SELECT COUNT(*) FROM {_lake('publication_candidate')} WHERE PublicationId = @PublicationId) <> 1
        THROW 50010, 'Publication candidate not found in lh_piep_core.serve.publication_candidate. Run nb_05 first or wait for SQL analytics endpoint sync.', 1;

    -- Tunggu sinkronisasi metadata SQL analytics endpoint: row count harus sama dengan manifest nb_05
    DECLARE @expectedTables int, @mismatches int;
    SELECT @expectedTables = COUNT(*) FROM {_lake('publication_row_count')} WHERE PublicationId = @PublicationId;
    SELECT @mismatches = COUNT(*)
    FROM (
        {count_union}
    ) AS a
    JOIN {_lake('publication_row_count')} AS e
      ON e.TableName = a.TableName AND e.PublicationId = @PublicationId
    WHERE e.ExpectedRows <> a.ActualRows;
    IF @expectedTables <> {len(tables)} OR @mismatches <> 0
        THROW 50011, 'Lakehouse serve tables are not yet visible with the expected row counts (SQL analytics endpoint sync). Retry later.', 1;

    BEGIN TRANSACTION;
    BEGIN TRY
{stage_copy}

        DELETE FROM ops.publication WHERE PublicationId = @PublicationId;
        INSERT INTO ops.publication (PublicationId, BatchId, ParentBatchId, DatasetVersion, AuthorityPolicyVersion,
            MappingVersion, KpiContractVersion, UomFactorVersion, PeriodStart, PeriodEnd, ControlTotalsJson,
            BlockerCount, WarningCount, InfoCount, Status, StagedAtUtc, RunId)
        SELECT PublicationId, BatchId, ParentBatchId, DatasetVersion, AuthorityPolicyVersion, MappingVersion,
               KpiContractVersion, UomFactorVersion, PeriodStart, PeriodEnd, ControlTotalsJson,
               BlockerCount, WarningCount, InfoCount, 'APPROVAL_PENDING', @now, COALESCE(@RunId, RunId)
        FROM {_lake('publication_candidate')}
        WHERE PublicationId = @PublicationId;

        INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
        SELECT PublicationId, 'SUPERSEDED_BEFORE_APPROVAL', 'system', CONCAT('Superseded by ', @PublicationId), @now
        FROM ops.publication
        WHERE Status = 'APPROVAL_PENDING' AND PublicationId <> @PublicationId;
        UPDATE ops.publication SET Status = 'SUPERSEDED', SupersededBy = @PublicationId
        WHERE Status = 'APPROVAL_PENDING' AND PublicationId <> @PublicationId;

        INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
        VALUES (@PublicationId, 'STAGED', 'pipeline', CONCAT('Run ', COALESCE(@RunId, 'manual')), @now);
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT PublicationId, Status, BlockerCount, WarningCount, InfoCount, ControlTotalsJson
    FROM ops.publication WHERE PublicationId = @PublicationId;
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_approve_publication
    @PublicationId varchar(30),
    @Decision varchar(10) = 'APPROVE',
    @Comment varchar(1000) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @actor varchar(256) = CAST(SUSER_SNAME() AS varchar(256));
    DECLARE @now datetime2(6) = SYSUTCDATETIME();

    IF @Decision NOT IN ('APPROVE', 'REJECT')
        THROW 50020, 'Decision must be APPROVE or REJECT.', 1;
    IF NOT EXISTS (SELECT 1 FROM ops.authorized_approver
                   WHERE LOWER(ApproverUpn) = LOWER(@actor) AND IsActive = 1 AND DataDomain = 'PRODUCTION')
        THROW 50021, 'The current user is not an active authorized approver for PRODUCTION publications.', 1;
    IF NOT EXISTS (SELECT 1 FROM ops.publication WHERE PublicationId = @PublicationId AND Status = 'APPROVAL_PENDING')
        THROW 50022, 'Publication is not waiting for approval (check ops.vw_publication_history).', 1;

    BEGIN TRANSACTION;
    BEGIN TRY
        UPDATE ops.publication
        SET Status = CASE WHEN @Decision = 'APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,
            DecidedBy = @actor, DecidedAtUtc = @now, DecisionComment = @Comment
        WHERE PublicationId = @PublicationId;
        INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
        VALUES (@PublicationId, CASE WHEN @Decision = 'APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END, @actor,
                @Comment, @now);
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT PublicationId, Status, DecidedBy, DecidedAtUtc FROM ops.publication WHERE PublicationId = @PublicationId;
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_publish_publication
    @PublicationId varchar(30),
    @RunId varchar(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(6) = SYSUTCDATETIME();

    IF EXISTS (SELECT 1 FROM ops.publication WHERE PublicationId = @PublicationId AND Status = 'PUBLISHED')
    BEGIN
        SELECT PublicationId, Status, PublishedAtUtc FROM ops.publication WHERE PublicationId = @PublicationId;
        RETURN;
    END;
    IF NOT EXISTS (SELECT 1 FROM ops.publication WHERE PublicationId = @PublicationId AND Status = 'APPROVED')
        THROW 50030, 'Publication is not APPROVED. Run ops.usp_approve_publication as an authorized approver first.', 1;

    BEGIN TRANSACTION;
    BEGIN TRY
{publish_copy}

        -- Kontrol total: Gold harus sama persis dengan total yang dihitung nb_05
        DECLARE @expectedGross decimal(19,6), @actualGross decimal(19,6);
        SELECT @expectedGross = CAST(JSON_VALUE(ControlTotalsJson, '$.GrossBoe') AS decimal(19,6))
        FROM ops.publication WHERE PublicationId = @PublicationId;
        SELECT @actualGross = COALESCE(SUM(GrossBoe), 0) FROM gold.fact_production_daily;
        IF @expectedGross IS NULL OR @expectedGross <> @actualGross
            THROW 50031, 'Gold control total GrossBoe does not match the candidate manifest. Publication rolled back.', 1;

        INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
        SELECT PublicationId, 'SUPERSEDED', 'system', CONCAT('Superseded by ', @PublicationId), @now
        FROM ops.publication WHERE Status = 'PUBLISHED';
        UPDATE ops.publication SET Status = 'SUPERSEDED', SupersededBy = @PublicationId WHERE Status = 'PUBLISHED';
        UPDATE ops.publication SET Status = 'PUBLISHED', PublishedAtUtc = @now
        WHERE PublicationId = @PublicationId;
        INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
        VALUES (@PublicationId, 'PUBLISHED', 'pipeline', CONCAT('Run ', COALESCE(@RunId, 'manual')), @now);
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT PublicationId, Status, PublishedAtUtc FROM ops.publication WHERE PublicationId = @PublicationId;
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_sync_quality_evidence
    @BatchId varchar(10),
    @RunId varchar(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(6) = SYSUTCDATETIME();
    DECLARE @publicationId varchar(30) = CONCAT('PUB-', @BatchId);

    BEGIN TRANSACTION;
    BEGIN TRY
        DELETE FROM ops.quality_evidence WHERE BatchId = @BatchId;
        INSERT INTO ops.quality_evidence (BatchId, Stage, Status, PublicationId, BlockerCount, WarningCount,
            InfoCount, Message, RunId, UpdatedAtUtc, SyncedAtUtc)
        SELECT BatchId, Stage, Status, PublicationId, BlockerCount, WarningCount, InfoCount,
               LEFT(Message, 4000), RunId, UpdatedAtUtc, @now
        FROM {LAKEHOUSE}.ops.batch_status WHERE BatchId = @BatchId;

        DELETE FROM ops.dq_issue_summary WHERE BatchId = @BatchId;
        INSERT INTO ops.dq_issue_summary (BatchId, Stage, RuleId, Severity, IssueCount, SyncedAtUtc)
        SELECT BatchId, Stage, RuleId, Severity, COUNT(*), @now
        FROM {LAKEHOUSE}.ops.dq_issue WHERE BatchId = @BatchId
        GROUP BY BatchId, Stage, RuleId, Severity;

        IF EXISTS (SELECT 1 FROM ops.quality_evidence WHERE BatchId = @BatchId AND Status = 'QUALITY_FAILED')
           AND NOT EXISTS (SELECT 1 FROM ops.publication WHERE PublicationId = @publicationId)
        BEGIN
            INSERT INTO ops.publication (PublicationId, BatchId, BlockerCount, WarningCount, InfoCount, Status, RunId)
            SELECT @publicationId, @BatchId, BlockerCount, WarningCount, InfoCount, 'QUALITY_FAILED', @RunId
            FROM ops.quality_evidence WHERE BatchId = @BatchId AND Status = 'QUALITY_FAILED';
            INSERT INTO ops.publication_event (PublicationId, EventType, Actor, Detail, EventAtUtc)
            VALUES (@publicationId, 'QUALITY_FAILED', 'pipeline', 'Gold keeps the previous published publication', @now);
        END;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT Stage, Status, BlockerCount, WarningCount, InfoCount FROM ops.quality_evidence
    WHERE BatchId = @BatchId ORDER BY UpdatedAtUtc;
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_record_consumer_status
    @PublicationId varchar(30),
    @Consumer varchar(60),
    @Status varchar(30),
    @Detail varchar(1000) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DELETE FROM ops.consumer_status WHERE PublicationId = @PublicationId AND Consumer = @Consumer;
    INSERT INTO ops.consumer_status (PublicationId, Consumer, Status, Detail, UpdatedAtUtc)
    VALUES (@PublicationId, @Consumer, @Status, @Detail, SYSUTCDATETIME());
END;
GO
"""


def _q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_seed() -> str:
    rows = ",\n    ".join(
        f"({_q(k)}, {_q(n)}, {_q(d)}, {_q(u)}, {_q(g)}, {_q(o)}, {_q(c)}, {_q(KPI_CONTRACT_VERSION)})"
        for k, n, d, u, g, o, c in KPI_CONTRACT)
    return f"""-- Generated by `python -m workshop render-warehouse`. Seed kontrak KPI dan approver.
-- Ganti <APPROVER_UPN> dengan UPN Microsoft Entra pemilik data produksi (business owner) sebelum menjalankan.
-- Versi kebijakan: authority {AUTHORITY_POLICY_VERSION}, mapping {MAPPING_VERSION}, KPI {KPI_CONTRACT_VERSION}.

DELETE FROM ops.kpi_contract WHERE ContractVersion = {_q(KPI_CONTRACT_VERSION)};
INSERT INTO ops.kpi_contract (KpiId, KpiName, Definition, Unit, Grain, DataOwner, SourceColumn, ContractVersion)
VALUES
    {rows};
GO

DELETE FROM ops.authorized_approver WHERE ApproverUpn = '<APPROVER_UPN>';
INSERT INTO ops.authorized_approver (ApproverUpn, ApproverRole, DataDomain, IsActive)
VALUES ('<APPROVER_UPN>', 'Production data owner (workshop)', 'PRODUCTION', 1);
GO

-- Cek: hasilnya harus sama dengan UPN Anda agar usp_approve_publication mengizinkan approval
SELECT SUSER_SNAME() AS CurrentUser, ApproverUpn, IsActive FROM ops.authorized_approver;
GO
"""
