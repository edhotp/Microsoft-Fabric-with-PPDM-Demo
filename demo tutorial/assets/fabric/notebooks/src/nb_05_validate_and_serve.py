# %% [markdown]
# # nb_05_validate_and_serve - Quality gate, rekonsiliasi, dan kandidat publikasi
#
# Notebook ini memutuskan apakah batch boleh menjadi **kandidat publikasi SSOT**:
#
# * Semua tahap Silver harus selesai untuk batch ini.
# * Tidak boleh ada issue `BLOCKER`. Jika ada, status `QUALITY_FAILED` dicatat dan notebook **gagal**
#   (pipeline berhenti; Gold tetap pada publikasi sebelumnya).
# * Fakta serving direkonsiliasi dengan Silver sebelum ditulis.
#
# Output: tabel `serve.*` per `PublicationId` dan manifest `serve.publication_candidate`.
# Publikasi ke Gold tetap memerlukan **persetujuan bisnis** di Warehouse.

# %% [parameters]
p_batch_id = "B0"
p_run_id = "manual"
p_table_format = "delta"

# %%
%run nb_00_common

# %%
STAGE = "SERVE"
ensure_schemas("serve", "ops")
latest = require_latest_batch()
publication_id = f"PUB-{p_batch_id}"
required = {"SILVER_MASTER": "SILVER_MASTER_DONE", "SILVER_PRODUCTION": "SILVER_PRODUCTION_DONE",
            "SILVER_BUSINESS": "SILVER_BUSINESS_DONE"}
done = {r["Stage"]: r["Status"] for r in
        spark.table("ops.batch_status").filter(F.col("BatchId") == p_batch_id).collect()}
not_ready = [stage for stage, status in required.items() if done.get(stage) != status]
if not_ready:
    record_status("VALIDATE", "NOT_READY", f"Stages not completed: {', '.join(not_ready)}")
    raise RuntimeError(f"Run these stages for {p_batch_id} first: {not_ready}")

# %% [markdown]
# ## Quality gate

# %%
issue_rows = spark.table("ops.dq_issue").filter(F.col("BatchId") == p_batch_id)
counts = {r["Severity"]: r["n"] for r in issue_rows.groupBy("Severity").agg(F.count("*").alias("n")).collect()}
blockers = {r["RuleId"]: r["n"] for r in issue_rows.filter(F.col("Severity") == "BLOCKER")
            .groupBy("RuleId").agg(F.count("*").alias("n")).collect()}
if blockers:
    detail = ", ".join(f"{rule}={n}" for rule, n in sorted(blockers.items()))
    record_status("VALIDATE", "QUALITY_FAILED", f"Blocking issues: {detail}", publication_id, counts)
    raise RuntimeError(f"QUALITY_FAILED for {p_batch_id}: {detail}. Gold keeps the previous approved publication.")
record_status("VALIDATE", "QUALITY_PASSED", "No blocking issues", publication_id, counts)

# %% [markdown]
# ## Dimensi dengan surrogate key stabil

# %%
silver = {name: spark.table(name) for name in [
    "silver.country", "silver.field", "silver.facility", "silver.equipment", "silver.well", "silver.wellbore",
    "silver.well_completion", "silver.reporting_stream", "silver.well_alias", "silver.uom_conversion",
    "silver.production_observation", "silver.equipment_downtime_event", "silver_ext.working_interest",
    "silver_ext.target_daily", "silver_ext.operating_cost_monthly", "silver_ext.loss_allocation"]}
gas_divisor = (silver["silver.uom_conversion"].filter(F.col("commodity") == "Gas")
               .select("boe_divisor").first()["boe_divisor"])
field = silver["silver.field"].join(silver["silver.country"].select("country_id", "country_name"), "country_id")
facility_by_field = silver["silver.facility"].groupBy("field_id").agg(F.min("facility_id").alias("facility_id"))

dim_asset = field.join(facility_by_field, "field_id", "left").select(
    stable_key("FIELD", "field_id").alias("AssetKey"), F.col("field_id").alias("AssetId"),
    F.col("field_name").alias("AssetName"), F.col("country_id").alias("CountryCode"),
    F.col("country_name").alias("CountryName"), F.col("facility_id").alias("FacilityId"))

wellbore, completion = silver["silver.wellbore"], silver["silver.well_completion"]
wellbore_counts = wellbore.groupBy("well_id").agg(F.count("*").cast("int").alias("WellboreCount"))
completion_counts = (completion.join(wellbore.select("wellbore_id", "well_id"), "wellbore_id")
                     .groupBy("well_id").agg(F.count("*").cast("int").alias("CompletionCount")))
aliases = silver["silver.well_alias"].groupBy("well_id").agg(F.concat_ws(", ", F.sort_array(F.collect_list(
    F.concat("source_system", F.lit(":"), "source_well_id")))).alias("AliasList"))
dim_well = (silver["silver.well"].join(silver["silver.reporting_stream"].select("well_id", "stream_id"), "well_id")
            .join(field.select("field_id", "country_id"), "field_id")
            .join(wellbore_counts, "well_id", "left").join(completion_counts, "well_id", "left")
            .join(aliases, "well_id", "left")
            .select(stable_key("WELL", "well_id").alias("WellKey"), F.col("well_id").alias("WellId"),
                    F.col("well_name").alias("WellName"), stable_key("FIELD", "field_id").alias("AssetKey"),
                    F.col("field_id").alias("AssetId"), F.col("country_id").alias("CountryCode"),
                    F.col("stream_id").alias("StreamId"), F.coalesce("WellboreCount", F.lit(0)).alias("WellboreCount"),
                    F.coalesce("CompletionCount", F.lit(0)).alias("CompletionCount"), "AliasList",
                    F.col("well_status").alias("WellStatus")))

dim_equipment = (silver["silver.equipment"].join(silver["silver.facility"].select("facility_id", "field_id"), "facility_id")
                 .join(field.select("field_id", "country_id"), "field_id")
                 .select(stable_key("EQUIPMENT", "equipment_id").alias("EquipmentKey"),
                         F.col("equipment_id").alias("EquipmentId"), F.col("equipment_name").alias("EquipmentName"),
                         F.col("equipment_type").alias("EquipmentType"), F.col("facility_id").alias("FacilityId"),
                         stable_key("FIELD", "field_id").alias("AssetKey"), F.col("field_id").alias("AssetId"),
                         F.col("country_id").alias("CountryCode")))

downtime, loss = silver["silver.equipment_downtime_event"], silver["silver_ext.loss_allocation"]
loss_incidents = loss.select("incident_id").distinct().withColumn("has_loss", F.lit(True))
dim_incident = (downtime.groupBy("incident_id").agg(F.count("*").cast("int").alias("EventCount"))
                .join(loss_incidents, "incident_id", "left")
                .select(stable_key("INCIDENT", "incident_id").alias("IncidentKey"), F.col("incident_id").alias("IncidentId"),
                        F.when(F.col("has_loss"), "PRODUCTION_LOSS").otherwise("MAINTENANCE_NO_LOSS").alias("IncidentCategory"),
                        "EventCount"))

targets = silver["silver_ext.target_daily"]
dim_scenario = targets.select("scenario_id").distinct().select(
    stable_key("SCENARIO", "scenario_id").alias("ScenarioKey"), F.col("scenario_id").alias("ScenarioId"),
    F.lit("Approved RKAP target (synthetic)").alias("ScenarioName"))
costs = silver["silver_ext.operating_cost_monthly"]
dim_cost_category = costs.select("cost_category").distinct().select(
    stable_key("COSTCAT", "cost_category").alias("CostCategoryKey"), F.col("cost_category").alias("CostCategory"))

period_start, period_end = latest["PeriodStart"], latest["PeriodEnd"]
bounds = targets.agg(F.min("business_date").alias("lo"), F.max("business_date").alias("hi")).first()
first_day = min(d for d in [period_start, bounds["lo"]] if d is not None)
last_day = max(d for d in [period_end, bounds["hi"]] if d is not None)
dim_date = (spark.createDataFrame([(first_day, last_day)], "s date, e date")
            .select(F.explode(F.sequence("s", "e")).alias("Date"))
            .select(date_key("Date").alias("DateKey"), "Date", F.year("Date").alias("Year"),
                    F.month("Date").alias("MonthNumber"), F.date_format("Date", "MMM").alias("MonthName"),
                    F.date_format("Date", "yyyy-MM").alias("YearMonth"), F.trunc("Date", "month").alias("MonthStart"),
                    F.dayofmonth("Date").alias("DayOfMonth"), F.dayofmonth(F.last_day("Date")).alias("DaysInMonth")))

# %% [markdown]
# ## Fakta produksi harian (grain: reporting stream x hari)
#
# Grid lengkap stream x hari dibuat dulu sehingga hari tanpa laporan terlihat sebagai *tidak lengkap*,
# bukan nol produksi. BOE = oil + gas / 6 (faktor dari registry satuan). Net WI = gross x WI as-of date.

# %%
observations = silver["silver.production_observation"]
current = F.col("observation_status") == "CURRENT"
daily = observations.groupBy("stream_id", "business_date").agg(
    *[F.sum(F.when(current & (F.col("commodity") == c), F.col("value_std"))).cast(VOLUME).alias(alias)
      for c, alias in [("Oil", "OilBbl"), ("Gas", "GasMscf"), ("Water", "WaterBbl")]],
    F.sum(F.when(current, 1).otherwise(0)).cast("int").alias("ObservationCount"),
    F.sum(F.when(~current, 1).otherwise(0)).cast("int").alias("RetractedCount"),
    F.concat_ws(",", F.sort_array(F.collect_set("selected_source_system"))).alias("SelectedSources"),
    F.max("selected_revision").cast("int").alias("MaxRevision"))
grid = (dim_well.select("StreamId", "WellKey", "AssetKey", "AssetId")
        .crossJoin(spark.createDataFrame([(period_start, period_end)], "s date, e date")
                   .select(F.explode(F.sequence("s", "e")).alias("BusinessDate"))))
wi = silver["silver_ext.working_interest"].select("field_id", "valid_from", "valid_to", "wi_share")
fact_production = (grid.join(daily, (F.col("StreamId") == F.col("stream_id")) & (F.col("BusinessDate") == F.col("business_date")), "left")
                   .join(wi, (F.col("AssetId") == F.col("field_id")) & (F.col("BusinessDate") >= F.col("valid_from"))
                         & (F.col("BusinessDate") < F.col("valid_to")), "left")
                   .withColumn("ObservationCount", F.coalesce("ObservationCount", F.lit(0)))
                   .withColumn("RetractedCount", F.coalesce("RetractedCount", F.lit(0)))
                   .withColumn("GrossBoe", F.when(F.col("OilBbl").isNull() & F.col("GasMscf").isNull(), F.lit(None))
                               .otherwise(F.coalesce("OilBbl", F.lit(0)) + F.round(F.coalesce("GasMscf", F.lit(0))
                                          / F.lit(gas_divisor).cast("decimal(10,0)"), 6)).cast(VOLUME))
                   .withColumn("NetWiBoe", F.round(F.col("GrossBoe") * F.col("wi_share"), 6).cast(VOLUME))
                   .select(date_key("BusinessDate").alias("DateKey"), "WellKey", "AssetKey", "StreamId", "OilBbl",
                           "GasMscf", "WaterBbl", "GrossBoe", F.col("wi_share").alias("WiShare"), "NetWiBoe",
                           "ObservationCount", F.lit(3).alias("ExpectedObservationCount"),
                           F.when(F.col("ObservationCount") == 3, 1).otherwise(0).alias("IsComplete"),
                           "RetractedCount", "SelectedSources", "MaxRevision"))

fact_target = targets.select(date_key("business_date").alias("DateKey"), stable_key("FIELD", "field_id").alias("AssetKey"),
                             stable_key("SCENARIO", "scenario_id").alias("ScenarioKey"),
                             F.col("target_oil_bbl").alias("TargetOilBbl"), F.col("target_gas_mscf").alias("TargetGasMscf"),
                             F.col("target_boe").alias("TargetBoe"))
fact_cost = costs.select(date_key("month_start").alias("MonthDateKey"), stable_key("FIELD", "field_id").alias("AssetKey"),
                         stable_key("COSTCAT", "cost_category").alias("CostCategoryKey"),
                         F.col("currency_code").alias("CurrencyCode"), F.col("amount_local").alias("AmountLocal"),
                         F.col("usd_per_unit").alias("UsdPerUnit"), F.col("amount_usd").alias("AmountUsd"),
                         F.col("closing_status").alias("ClosingStatus"), F.col("cost_id").alias("CostId"))
fact_downtime = downtime.select(F.col("event_id").alias("EventId"), stable_key("INCIDENT", "incident_id").alias("IncidentKey"),
                                stable_key("EQUIPMENT", "equipment_id").alias("EquipmentKey"),
                                stable_key("FIELD", "field_id").alias("AssetKey"), date_key("start_utc").alias("StartDateKey"),
                                F.col("start_utc").alias("StartUtc"), F.col("end_utc").alias("EndUtc"),
                                F.col("duration_hours").alias("DurationHours"), F.col("reason").alias("Reason"))
fact_loss = loss.select(F.col("loss_id").alias("LossId"), date_key("business_date").alias("DateKey"),
                        stable_key("WELL", "well_id").alias("WellKey"), stable_key("FIELD", "field_id").alias("AssetKey"),
                        stable_key("INCIDENT", "incident_id").alias("IncidentKey"),
                        stable_key("EQUIPMENT", "equipment_id").alias("EquipmentKey"), F.col("event_id").alias("EventId"),
                        F.col("lost_oil_bbl").alias("LostOilBbl"), F.col("lost_gas_mscf").alias("LostGasMscf"),
                        F.col("lost_boe_gross").alias("LostBoeGross"), F.col("wi_share").alias("WiShare"),
                        F.col("lost_boe_net_wi").alias("LostBoeNetWi"), F.col("value_usd_gross").alias("ValueUsdGross"),
                        F.col("value_usd_net_wi").alias("ValueUsdNetWi"))
master_wellbore = wellbore.select(F.col("wellbore_id").alias("WellboreId"), F.col("well_id").alias("WellId"),
                                  F.col("wellbore_name").alias("WellboreName"))
master_completion = completion.select(F.col("completion_id").alias("CompletionId"), F.col("wellbore_id").alias("WellboreId"),
                                      F.col("stream_id").alias("StreamId"), F.col("completion_name").alias("CompletionName"))
source_decision = spark.table("ops.source_decision").select(
    F.col("decision_id").alias("DecisionId"),
    F.concat_ws("|", "stream_id", F.col("business_date").cast("string"), "commodity").alias("CanonicalKey"),
    F.col("stream_id").alias("StreamId"), F.col("well_id").alias("WellId"), F.col("business_date").alias("BusinessDate"),
    F.col("commodity").alias("Commodity"), F.col("candidate_count").cast("int").alias("CandidateCount"),
    F.col("decision_status").alias("DecisionStatus"), F.col("selected_source_system").alias("SelectedSourceSystem"),
    F.col("selected_observation_id").alias("SelectedObservationId"), F.col("selected_revision").alias("SelectedRevision"),
    F.col("selected_value_std").alias("SelectedValueStd"), F.col("reason").alias("Reason"),
    F.col("candidates_json").alias("CandidatesJson"), F.col("authority_policy_version").alias("AuthorityPolicyVersion"))

# %% [markdown]
# ## Rekonsiliasi sebelum menjadi kandidat

# %%
def total(df, column, condition=None):
    frame = df.filter(condition) if condition is not None else df
    value = frame.agg(F.sum(column).alias("v")).first()["v"]
    return value if value is not None else 0


in_period = (F.col("business_date") >= F.lit(period_start)) & (F.col("business_date") <= F.lit(period_end))
checks = {
    "fact_rows": (fact_production.count(), dim_well.count() * ((period_end - period_start).days + 1)),
    "oil": (total(fact_production, "OilBbl"), total(observations, "value_std", current & in_period & (F.col("commodity") == "Oil"))),
    "gas": (total(fact_production, "GasMscf"), total(observations, "value_std", current & in_period & (F.col("commodity") == "Gas"))),
    "water": (total(fact_production, "WaterBbl"), total(observations, "value_std", current & in_period & (F.col("commodity") == "Water"))),
    "loss_boe": (total(fact_loss, "LostBoeGross"), total(loss, "lost_boe_gross")),
    "target_oil": (total(fact_target, "TargetOilBbl"),
                   total(spark.table("stg_df.target_monthly").filter((F.col("batch_id") == p_batch_id) & (F.col("commodity") == "Oil"))
                         .withColumn("v", F.col("target_value").cast(VOLUME)), "v")),
}
for name, df, key in [("dim_asset", dim_asset, "AssetKey"), ("dim_well", dim_well, "WellKey"),
                      ("dim_equipment", dim_equipment, "EquipmentKey"), ("dim_incident", dim_incident, "IncidentKey")]:
    checks[f"{name}_unique"] = (df.count(), df.select(key).distinct().count())
failed = {name: values for name, values in checks.items() if values[0] != values[1]}
if failed:
    record_status("VALIDATE", "RECONCILIATION_FAILED", json.dumps(failed, default=str)[:4000], publication_id, counts)
    raise RuntimeError(f"Reconciliation failed: {failed}")

# %% [markdown]
# ## Tulis kandidat publikasi (idempoten per PublicationId)

# %%
serve_tables = {
    "serve.dim_date": dim_date, "serve.dim_asset": dim_asset, "serve.dim_well": dim_well,
    "serve.dim_equipment": dim_equipment, "serve.dim_incident": dim_incident, "serve.dim_scenario": dim_scenario,
    "serve.dim_cost_category": dim_cost_category, "serve.fact_production_daily": fact_production,
    "serve.fact_target_daily": fact_target, "serve.fact_operating_cost_monthly": fact_cost,
    "serve.fact_downtime_event": fact_downtime, "serve.fact_loss_allocation": fact_loss,
    "serve.master_wellbore": master_wellbore, "serve.master_completion": master_completion,
    "serve.source_decision": source_decision,
}
row_counts = []
condition = f"PublicationId = {literal(publication_id)}"
for name, df in serve_tables.items():
    frame = df.withColumn("PublicationId", F.lit(publication_id))
    replace_where(frame, name, condition)
    row_counts.append((publication_id, name.split(".")[1], spark.table(name).filter(condition).count()))

control_totals = {
    "GrossBoe": str(total(fact_production, "GrossBoe")), "NetWiBoe": str(total(fact_production, "NetWiBoe")),
    "TargetBoe": str(total(fact_target, "TargetBoe")), "OpexUsd": str(total(fact_cost, "AmountUsd")),
    "LostBoeGross": str(total(fact_loss, "LostBoeGross")), "ValueUsdGross": str(total(fact_loss, "ValueUsdGross")),
}
policy_version = spark.table("silver_ext.source_authority").select("policy_version").first()["policy_version"]
silver_versions = {name: table_version(name) for name in silver}
candidate = spark.createDataFrame([(
    publication_id, p_batch_id, latest["ParentBatchId"], latest["DatasetVersion"], policy_version, MAPPING_VERSION,
    KPI_CONTRACT_VERSION, silver["silver.uom_conversion"].select("factor_version").first()["factor_version"],
    p_batch_id, period_start, period_end, json.dumps(silver_versions), json.dumps(control_totals),
    int(counts.get("BLOCKER", 0)), int(counts.get("WARNING", 0)), int(counts.get("INFO", 0)), RUN_ID, utc_now())],
    "PublicationId string, BatchId string, ParentBatchId string, DatasetVersion string, AuthorityPolicyVersion string, "
    "MappingVersion string, KpiContractVersion string, UomFactorVersion string, MasterSnapshotBatchId string, "
    "PeriodStart date, PeriodEnd date, SilverVersionsJson string, ControlTotalsJson string, BlockerCount int, "
    "WarningCount int, InfoCount int, RunId string, CreatedAtUtc timestamp")
replace_where(candidate, "serve.publication_candidate", condition)
replace_where(spark.createDataFrame(row_counts, "PublicationId string, TableName string, ExpectedRows long"),
              "serve.publication_row_count", condition)
record_status(STAGE, "CANDIDATE_READY", "Awaiting Warehouse staging and business approval", publication_id, counts)

# %%
finish({"batch_id": p_batch_id, "publication_id": publication_id, "status": "CANDIDATE_READY",
        "control_totals": control_totals, "issues": counts})
