"""Offline consistency checks for every workshop asset (no Azure, no Fabric, no Spark)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from workshop.contracts import PACKS, TABLES
from workshop.expected import expected_results
from workshop.generate import build_packs, pack_files
from workshop.governance import render_agent_evaluation, render_contracts
from workshop.notebooks import parse_cells, to_ipynb
from workshop.sqlgen import render_source_schema
from workshop.warehouse import GOLD_TABLES, OPS_TABLES, render_objects, render_procedures, render_seed

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
NOTEBOOK_SRC = ASSETS / "fabric" / "notebooks" / "src"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def standard_expected():
    return expected_results("standard")


# ---------------------------------------------------------------- generator and answer key

def test_generator_is_deterministic():
    first = {b: hashlib.sha256(b"".join(pack_files(p).values())).hexdigest() for b, p in build_packs("small").items()}
    second = {b: hashlib.sha256(b"".join(pack_files(p).values())).hexdigest() for b, p in build_packs("small").items()}
    assert first == second


def test_generated_values_fit_source_contract():
    """Every value must be storable in Azure SQL without rounding, otherwise the answer key drifts."""
    from workshop.contracts import TABLE_BY_NAME

    for name, pack in build_packs("small").items():
        for table_name, rows in pack["tables"].items():
            columns = TABLE_BY_NAME[table_name].columns
            for column in columns:
                if not column.sql_type.startswith("decimal"):
                    continue
                precision, scale = map(int, column.sql_type[len("decimal("):-1].split(","))
                for row in rows:
                    value = row.get(column.name)
                    if value is None:
                        continue
                    exponent = Decimal(value).as_tuple().exponent
                    assert exponent >= -scale, f"{name} {table_name}.{column.name}={value} exceeds scale {scale}"
                    assert len(str(abs(int(value)))) <= precision - scale, f"{table_name}.{column.name}={value}"


def test_pack_chain_is_linear_and_complete():
    packs = build_packs("small")
    assert list(packs) == PACKS
    for index, name in enumerate(PACKS):
        assert packs[name]["meta"]["parent_batch_id"] == (PACKS[index - 1] if index else None)
        assert len(pack_files(packs[name])) == len(TABLES)


def test_baseline_counts_match_plan():
    tables = build_packs("standard")["B0"]["tables"]
    assert len(tables["ref.well"]) == 120 and len(tables["ref.wellbore"]) == 150
    assert len(tables["ref.well_completion"]) == 180
    production = sum(len(tables[t]) for t in ("src_dz.production_report", "src_my.production_report",
                                               "src_iq.daily_volumes"))
    assert production == 131_400
    assert sum(content.count(b"\n") - 1 for content in pack_files(build_packs("standard")["B0"]).values()) == 134_597


def test_committed_expected_results_are_current(standard_expected):
    committed = json.loads(read(ASSETS / "expected" / "expected-results-standard.json"))
    assert committed == json.loads(json.dumps(standard_expected, default=str))
    small = json.loads(read(ASSETS / "expected" / "expected-results-small.json"))
    assert small == json.loads(json.dumps(expected_results("small"), default=str))


def test_key_business_outcomes(standard_expected):
    pubs = standard_expected["publications"]
    assert pubs["PUB-B0"]["totals"]["gross_boe_total"] == "23840575.796184"
    assert pubs["PUB-Q1"]["status"] == "QUALITY_FAILED"
    assert pubs["PUB-Q1"]["blockers"] == {"R01": 10, "R02": 20, "R03": 5}
    assert pubs["PUB-Q1"]["gold_after_approval"] == "PUB-X1"
    assert pubs["PUB-D1"]["info_and_warnings"] == {"R10": 100}
    assert pubs["PUB-S2"]["totals"]["gross_boe_total"] == "23901264.782757"
    checks = standard_expected["ssot_checks"]
    assert (checks["s1_selected_oil_bbl"], checks["s2_selected_oil_bbl"]) == ("284.014547", "289.014547")
    assert (checks["s2_gross_boe_delta"], checks["s2_net_wi_boe_delta"]) == ("5.000000", "2.000000")
    fixture = standard_expected["fixture"]
    assert (fixture["lost_boe_gross"], fixture["lost_boe_net_wi"]) == ("4000.000000", "1600.000000")
    assert (fixture["value_usd_gross"], fixture["value_usd_net_wi"]) == ("177080.0000", "70832.0000")
    assert (fixture["equipment_downtime_hours"], fixture["affected_well_hours"]) == ("48.000", "480.000")


# ---------------------------------------------------------------- generated files are up to date

def test_generated_sql_is_current():
    assert read(ASSETS / "sql" / "azure-sql" / "01_create_source_schema.sql") == render_source_schema()
    warehouse = ASSETS / "sql" / "warehouse"
    assert read(warehouse / "01_create_objects.sql") == render_objects()
    assert read(warehouse / "02_procedures.sql") == render_procedures()
    assert read(warehouse / "03_seed_contracts.sql") == render_seed()


def test_generated_contracts_are_current(standard_expected):
    for name, content in render_contracts().items():
        assert read(ASSETS / "contracts" / name) == content, name
    assert read(ASSETS / "agents" / "agent_evaluation_cases.csv") == render_agent_evaluation(
        json.loads(json.dumps(standard_expected, default=str)))


def test_notebooks_are_built_from_sources():
    sources = sorted(NOTEBOOK_SRC.glob("nb_*.py"))
    assert [p.stem for p in sources] == [f"nb_0{i}_{n}" for i, n in enumerate([
        "common", "land_bronze", "conform_master_ppdm", "conform_production", "conform_business",
        "validate_and_serve", "prepare_ai_serving"])]
    for path in sources:
        built = json.loads(read(ASSETS / "fabric" / "notebooks" / f"{path.stem}.ipynb"))
        assert built == to_ipynb(path.stem, read(path)), f"{path.stem}.ipynb is stale: run build-notebooks"
        tagged = [c for c in built["cells"] if "parameters" in c["metadata"].get("tags", [])]
        assert len(tagged) == (0 if path.stem == "nb_00_common" else 1)
        if path.stem != "nb_00_common":
            code = [c for c in parse_cells(read(path)) if c["kind"] != "markdown"]
            assert code[0]["kind"] == "parameters" and code[1]["lines"] == ["%run nb_00_common"]


def test_procedure_copy_lists_cover_every_gold_column():
    procedures = render_procedures()
    for table, columns in GOLD_TABLES.items():
        insert = re.search(rf"INSERT INTO stg\.{table} \(([^)]*)\)", procedures).group(1)
        assert [c.strip("[] ") for c in insert.split(",")] == [c[0] for c in columns] + ["PublicationId"]


# ---------------------------------------------------------------- cross-asset references

def _measure_names(dax: str) -> set[str]:
    return set(re.findall(r"MEASURE\s+'[^']+'\[([^\]]+)\]", dax))


def test_dax_references_existing_model_objects():
    model = {t: {c[0] for c in cols} | {"PublicationId"} for t, cols in GOLD_TABLES.items()}
    model["publication"] = {c[0] for c in OPS_TABLES["publication"]}
    measures_dax = read(ASSETS / "powerbi" / "measures.dax")
    measures = _measure_names(measures_dax)
    assert len(measures) >= 30
    for name in ["measures.dax", "validation_queries.dax"]:
        text = read(ASSETS / "powerbi" / name)
        for table, column in re.findall(r"'([^']+)'\[([^\]]+)\]", text):
            assert table in model, f"{name}: unknown table {table}"
            assert column in model[table] or column in measures, f"{name}: unknown {table}[{column}]"
        for measure in re.findall(r"(?<!')\[([A-Z][^\]]+)\]", text):
            assert measure in measures or any(measure in cols for cols in model.values()), f"{name}: [{measure}]"


def _nb06_tables() -> set[str]:
    return set(re.findall(r'"(ai\.[a-z_]+)":', read(NOTEBOOK_SRC / "nb_06_prepare_ai_serving.py")))


def test_ontology_matches_ai_projection():
    entities = list(csv.DictReader((ASSETS / "ontology" / "entity_types.csv").open(encoding="utf-8")))
    assert len(entities) == 13
    nb06 = read(NOTEBOOK_SRC / "nb_06_prepare_ai_serving.py")
    properties = {}
    for entity in entities:
        assert entity["source_table"] in _nb06_tables()
        props = [p.strip() for p in entity["properties"].split(",")]
        assert entity["key_property"] in props
        for prop in props:
            assert re.search(rf"\b{prop}\b", nb06), f"{entity['entity_type']}.{prop}"
        properties[entity["entity_type"]] = set(props)
    relationships = list(csv.DictReader((ASSETS / "ontology" / "relationship_types.csv").open(encoding="utf-8")))
    assert len(relationships) == 12
    for rel in relationships:
        assert rel["origin_property"] in properties[rel["origin_entity_type"]]
        assert rel["target_property"] in properties[rel["target_entity_type"]]
        assert len(rel["origin_entity_type"]) <= 26 and len(rel["target_entity_type"]) <= 26


def test_agent_example_queries_use_ai_tables():
    sql = read(ASSETS / "agents" / "da_zava_asset_context_example_queries.sql")
    used = set(re.findall(r"FROM (ai\.[a-z_]+)", sql))
    assert used and used <= _nb06_tables()
    cases = list(csv.DictReader((ASSETS / "agents" / "agent_evaluation_cases.csv").open(encoding="utf-8")))
    assert len(cases) == 24 and {c["publication_id"] for c in cases} == {"PUB-S2"}


def test_pipeline_sheet_references_existing_assets():
    sheet = read(ASSETS / "fabric" / "pipelines" / "pipeline-activity-sheet.md")
    procedures = set(re.findall(r"CREATE OR ALTER PROCEDURE (ops\.\w+)", render_procedures()))
    for procedure in set(re.findall(r"`(ops\.usp_\w+)`", sheet)):
        assert procedure in procedures, procedure
    for notebook in set(re.findall(r"`(nb_0\d_\w+)`", sheet)):
        assert (NOTEBOOK_SRC / f"{notebook}.py").exists(), notebook
    for dataflow in set(re.findall(r"`(df_zava_\w+)`", sheet)):
        assert (ASSETS / "fabric" / "dataflows" / f"{dataflow}.pq").exists(), dataflow
    for parameter in ["p_batch_id", "p_run_id", "p_fail_after_bronze"]:
        assert parameter in read(NOTEBOOK_SRC / "nb_02_conform_master_ppdm.py")


def test_dataflow_outputs_match_notebook_inputs():
    target = read(ASSETS / "fabric" / "dataflows" / "df_zava_target_etl.pq")
    cost = read(ASSETS / "fabric" / "dataflows" / "df_zava_cost_etl.pq")
    harness = read(ROOT / "tests" / "notebook_harness.py")
    for column in ["batch_id", "field_id", "commodity", "scenario_id", "month_start", "target_value", "target_uom",
                   "dq_status"]:
        assert f'"{column}"' in target and column in harness
    for column in ["cost_id", "currency_code", "amount_local", "usd_per_unit", "amount_usd", "closing_status"]:
        assert f'"{column}"' in cost and column in harness
    assert "pSqlServer" not in target + cost, "source paths must not be parameterized"


# ---------------------------------------------------------------- documentation hygiene

DOCS = sorted([*ROOT.glob("*.md"), *(ROOT / "tutorial").glob("*.md"), *(ASSETS).rglob("*.md")])


def _anchor(text: str) -> str:
    text = re.sub(r"[`*_]", lambda m: "_" if m.group(0) == "_" else "", text.strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(doc):
    text = read(doc)
    for target in re.findall(r"\]\((?!https?://|mailto:)([^)\s]+)\)", text):
        path, _, anchor = target.partition("#")
        resolved = (doc.parent / path).resolve() if path else doc
        assert resolved.exists(), f"{doc.name}: broken link {target}"
        if anchor and resolved.suffix == ".md":
            headings = {_anchor(h) for h in re.findall(r"^#{1,6} (.+)$", read(resolved), re.M)}
            assert anchor in headings, f"{doc.name}: missing anchor #{anchor} in {resolved.name}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_mermaid_blocks_are_closed(doc):
    text = read(doc)
    assert text.count("```mermaid") <= text.count("```") // 2
    for block in re.findall(r"```mermaid\n(.*?)```", text, re.S):
        first = block.strip().splitlines()[0].split()[0]
        assert first in {"flowchart", "sequenceDiagram", "stateDiagram-v2", "erDiagram"}, first


def test_tutorial_numbers_match_answer_key(standard_expected):
    pubs = standard_expected["publications"]

    def id_format(value: str, decimals: int = 6) -> str:
        whole, _, frac = f"{Decimal(value):.{decimals}f}".partition(".")
        return f"{int(whole):,}".replace(",", ".") + ("," + frac if frac else "")

    expectations = {
        "07-gold-warehouse-publication.md": [id_format(pubs["PUB-B0"]["by_country"]["DZ"]["gross_boe"])],
        "08-orchestration.md": [id_format(pubs["PUB-B1"]["totals"]["gross_boe_total"]),
                                id_format(pubs["PUB-C1"]["totals"]["gross_boe_total"])],
        "09-semantic-model.md": [id_format(pubs["PUB-D1"]["totals"]["net_wi_boe_total"])],
        "13-ssot-proof-failure-drill.md": [id_format(pubs["PUB-X1"]["totals"]["gross_boe_total"]),
                                           id_format(pubs["PUB-S2"]["totals"]["net_wi_boe_total"])],
    }
    for name, values in expectations.items():
        text = read(ROOT / "tutorial" / name)
        for value in values:
            assert value in text, f"{name} should mention {value}"


def test_json_assets_are_valid():
    for path in [ASSETS / "powerbi" / "zava-ssot-theme.json", ROOT / "config" / "workshop.example.json",
                 ROOT / "infra" / "azure-sql" / "main.parameters.example.json"]:
        json.loads(read(path))


# ---------------------------------------------------------------- findings from the live Fabric run

def test_sql_scripts_split_cleanly_on_go():
    """`run-sql`, the portal editor and the Script activity split on GO; a GO inside /* */ breaks the script."""
    from workshop.fabric_pipelines import sql_batches

    for path in (ASSETS / "sql").rglob("*.sql"):
        for batch in sql_batches(path):
            assert batch.count("/*") == batch.count("*/"), f"{path.name}: unbalanced block comment in a GO batch"


def test_pipeline_definitions_match_activity_sheet_and_committed_json():
    from workshop.fabric_pipelines import E, render

    sheet = read(ASSETS / "fabric" / "pipelines" / "pipeline-activity-sheet.md")
    for key, value in E.items():
        if key.startswith("E"):
            assert f"| {key} | `{value}` |" in sheet, f"{key} differs between sheet and pipeline builder"
    committed = {p.stem: json.loads(read(p)) for p in (ASSETS / "fabric" / "pipelines" / "definitions").glob("*.json")}
    ids = {k: f"<{k}>" for k in ["core_workspace", "ai_workspace", "lakehouse", "warehouse", "warehouse_endpoint",
                                 "sql_connection", "semantic_model", "semantic_model_connection",
                                 "notebook:nb_01_land_bronze", "notebook:nb_02_conform_master_ppdm",
                                 "notebook:nb_03_conform_production", "notebook:nb_04_conform_business",
                                 "notebook:nb_05_validate_and_serve", "notebook:nb_06_prepare_ai_serving",
                                 "dataflow:df_zava_target_etl", "dataflow:df_zava_cost_etl"]}
    ids.update(sql_database="sqldb_zava_source_demo", core_workspace_name="ws-zava-ppdm-demo")
    assert committed == json.loads(json.dumps(render(ids))), "run `python -m workshop render-pipelines`"
    names = [a["name"] for a in committed["pl_zava_e2e"]["properties"]["activities"]]
    for name in names:
        assert f"`{name}`" in sheet, name


def test_azure_cli_authentication_needs_no_username(tmp_path):
    from workshop.load import read_config

    config = {"azure_sql": {"server": "x.database.windows.net", "database": "db", "authentication": "AzureCli",
                            "username": "REPLACE@yourtenant.example"}}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert read_config(path)["azure_sql"]["authentication"] == "AzureCli"


def test_agent_scoring():
    from workshop.agents import score

    case = {"type": "NUMERIC", "expected_answer": "4,000 BOE gross / 1,600 BOE net WI", "tolerance": "exact",
            "publication_id": "PUB-S2"}
    assert score(case, "Lost 4,000 BOE gross and 1,600 BOE net WI. Source: SSOT publication PUB-S2") == "PASS"
    assert score(case, "Lost 3,999 BOE gross and 1,600 BOE net WI. Source: SSOT publication PUB-S2") == "FAIL"
    agent = {"type": "NUMERIC", "expected_answer": "100.0% (43,917 of 43,920 stream-days)", "tolerance": "±0.1 pp",
             "publication_id": "PUB-S2"}
    assert score(agent, "Completeness is 100.0%. Source: SSOT publication PUB-S2") == "PASS"
    assert score({**case, "type": "REFUSAL"}, "Not available") == "REVIEW"
