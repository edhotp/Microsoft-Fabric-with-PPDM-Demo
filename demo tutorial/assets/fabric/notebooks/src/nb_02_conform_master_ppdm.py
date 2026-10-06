# %% [markdown]
# # nb_02_conform_master_ppdm - Golden master PPDM-aligned (Silver)
#
# Membentuk master kanonis dari snapshot registry batch saat ini: field, well, wellbore,
# completion, reporting stream, alias, satuan, working interest, dan source authority.
# Nama tabel **disejajarkan** dengan konsep PPDM (*PPDM-aligned*), bukan salinan skema resmi.
#
# Parameter `p_fail_after_bronze=true` dipakai untuk latihan kegagalan **F1**.

# %% [parameters]
p_batch_id = "B0"
p_run_id = "manual"
p_table_format = "delta"
p_fail_after_bronze = "false"

# %%
%run nb_00_common

# %%
STAGE = "SILVER_MASTER"
ensure_schemas("silver", "silver_ext", "ops")
if str(p_fail_after_bronze).strip().lower() == "true":
    record_status(STAGE, "FAILED_DRILL", "F1 drill: Bronze is committed. Rerun with p_fail_after_bronze=false.")
    raise RuntimeError("F1 failure drill: stopping after Bronze. Rerun the same batch with p_fail_after_bronze=false.")
require_latest_batch()

# %% [markdown]
# ## Register alignment PPDM
#
# Status: `ALIGNED_TO_PUBLIC_CONCEPT` (mengikuti konsep publik PPDM), `DEMO_EXTENSION`
# (kebutuhan bisnis demo), atau `REQUIRES_DOMAIN_VALIDATION`.

# %%
ALIGNMENT = [
    ("silver.country", "ref.country", "Area / country", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.business_associate", "ref.business_associate", "Business associate (operator)", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.field", "ref.field", "Field / area", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.facility", "ref.facility", "Facility", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.equipment", "ref.equipment", "Equipment", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.well", "ref.well", "Well (What Is A Well? definition)", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.wellbore", "ref.wellbore", "Wellbore", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.well_completion", "ref.well_completion", "Wellbore completion", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.reporting_stream", "ref.reporting_stream", "Well reporting stream", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.well_alias", "ref.well_alias", "Well identifier crosswalk", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.uom_conversion", "ref.uom_conversion", "Unit of measure reference", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.production_observation", "src_*.production", "Production volume per reporting stream", "ALIGNED_TO_PUBLIC_CONCEPT"),
    ("silver.equipment_downtime_event", "src_my.downtime_event", "Equipment downtime event", "REQUIRES_DOMAIN_VALIDATION"),
    ("silver_ext.working_interest", "ref.working_interest", "Working interest (simplified, not entitlement)", "DEMO_EXTENSION"),
    ("silver_ext.source_authority", "ref.source_authority", "SSOT source authority policy", "DEMO_EXTENSION"),
    ("silver_ext.target_daily", "ref.target_monthly", "RKAP target allocated to days", "DEMO_EXTENSION"),
    ("silver_ext.operating_cost_monthly", "ref.operating_cost", "Operating cost after FX", "DEMO_EXTENSION"),
    ("silver_ext.loss_allocation", "src_my.loss_allocation", "Approved production loss allocation", "DEMO_EXTENSION"),
    ("silver_ext.price", "ref.price", "Indicative price deck", "DEMO_EXTENSION"),
]
alignment = spark.createDataFrame(
    [(t, s, c, st, MAPPING_VERSION, p_batch_id) for t, s, c, st in ALIGNMENT],
    "SilverTable string, SourceTable string, PpdmConcept string, AlignmentStatus string, "
    "MappingVersion string, MasterSnapshotBatchId string")
write_table(alignment, "ops.ppdm_alignment")

# %% [markdown]
# ## Konformasi registry ke Silver

# %%
def conform(entity, columns):
    return (snapshot(entity).select(*columns).dropDuplicates()
            .withColumn("master_snapshot_batch_id", F.lit(p_batch_id))
            .withColumn("mapping_version", F.lit(MAPPING_VERSION)))


country = conform("ref__country", ["country_id", "country_name"])
business_associate = conform("ref__business_associate", ["ba_id", "ba_name", "ba_role"])
field = conform("ref__field", ["field_id", "field_name", "country_id"])
facility = conform("ref__facility", ["facility_id", "facility_name", "field_id"])
equipment = conform("ref__equipment", ["equipment_id", "equipment_name", "equipment_type", "facility_id"])
well = conform("ref__well", ["well_id", "well_name", "field_id", "well_status"])
wellbore = conform("ref__wellbore", ["wellbore_id", "wellbore_name", "well_id"])
completion = conform("ref__well_completion", ["completion_id", "completion_name", "wellbore_id", "stream_id"])
stream = conform("ref__reporting_stream", ["stream_id", "stream_name", "well_id"])
alias = conform("ref__well_alias", ["source_system", "source_well_id", "well_id"])
uom = conform("ref__uom_conversion", ["commodity", "uom", "standard_uom", "to_standard_factor",
                                      "boe_divisor", "factor_version"])
working_interest = conform("ref__working_interest", ["field_id", "valid_from", "valid_to", "operator_ba_id",
                                                     "wi_share", "agreement_ref"])
authority = conform("ref__source_authority", ["policy_version", "domain", "source_system", "scope", "priority",
                                              "eligible_status", "valid_from", "valid_to", "owner_role"])
price = conform("ref__price", ["business_date", "commodity", "price_usd", "price_unit", "energy_factor"])

# %% [markdown]
# ## Pemeriksaan integritas master
#
# Delta tidak menegakkan PK/FK. Notebook ini menjalankan uniqueness, referential integrity,
# dan temporal integrity. Pelanggaran dicatat sebagai `BLOCKER`; publikasi ditahan di nb_05.

# %%
issues = []
for name, df, keys in [("country", country, ["country_id"]), ("business_associate", business_associate, ["ba_id"]),
                       ("field", field, ["field_id"]), ("facility", facility, ["facility_id"]),
                       ("equipment", equipment, ["equipment_id"]), ("well", well, ["well_id"]),
                       ("wellbore", wellbore, ["wellbore_id"]), ("well_completion", completion, ["completion_id"]),
                       ("reporting_stream", stream, ["stream_id"]),
                       ("well_alias", alias, ["source_system", "source_well_id"]),
                       ("uom_conversion", uom, ["commodity", "uom"]),
                       ("working_interest", working_interest, ["field_id", "valid_from"])]:
    duplicates = df.groupBy(*keys).count().filter("count > 1")
    issues.append(issues_from(duplicates, "M01", name, None, F.concat_ws("|", *keys)))

for name, child, child_col, parent, parent_col in [
        ("field", field, "country_id", country, "country_id"),
        ("facility", facility, "field_id", field, "field_id"),
        ("equipment", equipment, "facility_id", facility, "facility_id"),
        ("well", well, "field_id", field, "field_id"),
        ("wellbore", wellbore, "well_id", well, "well_id"),
        ("well_completion", completion, "wellbore_id", wellbore, "wellbore_id"),
        ("well_completion", completion, "stream_id", stream, "stream_id"),
        ("reporting_stream", stream, "well_id", well, "well_id"),
        ("well_alias", alias, "well_id", well, "well_id"),
        ("working_interest", working_interest, "field_id", field, "field_id"),
        ("working_interest", working_interest, "operator_ba_id", business_associate, "ba_id")]:
    orphans = child.join(parent.select(F.col(parent_col).alias(child_col)), child_col, "left_anti")
    issues.append(issues_from(orphans, "M02", name, None, F.col(child_col),
                              f"{name}.{child_col} has no matching parent"))

invalid_wi = working_interest.filter((F.col("wi_share") <= 0) | (F.col("wi_share") > 1)
                                     | (F.col("valid_from") >= F.col("valid_to")))
a, b = working_interest.alias("a"), working_interest.alias("b")
overlaps = (a.join(b, (F.col("a.field_id") == F.col("b.field_id")) & (F.col("a.valid_from") < F.col("b.valid_from"))
                   & (F.col("b.valid_from") < F.col("a.valid_to")))
            .select(F.col("a.field_id").alias("field_id"), F.col("b.valid_from").alias("valid_from")))
issues.append(issues_from(invalid_wi.select("field_id", "valid_from").unionByName(overlaps), "M03",
                          "working_interest", None, F.concat_ws("|", "field_id", F.col("valid_from").cast("string"))))
issues.append(issues_from(uom.filter(F.col("to_standard_factor") <= 0), "M04", "uom_conversion", None,
                          F.concat_ws("|", "commodity", "uom")))

# %%
for table, df in [("silver.country", country), ("silver.business_associate", business_associate),
                  ("silver.field", field), ("silver.facility", facility), ("silver.equipment", equipment),
                  ("silver.well", well), ("silver.wellbore", wellbore), ("silver.well_completion", completion),
                  ("silver.reporting_stream", stream), ("silver.well_alias", alias),
                  ("silver.uom_conversion", uom), ("silver_ext.working_interest", working_interest),
                  ("silver_ext.source_authority", authority), ("silver_ext.price", price)]:
    write_table(df, table)

counts = save_issues(issues)
record_status(STAGE, "SILVER_MASTER_DONE", "Golden master snapshot conformed", counts=counts)
finish({"batch_id": p_batch_id, "stage": STAGE, "issues": counts,
        "wells": well.count(), "wellbores": wellbore.count(), "completions": completion.count()})
