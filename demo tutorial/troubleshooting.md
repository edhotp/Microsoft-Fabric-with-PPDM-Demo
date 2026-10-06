# Pemecahan masalah

Setiap lab memiliki bagian pemecahan masalah sendiri. Halaman ini mengumpulkan masalah lintas lab dan kode error prosedur Warehouse.

## Kode error prosedur Warehouse

| Kode | Prosedur | Arti | Tindakan |
|---|---|---|---|
| 50010 | `usp_stage_candidate` | Kandidat tidak ada di `lh_piep_core.serve.publication_candidate` | Jalankan `nb_05`; periksa ID publikasi |
| 50011 | `usp_stage_candidate` | Row count di SQL analytics endpoint belum sama dengan manifest | Tunggu 1–2 menit; pipeline melakukan retry 3× |
| 50020 | `usp_approve_publication` | `@Decision` bukan `APPROVE`/`REJECT` | Perbaiki parameter |
| 50021 | `usp_approve_publication` | `SUSER_SNAME()` tidak terdaftar sebagai approver aktif | Tambahkan UPN ke `ops.authorized_approver` (Lab 07) |
| 50022 | `usp_approve_publication` | Publikasi tidak berstatus `APPROVAL_PENDING` | Lihat `ops.vw_publication_history`; kandidat mungkin `SUPERSEDED` |
| 50030 | `usp_publish_publication` | Publikasi belum `APPROVED` | Approve dulu |
| 50031 | `usp_publish_publication` | Total kontrol Gold ≠ manifest; transaksi di-*rollback* | Bandingkan `serve.*` dan `stg.*`; laporkan ke fasilitator |

## Status batch di `ops.batch_status`

| Stage / Status | Arti | Langkah berikutnya |
|---|---|---|
| `BRONZE` / `LANDING_MISMATCH` | Jumlah file landing ≠ manifest | Jalankan ulang pipeline (Copy menimpa landing) |
| `BRONZE` / `BRONZE_COMMITTED` | Bronze siap | Lanjut ke Silver |
| `SILVER_MASTER` / `FAILED_DRILL` | Drill F1 aktif | Jalankan ulang dengan `p_fail_after_bronze = false` |
| `VALIDATE` / `NOT_READY` | Tahap Silver belum selesai | Jalankan `nb_02`–`nb_04` |
| `VALIDATE` / `QUALITY_FAILED` | Ada issue BLOCKER | Perbaiki di sumber dengan batch berikutnya; Gold tidak berubah |
| `VALIDATE` / `RECONCILIATION_FAILED` | Total fakta ≠ Silver | Bug transformasi; hubungi fasilitator |
| `SERVE` / `CANDIDATE_READY` | Kandidat siap di-*stage* | `usp_stage_candidate` |

## Masalah umum

| Gejala | Penyebab | Solusi |
|---|---|---|
| `Batch order violation` | Batch dilewati | Proses sesuai urutan `B0 B1 C1 D1 H1 X1 Q1 Q2 S1 S2` |
| `Batch ... is not the latest committed batch` | Menjalankan notebook Silver untuk batch lama | Silver selalu dibangun untuk batch terbaru |
| Notebook gagal `%run nb_00_common` | Helper tidak ada di workspace yang sama | Impor `nb_00_common.ipynb` |
| Angka report ≠ SQL | Semantic model belum di-refresh | Jalankan `pl_piep_publish_gold` atau refresh model |
| Agent konteks aset memakai publikasi lama | Ontology belum di-refresh / `nb_06` belum jalan | Jalankan `nb_06`, lalu refresh ontology |
| Copy lambat | Kapasitas kecil | Kurangi `Batch count` ForEach; gunakan F8+ untuk kelas |
| Azure SQL timeout pertama kali | Auto-pause serverless | Tunggu resume ±1 menit |
| `Deny Public Network Access is set to Yes` | SQL privat diakses tanpa gateway | Gunakan koneksi pada VNet data gateway ([Lab 03 opsi B](tutorial/03-azure-sql-source.md#opsi-b---jaringan-privat-tanpa-endpoint-publik)) |
| Tabel baru tidak terlihat di SQL analytics endpoint | Sinkronisasi metadata endpoint tertinggal | Buka SQL analytics endpoint lalu pilih **Refresh**; `usp_stage_candidate` sudah menunggu dengan retry |

## Mengumpulkan diagnosis

Saat meminta bantuan, sertakan informasi berikut:

1. Lab dan langkah.
2. Run ID pipeline dari **Monitor**.
3. Hasil query berikut:

   ```sql
   SELECT BatchId, Stage, Status, Message FROM ops.batch_status ORDER BY UpdatedAtUtc DESC;  -- lh_piep_core
   SELECT * FROM ops.vw_publication_history;                                                 -- wh_piep_gold
   ```

4. Exit value notebook terakhir.

## Referensi

- [Monitor pipeline runs](https://learn.microsoft.com/fabric/data-factory/monitor-pipeline-runs)
- [Microsoft Fabric known issues](https://support.fabric.microsoft.com/known-issues/)
- [Fabric Data Warehouse limitations](https://learn.microsoft.com/fabric/data-warehouse/limitations)
