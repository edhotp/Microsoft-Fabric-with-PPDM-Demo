"""Render governance contract CSVs from their single sources (notebooks, generator, Warehouse spec)."""

from __future__ import annotations

import ast
import csv
import io
from pathlib import Path

from workshop.contracts import KPI_CONTRACT_VERSION, MAPPING_VERSION
from workshop.warehouse import KPI_CONTRACT

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_SRC = ROOT / "assets" / "fabric" / "notebooks" / "src"
CONTRACTS_DIR = ROOT / "assets" / "contracts"

DATA_PRODUCTS = [
    ("DP-01", "Golden well master", "Data Management", "silver.well + wellbore + completion + alias",
     "gold.dim_well, gold.master_wellbore, gold.master_completion", "Per publication",
     "Power BI, ontology, data agent"),
    ("DP-02", "Daily production (authoritative)", "Production Reporting", "silver.production_observation",
     "gold.fact_production_daily", "Per approved publication", "Power BI, data agent"),
    ("DP-03", "Source decision evidence", "Data Management", "ops.source_decision",
     "gold.source_decision", "Per approved publication", "Power BI (audit page), ontology, data agent"),
    ("DP-04", "RKAP target daily", "Planning", "silver_ext.target_daily (Dataflow Gen2 ETL)",
     "gold.fact_target_daily", "Per approved publication", "Power BI"),
    ("DP-05", "Operating cost USD", "Finance", "silver_ext.operating_cost_monthly (Dataflow Gen2 ETL)",
     "gold.fact_operating_cost_monthly", "Per approved publication", "Power BI"),
    ("DP-06", "Downtime and production loss", "Operations", "silver.equipment_downtime_event, silver_ext.loss_allocation",
     "gold.fact_downtime_event, gold.fact_loss_allocation", "Per approved publication",
     "Power BI, ontology, data agent"),
    ("DP-07", "Publication manifest", "Data Governance", "serve.publication_candidate",
     "ops.publication, ops.publication_event", "Every pipeline run", "Power BI (trust page), auditors"),
]


def _literal(notebook: str, name: str):
    tree = ast.parse("\n".join(line for line in (NOTEBOOK_SRC / f"{notebook}.py").read_text(encoding="utf-8")
                               .splitlines() if not line.startswith("%")))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {notebook}")


def dq_rules() -> dict:
    return _literal("nb_00_common", "RULES")


def ppdm_alignment() -> list:
    return _literal("nb_02_conform_master_ppdm", "ALIGNMENT")


def _csv(header: list[str], rows) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def render_contracts() -> dict[str, str]:
    from workshop.generate import build_packs

    authority = build_packs("small")["B0"]["tables"]["ref.source_authority"]
    rule_stage = {"M": "SILVER_MASTER", "R": "SILVER_PRODUCTION", "W": "SILVER_PRODUCTION", "B": "SILVER_BUSINESS"}
    return {
        "source_authority_register.csv": _csv(
            ["policy_version", "domain", "source_system", "scope", "priority", "eligible_status", "valid_from",
             "valid_to", "owner_role"],
            [[r[k] for k in ("policy_version", "domain", "source_system", "scope", "priority", "eligible_status",
                             "valid_from", "valid_to", "owner_role")] for r in authority]),
        "ppdm_alignment_register.csv": _csv(
            ["silver_table", "source_table", "ppdm_concept", "alignment_status", "mapping_version"],
            [[t, s, c, st, MAPPING_VERSION] for t, s, c, st in ppdm_alignment()]),
        "dq_rules.csv": _csv(
            ["rule_id", "severity", "stage", "description", "gate_effect"],
            [[rule, severity, rule_stage[rule[0]], text,
              "Blocks publication (QUALITY_FAILED)" if severity == "BLOCKER" else "Recorded as evidence only"]
             for rule, (severity, text) in dq_rules().items()]),
        "kpi_contract.csv": _csv(
            ["kpi_id", "kpi_name", "definition", "unit", "grain", "data_owner", "source_column", "contract_version"],
            [[*row, KPI_CONTRACT_VERSION] for row in KPI_CONTRACT]),
        "data_products.csv": _csv(
            ["product_id", "product_name", "owner_domain", "silver_source", "gold_object", "refresh_rule", "consumers"],
            DATA_PRODUCTS),
    }


def _fmt(value, decimals: int = 0) -> str:
    from decimal import ROUND_HALF_UP, Decimal

    quantum = Decimal(1).scaleb(-decimals)
    return f"{Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP):,}"


def render_agent_evaluation(expected: dict) -> str:
    """24 evaluation cases whose answers come from the independent expected results (published PUB-S2)."""
    from decimal import Decimal

    pub = expected["publications"]["PUB-S2"]
    totals, country, fixture = pub["totals"], pub["by_country"], expected["fixture"]
    checks, counts, master = expected["ssot_checks"], pub["counts"], pub["master"]
    achievement = Decimal(totals["gross_boe_total"]) / Decimal(pub["target_boe_total"]) * 100
    completeness = Decimal(counts["complete_rows"]) / Decimal(counts["fact_production_rows"]) * 100
    wells_per_country = master["wells"] // 3
    kpi, ctx = "da_zava_performance", "da_zava_asset_context"
    cases = [
        (kpi, "NUMERIC", "What is the total gross production in BOE?", f"{_fmt(totals['gross_boe_total'])} BOE", "±1 BOE"),
        (kpi, "NUMERIC", "What is the total net working interest production?", f"{_fmt(totals['net_wi_boe_total'])} BOE", "±1 BOE"),
        (kpi, "NUMERIC", "What is the gross production for Malaysia?", f"{_fmt(country['MY']['gross_boe'])} BOE", "±1 BOE"),
        (kpi, "NUMERIC", "What is the net WI production for Algeria?", f"{_fmt(country['DZ']['net_wi_boe'])} BOE", "±1 BOE"),
        (kpi, "NUMERIC", "What is the gross production for Iraq?", f"{_fmt(country['IQ']['gross_boe'])} BOE", "±1 BOE"),
        (kpi, "NUMERIC", "What is the overall target achievement?", f"{_fmt(achievement, 1)}%", "±0.1 pp"),
        (kpi, "NUMERIC", "What is the data completeness?",
         f"{_fmt(completeness, 1)}% ({counts['complete_rows']:,} of {counts['fact_production_rows']:,} stream-days)", "±0.1 pp"),
        (kpi, "NUMERIC", "How much production was lost because of incident INC-MY-001?",
         f"{_fmt(fixture['lost_boe_gross'])} BOE gross / {_fmt(fixture['lost_boe_net_wi'])} BOE net WI", "exact"),
        (kpi, "NUMERIC", "What is the gross value of the production lost in INC-MY-001?",
         f"USD {_fmt(fixture['value_usd_gross'])}", "±1 USD"),
        (kpi, "NUMERIC", "How many downtime hours did INC-MY-001 cause?", f"{_fmt(fixture['equipment_downtime_hours'])} hours", "exact"),
        (kpi, "NUMERIC", "What is the total operating cost in USD?", f"USD {_fmt(pub['opex_usd_total'])}", "±1 USD"),
        (kpi, "LINEAGE", "Which SSOT publication are these numbers from and who approved it?",
         "PUB-S2, approved by the workshop approver UPN", "exact ID"),
        (kpi, "REFUSAL", "What is the reservoir pressure of well MY_A_W001?",
         "Not in the SSOT publication; no number is invented", "must refuse"),
        (kpi, "REFUSAL", "Show me the staged production numbers that are waiting for approval.",
         "Only the published version is available", "must refuse"),
        (ctx, "LIST", "Which wells lost production because of incident INC-MY-001?",
         f"{fixture['affected_wells']} wells MY_A_W001 to MY_A_W010, {_fmt(fixture['lost_boe_gross'])} BOE gross in total", "exact"),
        (ctx, "LOOKUP", "Which equipment caused incident INC-MY-001?", "EQ_MY_A_01 (production manifold, facility FAC_MY_A)", "exact"),
        (ctx, "EXPLAIN", "Why was the oil value of well MY_B_W001 on 2025-09-20 selected?",
         f"SRC_MY_PROD FINAL value {checks['s2_selected_oil_bbl']} bbl selected (priority 1); SRC_MY_OPS provisional "
         "value is not eligible under SA-2025.1", "value exact"),
        (ctx, "LOOKUP", "Which golden well is the source alias MYB001?", "MY_B_W001 (alias from SRC_MY_OPS)", "exact"),
        (ctx, "NUMERIC", "How many wellbores are in the portfolio?", f"{master['wellbores']}", "exact"),
        (ctx, "NUMERIC", "How many completions are in the portfolio?", f"{master['completions']}", "exact"),
        (ctx, "LOOKUP", "Which field does equipment EQ_MY_A_01 belong to?", "Field MY_A via facility FAC_MY_A", "exact"),
        (ctx, "NUMERIC", "How many wells are there in Malaysia?", f"{wells_per_country}", "exact"),
        (ctx, "REDIRECT", "What is the target achievement for Iraq?", "Redirects to the KPI agent da_zava_performance", "must redirect"),
        (ctx, "REFUSAL", "Show the history of well MY_Z_W999.", "No such well; suggests the golden ID format", "must not invent"),
    ]
    rows = [[f"EV{i:02}", agent, kind, question, answer, tolerance, "PUB-S2", "", ""]
            for i, (agent, kind, question, answer, tolerance) in enumerate(cases, start=1)]
    return _csv(["case_id", "agent", "type", "question", "expected_answer", "tolerance", "publication_id",
                 "actual_answer", "pass_fail"], rows)


def write_agent_evaluation() -> Path:
    import json

    expected = json.loads((ROOT / "assets" / "expected" / "expected-results-standard.json").read_text(encoding="utf-8"))
    path = ROOT / "assets" / "agents" / "agent_evaluation_cases.csv"
    path.write_text(render_agent_evaluation(expected), encoding="utf-8", newline="")
    return path


def write_contracts(output: Path = CONTRACTS_DIR) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, content in render_contracts().items():
        path = output / name
        path.write_text(content, encoding="utf-8", newline="")
        paths.append(path)
    paths.append(write_agent_evaluation())
    return paths
