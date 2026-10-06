# %% [markdown]
# # nb_06_prepare_ai_serving - Proyeksi SSOT untuk ontology dan data agent
#
# Jalankan **setelah** publikasi Gold disetujui dan berhasil (`ops.usp_publish_publication`).
# Notebook ini membaca kandidat serving untuk `p_publication_id` yang **sama** dengan Gold dan menulis
# tabel terkelola `ai.*` di Lakehouse AI. Tabel AI tidak menghitung KPI baru dan tidak diedit manual.
#
# **Lakehouse default:** `lh_piep_ai` (schema-enabled) di workspace AI.

# %% [parameters]
p_publication_id = "PUB-B0"
p_source_prefix = "`ws-piep-ppdm-demo`.`lh_piep_core`.`serve`"
p_run_id = "manual"
p_table_format = "delta"

# %%
%run nb_00_common

# %%
p_batch_id = p_publication_id.replace("PUB-", "", 1)
ensure_schemas("ai")
pub = literal(p_publication_id)


def serve(table):
    return spark.table(f"{p_source_prefix}.{table}").filter(f"PublicationId = {pub}").drop("PublicationId")


candidate_rows = serve("publication_candidate").collect()
if len(candidate_rows) != 1:
    raise RuntimeError(f"Publication {p_publication_id} has no serving candidate in {p_source_prefix}.")
candidate = candidate_rows[0]
as_of = utc_now()


def stamp(df):
    return (df.withColumn("business_publication_id", F.lit(p_publication_id))
            .withColumn("kpi_contract_version", F.lit(candidate["KpiContractVersion"]))
            .withColumn("as_of_utc", F.lit(as_of).cast("timestamp")))

# %% [markdown]
# ## Entity tables (kunci string, tanpa karakter khusus pada nama kolom)

# %%
asset, well, equipment = serve("dim_asset"), serve("dim_well"), serve("dim_equipment")
incident, downtime, loss = serve("dim_incident"), serve("fact_downtime_event"), serve("fact_loss_allocation")
production = serve("fact_production_daily")
dates = serve("dim_date").select("DateKey", "Date")
well_keys = well.select("WellKey", "WellId")
equipment_keys = equipment.select("EquipmentKey", "EquipmentId")
incident_keys = incident.select("IncidentKey", "IncidentId")

tables = {
    "ai.country": asset.select(F.col("CountryCode").alias("country_id"), F.col("CountryName").alias("country_name"))
                     .distinct(),
    "ai.asset": asset.select(F.col("AssetId").alias("asset_id"), F.col("AssetName").alias("asset_name"),
                             F.col("CountryCode").alias("country_id"), F.col("FacilityId").alias("facility_id")),
    "ai.facility": asset.select(F.col("FacilityId").alias("facility_id"), F.col("AssetId").alias("asset_id")),
    "ai.equipment": equipment.select(F.col("EquipmentId").alias("equipment_id"), F.col("EquipmentName").alias("equipment_name"),
                                     F.col("EquipmentType").alias("equipment_type"), F.col("FacilityId").alias("facility_id"),
                                     F.col("AssetId").alias("asset_id"), F.col("CountryCode").alias("country_id")),
    "ai.well": well.select(F.col("WellId").alias("well_id"), F.col("WellName").alias("well_name"),
                           F.col("AssetId").alias("asset_id"), F.col("CountryCode").alias("country_id"),
                           F.col("StreamId").alias("stream_id"), F.col("WellboreCount").alias("wellbore_count"),
                           F.col("CompletionCount").alias("completion_count"), F.col("AliasList").alias("alias_list"),
                           F.col("WellStatus").alias("well_status")),
    "ai.wellbore": serve("master_wellbore").select(F.col("WellboreId").alias("wellbore_id"), F.col("WellId").alias("well_id"),
                                                   F.col("WellboreName").alias("wellbore_name")),
    "ai.completion": serve("master_completion").select(F.col("CompletionId").alias("completion_id"),
                                                       F.col("WellboreId").alias("wellbore_id"),
                                                       F.col("StreamId").alias("stream_id"),
                                                       F.col("CompletionName").alias("completion_name")),
    "ai.reporting_stream": well.select(F.col("StreamId").alias("stream_id"), F.col("WellId").alias("well_id"),
                                       F.col("AssetId").alias("asset_id")),
    "ai.reporting_stream_daily": production.join(dates, "DateKey").join(well_keys, "WellKey").select(
        F.concat_ws("|", "StreamId", F.col("Date").cast("string")).alias("stream_daily_id"),
        F.col("StreamId").alias("stream_id"), F.col("WellId").alias("well_id"), F.col("Date").alias("business_date"),
        F.col("OilBbl").alias("oil_bbl"), F.col("GasMscf").alias("gas_mscf"), F.col("WaterBbl").alias("water_bbl"),
        F.col("GrossBoe").alias("gross_boe"), F.col("NetWiBoe").alias("net_wi_boe"),
        F.col("IsComplete").alias("is_complete")),
    "ai.incident": downtime.join(incident_keys, "IncidentKey").join(equipment_keys, "EquipmentKey")
                           .groupBy("IncidentId").agg(F.min("EquipmentId").alias("equipment_id"),
                                                      F.count("*").cast("int").alias("event_count"),
                                                      F.sum("DurationHours").alias("equipment_downtime_hours"),
                                                      F.min("StartUtc").alias("first_start_utc"))
                           .join(incident.select("IncidentId", "IncidentCategory"), "IncidentId")
                           .select(F.col("IncidentId").alias("incident_id"), "equipment_id",
                                   F.col("IncidentCategory").alias("incident_category"), "event_count",
                                   "equipment_downtime_hours", "first_start_utc"),
    "ai.loss_allocation": loss.join(dates, "DateKey").join(well_keys, "WellKey").join(incident_keys, "IncidentKey")
                              .join(equipment_keys, "EquipmentKey").select(
        F.col("LossId").alias("loss_id"), F.col("IncidentId").alias("incident_id"), F.col("EventId").alias("event_id"),
        F.col("WellId").alias("well_id"), F.col("EquipmentId").alias("equipment_id"), F.col("Date").alias("business_date"),
        F.col("LostOilBbl").alias("lost_oil_bbl"), F.col("LostGasMscf").alias("lost_gas_mscf"),
        F.col("LostBoeGross").alias("lost_boe_gross"), F.col("LostBoeNetWi").alias("lost_boe_net_wi"),
        F.col("ValueUsdGross").alias("value_usd_gross"), F.col("ValueUsdNetWi").alias("value_usd_net_wi")),
    "ai.source_decision": serve("source_decision").select(
        F.col("DecisionId").alias("decision_id"), F.col("StreamId").alias("stream_id"), F.col("WellId").alias("well_id"),
        F.col("BusinessDate").alias("business_date"), F.col("Commodity").alias("commodity"),
        F.col("DecisionStatus").alias("decision_status"), F.col("SelectedSourceSystem").alias("selected_source_system"),
        F.col("SelectedValueStd").alias("selected_value_std"), F.col("CandidateCount").alias("candidate_count"),
        F.col("Reason").alias("reason"), F.col("CandidatesJson").alias("candidates_json"),
        F.col("AuthorityPolicyVersion").alias("authority_policy_version")),
    "ai.publication": spark.createDataFrame([(
        p_publication_id, candidate["BatchId"], candidate["DatasetVersion"], candidate["AuthorityPolicyVersion"],
        candidate["MappingVersion"], candidate["PeriodStart"], candidate["PeriodEnd"],
        json.loads(candidate["ControlTotalsJson"])["GrossBoe"], json.loads(candidate["ControlTotalsJson"])["NetWiBoe"])],
        "publication_id string, batch_id string, dataset_version string, authority_policy_version string, "
        "mapping_version string, period_start date, period_end date, gross_boe_total string, net_wi_boe_total string"),
}

# %%
counts = {}
for name, df in tables.items():
    write_table(stamp(df), name)
    counts[name] = spark.table(name).count()
finish({"publication_id": p_publication_id, "status": "AI_SERVING_READY", "tables": counts})
