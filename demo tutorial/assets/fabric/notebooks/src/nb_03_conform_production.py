# %% [markdown]
# # nb_03_conform_production - Observasi produksi kanonis dan source authority (Silver)
#
# Langkah SSOT untuk produksi:
#
# 1. Menyeragamkan empat sumber (`SRC_DZ_PROD`, `SRC_MY_PROD`, `SRC_MY_OPS`, `SRC_IQ_PROD`).
# 2. Memisahkan duplikasi pengiriman (payload sama) dari konflik (payload berbeda).
# 3. Memilih revisi terbaru per observasi sumber, lalu memvalidasi alias, satuan, dan nilai.
# 4. Menerapkan **source authority register** per canonical key (stream, tanggal, komoditas).
# 5. Menyimpan golden observation, keputusan sumber, dan karantina. Tidak ada *silent fallback*.

# %% [parameters]
p_batch_id = "B0"
p_run_id = "manual"
p_table_format = "delta"

# %%
%run nb_00_common

# %%
STAGE = "SILVER_PRODUCTION"
ensure_schemas("silver", "quarantine", "ops")
require_latest_batch()

PRODUCTION_DDL = ("batch_id string, change_id string, change_seq long, observation_id string, well_ref string, "
                  "report_date date, commodity string, quantity decimal(19,6), unit string, revision int, "
                  "operation string, report_status string")
IQ_DDL = ("batch_id string, chg_id string, seq_no long, obs_key string, well_code string, obs_date date, "
          "product string, qty decimal(19,6), qty_unit string, rev_no int, op_code string, approval_flag string")
COMMON = ["batch_id", "change_id", "change_seq", "observation_id", "well_ref", "report_date", "commodity",
          "quantity", "unit", "revision", "operation", "report_status"]


def standard(entity, source_system):
    return bronze_events(entity, PRODUCTION_DDL).select(*COMMON).withColumn("source_system", F.lit(source_system))


iq = bronze_events("src_iq__daily_volumes", IQ_DDL).select(
    "batch_id", F.col("chg_id").alias("change_id"), F.col("seq_no").alias("change_seq"),
    F.col("obs_key").alias("observation_id"), F.col("well_code").alias("well_ref"),
    F.col("obs_date").alias("report_date"),
    F.when(F.col("product") == "OIL", "Oil").when(F.col("product") == "GAS", "Gas")
     .when(F.col("product") == "WTR", "Water").otherwise(F.col("product")).alias("commodity"),
    F.col("qty").alias("quantity"), F.col("qty_unit").alias("unit"), F.col("rev_no").alias("revision"),
    F.col("op_code").alias("operation"),
    F.when(F.col("approval_flag") == "Y", "FINAL").otherwise("PROVISIONAL").alias("report_status"),
).withColumn("source_system", F.lit("SRC_IQ_PROD"))

events = (standard("src_dz__production_report", "SRC_DZ_PROD")
          .unionByName(standard("src_my__production_report", "SRC_MY_PROD"))
          .unionByName(standard("src_my__production_provisional", "SRC_MY_OPS"))
          .unionByName(iq)
          .withColumn("payload_hash", F.sha2(F.to_json(F.struct(
              "well_ref", "report_date", "commodity", F.col("quantity").cast("string").alias("quantity"),
              "unit", "operation", "report_status")), 256)))

# %% [markdown]
# ## Duplikasi, konflik, dan revisi terbaru

# %%
REVISION_KEY = ["source_system", "observation_id", "revision"]
groups = events.groupBy(*REVISION_KEY).agg(F.countDistinct("payload_hash").alias("payloads"),
                                           F.count("*").alias("deliveries"))
issues = [issues_from(groups.filter("payloads > 1"), "R06", "production_observation", "source_system",
                      F.concat_ws("|", *REVISION_KEY))]
clean = events.join(groups.filter("payloads = 1").select(*REVISION_KEY), REVISION_KEY)
ranked = clean.withColumn("delivery_rank", F.row_number().over(Window.partitionBy(*REVISION_KEY).orderBy("change_seq")))
issues.append(issues_from(ranked.filter("delivery_rank > 1"), "R10", "production_observation", "source_system",
                          F.col("change_id")))
revisions = ranked.filter("delivery_rank = 1").drop("delivery_rank")
latest = (revisions.withColumn("revision_rank", F.row_number().over(
              Window.partitionBy("source_system", "observation_id").orderBy(F.desc("revision"), F.desc("change_seq"))))
          .filter("revision_rank = 1").drop("revision_rank"))

# %% [markdown]
# ## Validasi revisi terbaru
#
# Jika revisi terbaru tidak valid, observasi masuk karantina dan menjadi `BLOCKER`.
# Pipeline **tidak** mengambil revisi lama secara diam-diam.

# %%
alias = spark.table("silver.well_alias").select("source_system", F.col("source_well_id").alias("well_ref"), "well_id")
geography = (spark.table("silver.reporting_stream").select("well_id", "stream_id")
             .join(spark.table("silver.well").select("well_id", "field_id"), "well_id")
             .join(spark.table("silver.field").select("field_id", "country_id"), "field_id"))
uom = spark.table("silver.uom_conversion").select("commodity", F.col("uom").alias("unit"), "to_standard_factor",
                                                 "standard_uom")
checked = (latest.join(alias, ["source_system", "well_ref"], "left").join(geography, "well_id", "left")
           .join(uom, ["commodity", "unit"], "left")
           .withColumn("r01", F.col("well_id").isNull())
           .withColumn("r05", ~F.col("commodity").isin(COMMODITIES))
           .withColumn("r02", F.col("commodity").isin(COMMODITIES) & F.col("to_standard_factor").isNull())
           .withColumn("r03", F.col("quantity").isNull() & (F.col("operation") != "D"))
           .withColumn("r04", F.coalesce(F.col("quantity") < 0, F.lit(False))))
record_key = F.concat_ws("|", "source_system", "observation_id", F.col("revision").cast("string"))
for rule in ["R01", "R02", "R03", "R04", "R05"]:
    issues.append(issues_from(checked.filter(F.col(rule.lower())), rule, "production_observation",
                              "source_system", record_key))
invalid_flag = F.col("r01") | F.col("r02") | F.col("r03") | F.col("r04") | F.col("r05")
quarantine = (checked.filter(invalid_flag)
              .withColumn("failed_rules", F.concat_ws(",", *[F.when(F.col(r), F.lit(r.upper())) for r in
                                                             ["r01", "r02", "r03", "r04", "r05"]]))
              .withColumn("quarantined_in_batch", F.lit(p_batch_id))
              .drop("r01", "r02", "r03", "r04", "r05", "payload_hash"))
write_table(quarantine, "quarantine.production_observation")

candidates = (checked.filter(~invalid_flag)
              .withColumn("observation_status", F.when(F.col("operation") == "D", "RETRACTED").otherwise("CURRENT"))
              .withColumn("value_std", F.when(F.col("operation") != "D", F.round(
                  F.col("quantity") * F.col("to_standard_factor"), 6)).cast(VOLUME)))

# %% [markdown]
# ## Source authority: satu angka berwenang per canonical key
#
# Kandidat **eligible** jika `report_status` sama dengan `eligible_status` dalam policy untuk source,
# scope negara, dan tanggal tersebut. Pemenang adalah kandidat eligible dengan prioritas tertinggi.
# Timestamp terbaru **bukan** dasar kewenangan.

# %%
policy = (spark.table("silver_ext.source_authority").filter(F.col("domain") == "PRODUCTION")
          .select(F.col("source_system").alias("p_source"), F.col("scope").alias("p_scope"), "priority",
                  "eligible_status", F.col("valid_from").alias("p_from"), F.col("valid_to").alias("p_to"),
                  "policy_version"))
policy_version = policy.select("policy_version").first()["policy_version"]
matched = candidates.join(policy, (F.col("source_system") == F.col("p_source"))
                          & F.col("p_scope").isin(F.col("country_id"), F.lit("ALL"))
                          & (F.col("report_date") >= F.col("p_from")) & (F.col("report_date") < F.col("p_to")), "left")
matched = (matched.withColumn("policy_rank", F.row_number().over(
               Window.partitionBy("source_system", "observation_id").orderBy(F.col("priority").asc_nulls_last())))
           .filter("policy_rank = 1")
           .withColumn("eligible", F.coalesce(F.col("eligible_status") == F.col("report_status"), F.lit(False))))

KEY = ["stream_id", "report_date", "commodity"]
by_key = Window.partitionBy(*KEY)
scored = (matched.withColumn("candidate_count", F.count("*").over(by_key))
          .withColumn("best_priority", F.min(F.when(F.col("eligible"), F.col("priority"))).over(by_key))).cache()
winners = scored.filter(F.col("eligible") & (F.col("priority") == F.col("best_priority")))
variants = winners.groupBy(*KEY).agg(F.countDistinct(F.concat_ws(
    "|", "observation_status", F.col("value_std").cast("string"))).alias("variants"))
selected = (winners.join(variants.filter("variants = 1").select(*KEY), KEY)
            .withColumn("pick", F.row_number().over(Window.partitionBy(*KEY).orderBy("source_system", "observation_id")))
            .filter("pick = 1").drop("pick"))
key_status = (scored.select(*KEY, "well_id", "candidate_count", "best_priority").dropDuplicates(KEY)
              .join(variants, KEY, "left")
              .withColumn("decision_status", F.when(F.col("best_priority").isNull(), "NO_AUTHORITATIVE_SOURCE")
                          .when(F.col("variants") > 1, "REVIEW_REQUIRED").otherwise("SELECTED")))
canonical_key = F.concat_ws("|", "stream_id", F.col("report_date").cast("string"), "commodity")
issues.append(issues_from(key_status.filter(F.col("decision_status") == "NO_AUTHORITATIVE_SOURCE"), "W01",
                          "production_observation", None, canonical_key))
issues.append(issues_from(key_status.filter(F.col("decision_status") == "REVIEW_REQUIRED"), "R07",
                          "production_observation", None, canonical_key))

# %%
candidate_json = scored.groupBy(*KEY).agg(F.to_json(F.sort_array(F.collect_list(F.struct(
    "source_system", "observation_id", "revision", "report_status", "eligible", "priority", "observation_status",
    F.col("value_std").cast("string").alias("value_std"))))).alias("candidates_json"))
decisions = (key_status.filter((F.col("candidate_count") > 1) | (F.col("decision_status") != "SELECTED"))
             .join(candidate_json, KEY)
             .join(selected.select(*KEY, F.col("source_system").alias("selected_source_system"),
                                   F.col("observation_id").alias("selected_observation_id"),
                                   F.col("revision").alias("selected_revision"),
                                   F.col("value_std").alias("selected_value_std"),
                                   F.col("report_status").alias("selected_report_status")), KEY, "left")
             .withColumn("decision_id", F.sha2(F.concat_ws("|", canonical_key, F.lit(policy_version)), 256))
             .withColumn("authority_policy_version", F.lit(policy_version))
             .withColumn("reason", F.when(F.col("decision_status") == "SELECTED", F.concat(
                 F.lit("Selected "), F.col("selected_source_system"), F.lit(" (priority "),
                 F.col("best_priority").cast("string"), F.lit(", "), F.col("selected_report_status"),
                 F.lit(") under "), F.lit(policy_version),
                 F.lit(". Other candidates were not eligible or had lower priority.")))
                 .when(F.col("decision_status") == "NO_AUTHORITATIVE_SOURCE",
                       F.lit(f"No candidate met the eligible status required by {policy_version}."))
                 .otherwise(F.lit("Equal-priority eligible sources disagree; owner review is required.")))
             .withColumnRenamed("report_date", "business_date")
             .withColumn("decided_in_batch", F.lit(p_batch_id)))
write_table(decisions, "ops.source_decision")

observation = (selected.select(
    "stream_id", "well_id", "field_id", "country_id", F.col("report_date").alias("business_date"), "commodity",
    "value_std", "standard_uom", "observation_status", "report_status",
    F.col("source_system").alias("selected_source_system"), F.col("observation_id").alias("selected_observation_id"),
    F.col("revision").alias("selected_revision"), F.col("change_seq").alias("selected_change_seq"),
    F.col("batch_id").alias("selected_batch_id"), "candidate_count")
    .withColumn("authority_policy_version", F.lit(policy_version))
    .withColumn("decision_status", F.lit("SELECTED")))
write_table(observation, "silver.production_observation")
scored.unpersist()

# %%
counts = save_issues(issues)
record_status(STAGE, "SILVER_PRODUCTION_DONE", "Authoritative production observations selected", counts=counts)
finish({"batch_id": p_batch_id, "stage": STAGE, "issues": counts,
        "observations": spark.table("silver.production_observation").count(),
        "decisions": spark.table("ops.source_decision").count()})
