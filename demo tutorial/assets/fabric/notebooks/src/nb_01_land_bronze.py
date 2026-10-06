# %% [markdown]
# # nb_01_land_bronze - Landing ke Bronze (ELT: Load)
#
# Membaca file Parquet yang ditulis Copy activity ke `Files/landing/<batch>/<entity>/`,
# memeriksa jumlah baris terhadap `ctl.batch_entity`, lalu menambahkan baris **baru** ke tabel
# `bronze.<entity>` secara idempoten. Bronze menyimpan bukti sumber apa adanya.
#
# **Lakehouse default:** `lh_piep_core`.

# %% [parameters]
p_batch_id = "B0"
p_run_id = "manual"
p_landing_root = "Files/landing"
p_table_format = "delta"

# %%
%run nb_00_common

# %%
STAGE = "BRONZE"
ensure_schemas("bronze", "ops")
landing = f"{p_landing_root}/{p_batch_id}"


def read_landing(entity):
    path = f"{landing}/{entity}"
    try:
        return spark.read.parquet(path), path
    except Exception as error:  # Copy writes no file for some empty entities
        message = str(error).lower()
        if "path does not exist" in message or "path_not_found" in message or "unable to infer schema" in message:
            return None, path
        raise


manifest, _ = read_landing("ctl__batch_entity")
source_batch, _ = read_landing("ctl__source_batch")
if manifest is None or source_batch is None:
    raise RuntimeError(f"Control files for {p_batch_id} were not found in {landing}. Run the Copy step first.")
batch_rows = source_batch.filter(F.col("batch_id") == p_batch_id).collect()
if len(batch_rows) != 1 or batch_rows[0]["state"] != "SEALED":
    raise RuntimeError(f"{p_batch_id} is not a single SEALED source batch. Stop and check the source.")
batch = batch_rows[0]
expected = {r["entity_name"]: int(r["row_count"])
            for r in manifest.filter(F.col("batch_id") == p_batch_id).collect()}

# %% [markdown]
# ## Urutan batch dan rekonsiliasi jumlah baris
#
# Batch harus diproses berurutan (`parent_batch_id` = batch terakhir yang sudah commit).
# Jika jumlah baris landing tidak sama dengan manifest sumber, Bronze **tidak** diubah.

# %%
history = committed_batches()
already_committed = any(b["BatchId"] == p_batch_id for b in history)
if not already_committed:
    expected_parent = history[-1]["BatchId"] if history else None
    if batch["parent_batch_id"] != expected_parent:
        raise RuntimeError(f"Batch order violation: {p_batch_id} has parent {batch['parent_batch_id']}, "
                           f"but the latest committed batch is {expected_parent}.")

landed, results, mismatches = {}, [], []
for entity, expected_rows in sorted(expected.items()):
    df, path = read_landing(entity)
    if df is not None and "batch_id" in df.columns:
        foreign = df.filter(F.col("batch_id") != p_batch_id).count()
        if foreign:
            mismatches.append(f"{entity}: {foreign} rows belong to another batch")
    rows = 0 if df is None else df.count()
    landed[entity] = (df, path)
    results.append((entity, expected_rows, rows))
    if rows != expected_rows:
        mismatches.append(f"{entity}: expected {expected_rows}, landed {rows}")
if mismatches:
    record_status(STAGE, "LANDING_MISMATCH", "; ".join(mismatches)[:4000])
    raise RuntimeError("Landing does not match the source manifest: " + "; ".join(mismatches))

# %% [markdown]
# ## Append idempoten ke Bronze
#
# `_row_hash` dihitung dari seluruh kolom sumber. Mengulang batch yang sama tidak menambah baris
# (duplikasi transport). Duplikasi bisnis (change ID berbeda, payload sama) tetap disimpan sebagai bukti.

# %%
log_rows = []
for entity, expected_rows, rows in results:
    df, path = landed[entity]
    new_rows = 0
    if df is not None and rows:
        source_columns = df.columns
        incoming = (df.withColumn("_row_hash", F.sha2(F.to_json(F.struct(*[F.col(c) for c in source_columns])), 256))
                    .withColumn("_ingested_at_utc", F.lit(utc_now()).cast("timestamp"))
                    .withColumn("_pipeline_run_id", F.lit(RUN_ID))
                    .withColumn("_landing_path", F.lit(path))
                    .dropDuplicates(["_row_hash"]))
        name = f"bronze.{entity}"
        if table_exists(name):
            incoming = incoming.join(spark.table(name).select("_row_hash"), "_row_hash", "left_anti")
        incoming = incoming.cache()
        new_rows = incoming.count()
        if new_rows:
            append_table(incoming.select(*source_columns, "_row_hash", "_ingested_at_utc",
                                         "_pipeline_run_id", "_landing_path"), name)
        incoming.unpersist()
    log_rows.append((p_batch_id, entity, expected_rows, rows, new_rows, "COMMITTED", RUN_ID, utc_now()))

log = spark.createDataFrame(log_rows, "BatchId string, EntityName string, ExpectedRows long, LandedRows long, "
                                      "NewBronzeRows long, Status string, RunId string, LoggedAtUtc timestamp")
replace_where(log, "ops.ingestion_log", f"BatchId = {literal(p_batch_id)}")
if not already_committed:
    order = (history[-1]["CommitOrder"] + 1) if history else 1
    commit = spark.createDataFrame(
        [(p_batch_id, batch["parent_batch_id"], order, str(batch["period_start"]), str(batch["period_end"]),
          batch["dataset_version"], RUN_ID, utc_now())],
        "BatchId string, ParentBatchId string, CommitOrder int, PeriodStart string, PeriodEnd string, "
        "DatasetVersion string, RunId string, CommittedAtUtc timestamp")
    append_table(commit.withColumn("PeriodStart", F.to_date("PeriodStart"))
                 .withColumn("PeriodEnd", F.to_date("PeriodEnd")), "ops.ingestion_batch")
record_status(STAGE, "BRONZE_COMMITTED", f"{len(results)} entities reconciled")

# %%
finish({"batch_id": p_batch_id, "status": "BRONZE_COMMITTED", "already_committed": already_committed,
        "entities": len(results), "new_bronze_rows": sum(r[4] for r in log_rows)})
