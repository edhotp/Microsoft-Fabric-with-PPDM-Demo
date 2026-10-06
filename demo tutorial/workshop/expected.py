"""Independent pure-Python reference implementation of the SSOT publication rules.

This module intentionally does not use Spark. Tests compare notebook output with
these results, and participants compare Warehouse/Power BI/agent answers with the
generated expected-results JSON.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .contracts import (
    AUTHORITY_POLICY_VERSION, EXPECTED_FIXTURE, INCIDENT_ID, KPI_CONTRACT_VERSION, MAPPING_VERSION,
    PACKS, S_DATE, SOURCE_SYSTEMS,
)
from .generate import build_packs

D = Decimal
Q6, Q4, Q3 = D("0.000001"), D("0.0001"), D("0.001")
IQ_PRODUCT = {"OIL": "Oil", "GAS": "Gas", "WTR": "Water"}


def q(value: Decimal, quantum: Decimal = Q6) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def standardize(table: str, row: dict, batch: str) -> dict:
    if table == "src_iq.daily_volumes":
        row = {"change_id": row["chg_id"], "change_seq": row["seq_no"], "observation_id": row["obs_key"],
               "well_ref": row["well_code"], "report_date": row["obs_date"],
               "commodity": IQ_PRODUCT.get(row["product"], row["product"]), "quantity": row["qty"],
               "unit": row["qty_unit"], "revision": row["rev_no"], "operation": row["op_code"],
               "report_status": "FINAL" if row["approval_flag"] == "Y" else "PROVISIONAL"}
    return {**row, "source_system": SOURCE_SYSTEMS[table], "batch_id": batch}


def payload(row: dict) -> tuple:
    return tuple(row[k] for k in ("well_ref", "report_date", "commodity", "quantity", "unit",
                                  "operation", "report_status"))


def evaluate(events: list[dict], snapshot: dict[str, list[dict]], meta: dict) -> dict:
    """Apply the documented SSOT rules to cumulative events and one registry snapshot."""
    issues: dict[str, int] = defaultdict(int)
    alias = {(r["source_system"], r["source_well_id"]): r["well_id"] for r in snapshot["ref.well_alias"]}
    stream_by_well = {r["well_id"]: r["stream_id"] for r in snapshot["ref.reporting_stream"]}
    field_by_well = {r["well_id"]: r["field_id"] for r in snapshot["ref.well"]}
    country_by_field = {r["field_id"]: r["country_id"] for r in snapshot["ref.field"]}
    uom = {(r["commodity"], r["uom"]): r for r in snapshot["ref.uom_conversion"]}
    gas_divisor = next(r["boe_divisor"] for r in snapshot["ref.uom_conversion"] if r["commodity"] == "Gas")

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for event in events:
        groups[(event["source_system"], event["observation_id"], event["revision"])].append(event)
    revisions: dict[tuple, dict] = {}
    for key, rows in groups.items():
        payloads = {payload(r) for r in rows}
        if len(payloads) > 1:
            issues["R06"] += 1
            continue
        if len(rows) > 1:
            issues["R10"] += len(rows) - 1
        revisions[key] = min(rows, key=lambda r: r["change_seq"])
    latest: dict[tuple, dict] = {}
    for (source, observation, _), row in revisions.items():
        current = latest.get((source, observation))
        if current is None or (row["revision"], row["change_seq"]) > (current["revision"], current["change_seq"]):
            latest[(source, observation)] = row

    candidates: dict[tuple, list[dict]] = defaultdict(list)
    for row in latest.values():
        well = alias.get((row["source_system"], row["well_ref"]))
        failures = []
        if well is None:
            failures.append("R01")
        if row["commodity"] not in ("Oil", "Gas", "Water"):
            failures.append("R05")
        elif (row["commodity"], row["unit"]) not in uom:
            failures.append("R02")
        if row["quantity"] is None and row["operation"] != "D":
            failures.append("R03")
        if row["quantity"] is not None and row["quantity"] < 0:
            failures.append("R04")
        for rule in failures:
            issues[rule] += 1
        if failures:
            continue
        retracted = row["operation"] == "D"
        value = None if retracted else q(row["quantity"] * uom[(row["commodity"], row["unit"])]["to_standard_factor"])
        candidates[(stream_by_well[well], row["report_date"], row["commodity"])].append(
            {**row, "well_id": well, "country": country_by_field[field_by_well[well]],
             "status": "RETRACTED" if retracted else "CURRENT", "value": value})

    policy = [p for p in snapshot["ref.source_authority"] if p["domain"] == "PRODUCTION"]
    selected: dict[tuple, dict] = {}
    decisions: dict[str, int] = defaultdict(int)
    for key, items in candidates.items():
        for item in items:
            matches = [p for p in policy if p["source_system"] == item["source_system"]
                       and p["scope"] in (item["country"], "ALL")
                       and p["valid_from"] <= item["report_date"] < p["valid_to"]]
            rule = min(matches, key=lambda p: p["priority"]) if matches else None
            item["eligible"] = bool(rule) and rule["eligible_status"] == item["report_status"]
            item["priority"] = rule["priority"] if rule else None
        eligible = [i for i in items if i["eligible"]]
        status = "SELECTED"
        if not eligible:
            status = "NO_AUTHORITATIVE_SOURCE"
            issues["W01"] += 1
        else:
            best = min(i["priority"] for i in eligible)
            winners = [i for i in eligible if i["priority"] == best]
            if len({(w["status"], w["value"]) for w in winners}) > 1:
                status = "REVIEW_REQUIRED"
                issues["R07"] += 1
            else:
                selected[key] = min(winners, key=lambda w: (w["source_system"], w["observation_id"]))
        if len(items) > 1 or status != "SELECTED":
            decisions[status] += 1

    wi_rows = snapshot["ref.working_interest"]

    def wi(field: str, day: date) -> Decimal:
        return next(r["wi_share"] for r in wi_rows
                    if r["field_id"] == field and r["valid_from"] <= day < r["valid_to"])

    metrics = defaultdict(lambda: D(0))
    counts = defaultdict(int)
    by_country = defaultdict(lambda: {"gross_boe": D(0), "net_wi_boe": D(0)})
    period = [meta["period_start"] + timedelta(days=i)
              for i in range((meta["period_end"] - meta["period_start"]).days + 1)]
    s_value = None
    for stream in snapshot["ref.reporting_stream"]:
        well = stream["well_id"]
        field = field_by_well[well]
        for day in period:
            counts["fact_production_rows"] += 1
            values, available, retracted = {}, 0, 0
            for commodity in ("Oil", "Gas", "Water"):
                winner = selected.get((stream["stream_id"], day, commodity))
                if winner and winner["status"] == "CURRENT":
                    values[commodity] = winner["value"]
                    available += 1
                    metrics[f"{commodity.lower()}_total"] += winner["value"]
                elif winner:
                    retracted += 1
            counts["observation_count"] += available
            counts["retracted_count"] += retracted
            counts["complete_rows"] += int(available == 3)
            if well == "MY_B_W001" and day == S_DATE:
                s_value = values.get("Oil")
            if "Oil" in values or "Gas" in values:
                gross = values.get("Oil", D(0)) + q(values.get("Gas", D(0)) / gas_divisor)
                net = q(gross * wi(field, day))
                metrics["gross_boe_total"] += gross
                metrics["net_wi_boe_total"] += net
                country = country_by_field[field]
                by_country[country]["gross_boe"] += gross
                by_country[country]["net_wi_boe"] += net

    target_boe = D(0)
    for row in snapshot["ref.target_monthly"]:
        for month in range(1, 13):
            first = date(row["target_year"], month, 1)
            days_in_month = ((first.replace(day=28) + timedelta(days=4)).replace(day=1) - first).days
            monthly = row[f"m{month:02}"]
            base = q(monthly / days_in_month)
            daily = [base] * (days_in_month - 1) + [monthly - base * (days_in_month - 1)]
            if row["commodity"] == "Oil":
                target_boe += sum(daily)
            else:
                target_boe += sum(q(v / gas_divisor) for v in daily)
    fx = {(r["valid_on"], r["currency_code"]): r["usd_per_unit"] for r in snapshot["ref.fx_rate"]}
    opex = sum(q(r["amount_local"] * fx[(r["month_start"], r["currency_code"])], Q4)
               for r in snapshot["ref.operating_cost"])

    blocker_rules = ("R01", "R02", "R03", "R04", "R05", "R06", "R07")
    blockers = {rule: issues[rule] for rule in blocker_rules if issues[rule]}
    return {
        "status": "QUALITY_FAILED" if blockers else "APPROVAL_PENDING",
        "blockers": blockers,
        "info_and_warnings": {k: v for k, v in issues.items() if k not in blocker_rules and v},
        "decisions": dict(sorted(decisions.items())),
        "counts": dict(counts),
        "totals": {k: str(q(v)) for k, v in sorted(metrics.items())},
        "by_country": {k: {m: str(q(v)) for m, v in sorted(by_country[k].items())} for k in sorted(by_country)},
        "s_check_oil_bbl": None if s_value is None else str(s_value),
        "target_boe_total": str(q(target_boe)),
        "opex_usd_total": str(q(opex, Q4)),
    }


def loss_metrics(packs: dict) -> dict:
    snapshot = packs["B0"]["tables"]
    events = {e["event_id"]: e for e in snapshot["src_my.downtime_event"]}
    wi = {r["field_id"]: r["wi_share"] for r in snapshot["ref.working_interest"]}
    result = defaultdict(lambda: D(0))
    for row in snapshot["src_my.loss_allocation"]:
        gross = row["lost_oil_bbl"] + q(row["lost_gas_mscf"] / D(6))
        value = q(row["lost_oil_bbl"] * D(70) + row["lost_gas_mscf"] * D("1.03") * D(3), Q4)
        result["lost_oil_bbl"] += row["lost_oil_bbl"]
        result["lost_gas_mscf"] += row["lost_gas_mscf"]
        result["lost_boe_gross"] += gross
        result["lost_boe_net_wi"] += q(gross * wi["MY_A"])
        result["value_usd_gross"] += value
        result["value_usd_net_wi"] += q(value * wi["MY_A"], Q4)
    fixture_hours = sum(D((e["end_utc"] - e["start_utc"]).total_seconds()) / D(3600)
                        for e in events.values() if e["incident_id"] == INCIDENT_ID)
    all_hours = sum(D((e["end_utc"] - e["start_utc"]).total_seconds()) / D(3600) for e in events.values())
    wells = {r["well_ref"] for r in snapshot["src_my.loss_allocation"]}
    return {
        "incident_id": INCIDENT_ID,
        "affected_wells": len(wells),
        "allocation_rows": len(snapshot["src_my.loss_allocation"]),
        "lost_oil_bbl": str(q(result["lost_oil_bbl"])),
        "lost_gas_mscf": str(q(result["lost_gas_mscf"])),
        "lost_boe_gross": str(q(result["lost_boe_gross"])),
        "lost_boe_net_wi": str(q(result["lost_boe_net_wi"])),
        "value_usd_gross": str(q(result["value_usd_gross"], Q4)),
        "value_usd_net_wi": str(q(result["value_usd_net_wi"], Q4)),
        "equipment_downtime_hours": str(q(fixture_hours, Q3)),
        "affected_well_hours": str(q(D(len(wells)) * fixture_hours, Q3)),
        "all_downtime_events": len(events),
        "all_downtime_hours": str(q(all_hours, Q3)),
    }


def expected_results(profile: str = "standard", packs: dict | None = None) -> dict:
    packs = packs or build_packs(profile)
    events: list[dict] = []
    published = None
    result = {"profile": profile, "authority_policy_version": AUTHORITY_POLICY_VERSION,
              "mapping_version": MAPPING_VERSION, "kpi_contract_version": KPI_CONTRACT_VERSION,
              "fixture": loss_metrics(packs), "publications": {}}
    for pack_name in PACKS:
        pack = packs[pack_name]
        for table in SOURCE_SYSTEMS:
            events.extend(standardize(table, row, pack_name) for row in pack["tables"][table])
        tables = pack["tables"]
        master = {"wells": len(tables["ref.well"]), "wellbores": len(tables["ref.wellbore"]),
                  "completions": len(tables["ref.well_completion"]),
                  "reporting_streams": len(tables["ref.reporting_stream"]),
                  "aliases": len(tables["ref.well_alias"])}
        outcome = evaluate(events, tables, pack["meta"])
        outcome.update({"publication_id": f"PUB-{pack_name}", "batch_id": pack_name,
                        "parent_batch_id": pack["meta"]["parent_batch_id"],
                        "period_end": pack["meta"]["period_end"].isoformat(), "master": master,
                        "gold_after_approval": f"PUB-{pack_name}" if outcome["status"] != "QUALITY_FAILED"
                        else published})
        if outcome["status"] != "QUALITY_FAILED":
            published = f"PUB-{pack_name}"
        result["publications"][f"PUB-{pack_name}"] = outcome
    s1 = D(result["publications"]["PUB-S1"]["s_check_oil_bbl"])
    s2 = D(result["publications"]["PUB-S2"]["s_check_oil_bbl"])
    result["ssot_checks"] = {
        "s1_selected_oil_bbl": str(s1),
        "s1_provisional_oil_bbl": str(s1 + 10),
        "s2_selected_oil_bbl": str(s2),
        "s2_gross_boe_delta": str(s2 - s1),
        "s2_net_wi_boe_delta": str(q((s2 - s1) * D("0.400000"))),
        "s2_gross_total_delta": str(D(result["publications"]["PUB-S2"]["totals"]["gross_boe_total"])
                                    - D(result["publications"]["PUB-S1"]["totals"]["gross_boe_total"])),
    }
    if profile == "standard":
        assert result["fixture"]["lost_boe_gross"] == EXPECTED_FIXTURE["lost_boe_gross"]
    return result
