# %% [markdown]
# # nb_04_conform_business - Target, biaya, downtime, dan loss allocation (Silver)
#
# Menggabungkan hasil **ETL Dataflow Gen2** (`stg_df.target_monthly`, `stg_df.cost_monthly`) dengan
# event maintenance dan loss allocation yang sudah berada di Bronze.
#
# Dataflow harus dijalankan untuk batch yang **sama** sebelum notebook ini dijalankan.

# %% [parameters]
p_batch_id = "B0"
p_run_id = "manual"
p_table_format = "delta"

# %%
%run nb_00_common

# %%
STAGE = "SILVER_BUSINESS"
ensure_schemas("silver", "silver_ext", "ops")
require_latest_batch()
issues = []
missing = [t for t in ["stg_df.target_monthly", "stg_df.cost_monthly"] if not table_exists(t)]
if missing:
    record_status(STAGE, "WAITING_FOR_DATAFLOW", f"Missing: {', '.join(missing)}")
    raise RuntimeError(f"Dataflow output not found: {missing}. Run the Dataflow Gen2 items for {p_batch_id}.")

target_stage = spark.table("stg_df.target_monthly")
cost_stage = spark.table("stg_df.cost_monthly")
for name, df in [("target_monthly", target_stage), ("cost_monthly", cost_stage)]:
    wrong = df.filter(F.col("batch_id") != p_batch_id)
    issues.append(issues_from(wrong, "B01", name, None, F.col("batch_id"),
                              f"Dataflow output belongs to another batch; rerun it with pBatchId={p_batch_id}"))
    if df.filter(F.col("batch_id") == p_batch_id).limit(1).count() == 0:
        issues.append(issues_from(spark.createDataFrame([(p_batch_id,)], "batch_id string"), "B01", name, None,
                                  F.col("batch_id"), f"No Dataflow rows for {p_batch_id}"))

# %% [markdown]
# ## Target harian dari target bulanan
#
# Target bulanan dibagi rata per hari; sisa pembulatan ditaruh pada hari terakhir sehingga total bulanan
# **tetap sama persis**. Target tidak pernah dibuat per well.

# %%
gas_divisor = (spark.table("silver.uom_conversion").filter(F.col("commodity") == "Gas")
               .select("boe_divisor").first()["boe_divisor"])
targets = target_stage.filter(F.col("batch_id") == p_batch_id)
issues.append(issues_from(targets.filter(F.col("dq_status") != "VALID"), "B02", "target_monthly", None,
                          F.concat_ws("|", "field_id", "commodity", F.col("month_start").cast("string"))))
monthly = (targets.filter(F.col("dq_status") == "VALID")
           .withColumn("monthly_target", F.col("target_value").cast(VOLUME))
           .withColumn("month_end", F.last_day("month_start"))
           .withColumn("days_in_month", F.dayofmonth("month_end").cast("decimal(10,0)")))
daily = (monthly.withColumn("business_date", F.explode(F.sequence("month_start", "month_end")))
         .withColumn("base", F.round(F.col("monthly_target") / F.col("days_in_month"), 6).cast(VOLUME))
         .withColumn("daily_target", F.when(F.col("business_date") == F.col("month_end"),
                                            F.col("monthly_target") - F.col("base") * (F.col("days_in_month") - 1))
                     .otherwise(F.col("base")).cast(VOLUME)))
target_daily = (daily.groupBy("field_id", "business_date", "scenario_id").agg(
        F.sum(F.when(F.col("commodity") == "Oil", F.col("daily_target"))).cast(VOLUME).alias("target_oil_bbl"),
        F.sum(F.when(F.col("commodity") == "Gas", F.col("daily_target"))).cast(VOLUME).alias("target_gas_mscf"))
    .withColumn("target_boe", (F.coalesce(F.col("target_oil_bbl"), F.lit(0)) + F.round(
        F.coalesce(F.col("target_gas_mscf"), F.lit(0)) / F.lit(gas_divisor).cast("decimal(10,0)"), 6)).cast(VOLUME))
    .withColumn("source_batch_id", F.lit(p_batch_id)))

# %% [markdown]
# ## Biaya operasi (USD) dari Dataflow

# %%
costs = cost_stage.filter(F.col("batch_id") == p_batch_id)
issues.append(issues_from(costs.filter(F.col("dq_status") != "VALID"), "B03", "cost_monthly", None,
                          F.col("cost_id")))
operating_cost = (costs.filter(F.col("dq_status") == "VALID").select(
    "cost_id", "field_id", "month_start", "cost_category", "currency_code",
    F.col("amount_local").cast(MONEY).alias("amount_local"),
    F.col("usd_per_unit").cast("decimal(18,9)").alias("usd_per_unit"),
    F.col("amount_usd").cast(MONEY).alias("amount_usd"), "closing_status")
    .withColumn("source_batch_id", F.lit(p_batch_id)))

# %% [markdown]
# ## Downtime event dan loss allocation

# %%
DOWNTIME_DDL = ("batch_id string, event_id string, incident_id string, equipment_id string, start_utc timestamp, "
                "end_utc timestamp, reason string, change_seq long")
LOSS_DDL = ("batch_id string, loss_id string, event_id string, well_ref string, business_date date, "
            "lost_oil_bbl decimal(19,6), lost_gas_mscf decimal(19,6), allocation_status string, change_seq long")
latest_by = lambda df, key: (df.withColumn("rank", F.row_number().over(Window.partitionBy(key).orderBy(F.desc("change_seq"))))
                             .filter("rank = 1").drop("rank"))
equipment = spark.table("silver.equipment").select("equipment_id", "facility_id")
facility = spark.table("silver.facility").select("facility_id", "field_id")
downtime = (latest_by(bronze_events("src_my__downtime_event", DOWNTIME_DDL), "event_id")
            .join(equipment, "equipment_id", "left").join(facility, "facility_id", "left"))
bad_downtime = downtime.filter(F.col("facility_id").isNull() | (F.col("end_utc") <= F.col("start_utc")))
issues.append(issues_from(bad_downtime, "B04", "downtime_event", None, F.col("event_id")))
downtime_event = (downtime.join(bad_downtime.select("event_id"), "event_id", "left_anti")
                  .withColumn("duration_hours", F.round((F.col("end_utc").cast("long") - F.col("start_utc").cast("long"))
                                                        .cast("decimal(18,0)") / F.lit(3600).cast("decimal(10,0)"), 3)
                              .cast("decimal(9,3)"))
                  .select("event_id", "incident_id", "equipment_id", "facility_id", "field_id", "start_utc", "end_utc",
                          "duration_hours", "reason", F.col("batch_id").alias("source_batch_id")))

# Loss allocation dibuat oleh tim operasi dari registry sumur SSOT, sehingga well_ref = golden well_id.
wells = spark.table("silver.well").select(F.col("well_id").alias("well_ref"), "well_id",
                                          F.col("field_id").alias("well_field_id"))
working_interest = spark.table("silver_ext.working_interest")
price = spark.table("silver_ext.price")
oil_price = price.filter(F.col("commodity") == "Oil").select("business_date", F.col("price_usd").alias("oil_price"))
gas_price = price.filter(F.col("commodity") == "Gas").select("business_date", F.col("price_usd").alias("gas_price"),
                                                            F.col("energy_factor").alias("gas_energy_factor"))
loss = (latest_by(bronze_events("src_my__loss_allocation", LOSS_DDL), "loss_id")
        .join(wells, "well_ref", "left")
        .join(downtime_event.select("event_id", "incident_id", "equipment_id", F.to_date("start_utc").alias("event_date")),
              "event_id", "left"))
bad_loss = loss.filter(F.col("well_id").isNull() | F.col("incident_id").isNull()
                       | (F.col("event_date") != F.col("business_date")))
issues.append(issues_from(bad_loss, "B05", "loss_allocation", None, F.col("loss_id")))
wi = working_interest.select(F.col("field_id").alias("wi_field"), "valid_from", "valid_to", "wi_share")
loss_allocation = (loss.join(bad_loss.select("loss_id"), "loss_id", "left_anti")
                   .join(wi, (F.col("well_field_id") == F.col("wi_field")) & (F.col("business_date") >= F.col("valid_from"))
                         & (F.col("business_date") < F.col("valid_to")), "left")
                   .join(oil_price, "business_date", "left").join(gas_price, "business_date", "left")
                   .withColumn("lost_boe_gross", (F.col("lost_oil_bbl") + F.round(
                       F.col("lost_gas_mscf") / F.lit(gas_divisor).cast("decimal(10,0)"), 6)).cast(VOLUME))
                   .withColumn("lost_boe_net_wi", F.round(F.col("lost_boe_gross") * F.col("wi_share"), 6).cast(VOLUME))
                   .withColumn("value_usd_gross", F.round(F.col("lost_oil_bbl") * F.col("oil_price")
                                                          + F.col("lost_gas_mscf") * F.col("gas_energy_factor")
                                                          * F.col("gas_price"), 4).cast(MONEY))
                   .withColumn("value_usd_net_wi", F.round(F.col("value_usd_gross") * F.col("wi_share"), 4).cast(MONEY))
                   .select("loss_id", "event_id", "incident_id", "equipment_id", "well_id",
                           F.col("well_field_id").alias("field_id"), "business_date", "lost_oil_bbl", "lost_gas_mscf",
                           "lost_boe_gross", "wi_share", "lost_boe_net_wi", "value_usd_gross", "value_usd_net_wi",
                           "allocation_status", F.col("batch_id").alias("source_batch_id")))

# %%
write_table(target_daily, "silver_ext.target_daily")
write_table(operating_cost, "silver_ext.operating_cost_monthly")
write_table(downtime_event, "silver.equipment_downtime_event")
write_table(loss_allocation, "silver_ext.loss_allocation")
counts = save_issues(issues)
record_status(STAGE, "SILVER_BUSINESS_DONE", "Targets, costs, downtime, and loss allocation conformed", counts=counts)
finish({"batch_id": p_batch_id, "stage": STAGE, "issues": counts,
        "target_days": spark.table("silver_ext.target_daily").count(),
        "loss_rows": spark.table("silver_ext.loss_allocation").count()})
