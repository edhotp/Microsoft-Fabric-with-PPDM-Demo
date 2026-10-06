// df_piep_target_etl - Dataflow Gen2 (ETL): target RKAP bulanan -> stg_df.target_monthly
// Parameter (Home > Manage parameters): pBatchId (Text, tidak required, current value B0)
// Ganti <SERVER> dengan nama logical server Azure SQL Anda. Server/database TIDAK diparameterkan karena public
// parameters tidak boleh mengubah path sumber atau destination.
// Destination: Lakehouse lh_piep_core, schema stg_df, table target_monthly, Update method = Replace.
// Kolom output harus sama dengan yang dibaca nb_04_conform_business.
let
    Source = Sql.Database("<SERVER>.database.windows.net", "sqldb_piep_source_demo"),
    TargetMonthly = Source{[Schema = "ref", Item = "target_monthly"]}[Data],
    CurrentBatch = Table.SelectRows(TargetMonthly, each [batch_id] = pBatchId),
    MonthColumns = List.Transform({1..12}, each "m" & Text.PadStart(Text.From(_), 2, "0")),
    Unpivoted = Table.Unpivot(CurrentBatch, MonthColumns, "month_code", "target_value"),
    WithMonthStart = Table.AddColumn(
        Unpivoted, "month_start",
        each #date([target_year], Number.FromText(Text.End([month_code], 2)), 1), type date),
    WithStatus = Table.AddColumn(
        WithMonthStart, "dq_status",
        each if [target_value] = null or [target_value] < 0 then "INVALID" else "VALID", type text),
    Selected = Table.SelectColumns(
        WithStatus,
        {"batch_id", "field_id", "commodity", "scenario_id", "month_start", "target_value", "target_uom", "dq_status"}),
    Typed = Table.TransformColumnTypes(
        Selected,
        {{"batch_id", type text}, {"field_id", type text}, {"commodity", type text}, {"scenario_id", type text},
         {"month_start", type date}, {"target_value", type number}, {"target_uom", type text}, {"dq_status", type text}})
in
    Typed
