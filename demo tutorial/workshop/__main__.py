"""Command line for the PIEP SSOT workshop.

Examples (run from the `demo tutorial` folder):
    python -m workshop generate --profile standard
    python -m workshop expected --profile standard
    python -m workshop run-sql --config config/local.json --file assets/sql/azure-sql/01_create_source_schema.sql
    python -m workshop load --config config/local.json --batch B0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workshop.contracts import PACKS, PROFILES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "source"
SQL_SCHEMA = ROOT / "assets" / "sql" / "azure-sql" / "01_create_source_schema.sql"
NOTEBOOK_SRC = ROOT / "assets" / "fabric" / "notebooks" / "src"
NOTEBOOK_OUT = ROOT / "assets" / "fabric" / "notebooks"
EXPECTED_DIR = ROOT / "assets" / "expected"
WAREHOUSE_SQL = ROOT / "assets" / "sql" / "warehouse"


def _print_rows(rows) -> None:
    for row in rows:
        print(" | ".join("" if v is None else str(v) for v in row))


def cmd_generate(args) -> int:
    from workshop.generate import write_packs

    summary = write_packs(Path(args.output), args.profile)
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_expected(args) -> int:
    from workshop.expected import expected_results

    result = expected_results(args.profile)
    output = Path(args.output or EXPECTED_DIR / f"expected-results-{args.profile}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


def cmd_render_sql(args) -> int:
    from workshop.sqlgen import render_source_schema

    output = Path(args.output or SQL_SCHEMA)
    output.write_text(render_source_schema(), encoding="utf-8", newline="\n")
    print(f"Wrote {output}")
    return 0


def cmd_render_warehouse(args) -> int:
    from workshop.warehouse import render_objects, render_procedures, render_seed

    for name, content in [("01_create_objects.sql", render_objects()), ("02_procedures.sql", render_procedures()),
                          ("03_seed_contracts.sql", render_seed())]:
        path = WAREHOUSE_SQL / name
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")
    return 0


def cmd_render_contracts(args) -> int:
    from workshop.governance import write_contracts

    for path in write_contracts():
        print(f"Wrote {path}")
    return 0


def cmd_render_pipelines(args) -> int:
    from workshop.fabric_pipelines import render

    placeholders = {k: f"<{k}>" for k in [
        "core_workspace", "core_workspace_name", "ai_workspace", "lakehouse", "warehouse", "warehouse_endpoint",
        "sql_connection", "semantic_model", "semantic_model_connection",
        "notebook:nb_01_land_bronze", "notebook:nb_02_conform_master_ppdm", "notebook:nb_03_conform_production",
        "notebook:nb_04_conform_business", "notebook:nb_05_validate_and_serve", "notebook:nb_06_prepare_ai_serving",
        "dataflow:df_piep_target_etl", "dataflow:df_piep_cost_etl"]}
    placeholders["sql_database"] = "sqldb_piep_source_demo"
    placeholders["core_workspace_name"] = "ws-piep-ppdm-demo"
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name, body in render(placeholders).items():
        path = output / f"{name}.json"
        path.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {path}")
    return 0


def cmd_deploy_pipelines(args) -> int:
    from workshop.fabric_pipelines import deploy

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    for name, item_id in deploy(config, args.pipeline or None).items():
        print(f"Deployed {name}: {item_id}")
    return 0


def cmd_evaluate_agents(args) -> int:
    from workshop.agents import evaluate

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    summary = evaluate(config, Path(args.cases), Path(args.output), args.rounds)
    print(json.dumps(summary))
    print(f"Wrote {args.output}. Review every REVIEW row and copy the results into the evidence template.")
    return 0 if summary["FAIL"] == 0 else 1


def cmd_build_notebooks(args) -> int:
    from workshop.notebooks import build_all

    for path in build_all(NOTEBOOK_SRC, NOTEBOOK_OUT):
        print(f"Wrote {path}")
    return 0


def cmd_run_sql(args) -> int:
    from workshop.load import read_config, run_sql_file

    run_sql_file(read_config(Path(args.config)), Path(args.file))
    print(f"Executed {args.file}")
    return 0


def cmd_load(args) -> int:
    from workshop.load import load_pack, read_config

    config = read_config(Path(args.config))
    batches = PACKS[: PACKS.index(args.through) + 1] if args.through else [args.batch]
    for batch in batches:
        print(f"{batch}: {load_pack(config, Path(args.source), batch)}")
    return 0


def cmd_status(args) -> int:
    from workshop.load import batch_status, read_config

    _print_rows(batch_status(read_config(Path(args.config))))
    return 0


def cmd_verify(args) -> int:
    from workshop.load import read_config, verify_pack

    results = verify_pack(read_config(Path(args.config)), args.batch)
    print("entity | expected | actual | status")
    _print_rows(results)
    if any(row[3] != "OK" for row in results):
        return 1
    print(f"{args.batch}: all entity row counts match ctl.batch_entity")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m workshop", description="PIEP SSOT workshop tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate", help="Generate synthetic source packs as CSV")
    p.add_argument("--profile", choices=sorted(PROFILES), default="standard")
    p.add_argument("--output", default=str(DEFAULT_SOURCE))
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("expected", help="Write the independent expected results (answer key)")
    p.add_argument("--profile", choices=sorted(PROFILES), default="standard")
    p.add_argument("--output")
    p.set_defaults(func=cmd_expected)

    p = sub.add_parser("render-sql", help="Render the Azure SQL source schema script")
    p.add_argument("--output")
    p.set_defaults(func=cmd_render_sql)

    p = sub.add_parser("render-warehouse", help="Render Fabric Warehouse objects, procedures, and seed scripts")
    p.set_defaults(func=cmd_render_warehouse)

    p = sub.add_parser("render-contracts", help="Render governance contract CSVs (authority, PPDM, DQ, KPI)")
    p.set_defaults(func=cmd_render_contracts)

    p = sub.add_parser("render-pipelines", help="Write Fabric pipeline JSON definitions with ID placeholders")
    p.add_argument("--output", default=str(ROOT / "assets" / "fabric" / "pipelines" / "definitions"))
    p.set_defaults(func=cmd_render_pipelines)

    p = sub.add_parser("deploy-pipelines", help="Create or update the workshop pipelines in Fabric (uses az login)")
    p.add_argument("--config", required=True)
    p.add_argument("--pipeline", action="append", choices=["pl_piep_setup_source", "pl_piep_load_source",
                                                          "pl_piep_e2e", "pl_piep_publish_gold"])
    p.set_defaults(func=cmd_deploy_pipelines)

    p = sub.add_parser("evaluate-agents", help="Ask the published data agents the 24 evaluation cases (uses az login)")
    p.add_argument("--config", required=True)
    p.add_argument("--cases", default=str(ROOT / "assets" / "agents" / "agent_evaluation_cases.csv"))
    p.add_argument("--output", default=str(ROOT / "evidence" / "agent-evaluation.csv"))
    p.add_argument("--rounds", type=int, default=1)
    p.set_defaults(func=cmd_evaluate_agents)

    p = sub.add_parser("build-notebooks", help="Build Fabric .ipynb files from notebook sources")
    p.set_defaults(func=cmd_build_notebooks)

    p = sub.add_parser("run-sql", help="Run a T-SQL script (GO separated) against Azure SQL")
    p.add_argument("--config", required=True)
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_run_sql)

    p = sub.add_parser("load", help="Load one batch (or all batches through one) into Azure SQL")
    p.add_argument("--config", required=True)
    p.add_argument("--source", default=str(DEFAULT_SOURCE))
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch", choices=PACKS)
    group.add_argument("--through", choices=PACKS)
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("status", help="Show ctl.source_batch state in Azure SQL")
    p.add_argument("--config", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("verify", help="Compare loaded row counts with ctl.batch_entity")
    p.add_argument("--config", required=True)
    p.add_argument("--batch", required=True, choices=PACKS)
    p.set_defaults(func=cmd_verify)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
