"""Local harness that executes the Fabric notebook sources with Spark + Delta.

It simulates the two Fabric services that are not available locally:
* the Copy activity (Azure SQL -> Parquet landing files), and
* the Dataflow Gen2 ETL output (stg_df.target_monthly / stg_df.cost_monthly),
using the same documented rules as the M scripts in assets/fabric/dataflows.
"""

from __future__ import annotations

import io
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

from workshop.contracts import TABLE_BY_NAME, TABLES
from workshop.generate import pack_files
from workshop.load import convert
from workshop.notebooks import parse_cells

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_SOURCES = ROOT / "assets" / "fabric" / "notebooks" / "src"


class NotebookExit(Exception):
    def __init__(self, value: str):
        super().__init__(value)
        self.value = value


class _Notebook:
    @staticmethod
    def exit(value):
        raise NotebookExit(value)


class FakeNotebookUtils:
    notebook = _Notebook()


def spark_type(sql_type: str):
    from pyspark.sql import types as T

    base = sql_type.split("(")[0]
    if base in ("varchar", "char"):
        return T.StringType()
    if base == "int":
        return T.IntegerType()
    if base == "bigint":
        return T.LongType()
    if base == "decimal":
        precision, scale = sql_type[len("decimal("):-1].split(",")
        return T.DecimalType(int(precision), int(scale))
    if base == "date":
        return T.DateType()
    if base == "datetime2":
        return T.TimestampType()
    if base == "bit":
        return T.BooleanType()
    raise ValueError(sql_type)


def schema_for(table_name: str):
    from pyspark.sql import types as T

    table = TABLE_BY_NAME[table_name]
    return T.StructType([T.StructField(c.name, spark_type(c.sql_type), c.nullable) for c in table.columns])


def rows_from_csv(table_name: str, content: bytes) -> list[tuple]:
    """Parse CSV like the Copy activity would; datetime2 values are UTC wall-clock times."""
    import csv
    from datetime import datetime, timezone

    table = TABLE_BY_NAME[table_name]
    reader = csv.reader(io.StringIO(content.decode("utf-8")))
    next(reader)

    def value(raw, column):
        parsed = convert(raw, column.sql_type, column.nullable)
        # PySpark converts naive datetimes with the OS time zone; make them explicit UTC instants.
        return parsed.replace(tzinfo=timezone.utc) if isinstance(parsed, datetime) else parsed

    return [tuple(value(v, c) for v, c in zip(row, table.columns)) for row in reader]


def simulate_copy(spark, pack: dict, landing_root: Path) -> None:
    """Write Parquet exactly where the Copy activity writes it: landing/<batch>/<entity>/."""
    batch = pack["meta"]["batch_id"]
    folder = landing_root / batch
    if folder.exists():
        shutil.rmtree(folder)
    for table_name, content in pack_files(pack).items():
        rows = rows_from_csv(table_name, content)
        if not rows:
            continue  # Copy may produce no file for an empty result; nb_01 must handle it
        spark.createDataFrame(rows, schema_for(table_name)).coalesce(1).write.mode("overwrite").parquet(
            str(folder / TABLE_BY_NAME[table_name].entity))


def simulate_dataflows(spark, pack: dict, table_format: str = "delta") -> None:
    """Reproduce df_piep_target_etl and df_piep_cost_etl output (Replace into stg_df)."""
    batch, tables = pack["meta"]["batch_id"], pack["tables"]
    target_rows = []
    for row in tables["ref.target_monthly"]:
        for month in range(1, 13):
            value = row[f"m{month:02}"]
            target_rows.append((batch, row["field_id"], row["commodity"], row["scenario_id"],
                                date(row["target_year"], month, 1), float(value), row["target_uom"],
                                "INVALID" if value is None or value < 0 else "VALID"))
    fx = {(r["valid_on"], r["currency_code"]): r["usd_per_unit"] for r in tables["ref.fx_rate"]}
    cost_rows = []
    for row in tables["ref.operating_cost"]:
        rate = fx.get((row["month_start"], row["currency_code"]))
        amount_usd = None if rate is None else float(row["amount_local"]) * float(rate)
        status = "MISSING_FX" if rate is None else ("NEGATIVE_AMOUNT" if row["amount_local"] < 0 else "VALID")
        cost_rows.append((batch, row["cost_id"], row["field_id"], row["month_start"], row["cost_category"],
                          row["currency_code"], float(row["amount_local"]), None if rate is None else float(rate),
                          amount_usd, row["closing_status"], status))
    spark.sql("CREATE SCHEMA IF NOT EXISTS stg_df")
    (spark.createDataFrame(target_rows, "batch_id string, field_id string, commodity string, scenario_id string, "
                                        "month_start date, target_value double, target_uom string, dq_status string")
     .write.format(table_format).mode("overwrite").option("overwriteSchema", "true").saveAsTable("stg_df.target_monthly"))
    (spark.createDataFrame(cost_rows, "batch_id string, cost_id string, field_id string, month_start date, "
                                      "cost_category string, currency_code string, amount_local double, "
                                      "usd_per_unit double, amount_usd double, closing_status string, dq_status string")
     .write.format(table_format).mode("overwrite").option("overwriteSchema", "true").saveAsTable("stg_df.cost_monthly"))


def run_notebook(spark, name: str, params: dict) -> dict | None:
    """Execute a notebook source cell by cell, injecting parameters like a pipeline run."""
    namespace = {"spark": spark, "notebookutils": FakeNotebookUtils(), "__name__": name}

    def execute(notebook: str, inject: dict | None):
        source = (NOTEBOOK_SOURCES / f"{notebook}.py").read_text(encoding="utf-8")
        for cell in parse_cells(source):
            if cell["kind"] == "markdown":
                continue
            code = "\n".join(cell["lines"])
            if code.strip().startswith("%run "):
                execute(code.strip().split()[1], None)
                continue
            exec(compile(code, f"<{notebook}>", "exec"), namespace)
            if cell["kind"] == "parameters" and inject:
                namespace.update(inject)

    try:
        execute(name, params)
    except NotebookExit as done:
        return json.loads(done.value)
    return None


def decimal_sum(df, column) -> Decimal:
    from pyspark.sql import functions as F

    value = df.agg(F.sum(column).alias("v")).first()["v"]
    return Decimal(0) if value is None else Decimal(value)
