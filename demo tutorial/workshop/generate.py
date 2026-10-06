"""Deterministic synthetic source generator for the PIEP SSOT workshop.

All values are synthetic. Each pack contains a full snapshot of reference
registries and only the event rows introduced by that pack.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

from .contracts import (
    AUTHORITY_POLICY_VERSION, DATASET_VERSION, INCIDENT_ID, OPEN_END, PACK_DESCRIPTIONS,
    PACKS, PROFILES, S_DATE, SEED, TABLE_BY_NAME, TABLES, UOM_FACTOR_VERSION,
)

D = Decimal
Q6 = D("0.000001")
COUNTRIES = (("DZ", "Algeria"), ("MY", "Malaysia"), ("IQ", "Iraq"))
SOURCE_BY_COUNTRY = {"DZ": "SRC_DZ_PROD", "MY": "SRC_MY_PROD", "IQ": "SRC_IQ_PROD"}
TABLE_BY_SOURCE = {
    "SRC_DZ_PROD": "src_dz.production_report",
    "SRC_MY_PROD": "src_my.production_report",
    "SRC_MY_OPS": "src_my.production_provisional",
    "SRC_IQ_PROD": "src_iq.daily_volumes",
}
WI_SHARE = {"DZ": D("0.500000"), "MY": D("0.400000"), "IQ": D("0.300000")}
EQUIPMENT_TYPES = ("Production manifold", "Separator", "Gas compressor",
                   "Export pump", "Water injection pump", "Gas lift unit")
M3_TO_BBL = D("6.289810770")  # 1 m3 = 6.28981077 bbl; must fit ref.uom_conversion decimal(18,9)
SCF_TO_MSCF = D("0.001")
COMMODITIES = ("Oil", "Gas", "Water")
IQ_PRODUCT = {"Oil": "OIL", "Gas": "GAS", "Water": "WTR"}


def q6(value: Decimal) -> Decimal:
    return value.quantize(Q6, rounding=ROUND_HALF_UP)


def days(start: date, end: date):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def h(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def unit_for(country: str, commodity: str) -> tuple[str, Decimal]:
    if country == "DZ" and commodity in ("Oil", "Water"):
        return "m3", M3_TO_BBL
    if country == "IQ" and commodity == "Gas":
        return "scf", SCF_TO_MSCF
    return ("Mscf" if commodity == "Gas" else "bbl"), D(1)


def is_fixture(well_id: str, day: date) -> bool:
    return (well_id.startswith("MY_A_W") and int(well_id[-3:]) <= 10
            and date(2025, 9, 15) <= day <= date(2025, 9, 18))


@lru_cache(maxsize=None)
def potential(seed: int, well_id: str, day: date) -> dict[str, Decimal]:
    """Normal (unconstrained) daily potential in standard units."""
    base = D(80 + h(seed, well_id, "base") % 420)
    age = D((day - date(2025, 1, 1)).days)
    noise = D(h(seed, well_id, day) % 401 - 200) / D(10000)
    oil = q6(base * (D(1) - age * D("0.0003")) * (D(1) + noise))
    gor = D(3 + h(seed, well_id, "gor") % 7) + D(h(seed, well_id, "gor2") % 10) / D(10)
    water_cut = D(20 + h(seed, well_id, "water") % 130) / D(100)
    return {"Oil": oil, "Gas": q6(oil * gor), "Water": q6(oil * water_cut)}


def actual(seed: int, well_id: str, day: date) -> dict[str, Decimal]:
    if is_fixture(well_id, day):
        return {"Oil": D("50.000000"), "Gas": D("300.000000"), "Water": D("20.000000")}
    return potential(seed, well_id, day)


class Builder:
    def __init__(self, profile: str, seed: int):
        if profile not in PROFILES:
            raise ValueError(f"profile must be one of {sorted(PROFILES)}")
        self.profile, self.seed = profile, seed
        settings = PROFILES[profile]
        self.wells_per_field = settings["wells_per_field"]
        self.start, self.end = settings["start"], settings["end"]
        self.sequence = 0
        self.snapshot = self._registry()
        self.wells = self.snapshot["ref.well"]

    # ---------------------------------------------------------------- masters
    def _registry(self) -> dict[str, list[dict]]:
        out = {table.full_name: [] for table in TABLES if table.kind == "SNAPSHOT"}
        index = 0
        for country, country_name in COUNTRIES:
            out["ref.country"].append({"country_id": country, "country_name": country_name})
            out["ref.business_associate"].append({
                "ba_id": f"OP_{country}", "ba_name": f"DEMO Operator {country}", "ba_role": "OPERATOR"})
            for suffix in "AB":
                field_id, facility_id = f"{country}_{suffix}", f"FAC_{country}_{suffix}"
                out["ref.field"].append({"field_id": field_id, "country_id": country,
                                         "field_name": f"{country}_DEMO_FIELD_{suffix}"})
                out["ref.facility"].append({"facility_id": facility_id, "field_id": field_id,
                                            "facility_name": f"DEMO Facility {field_id}"})
                for number in range(1, 7):
                    out["ref.equipment"].append({
                        "equipment_id": f"EQ_{field_id}_{number:02}", "facility_id": facility_id,
                        "equipment_name": f"DEMO {EQUIPMENT_TYPES[number - 1]} {field_id}-{number:02}",
                        "equipment_type": EQUIPMENT_TYPES[number - 1]})
                out["ref.working_interest"].append({
                    "field_id": field_id, "valid_from": date(2025, 1, 1), "valid_to": OPEN_END,
                    "operator_ba_id": f"OP_{country}", "wi_share": WI_SHARE[country],
                    "agreement_ref": f"JOA-{field_id}-2025"})
                for local in range(1, self.wells_per_field + 1):
                    well_id, stream_id = f"{field_id}_W{local:03}", f"RS_{field_id}_W{local:03}"
                    out["ref.well"].append({"well_id": well_id, "field_id": field_id,
                                            "well_name": f"DEMO {well_id}", "well_status": "PRODUCING"})
                    out["ref.reporting_stream"].append({"stream_id": stream_id, "well_id": well_id,
                                                        "stream_name": f"DEMO stream {well_id}"})
                    out["ref.well_alias"].append({"source_system": SOURCE_BY_COUNTRY[country],
                                                  "source_well_id": self.local_ref(well_id),
                                                  "well_id": well_id})
                    if country == "MY":
                        out["ref.well_alias"].append({"source_system": "SRC_MY_OPS",
                                                      "source_well_id": f"MY{suffix}{local:03}",
                                                      "well_id": well_id})
                    bores = 2 if index % 4 == 0 else 1
                    for bore in range(1, bores + 1):
                        wellbore_id = f"{well_id}_B{bore}"
                        out["ref.wellbore"].append({"wellbore_id": wellbore_id, "well_id": well_id,
                                                    "wellbore_name": f"DEMO {wellbore_id}"})
                        for completion in range(1, (2 if index % 4 == 1 else 1) + 1):
                            completion_id = f"{wellbore_id}_C{completion}"
                            out["ref.well_completion"].append({
                                "completion_id": completion_id, "wellbore_id": wellbore_id,
                                "stream_id": stream_id, "completion_name": f"DEMO {completion_id}"})
                    index += 1
        for commodity, uom, standard, factor, divisor in (
                ("Oil", "bbl", "bbl", D(1), D(1)), ("Oil", "m3", "bbl", M3_TO_BBL, D(1)),
                ("Gas", "Mscf", "Mscf", D(1), D(6)), ("Gas", "scf", "Mscf", SCF_TO_MSCF, D(6)),
                ("Water", "bbl", "bbl", D(1), None), ("Water", "m3", "bbl", M3_TO_BBL, None)):
            out["ref.uom_conversion"].append({
                "commodity": commodity, "uom": uom, "standard_uom": standard,
                "to_standard_factor": factor, "boe_divisor": divisor,
                "factor_version": UOM_FACTOR_VERSION})
        self._targets(out)
        self._finance(out)
        out["ref.source_authority"] = self._authority()
        return out

    def local_ref(self, well_id: str) -> str:
        if well_id.startswith("IQ_"):
            return f"IQ-{well_id[3]}-{well_id[-3:]}"
        return well_id

    def _targets(self, out: dict[str, list[dict]]) -> None:
        for field in out["ref.field"]:
            wells = [w["well_id"] for w in out["ref.well"] if w["field_id"] == field["field_id"]]
            for commodity in ("Oil", "Gas"):
                months = {f"m{m:02}": D(0) for m in range(1, 13)}
                for day in days(date(2025, 1, 1), date(2025, 12, 31)):
                    months[f"m{day.month:02}"] += sum(
                        potential(self.seed, well, day)[commodity] for well in wells)
                out["ref.target_monthly"].append({
                    "field_id": field["field_id"], "commodity": commodity, "scenario_id": "RKAP_V1",
                    "target_year": 2025, **{k: q6(v * D("1.03")) for k, v in months.items()},
                    "target_uom": "Mscf" if commodity == "Gas" else "bbl"})

    def _finance(self, out: dict[str, list[dict]]) -> None:
        currency = {"DZ": ("DZD", 137), "MY": ("MYR", 4), "IQ": ("USD", 1)}
        categories = (("People", 4), ("Maintenance", 3), ("Energy", 2), ("Other", 1))
        for field_index, field in enumerate(out["ref.field"]):
            code, multiplier = currency[field["country_id"]]
            for month in range(1, 13):
                for category, weight in categories:
                    usd = (25000 * weight) + month * 500 + field_index * 1000
                    out["ref.operating_cost"].append({
                        "cost_id": f"OPEX-{field['field_id']}-2025{month:02}-{category.upper()}",
                        "field_id": field["field_id"], "month_start": date(2025, month, 1),
                        "cost_category": category, "currency_code": code,
                        "amount_local": D(usd * multiplier).quantize(D("0.0001")),
                        "closing_status": "CLOSED"})
        for day in days(date(2025, 1, 1), date(2025, 12, 31)):
            for code, rate in (("USD", D("1.0000")), ("MYR", D("0.2100") + D(day.month) / D(1000)),
                               ("DZD", D("0.0073"))):
                out["ref.fx_rate"].append({"valid_on": day, "currency_code": code, "usd_per_unit": rate})
            out["ref.price"].append({"business_date": day, "commodity": "Oil", "price_usd": D("70"),
                                     "price_unit": "USD/bbl", "energy_factor": D("1")})
            out["ref.price"].append({"business_date": day, "commodity": "Gas", "price_usd": D("3"),
                                     "price_unit": "USD/MMBtu", "energy_factor": D("1.03")})

    def _authority(self) -> list[dict]:
        rows = []
        for domain, source, scope, priority, status, owner in (
                ("PRODUCTION", "SRC_DZ_PROD", "DZ", 1, "FINAL", "Production reporting owner"),
                ("PRODUCTION", "SRC_MY_PROD", "MY", 1, "FINAL", "Production reporting owner"),
                ("PRODUCTION", "SRC_IQ_PROD", "IQ", 1, "FINAL", "Production reporting owner"),
                ("PRODUCTION", "SRC_MY_OPS", "MY", 99, "NONE", "Production reporting owner"),
                ("MASTER", "SRC_REGISTRY", "ALL", 1, "APPROVED", "Asset data owner"),
                ("TARGET", "SRC_PLANNING_RKAP", "ALL", 1, "APPROVED", "Planning owner"),
                ("COST", "SRC_FINANCE_CLOSE", "ALL", 1, "CLOSED", "Finance owner"),
                ("WORKING_INTEREST", "SRC_JV_REGISTER", "ALL", 1, "APPROVED", "Portfolio/JV owner"),
                ("LOSS_ALLOCATION", "SRC_MY_PROD", "MY", 1, "APPROVED", "Production reporting owner"),
                ("UOM", "SRC_REFERENCE", "ALL", 1, "APPROVED", "Reference data steward")):
            rows.append({"policy_version": AUTHORITY_POLICY_VERSION, "domain": domain,
                         "source_system": source, "scope": scope, "priority": priority,
                         "eligible_status": status, "valid_from": date(2025, 1, 1),
                         "valid_to": OPEN_END, "owner_role": owner})
        return rows

    # ----------------------------------------------------------------- events
    def next_seq(self, pack: str) -> int:
        self.sequence += 1
        return (PACKS.index(pack) + 1) * 10_000_000 + self.sequence

    def production(self, pack: str, source: str, well_ref: str, day: date, commodity: str,
                   quantity: Decimal | None, unit: str, revision: int, operation: str,
                   status: str, observation_id: str | None = None) -> dict:
        seq = self.next_seq(pack)
        default_id = hashlib.sha256(f"{source}|{well_ref}|{day}|{commodity}".encode()).hexdigest()[:24]
        return {"source": source, "change_id": f"{pack}-{source}-{seq}", "change_seq": seq,
                "observation_id": observation_id or default_id,
                "well_ref": well_ref, "report_date": day, "commodity": commodity, "quantity": quantity,
                "unit": unit, "revision": revision, "operation": operation, "report_status": status}

    def daily(self, pack: str, period: list[date]) -> list[dict]:
        rows = []
        for well in self.wells:
            country, well_id = well["field_id"][:2], well["well_id"]
            for day in period:
                values = actual(self.seed, well_id, day)
                for commodity in COMMODITIES:
                    unit, factor = unit_for(country, commodity)
                    rows.append(self.production(pack, SOURCE_BY_COUNTRY[country], self.local_ref(well_id),
                                                day, commodity, q6(values[commodity] / factor), unit,
                                                1, "I", "FINAL"))
        return rows

    def maintenance(self, pack: str) -> tuple[list[dict], list[dict]]:
        events, losses = [], []
        for day in days(date(2025, 9, 15), date(2025, 9, 18)):
            event_id = f"DT-MY-{day:%Y%m%d}"
            events.append({"event_id": event_id, "incident_id": INCIDENT_ID,
                           "equipment_id": "EQ_MY_A_01",
                           "start_utc": datetime.combine(day, datetime.min.time()),
                           "end_utc": datetime.combine(day, datetime.min.time()) + timedelta(hours=12),
                           "reason": "DEMO production manifold interruption",
                           "change_seq": self.next_seq(pack)})
            for number in range(1, 11):
                losses.append({"loss_id": f"LA-{day:%Y%m%d}-MY_A_W{number:03}", "event_id": event_id,
                               "well_ref": f"MY_A_W{number:03}", "business_date": day,
                               "lost_oil_bbl": D("50.000000"), "lost_gas_mscf": D("300.000000"),
                               "allocation_status": "APPROVED", "change_seq": self.next_seq(pack)})
        standby = [e["equipment_id"] for e in self.snapshot["ref.equipment"]
                   if e["equipment_id"].startswith("EQ_MY_") and e["equipment_id"] != "EQ_MY_A_01"]
        period_days = (self.end - self.start).days + 1
        step = max(1, period_days // 18)
        for number in range(196):
            day = self.start + timedelta(days=((number // len(standby)) * step) % period_days)
            start = datetime.combine(day, datetime.min.time()) + timedelta(hours=number % 12)
            events.append({"event_id": f"MNT-{number + 1:04}", "incident_id": f"CASE-{number + 1:04}",
                           "equipment_id": standby[number % len(standby)], "start_utc": start,
                           "end_utc": start + timedelta(hours=1 + number % 8),
                           "reason": "Standby equipment maintenance; no production loss allocated",
                           "change_seq": self.next_seq(pack)})
        return events, losses


def _period_slice(rows: list[dict], well_ref: str, first: int, count: int, start: date,
                  commodities=COMMODITIES) -> list[dict]:
    wanted = {start + timedelta(days=i) for i in range(first, first + count)}
    return [r for r in rows if r["well_ref"] == well_ref and r["report_date"] in wanted
            and r["commodity"] in commodities]


def build_packs(profile: str = "standard", seed: int = SEED) -> dict[str, dict]:
    """Return {pack: {"meta": {...}, "tables": {table: rows}}} for the linear sequence."""
    builder = Builder(profile, seed)
    period = list(days(builder.start, builder.end))
    base_events = builder.daily("B0", period)
    downtime, losses = builder.maintenance("B0")
    by_key = {(r["well_ref"], r["report_date"], r["commodity"]): r for r in base_events}
    snapshot = builder.snapshot
    packs: dict[str, dict] = {}
    period_end = builder.end
    for pack in PACKS:
        production: list[dict] = []
        downtime_rows: list[dict] = []
        loss_rows: list[dict] = []
        if pack == "B0":
            production, downtime_rows, loss_rows = base_events, downtime, losses
        elif pack == "B1":
            period_end = builder.end + timedelta(days=1)
            production = builder.daily(pack, [period_end])
        elif pack == "C1":
            for row in _period_slice(base_events, "DZ_B_W001", 0, 8, builder.start):
                production.append(builder.production(
                    pack, row["source"], row["well_ref"], row["report_date"], row["commodity"],
                    q6(row["quantity"] * D("1.01")), row["unit"], 2, "U", "FINAL", row["observation_id"]))
        elif pack == "D1":
            iq_a = [r for r in base_events if r["well_ref"].startswith("IQ-A-")][:100]
            for row in iq_a:
                production.append(builder.production(
                    pack, row["source"], row["well_ref"], row["report_date"], row["commodity"],
                    row["quantity"], row["unit"], row["revision"], row["operation"],
                    row["report_status"], row["observation_id"]))
        elif pack in ("Q1", "Q2"):
            rows = _period_slice(base_events, "IQ-B-001", 9, 12, builder.start)[:35]
            for index, row in enumerate(rows):
                quantity, unit, well_ref = row["quantity"], row["unit"], row["well_ref"]
                if pack == "Q1":
                    if index < 20:
                        unit = "UNKNOWN_UNIT"
                    elif index < 30:
                        well_ref = "IQ-X-999"
                    else:
                        quantity = None
                production.append(builder.production(
                    pack, row["source"], well_ref, row["report_date"], row["commodity"], quantity, unit,
                    2 if pack == "Q1" else 3, "U", "FINAL", row["observation_id"]))
        elif pack == "H1":
            snapshot = {name: [dict(r) for r in rows] for name, rows in snapshot.items()}
            snapshot["ref.business_associate"].append(
                {"ba_id": "OP_NEW", "ba_name": "DEMO New Operator", "ba_role": "OPERATOR"})
            for row in snapshot["ref.working_interest"]:
                if row["field_id"] == "DZ_A":
                    row["valid_to"] = date(2025, 7, 1)
            snapshot["ref.working_interest"].append({
                "field_id": "DZ_A", "valid_from": date(2025, 7, 1), "valid_to": OPEN_END,
                "operator_ba_id": "OP_NEW", "wi_share": D("0.350000"), "agreement_ref": "JOA-DZ_A-2025-A1"})
        elif pack == "X1":
            for row in _period_slice(base_events, "MY_B_W005", 0, 3, builder.start, ("Oil",)):
                production.append(builder.production(
                    pack, row["source"], row["well_ref"], row["report_date"], row["commodity"], None,
                    row["unit"], 2, "D", "FINAL", row["observation_id"]))
        elif pack in ("S1", "S2"):
            final = by_key[("MY_B_W001", S_DATE, "Oil")]
            if pack == "S1":
                production.append(builder.production(
                    pack, "SRC_MY_OPS", "MYB001", S_DATE, "Oil", final["quantity"] + D(10), "bbl",
                    1, "I", "PROVISIONAL"))
            else:
                production.append(builder.production(
                    pack, "SRC_MY_PROD", "MY_B_W001", S_DATE, "Oil", final["quantity"] + D(5), "bbl",
                    2, "U", "FINAL", final["observation_id"]))
        tables: dict[str, list[dict]] = {name: [dict(r) for r in rows] for name, rows in snapshot.items()}
        for source, table in TABLE_BY_SOURCE.items():
            tables[table] = [_render_production(table, r) for r in production if r["source"] == source]
        tables["src_my.downtime_event"] = downtime_rows
        tables["src_my.loss_allocation"] = loss_rows
        packs[pack] = {"meta": {"batch_id": pack, "parent_batch_id": PACKS[PACKS.index(pack) - 1] if pack != "B0" else None,
                                "description": PACK_DESCRIPTIONS[pack], "period_start": builder.start,
                                "period_end": period_end}, "tables": tables}
    return packs


def _render_production(table: str, row: dict) -> dict:
    if table == "src_iq.daily_volumes":
        return {"chg_id": row["change_id"], "seq_no": row["change_seq"], "obs_key": row["observation_id"],
                "well_code": row["well_ref"], "obs_date": row["report_date"],
                "product": IQ_PRODUCT[row["commodity"]], "qty": row["quantity"], "qty_unit": row["unit"],
                "rev_no": row["revision"], "op_code": row["operation"],
                "approval_flag": "Y" if row["report_status"] == "FINAL" else "N"}
    return {k: row[k] for k in ("change_id", "change_seq", "observation_id", "well_ref", "report_date",
                                "commodity", "quantity", "unit", "revision", "operation", "report_status")}


def text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def csv_bytes(table_name: str, rows: list[dict]) -> bytes:
    table = TABLE_BY_NAME[table_name]
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(table.column_names)
    for row in rows:
        writer.writerow([text(row.get(column)) for column in table.column_names])
    return buffer.getvalue().encode("utf-8")


def with_batch(pack: str, rows: list[dict]) -> list[dict]:
    return [{"batch_id": pack, **row} for row in rows]


def pack_files(pack: dict) -> dict[str, bytes]:
    """Render the pack, including control rows, as CSV bytes keyed by table name."""
    meta, batch = pack["meta"], pack["meta"]["batch_id"]
    files = {name: csv_bytes(name, with_batch(batch, rows)) for name, rows in pack["tables"].items()}
    entities = []
    for name in sorted(files):
        table = TABLE_BY_NAME[name]
        entities.append({"batch_id": batch, "entity_name": table.entity,
                         "row_count": len(pack["tables"][name]),
                         "content_sha256": hashlib.sha256(files[name]).hexdigest()})
    content = hashlib.sha256("".join(e["content_sha256"] for e in entities).encode()).hexdigest()
    data_entities = len(entities)
    # Control rows are counted too, so the landing check covers every copied entity.
    entities.append({"batch_id": batch, "entity_name": TABLE_BY_NAME["ctl.source_batch"].entity,
                     "row_count": 1, "content_sha256": "0" * 64})
    entities.append({"batch_id": batch, "entity_name": TABLE_BY_NAME["ctl.batch_entity"].entity,
                     "row_count": data_entities + 2, "content_sha256": "0" * 64})
    files["ctl.source_batch"] = csv_bytes("ctl.source_batch", [{
        "batch_id": batch, "parent_batch_id": meta["parent_batch_id"], "dataset_version": DATASET_VERSION,
        "description": meta["description"], "period_start": meta["period_start"],
        "period_end": meta["period_end"], "state": "SEALED", "content_sha256": content,
        "sealed_at_utc": None}])
    files["ctl.batch_entity"] = csv_bytes("ctl.batch_entity", entities)
    return files


def write_packs(output: Path, profile: str = "standard", seed: int = SEED) -> dict:
    """Write immutable pack folders. Re-running with the same inputs is safe."""
    packs = build_packs(profile, seed)
    index = {"dataset_version": DATASET_VERSION, "profile": profile, "seed": seed, "packs": []}
    for name, pack in packs.items():
        folder = output / name
        folder.mkdir(parents=True, exist_ok=True)
        files = pack_files(pack)
        for table_name, content in files.items():
            target = folder / f"{table_name}.csv"
            if target.exists() and target.read_bytes() != content:
                raise FileExistsError(f"{target} exists with different content. Use a new folder.")
            target.write_bytes(content)
        counts = {t: len(r) for t, r in pack["tables"].items()}
        index["packs"].append({"batch_id": name, "parent_batch_id": pack["meta"]["parent_batch_id"],
                               "description": pack["meta"]["description"], "row_counts": counts})
    (output / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def month_days(year: int, month: int) -> int:
    return monthrange(year, month)[1]
