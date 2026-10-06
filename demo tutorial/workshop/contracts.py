"""Single source of truth for the workshop source contract.

The same definitions drive the synthetic generator, Azure SQL DDL, the loader,
landing-file schemas used in local tests, and the Copy entity configuration.
Names are PPDM-aligned workshop names, not official PPDM table names.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DATASET_VERSION = "piep-ssot-1.0"
SEED = 20261005
AUTHORITY_POLICY_VERSION = "SA-2025.1"
MAPPING_VERSION = "PPDM-ALIGN-1.0"
KPI_CONTRACT_VERSION = "KPI-1.0"
UOM_FACTOR_VERSION = "UOM-2025.1"
INCIDENT_ID = "INC-MY-001"
S_DATE = date(2025, 9, 20)
OPEN_END = date(9999, 12, 31)

# Linear workshop sequence. Each pack is applied on top of its parent.
# H1 and X1 come before the Q1/Q2 drill so they can run as background "express" batches during Lab 10.
PACKS = ["B0", "B1", "C1", "D1", "H1", "X1", "Q1", "Q2", "S1", "S2"]
PACK_DESCRIPTIONS = {
    "B0": "Clean baseline, including the INC-MY-001 operational incident",
    "B1": "One additional production day",
    "C1": "24 authoritative revisions from the Algeria source",
    "D1": "100 duplicate deliveries with identical business payload",
    "Q1": "35 invalid revisions; publication must be blocked",
    "Q2": "Approved corrections for the 35 Q1 records",
    "H1": "Working-interest and operator change for DZ_A from 2025-07-01",
    "X1": "Three oil observations retracted by the source",
    "S1": "Provisional operations report that conflicts with the final value",
    "S2": "Authoritative correction that requires business approval",
}

PROFILES = {
    "standard": {"wells_per_field": 20, "start": date(2025, 1, 1), "end": date(2025, 12, 31)},
    "small": {"wells_per_field": 10, "start": date(2025, 9, 1), "end": date(2025, 9, 30)},
}


@dataclass(frozen=True)
class Column:
    name: str
    sql_type: str
    nullable: bool = False


@dataclass(frozen=True)
class SourceTable:
    schema: str
    name: str
    kind: str  # SNAPSHOT, EVENT, CONTROL
    columns: tuple[Column, ...]
    key: tuple[str, ...]
    description: str

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"

    @property
    def entity(self) -> str:
        return f"{self.schema}__{self.name}"

    @property
    def column_names(self) -> list[str]:
        return [column.name for column in self.columns]


def _columns(spec: str) -> tuple[Column, ...]:
    result = []
    for token in spec.split():
        name, sql_type = token.split(":", 1)
        nullable = sql_type.endswith("?")
        result.append(Column(name, sql_type.rstrip("?"), nullable))
    return tuple(result)


def _table(schema: str, name: str, kind: str, spec: str, key: str, description: str) -> SourceTable:
    columns = _columns(spec)
    if kind != "CONTROL":
        columns = (Column("batch_id", "varchar(10)"),) + columns
    return SourceTable(schema, name, kind, columns, tuple(key.split()), description)


_PRODUCTION = (
    "change_id:varchar(64) change_seq:bigint observation_id:varchar(32) well_ref:varchar(30) "
    "report_date:date commodity:varchar(10) quantity:decimal(19,6)? unit:varchar(20) "
    "revision:int operation:char(1) report_status:varchar(20)"
)
_MONTHS = " ".join(f"m{month:02}:decimal(19,6)" for month in range(1, 13))

TABLES: tuple[SourceTable, ...] = (
    _table("ref", "country", "SNAPSHOT", "country_id:varchar(2) country_name:varchar(100)",
           "batch_id country_id", "Country registry"),
    _table("ref", "business_associate", "SNAPSHOT",
           "ba_id:varchar(20) ba_name:varchar(100) ba_role:varchar(30)",
           "batch_id ba_id", "Operator and partner registry"),
    _table("ref", "field", "SNAPSHOT",
           "field_id:varchar(10) country_id:varchar(2) field_name:varchar(100)",
           "batch_id field_id", "Field (asset) registry"),
    _table("ref", "facility", "SNAPSHOT",
           "facility_id:varchar(20) field_id:varchar(10) facility_name:varchar(100)",
           "batch_id facility_id", "Facility registry"),
    _table("ref", "equipment", "SNAPSHOT",
           "equipment_id:varchar(20) facility_id:varchar(20) equipment_name:varchar(100) "
           "equipment_type:varchar(40)", "batch_id equipment_id", "Equipment registry"),
    _table("ref", "well", "SNAPSHOT",
           "well_id:varchar(20) field_id:varchar(10) well_name:varchar(100) well_status:varchar(20)",
           "batch_id well_id", "Golden well registry"),
    _table("ref", "wellbore", "SNAPSHOT",
           "wellbore_id:varchar(30) well_id:varchar(20) wellbore_name:varchar(100)",
           "batch_id wellbore_id", "Wellbore registry"),
    _table("ref", "well_completion", "SNAPSHOT",
           "completion_id:varchar(40) wellbore_id:varchar(30) stream_id:varchar(30) "
           "completion_name:varchar(100)", "batch_id completion_id", "Completion registry"),
    _table("ref", "reporting_stream", "SNAPSHOT",
           "stream_id:varchar(30) well_id:varchar(20) stream_name:varchar(100)",
           "batch_id stream_id", "Production reporting stream registry"),
    _table("ref", "well_alias", "SNAPSHOT",
           "source_system:varchar(30) source_well_id:varchar(30) well_id:varchar(20)",
           "batch_id source_system source_well_id", "Source identifier crosswalk"),
    _table("ref", "uom_conversion", "SNAPSHOT",
           "commodity:varchar(10) uom:varchar(20) standard_uom:varchar(10) "
           "to_standard_factor:decimal(18,9) boe_divisor:decimal(9,3)? factor_version:varchar(20)",
           "batch_id commodity uom", "Unit conversion and BOE factors"),
    _table("ref", "working_interest", "SNAPSHOT",
           "field_id:varchar(10) valid_from:date valid_to:date operator_ba_id:varchar(20) "
           "wi_share:decimal(9,6) agreement_ref:varchar(30)",
           "batch_id field_id valid_from", "Effective-dated working interest register"),
    _table("ref", "target_monthly", "SNAPSHOT",
           f"field_id:varchar(10) commodity:varchar(10) scenario_id:varchar(20) target_year:int "
           f"{_MONTHS} target_uom:varchar(10)",
           "batch_id field_id commodity scenario_id target_year", "Approved RKAP target snapshot"),
    _table("ref", "operating_cost", "SNAPSHOT",
           "cost_id:varchar(30) field_id:varchar(10) month_start:date cost_category:varchar(30) "
           "currency_code:varchar(3) amount_local:decimal(19,4) closing_status:varchar(20)",
           "batch_id cost_id", "Finance closing operating cost"),
    _table("ref", "fx_rate", "SNAPSHOT",
           "valid_on:date currency_code:varchar(3) usd_per_unit:decimal(18,9)",
           "batch_id valid_on currency_code", "Approved FX rates"),
    _table("ref", "price", "SNAPSHOT",
           "business_date:date commodity:varchar(10) price_usd:decimal(19,6) price_unit:varchar(20) "
           "energy_factor:decimal(9,6)", "batch_id business_date commodity", "Indicative price deck"),
    _table("ref", "source_authority", "SNAPSHOT",
           "policy_version:varchar(20) domain:varchar(30) source_system:varchar(30) scope:varchar(10) "
           "priority:int eligible_status:varchar(20) valid_from:date valid_to:date owner_role:varchar(60)",
           "batch_id policy_version domain source_system scope", "Source authority register"),
    _table("src_dz", "production_report", "EVENT", _PRODUCTION, "batch_id change_id",
           "Algeria operator final production reports"),
    _table("src_my", "production_report", "EVENT", _PRODUCTION, "batch_id change_id",
           "Malaysia operator final production reports"),
    _table("src_my", "production_provisional", "EVENT", _PRODUCTION, "batch_id change_id",
           "Malaysia daily operations provisional reports"),
    _table("src_iq", "daily_volumes", "EVENT",
           "chg_id:varchar(64) seq_no:bigint obs_key:varchar(32) well_code:varchar(30) obs_date:date "
           "product:varchar(5) qty:decimal(19,6)? qty_unit:varchar(20) rev_no:int op_code:char(1) "
           "approval_flag:char(1)", "batch_id chg_id", "Iraq daily volumes with local column names"),
    _table("src_my", "downtime_event", "EVENT",
           "event_id:varchar(30) incident_id:varchar(30) equipment_id:varchar(20) "
           "start_utc:datetime2(0) end_utc:datetime2(0) reason:varchar(120) change_seq:bigint",
           "batch_id event_id", "Maintenance downtime events"),
    _table("src_my", "loss_allocation", "EVENT",
           "loss_id:varchar(40) event_id:varchar(30) well_ref:varchar(30) business_date:date "
           "lost_oil_bbl:decimal(19,6) lost_gas_mscf:decimal(19,6) allocation_status:varchar(20) "
           "change_seq:bigint", "batch_id loss_id", "Approved production loss allocation"),
    _table("ctl", "source_batch", "CONTROL",
           "batch_id:varchar(10) parent_batch_id:varchar(10)? dataset_version:varchar(30) "
           "description:varchar(200) period_start:date period_end:date state:varchar(10) "
           "content_sha256:char(64) sealed_at_utc:datetime2(0)?",
           "batch_id", "Source batch manifest"),
    _table("ctl", "batch_entity", "CONTROL",
           "batch_id:varchar(10) entity_name:varchar(80) row_count:bigint content_sha256:char(64)",
           "batch_id entity_name", "Expected row counts per batch and entity"),
)

TABLE_BY_NAME = {table.full_name: table for table in TABLES}
DATA_TABLES = tuple(table for table in TABLES if table.kind != "CONTROL")
# Entities copied by the Fabric pipeline. entity_config is static and not copied.
COPY_ENTITIES = tuple(TABLES)

SOURCE_SYSTEMS = {
    "src_dz.production_report": "SRC_DZ_PROD",
    "src_my.production_report": "SRC_MY_PROD",
    "src_my.production_provisional": "SRC_MY_OPS",
    "src_iq.daily_volumes": "SRC_IQ_PROD",
}

EXPECTED_FIXTURE = {
    "incident_id": INCIDENT_ID,
    "affected_wells": 10,
    "allocation_rows": 40,
    "lost_oil_bbl": "2000.000000",
    "lost_gas_mscf": "12000.000000",
    "lost_boe_gross": "4000.000000",
    "lost_boe_net_wi": "1600.000000",
    "value_usd_gross": "177080.0000",
    "value_usd_net_wi": "70832.0000",
    "equipment_downtime_hours": "48.000",
    "affected_well_hours": "480.000",
}
