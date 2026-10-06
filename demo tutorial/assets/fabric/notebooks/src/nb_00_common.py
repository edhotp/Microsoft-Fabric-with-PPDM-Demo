# %% [markdown]
# # nb_00_common - PIEP SSOT shared helpers
#
# Notebook lain menjalankan notebook ini melalui `%run nb_00_common`. Jangan jalankan notebook ini sendiri.
#
# Semua data dalam workshop ini **sintetis**. Nama tabel Silver bersifat *PPDM-aligned*,
# bukan nama tabel resmi PPDM.

# %%
import json
from datetime import datetime, timezone

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

spark.conf.set("spark.sql.session.timeZone", "UTC")

TABLE_FORMAT = globals().get("p_table_format", "delta")
RUN_ID = globals().get("p_run_id", "manual")
DATASET_VERSION = "piep-ssot-1.0"
MAPPING_VERSION = "PPDM-ALIGN-1.0"
KPI_CONTRACT_VERSION = "KPI-1.0"
VOLUME = "decimal(19,6)"
MONEY = "decimal(19,4)"
COMMODITIES = ["Oil", "Gas", "Water"]
LINEAGE_COLUMNS = ["_row_hash", "_ingested_at_utc", "_pipeline_run_id", "_landing_path"]

ISSUE_SCHEMA = T.StructType([
    T.StructField("BatchId", T.StringType(), False),
    T.StructField("Stage", T.StringType(), False),
    T.StructField("RuleId", T.StringType(), False),
    T.StructField("Severity", T.StringType(), False),
    T.StructField("SourceSystem", T.StringType(), True),
    T.StructField("EntityName", T.StringType(), True),
    T.StructField("RecordKey", T.StringType(), True),
    T.StructField("Message", T.StringType(), True),
    T.StructField("RunId", T.StringType(), False),
    T.StructField("DetectedAtUtc", T.TimestampType(), False),
])

RULES = {
    "M01": ("BLOCKER", "Duplicate master key in the registry snapshot"),
    "M02": ("BLOCKER", "Master record references a missing parent"),
    "M03": ("BLOCKER", "Working interest is outside (0,1] or periods overlap"),
    "M04": ("BLOCKER", "Unit conversion factor must be greater than zero"),
    "R01": ("BLOCKER", "Source well reference has no approved alias"),
    "R02": ("BLOCKER", "Unit of measure is not registered for the commodity"),
    "R03": ("BLOCKER", "Quantity is missing for a non-retraction record"),
    "R04": ("BLOCKER", "Quantity is negative"),
    "R05": ("BLOCKER", "Commodity is not Oil, Gas, or Water"),
    "R06": ("BLOCKER", "Same observation and revision delivered with different payloads"),
    "R07": ("BLOCKER", "Equal-priority authoritative sources disagree"),
    "R10": ("INFO", "Duplicate delivery with identical payload was ignored"),
    "W01": ("WARNING", "No candidate is eligible under the source authority policy"),
    "B01": ("BLOCKER", "Dataflow staging output is missing or belongs to another batch"),
    "B02": ("BLOCKER", "Target staging row failed Dataflow validation"),
    "B03": ("BLOCKER", "Cost staging row failed Dataflow validation"),
    "B04": ("BLOCKER", "Downtime event is invalid or references unknown equipment"),
    "B05": ("BLOCKER", "Loss allocation references an unknown event, well, or date"),
}


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_schemas(*names):
    for name in names:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {name}")


def table_exists(name):
    return spark.catalog.tableExists(name)


def write_table(df, name):
    """Replace a whole table. Used for current-state Silver tables."""
    df.write.format(TABLE_FORMAT).mode("overwrite").option("overwriteSchema", "true").saveAsTable(name)


def replace_where(df, name, condition):
    """Idempotently replace rows that match `condition` (every row in df must match it)."""
    if not table_exists(name):
        write_table(df, name)
        return
    df.write.format(TABLE_FORMAT).mode("overwrite").option("replaceWhere", condition).saveAsTable(name)


def append_table(df, name):
    df.write.format(TABLE_FORMAT).mode("append").saveAsTable(name)


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def bronze_events(entity, schema_ddl):
    """All committed Bronze rows for an event entity, or an empty frame if it never had rows."""
    name = f"bronze.{entity}"
    if table_exists(name):
        return spark.table(name).drop(*LINEAGE_COLUMNS)
    return spark.createDataFrame([], schema_ddl)


def snapshot(entity):
    """Registry snapshot delivered with the current batch."""
    return spark.table(f"bronze.{entity}").filter(F.col("batch_id") == p_batch_id).drop(*LINEAGE_COLUMNS)


def issues_from(df, rule, entity, source_col, key_expr, message=None):
    severity, default_message = RULES[rule]
    return df.select(
        F.lit(p_batch_id).alias("BatchId"), F.lit(STAGE).alias("Stage"), F.lit(rule).alias("RuleId"),
        F.lit(severity).alias("Severity"),
        (F.col(source_col) if source_col else F.lit(None)).cast("string").alias("SourceSystem"),
        F.lit(entity).alias("EntityName"), key_expr.cast("string").alias("RecordKey"),
        F.lit(message or default_message).alias("Message"), F.lit(RUN_ID).alias("RunId"),
        F.lit(utc_now()).cast("timestamp").alias("DetectedAtUtc"))


def save_issues(frames):
    """Replace this batch+stage's issues so reruns never double count."""
    issues = spark.createDataFrame([], ISSUE_SCHEMA)
    for frame in frames:
        issues = issues.unionByName(frame)
    rows = issues.collect()
    issues = spark.createDataFrame(rows, ISSUE_SCHEMA)
    replace_where(issues, "ops.dq_issue", f"BatchId = {literal(p_batch_id)} AND Stage = {literal(STAGE)}")
    counts = {}
    for row in rows:
        counts[row["Severity"]] = counts.get(row["Severity"], 0) + 1
    return counts


def record_status(stage, status, message="", publication_id=None, counts=None):
    counts = counts or {}
    schema = ("BatchId string, Stage string, Status string, PublicationId string, BlockerCount int, "
              "WarningCount int, InfoCount int, Message string, RunId string, UpdatedAtUtc timestamp")
    row = [(p_batch_id, stage, status, publication_id, int(counts.get("BLOCKER", 0)),
            int(counts.get("WARNING", 0)), int(counts.get("INFO", 0)), message, RUN_ID, utc_now())]
    replace_where(spark.createDataFrame(row, schema), "ops.batch_status",
                  f"BatchId = {literal(p_batch_id)} AND Stage = {literal(stage)}")


def committed_batches():
    if not table_exists("ops.ingestion_batch"):
        return []
    return [r.asDict() for r in spark.table("ops.ingestion_batch").orderBy("CommitOrder").collect()]


def require_latest_batch():
    """Silver is rebuilt for the latest committed batch only; processing an older batch is refused."""
    batches = committed_batches()
    if not batches:
        raise RuntimeError("No batch is committed in Bronze. Run nb_01_land_bronze first.")
    latest = batches[-1]
    if latest["BatchId"] != p_batch_id:
        raise RuntimeError(f"Batch {p_batch_id} is not the latest committed batch ({latest['BatchId']}). "
                           "Process batches in order and rerun the latest batch.")
    return latest


def stable_key(prefix, column):
    """Deterministic surrogate key: the same business ID always yields the same key."""
    return F.xxhash64(F.lit(prefix), F.col(column)).cast("bigint")


def date_key(column):
    return F.date_format(F.col(column), "yyyyMMdd").cast("int")


def table_version(name):
    return int(spark.sql(f"DESCRIBE HISTORY {name} LIMIT 1").collect()[0]["version"])


def finish(summary):
    """Return a JSON summary as the notebook exit value (visible in pipeline activity output)."""
    text = json.dumps(summary, default=str)
    print(text)
    notebookutils.notebook.exit(text)
