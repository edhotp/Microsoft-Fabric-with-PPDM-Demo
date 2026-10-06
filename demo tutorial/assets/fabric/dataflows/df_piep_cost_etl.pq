// df_piep_cost_etl - Dataflow Gen2 (ETL): opex closing + kurs -> stg_df.cost_monthly
// Parameter (Home > Manage parameters): pBatchId (Text, tidak required, current value B0)
// Ganti <SERVER> dengan nama logical server Azure SQL Anda. Server/database TIDAK diparameterkan karena public
// parameters tidak boleh mengubah path sumber atau destination.
// Destination: Lakehouse lh_piep_core, schema stg_df, table cost_monthly, Update method = Replace.
let
    Source = Sql.Database("<SERVER>.database.windows.net", "sqldb_piep_source_demo"),
    Cost = Table.SelectRows(Source{[Schema = "ref", Item = "operating_cost"]}[Data], each [batch_id] = pBatchId),
    Fx = Table.SelectColumns(
        Table.SelectRows(Source{[Schema = "ref", Item = "fx_rate"]}[Data], each [batch_id] = pBatchId),
        {"valid_on", "currency_code", "usd_per_unit"}),
    Joined = Table.NestedJoin(
        Cost, {"month_start", "currency_code"}, Fx, {"valid_on", "currency_code"}, "fx", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "fx", {"usd_per_unit"}, {"usd_per_unit"}),
    WithUsd = Table.AddColumn(
        Expanded, "amount_usd",
        each if [usd_per_unit] = null then null else [amount_local] * [usd_per_unit], type number),
    WithStatus = Table.AddColumn(
        WithUsd, "dq_status",
        each if [usd_per_unit] = null then "MISSING_FX"
             else if [amount_local] < 0 then "NEGATIVE_AMOUNT"
             else "VALID", type text),
    Selected = Table.SelectColumns(
        WithStatus,
        {"batch_id", "cost_id", "field_id", "month_start", "cost_category", "currency_code", "amount_local",
         "usd_per_unit", "amount_usd", "closing_status", "dq_status"}),
    Typed = Table.TransformColumnTypes(
        Selected,
        {{"batch_id", type text}, {"cost_id", type text}, {"field_id", type text}, {"month_start", type date},
         {"cost_category", type text}, {"currency_code", type text}, {"amount_local", type number},
         {"usd_per_unit", type number}, {"amount_usd", type number}, {"closing_status", type text},
         {"dq_status", type text}})
in
    Typed
