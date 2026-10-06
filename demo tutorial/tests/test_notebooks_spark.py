"""End-to-end execution of the Fabric notebook sources against the independent reference results."""

from decimal import Decimal

import pytest

pytest.importorskip("pyspark")
pytest.importorskip("delta")

from pyspark.sql import functions as F  # noqa: E402

from notebook_harness import decimal_sum, run_notebook, simulate_copy, simulate_dataflows  # noqa: E402
from workshop.contracts import INCIDENT_ID, PACKS, S_DATE  # noqa: E402
from workshop.expected import expected_results  # noqa: E402
from workshop.generate import build_packs  # noqa: E402

pytestmark = pytest.mark.spark
PROFILE = "small"


@pytest.fixture(scope="module")
def sequence(spark, tmp_path_factory):
    for schema in ["bronze", "silver", "silver_ext", "quarantine", "ops", "serve", "stg_df", "ai"]:
        spark.sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    landing = tmp_path_factory.mktemp("landing")
    ai_root = "serve"
    packs = build_packs(PROFILE)
    expected = expected_results(PROFILE, packs)
    outcomes = {}
    for batch in PACKS:
        spark.catalog.clearCache()
        pack = packs[batch]
        params = {"p_batch_id": batch, "p_run_id": f"test-{batch}", "p_landing_root": str(landing),
                  "p_table_format": "delta"}
        simulate_copy(spark, pack, landing)
        bronze = run_notebook(spark, "nb_01_land_bronze", params)
        if batch == "B1":  # rerun the same batch: transport retry must add nothing
            again = run_notebook(spark, "nb_01_land_bronze", params)
            assert again["new_bronze_rows"] == 0 and again["already_committed"]
        if batch == "C1":  # F1 drill: fail after Bronze, then resume the same batch
            with pytest.raises(RuntimeError, match="F1 failure drill"):
                run_notebook(spark, "nb_02_conform_master_ppdm", {**params, "p_fail_after_bronze": "true"})
        run_notebook(spark, "nb_02_conform_master_ppdm", {**params, "p_fail_after_bronze": "false"})
        run_notebook(spark, "nb_03_conform_production", params)
        simulate_dataflows(spark, pack)
        run_notebook(spark, "nb_04_conform_business", params)
        try:
            serve = run_notebook(spark, "nb_05_validate_and_serve", params)
            status = serve["status"]
        except RuntimeError as error:
            assert "QUALITY_FAILED" in str(error)
            status = "QUALITY_FAILED"
        ai = None
        if status == "CANDIDATE_READY":
            ai = run_notebook(spark, "nb_06_prepare_ai_serving",
                              {"p_publication_id": f"PUB-{batch}", "p_source_prefix": ai_root,
                               "p_run_id": f"test-{batch}", "p_table_format": "delta"})
        outcomes[batch] = {"bronze": bronze, "status": status, "ai": ai}
    return {"expected": expected, "outcomes": outcomes}


def published(spark, table, batch):
    return spark.table(f"serve.{table}").filter(F.col("PublicationId") == f"PUB-{batch}")


def test_quality_gate_matches_reference(spark, sequence):
    for batch in PACKS:
        expected = sequence["expected"]["publications"][f"PUB-{batch}"]
        actual = sequence["outcomes"][batch]["status"]
        assert actual == ("QUALITY_FAILED" if expected["status"] == "QUALITY_FAILED" else "CANDIDATE_READY"), batch
        issues = spark.table("ops.dq_issue").filter(F.col("BatchId") == batch)
        by_rule = {r["RuleId"]: r["n"] for r in issues.groupBy("RuleId").agg(F.count("*").alias("n")).collect()}
        assert by_rule == {**expected["blockers"], **expected["info_and_warnings"]}, batch


def test_production_totals_match_reference(spark, sequence):
    for batch in PACKS:
        expected = sequence["expected"]["publications"][f"PUB-{batch}"]
        if expected["status"] == "QUALITY_FAILED":
            assert published(spark, "fact_production_daily", batch).count() == 0
            continue
        fact = published(spark, "fact_production_daily", batch)
        assert fact.count() == expected["counts"]["fact_production_rows"], batch
        assert fact.agg(F.sum("IsComplete")).first()[0] == expected["counts"]["complete_rows"], batch
        assert fact.agg(F.sum("RetractedCount")).first()[0] == expected["counts"]["retracted_count"], batch
        for column, key in [("OilBbl", "oil_total"), ("GasMscf", "gas_total"), ("WaterBbl", "water_total"),
                            ("GrossBoe", "gross_boe_total"), ("NetWiBoe", "net_wi_boe_total")]:
            assert decimal_sum(fact, column) == Decimal(expected["totals"][key]), (batch, column)
        assert decimal_sum(published(spark, "fact_target_daily", batch), "TargetBoe") == Decimal(expected["target_boe_total"])
        assert decimal_sum(published(spark, "fact_operating_cost_monthly", batch), "AmountUsd") == Decimal(expected["opex_usd_total"])
        decisions = published(spark, "source_decision", batch)
        assert {r["DecisionStatus"]: r["n"] for r in decisions.groupBy("DecisionStatus").agg(F.count("*").alias("n")).collect()} \
            == expected["decisions"], batch


def test_master_and_fixture(spark, sequence):
    expected = sequence["expected"]
    wells = published(spark, "dim_well", "B0")
    master = expected["publications"]["PUB-B0"]["master"]
    assert wells.count() == master["wells"]
    assert wells.agg(F.sum("WellboreCount")).first()[0] == master["wellbores"]
    assert wells.agg(F.sum("CompletionCount")).first()[0] == master["completions"]
    loss = published(spark, "fact_loss_allocation", "B0")
    fixture = expected["fixture"]
    assert loss.count() == fixture["allocation_rows"]
    for column, key in [("LostOilBbl", "lost_oil_bbl"), ("LostGasMscf", "lost_gas_mscf"),
                        ("LostBoeGross", "lost_boe_gross"), ("LostBoeNetWi", "lost_boe_net_wi"),
                        ("ValueUsdGross", "value_usd_gross"), ("ValueUsdNetWi", "value_usd_net_wi")]:
        assert decimal_sum(loss, column) == Decimal(fixture[key]), column
    incidents = published(spark, "dim_incident", "B0").filter(F.col("IncidentId") == INCIDENT_ID)
    downtime = published(spark, "fact_downtime_event", "B0").join(incidents.select("IncidentKey"), "IncidentKey")
    assert decimal_sum(downtime, "DurationHours") == Decimal(fixture["equipment_downtime_hours"])


def test_s1_s2_authority_and_correction(spark, sequence):
    checks = sequence["expected"]["ssot_checks"]

    def oil_for(batch):
        well_key = published(spark, "dim_well", batch).filter(F.col("WellId") == "MY_B_W001").first()["WellKey"]
        row = published(spark, "fact_production_daily", batch).filter(
            (F.col("WellKey") == well_key) & (F.col("DateKey") == int(S_DATE.strftime("%Y%m%d")))).first()
        return Decimal(row["OilBbl"])

    assert oil_for("S1") == Decimal(checks["s1_selected_oil_bbl"])
    assert oil_for("S2") == Decimal(checks["s2_selected_oil_bbl"])
    decision = published(spark, "source_decision", "S1").first()
    assert decision["SelectedSourceSystem"] == "SRC_MY_PROD" and decision["CandidateCount"] == 2
    assert "SRC_MY_OPS" in decision["CandidatesJson"]
    gross_delta = (decimal_sum(published(spark, "fact_production_daily", "S2"), "GrossBoe")
                   - decimal_sum(published(spark, "fact_production_daily", "S1"), "GrossBoe"))
    net_delta = (decimal_sum(published(spark, "fact_production_daily", "S2"), "NetWiBoe")
                 - decimal_sum(published(spark, "fact_production_daily", "S1"), "NetWiBoe"))
    assert gross_delta == Decimal(checks["s2_gross_boe_delta"]) and net_delta == Decimal(checks["s2_net_wi_boe_delta"])


def test_serve_schema_matches_warehouse_contract(spark, sequence):
    """Every serve table must load into the Warehouse Gold table without type or NULL surprises."""
    from workshop.warehouse import GOLD_TABLES

    def family(spark_type: str) -> str:
        if spark_type.startswith("decimal"):
            return spark_type.replace(" ", "")
        return {"int": "int", "bigint": "bigint", "string": "varchar", "date": "date",
                "timestamp": "datetime2"}.get(spark_type, spark_type)

    for table, columns in GOLD_TABLES.items():
        frame = spark.table(f"serve.{table}")
        actual = {f.name: family(f.dataType.simpleString()) for f in frame.schema.fields if f.name != "PublicationId"}
        expected = {name: sql_type.split("(")[0] if not sql_type.startswith("decimal") else sql_type
                    for name, sql_type, _ in columns}
        assert actual == expected, table
        for name, _, nullable in columns:
            if not nullable:
                assert frame.filter(F.col(name).isNull()).count() == 0, f"{table}.{name} has NULLs"


def test_ai_serving_uses_the_same_publication(spark, sequence):
    final = sequence["outcomes"]["S2"]["ai"]
    assert final["status"] == "AI_SERVING_READY"
    assert spark.table("ai.publication").first()["publication_id"] == "PUB-S2"
    assert {r["business_publication_id"] for r in spark.table("ai.well").collect()} == {"PUB-S2"}
    ai_total = decimal_sum(spark.table("ai.reporting_stream_daily"), "gross_boe")
    assert ai_total == Decimal(sequence["expected"]["publications"]["PUB-S2"]["totals"]["gross_boe_total"])
    assert spark.table("ai.wellbore").count() == sequence["expected"]["publications"]["PUB-S2"]["master"]["wellbores"]
    loss = spark.table("ai.loss_allocation")
    fixture = sequence["expected"]["fixture"]
    assert loss.select("well_id").distinct().count() == fixture["affected_wells"]
    assert decimal_sum(loss, "lost_boe_gross") == Decimal(fixture["lost_boe_gross"])
