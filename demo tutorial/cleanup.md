# Reset dan pembersihan

## Reset untuk mengulang

Gunakan langkah ini untuk menjalankan ulang workshop dari `B0` tanpa membuat ulang semua item.

1. **Azure SQL:** hapus data batch. Jalankan di Query editor database:

   ```sql
   DECLARE @sql nvarchar(max) = N'';
   SELECT @sql = @sql + N'DELETE FROM ' + QUOTENAME(source_schema) + N'.' + QUOTENAME(source_table) + N';'
   FROM ctl.entity_config;
   EXEC sys.sp_executesql @sql;
   ```

   Tabel `ctl.entity_config` tidak terhapus karena tidak terdaftar sebagai entitasnya sendiri.
2. **Lakehouse `lh_zava_core`:** jalankan di notebook baru dengan `lh_zava_core` sebagai default:

   ```python
   for schema in ["bronze", "silver", "silver_ext", "quarantine", "ops", "serve", "stg_df"]:
       spark.sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
   notebookutils.fs.rm("Files/landing", True)
   spark.sql("CREATE SCHEMA IF NOT EXISTS stg_df")
   ```

3. **Warehouse `wh_zava_gold`:** jalankan di SQL query editor:

   ```sql
   DECLARE @sql nvarchar(max) = N'';
   SELECT @sql = @sql + N'DELETE FROM ' + QUOTENAME(s.name) + N'.' + QUOTENAME(t.name) + N';'
   FROM sys.tables AS t JOIN sys.schemas AS s ON s.schema_id = t.schema_id
   WHERE s.name IN (N'stg', N'gold') OR (s.name = N'ops' AND t.name NOT IN (N'authorized_approver', N'kpi_contract'));
   EXEC sys.sp_executesql @sql;
   ```

4. **Lakehouse `lh_zava_ai`:** jalankan `spark.sql("DROP SCHEMA IF EXISTS ai CASCADE")`, lalu refresh ontology setelah `nb_06` berjalan lagi.
5. Muat ulang `B0` (Lab 03, langkah 4) dan lanjutkan dari Lab 04.

> [!NOTE]
> Time travel Warehouse tetap menyimpan versi lama selama periode retensi. Hal ini tidak memengaruhi reset.

## Hapus semua resource

1. **Fabric:** hapus workspace `ws-zava-ppdm-demo` dan `ws-zava-ppdm-ai-demo` melalui **Workspace settings** > **General** > **Remove this workspace**. Semua item di dalamnya ikut terhapus.
2. **Koneksi dan gateway:** hapus `conn_sql_zava_source` di **Settings** > **Manage connections and gateways**. Jika memakai opsi B, hapus juga VNet data gateway `vnetgw-zava-ssot`. Gateway harus dihapus sebelum VNet agar delegasi subnet terlepas.
3. **Azure:**

   ```powershell
   az group delete --name rg-zava-ppdm-demo --yes --no-wait
   ```

4. **Lokal:** hapus `data/`, `config/local.json`, folder `evidence/`, dan virtual environment `.venv`.
5. **Kapasitas:** jika kapasitas F dibuat khusus untuk workshop, *pause* atau hapus kapasitas di Azure portal agar biaya berhenti.

## Referensi

- [Delete a workspace](https://learn.microsoft.com/fabric/fundamentals/workspaces)
- [Pause and resume your capacity](https://learn.microsoft.com/fabric/enterprise/pause-resume)
- [az group delete](https://learn.microsoft.com/cli/azure/group#az-group-delete)
