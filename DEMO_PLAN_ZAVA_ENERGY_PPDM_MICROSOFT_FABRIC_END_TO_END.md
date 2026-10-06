# Demo Plan End-to-End: Zava Energy Single Source of Truth dengan Microsoft Fabric, PPDM-Aligned

**Versi:** 2.1 - SSOT-first, diselaraskan dengan paket tutorial  
**Tanggal:** 5 Oktober 2026  
**Status:** rencana demo dan kurikulum. Paket tutorial siap ikut ada di folder [`demo tutorial`](./demo%20tutorial/README.md); bukan hasil deployment.  
**Nama demo:** **Zava Energy Governed Upstream Single Source of Truth**.  
**Skenario:** Zava Energy adalah perusahaan hulu migas **fiktif** dengan aset di beberapa negara; seluruh data bersifat sintetis.

**Penyelarasan v2.1 dengan paket tutorial:**

1. Generator berjalan **lokal** (`python -m workshop generate`) dan dimuat ke Azure SQL dengan loader berbasis Microsoft Entra. Fabric tetap membaca dari Azure SQL, bukan dari output generator.
2. Paket batch membentuk **satu rantai linear** `B0 → B1 → C1 → D1 → H1 → X1 → Q1 → Q2 → S1 → S2`; `H1`/`X1` ditempatkan sebelum drill `Q1`/`Q2` agar dapat dijalankan di latar belakang. F1 adalah parameter drill (`p_fail_after_bronze`), bukan paket data.
3. Proyeksi AI dijalankan oleh `nb_06_prepare_ai_serving` di workspace AI dan membaca kandidat `serve.*` lintas workspace untuk `PublicationId` yang sama dengan Gold.

Dokumen pendamping: [paket tutorial workshop](./demo%20tutorial/README.md) dan [PPDM Association](https://ppdm.org/).

> **Batas klaim:** seluruh nama aset, identitas sumur, volume, biaya, insiden, dan kepemilikan dalam demo adalah sintetis. Negara digunakan sebagai konteks pembelajaran, bukan representasi portofolio aktual. Penggunaan PPDM maupun Fabric secara internal oleh Zava Energy tidak diasumsikan. Baseline adalah **SSOT analitis dengan model kanonis PPDM-aligned**, bukan implementasi atau sertifikasi kepatuhan penuh terhadap skema PPDM resmi. Pemakaian artefak resmi di luar referensi publik tetap memerlukan hak penggunaan yang sah.

**Perubahan utama dari versi 1.0:** fokus bergeser dari demonstrasi rangkaian produk dan subset skema PPDM resmi menjadi pembuktian **satu identitas, satu sumber berwenang per domain, satu definisi KPI, dan satu versi publikasi yang dapat ditelusuri**. Sembilan komponen teknologi tetap dipertahankan. PPDM menjadi acuan alignment; akses model resmi bukan prasyarat baseline workshop.

## Daftar isi

1. [Hasil yang dituju dan cakupan](#1-hasil-yang-dituju-dan-cakupan)
2. [Keputusan desain dan prasyarat](#2-keputusan-desain-dan-prasyarat)
3. [Use case dan alur cerita](#3-use-case-dan-alur-cerita)
4. [Arsitektur dan inventaris komponen](#4-arsitektur-dan-inventaris-komponen)
5. [Data dummy dan generator](#5-data-dummy-dan-generator)
6. [Azure SQL Database sebagai sumber](#6-azure-sql-database-sebagai-sumber)
7. [Ingestion dengan Fabric Data Factory](#7-ingestion-dengan-fabric-data-factory)
8. [Lakehouse medallion dan pemetaan PPDM](#8-lakehouse-medallion-dan-pemetaan-ppdm)
9. [ETL dan ELT](#9-etl-dan-elt)
10. [Fabric Warehouse untuk Gold](#10-fabric-warehouse-untuk-gold)
11. [Orkestrasi dan pemulihan](#11-orkestrasi-dan-pemulihan)
12. [Semantic model dan definisi KPI](#12-semantic-model-dan-definisi-kpi)
13. [Rencana Power BI report](#13-rencana-power-bi-report)
14. [Fabric ontology](#14-fabric-ontology)
15. [Fabric data agents](#15-fabric-data-agents)
16. [Keamanan dan tata kelola](#16-keamanan-dan-tata-kelola)
17. [Pengujian dan acceptance criteria](#17-pengujian-dan-acceptance-criteria)
18. [Kurikulum tutorial dan urutan implementasi](#18-kurikulum-tutorial-dan-urutan-implementasi)
19. [Runbook presentasi demo](#19-runbook-presentasi-demo)
20. [Operasional, biaya, deliverables, dan pengembangan](#20-operasional-biaya-deliverables-dan-pengembangan)
21. [Referensi resmi](#21-referensi-resmi)

## 1. Hasil yang dituju dan cakupan

Demo harus menjawab pertanyaan bisnis berikut:

> Bagaimana Zava Energy memperoleh satu versi data hulu internasional yang dipercaya untuk keputusan korporat, ketika beberapa sumber memiliki nama objek, satuan, status persetujuan, dan angka yang berbeda; lalu memastikan Power BI, ontology, dan data agents menggunakan identitas, definisi, serta publikasi yang sama?

Zava Energy berfokus pada aset dan bisnis hulu luar negeri; konteks lintas negara ini menjadi alasan pemilihan use case integrasi, produksi, dan keandalan, bukan transaksi ritel BBM.

### 1.1 Pemetaan sembilan kebutuhan

| No. | Kebutuhan | Implementasi yang direncanakan | Bukti keberhasilan |
|---|---|---|---|
| 1 | Dummy data/data generator | Generator deterministik dengan master, produksi, target, biaya, kejadian, serta konflik sumber dan persetujuan | Seed yang sama menghasilkan data dan keputusan SSOT acuan yang sama |
| 2 | Azure SQL Database | Satu database menyimulasikan beberapa system of record, termasuk laporan provisional dan approved | Asal, kewenangan, grain, dan status tiap sumber tercatat |
| 3 | Ingestion Fabric Factory | Fabric Data Factory pipeline dengan Copy activity, full load, dan incremental load | Jumlah record dan batas batch dapat direkonsiliasi |
| 4 | Medallion Lakehouse PPDM-aligned | Bronze mempertahankan bukti; Silver membentuk model kanonis, identitas, relasi, dan reference data yang disejajarkan dengan PPDM | Alignment register, golden records, histori, dan aturan resolusi konflik tervalidasi |
| 5 | ETL dan ELT | ETL Power Query/Dataflow Gen2; ELT Bronze-to-Silver dengan Spark; ELT staging-to-Gold dengan T-SQL | Kedua urutan proses ditunjukkan dengan input dan output yang nyata |
| 6 | Orchestrator Fabric Factory | Pipeline, quality/authority/approval gates, audit, retry, dan rerun | Data belum disetujui tidak menjadi angka korporat hanya karena pipeline sukses |
| 7 | Data warehouse Gold | Fabric Warehouse untuk data product analitis approved dan manifest publikasi | Satu publikasi berwenang per produk, bukan beberapa tabel Gold yang bersaing |
| 8 | Semantic model dan Power BI | Explicit measures dari KPI contract yang sama, Direct Lake, RLS, lima halaman dan satu drillthrough | Angka, filter, versi, dan sumber dapat direkonsiliasi |
| 9 | Fabric ontology dan data agents | Konsumsi definisi PPDM-aligned, golden records, dan publikasi SSOT | Tidak menciptakan master, KPI, atau kebenaran alternatif lewat prompt |

Tambahan wajib: source authority register, business/data owner, data steward, approval, lineage, data contracts, konektivitas, keamanan, observability, pengujian, version control, biaya, reset demo, dan dokumentasi tutorial. Hak penggunaan PPDM diperiksa sesuai sumber yang digunakan, bukan dianggap memerlukan model penuh untuk baseline.

**Di luar baseline:** data produksi nyata, implementasi fisik skema PPDM resmi, sertifikasi kepatuhan PPDM, interpretasi reservoir, optimasi operasi otomatis, real-time SCADA, RAG dokumen, serta implementasi production-grade lintas negara.

### 1.2 Definisi SSOT yang dipakai

Dalam demo ini, **SSOT adalah satu rujukan data yang berwenang dan terkelola untuk suatu domain, grain, periode, basis, dan versi tertentu**. SSOT tidak berarti semua sistem operasi diganti, seluruh data dunia harus berada di satu database, atau tidak boleh ada cache/proyeksi serving.

| Lapisan kewenangan | Peran | Yang tidak boleh dilakukan |
|---|---|---|
| System of record | Mencatat transaksi, pengukuran, laporan operator, atau persetujuan bisnis sumber | Dianggap otomatis konsisten hanya karena sumbernya resmi |
| Canonical/golden data di Silver | Menyatukan identitas, makna, satuan, histori, dan keputusan sumber berwenang | Memilih angka terbesar/terbaru tanpa aturan kewenangan |
| Approved analytical data di Gold | Menyediakan fakta/dimensi untuk publikasi bisnis yang telah disetujui | Menjadikan data provisional sebagai angka korporat tanpa status |
| Semantic model dan KPI contract | Menetapkan rumus, unit, filter, grain, dan perilaku agregasi | Membuat definisi KPI berbeda untuk report dan agent |
| Power BI, ontology, dan agents | Mengonsumsi rujukan yang sama sesuai izin dan publication ID | Mengedit golden record atau menetapkan angka sendiri |

OneLake mendukung akses dan tata kelola data bersama di Fabric, tetapi platform tidak menggantikan keputusan mengenai pemilik, sumber berwenang, dan persetujuan bisnis. [S25]

### 1.3 Janji bisnis yang harus dibuktikan

1. **Satu identitas:** alias dari sumber berbeda terhubung ke canonical ID; well, wellbore, dan completion tetap dibedakan.
2. **Satu aturan kewenangan:** setiap atribut/indikator memiliki sumber utama, kriteria approval, dan aturan ketika sumber bertentangan.
3. **Satu definisi:** KPI menggunakan unit, basis, grain, dan versi target yang konsisten.
4. **Satu publikasi yang dapat ditelusuri:** angka selalu terikat pada input snapshot, mapping, aturan kualitas, dan persetujuan tertentu.
5. **Satu hasil lintas kanal:** untuk publikasi, scope akses, periode, filter, dan basis yang sama, hasil SQL acuan, Power BI, serta agent harus cocok.

Perbedaan hasil karena RLS atau versi publikasi tidak disebut inkonsistensi apabila konteks tersebut dinyatakan. Perbedaan untuk konteks yang identik adalah kegagalan SSOT.

## 2. Keputusan desain dan prasyarat

### 2.1 Keputusan awal

| Area | Keputusan |
|---|---|
| Fokus bisnis | SSOT Zava Energy yang dipercaya untuk produksi, loss, biaya, identitas aset, dan keputusan portofolio |
| Model PPDM | **PPDM-aligned canonical model** berbasis konsep dan referensi yang dapat digunakan secara sah; bukan salinan skema resmi |
| Otoritas data | Source authority per domain/atribut, approval, effective dates, serta lineage wajib sebelum publikasi |
| Penyimpanan | Satu Lakehouse utama untuk Bronze/Silver; satu **Fabric Warehouse** untuk Gold |
| Dataset | Periode tetap 1 Januari-31 Desember 2025; penambahan hari dan koreksi lewat paket terpisah |
| Frekuensi | Batch harian; incremental sesuai perubahan sumber, bukan klaim streaming |
| Transformasi | Spark untuk identitas/histori/volume; Dataflow Gen2 untuk target dan biaya berformat bisnis |
| Power BI | Semantic model berwenang di atas Gold, explicit measures mengikuti KPI contract; Direct Lake diprioritaskan |
| Ontology | Binding konservatif ke managed Lakehouse tables yang telah disiapkan untuk AI |
| Agents | Agent KPI melalui semantic model; agent hubungan aset melalui ontology context |
| Bahasa | Tutorial/report Indonesia; nama teknis konsisten; pertanyaan, instruksi, dan contoh agent dalam bahasa Inggris |
| Implementasi saat ini | Hanya rencana; seluruh resource dan nama item di bawah merupakan usulan |

### 2.2 Gate sebelum implementasi

| Gate | Yang harus tersedia atau diverifikasi | Jika belum terpenuhi |
|---|---|---|
| G0 - Kontrak SSOT dan alignment | Domain owner, sumber berwenang, canonical keys, grain, KPI, approval rules, serta register referensi PPDM-aligned disepakati | Publikasi bisnis ditahan sampai kontrak jelas; akses skema PPDM resmi tidak menjadi blocker baseline |
| G1 - Azure | Subscription, resource group demo, Azure SQL, izin provisioning, dan anggaran | Tutorial Azure menunggu resource yang disetujui |
| G2 - Fabric | Capacity aktif, workspace, izin authoring, dan koneksi sumber | Tidak mengklaim pipeline dapat dijalankan sebelum smoke test |
| G3 - Power BI | Lisensi author dan viewer sesuai kapasitas; Desktop terkini untuk PBIP/preview | Sesuaikan distribusi report, bukan mengasumsikan semua viewer gratis |
| G4 - Ontology | Tenant setting pembuatan ontology dan Fabric items aktif | Modul ontology belum lulus; diagram saja bukan pengganti implementasi |
| G5 - Data agents | Capacity berbayar yang didukung, pengaturan Copilot/AI, izin sumber, dan kesesuaian region | BI boleh selesai lebih dahulu; modul agent tetap berstatus belum tersedia |
| G6 - Keamanan | Persetujuan lokasi data, koneksi, akses pengguna, serta pemrosesan/penyimpanan AI | Jangan menonaktifkan kontrol tenant demi demo |

Catatan berdasarkan dokumentasi yang diperiksa:

- PPDM 3.9 adalah model relasional dengan lebih dari 60 area subjek. Baseline memakai alignment konsep dan dokumentasi yang boleh diakses, bukan DDL model tersebut. Penggunaan model resmi adalah jalur lanjutan dengan gate hak akses tersendiri. [S02] [S04]
- Fabric data agent disebut **generally available**; ontology dan integrasi ontology sebagai context masih **preview**. Periksa lagi saat lab dimulai. [S18] [S21] [S23]
- Data agent mensyaratkan **paid F2 atau lebih tinggi**, atau P1+ yang didukung. F2 adalah batas kelayakan fitur, **bukan rekomendasi sizing** seluruh demo. Jangan mengandalkan Fabric Trial untuk menyelesaikan semua modul AI. [S21]
- Authoring Power BI memerlukan lisensi yang sesuai; pada F SKU di bawah F64, distribusi Power BI kepada viewer umumnya tetap membutuhkan Pro/PPU yang sesuai. PPU sendiri bukan pengganti Fabric capacity untuk workload non-Power BI. [S17]
- Dokumentasi data agent saat ini menyatakan bahasa non-Inggris belum didukung. Versi pertanyaan Indonesia boleh dijadikan eksperimen tambahan, bukan acceptance test utama. [S21]
- Capacity sumber dan data agent harus berada di region yang sama. Untuk region tertentu, penggunaan AI memerlukan persetujuan tenant atas pemrosesan dan penyimpanan lintas geografi. [S21] [S22]

### 2.3 Source authority register

Tabel ini adalah **rancangan kewenangan untuk simulasi workshop**, bukan kebijakan internal Zava Energy yang telah diverifikasi. Dalam implementasi nyata, nama sistem dan pemilik disetujui bersama Zava Energy.

| Domain | Sumber berwenang dalam demo | Sumber pembanding | Pemilik keputusan yang disimulasikan |
|---|---|---|---|
| Identitas aset/well dan relasinya | Master registry approved + crosswalk ID | Nama/alias dalam laporan lokal | Asset data owner dan data steward |
| Produksi | Laporan operator final yang disetujui, per stream/date/commodity/basis | Laporan operasi provisional | Production reporting owner |
| Target | Snapshot RKAP dengan versi yang disetujui | Target lokal/versi kerja | Planning owner |
| WI/operator history | Register kepentingan dan operator yang effective-dated | Kolom persentase di spreadsheet operasional | Portfolio/JV owner |
| Biaya dan FX | Closing finance dan sumber kurs yang disetujui | Estimasi biaya operasi | Finance owner |
| UOM/BOE dan klasifikasi | Reference registry berversi dengan metodologi yang disetujui | Kode/unit lokal | Engineering/reference-data steward |
| Kejadian dan loss attribution | Event maintenance valid + aturan alokasi yang disetujui fungsi produksi | Catatan naratif bebas | Maintenance dan production owner |

Setiap aturan memuat domain/atribut, scope aset/negara, grain, source ID, prioritas, status approval yang diperlukan, valid from/to, `authority_policy_version`, owner, dan aturan konflik. **Prioritas bukan satu angka global untuk seluruh atribut.**

Urutan pemilihan candidate: cocokkan canonical object dan grain -> periksa unit/basis -> cek otoritas dan approval -> pilih revisi dalam sumber yang berwenang -> uji kualitas -> simpan winner, candidate lain, serta alasan keputusan. Timestamp ingestion atau revision number dari dua issuer berbeda tidak boleh langsung dibandingkan sebagai bukti kewenangan.

### 2.4 Data product dan kepemilikan

| Produk | Rujukan berwenang | Consumer | Kontrak minimum |
|---|---|---|---|
| Asset & Well Registry | Snapshot golden master Silver yang approved | Engineering, ontology, dimensi Gold | Canonical ID, relasi, alias, histori, owner |
| Production Performance | Gold published + semantic KPI contract | Power BI dan agent KPI | Grain, gross/net-WI, unit, periode, target version |
| Cost & Portfolio View | Gold published untuk bulan/cakupan yang sesuai | Finance report dan agent KPI | Currency/FX, closing status, denominator BOE |
| Data Trust & Publication | Decision log, quality evidence, dan publication manifest | Steward, auditor, semua kanal status | Sumber dipilih, approval, lineage, freshness, exceptions |

Domain Fabric dapat membantu discovery dan ownership secara federatif. Domain assignment bukan pengganti workspace/item permissions; domain tidak otomatis membatasi atau memberikan akses data. [S26]

## 3. Use case dan alur cerita

| ID | Use case | Persona | Pertanyaan |
|---|---|---|---|
| UC00 | Rekonsiliasi dan satu angka korporat | Reporting owner/data steward | Ketika laporan provisional berbeda dari final, angka mana yang berwenang, siapa yang menyetujui, dan mengapa? |
| UC01 | International production performance | Manajemen/analyst | Aset mana yang di bawah target, dalam periode dan basis volume yang sama? |
| UC02 | Production loss dan keandalan | Operasi/maintenance | Kejadian apa yang berkaitan dengan kehilangan produksi, dan sumur mana yang terdampak? |
| UC03 | Golden identity PPDM-aligned dan data quality | Data steward/engineer | Apakah dua identitas menunjuk objek yang sama, dan apa dasar pemilihannya sebagai golden record? |
| UC04 | Cost dan working-interest view | Finance/portfolio analyst | Bagaimana biaya per BOE dan tampilan gross vs net working interest berubah? |
| UC05 | Publikasi dan histori yang dapat ditelusuri | Semua persona | Dari sumber, keputusan authority, revisi, dan approval mana angka ini berasal? |
| UC06 | Konsumsi SSOT lintas kanal | Pengguna bisnis/teknis | Apakah report dan agent menjawab dengan angka, definisi, publikasi, serta izin yang sama? |

### Cerita utama

1. Dua laporan untuk objek dan periode yang sama menunjukkan angka berbeda; peserta tidak diminta memilih angka yang paling baru.
2. Source authority register menjelaskan bahwa final approved lebih berwenang daripada laporan provisional.
3. Crosswalk PPDM-aligned mempertemukan alias sumber dengan golden identity, tanpa menyamakan well dengan wellbore/completion.
4. Steward melihat candidate, alasan pemilihan, issue kualitas, dan revisi; owner menyetujui koreksi melalui mekanisme yang tercatat.
5. Pipeline memublikasikan data product SSOT dengan satu publication ID setelah quality, authority, reconciliation, dan approval gates lulus.
6. Portfolio report menunjukkan deviasi produksi; investigasi menemukan empat hari gangguan yang memengaruhi sepuluh well.
7. SQL acuan, Power BI, dan agent menunjukkan hasil fixture yang sama; ontology menjelaskan relasi memakai master snapshot yang sama.
8. Peserta membuka lineage dan publikasi sebelumnya untuk menjelaskan apa yang berubah, bukan menimpa sejarah.

**Nilai demo:** bukan hanya "semua data sudah masuk", melainkan **makna yang konsisten, angka yang dapat diperiksa, dan akses yang terkendali**.

## 4. Arsitektur dan inventaris komponen

### 4.1 Arsitektur target

```text
Generator sintetis + manifest hasil acuan
                  |
                  v
Azure SQL Database: src_dz / src_my / src_iq / ref / ctl
                  |
       Fabric Data Factory - Copy activity
                  |
                  v
Lakehouse utama - Bronze: salinan sumber + metadata batch
                  |
          +-------+--------------------------------------+
          |                                              |
          v                                              v
Spark: identitas, histori, produksi       Dataflow Gen2: target dan biaya
          |                               ETL dari snapshot Azure SQL
          |                               yang juga telah diarsipkan
          +----------------------+-----------------------+
                                 v
Lakehouse - Silver kanonis PPDM-aligned + golden records
                                 |
           Authority + quality + reconciliation + approval
                                 |
                                 v
Fabric Warehouse: stg -> approved Gold + publication manifest
                                 |
                    +------------+-------------------+
                    |                                |
                    v                                v
Semantic model / Power BI              Proyeksi serving AI + objek Silver
                    |                                |
                    v                                v
Data agent KPI                         Managed Lakehouse AI -> Ontology
                                                     |
                                                     v
                                          Data agent hubungan aset

Orkestrasi: Fabric Data Factory
Lintas alur: identity, permissions, lineage, data contracts, audit, monitoring
```

Gold adalah rujukan fakta analitis approved; semantic model mengimplementasikan KPI contract berwenang di atas fakta tersebut. Proyeksi AI memakai master snapshot yang direferensikan oleh publikasi Gold dan nilai turunan yang sama, bukan Silver "paling baru" yang mungkin belum disetujui.

Salinan fisik untuk staging, historisasi, atau serving tidak melanggar SSOT selama lineage, publication ID, refresh, dan aturan read-only-nya jelas. Sebaliknya, menaruh semua file di OneLake tanpa aturan kewenangan belum menghasilkan SSOT. [S25]

### 4.2 Resource yang direncanakan

| Komponen | Nama usulan | Fungsi |
|---|---|---|
| Azure resource group | `rg-zava-ppdm-demo` | Batas resource demo, tag owner dan expiry |
| Azure SQL logical server | Nama unik ditentukan saat provisioning | Hosting database sumber |
| Azure SQL database | `sqldb_zava_source_demo` | Sumber operasional sintetis dan kontrol sumber |
| Workspace inti | `ws-zava-ppdm-demo` | Lakehouse, Warehouse, pipelines, notebooks, dataflows, semantic model, report |
| Lakehouse inti | `lh_zava_core` | Schema-enabled; Bronze, Silver, staging, quarantine, dan metadata |
| Warehouse | `wh_zava_gold` | Data product SSOT analitis, authority/approval evidence, dan publication manifest |
| Workspace AI | `ws-zava-ppdm-ai-demo` | Isolasi sumber dan pengguna AI; capacity/region sama dengan inti |
| Lakehouse AI | `lh_zava_ai` | Managed serving tables untuk ontology, tanpa shortcut sebagai binding baseline |
| Semantic model | `sm_zava_performance` | KPI bisnis, metadata, dan RLS |
| Power BI report | `Zava Energy SSOT - Performance & Data Trust` | Lima halaman utama dan satu drillthrough; technical item names lain dipertahankan |
| Ontology | `ont_zava_upstream` | Konsep, hubungan, dan binding objek bisnis |
| Data agent KPI | `da_zava_performance` | Pertanyaan numerik atas semantic model |
| Data agent aset | `da_zava_asset_context` | Pertanyaan hubungan atas ontology dan sumber terkurasi |

Dua workspace dipilih untuk membedakan akses engineer/BI dari serving AI. Tidak diperlukan tiga Lakehouse terpisah hanya untuk memberi nama Bronze/Silver/Gold. Gold berbentuk Warehouse sesuai kebutuhan pengguna; pola medallion dapat memakai kombinasi Lakehouse dan Warehouse. [S09]

## 5. Data dummy dan generator

### 5.1 Prinsip generator

- Default: **Python dengan seed tetap `20261005`**, dijalankan lokal (`python -m workshop generate`) tanpa dependensi pihak ketiga; label fiktif dibentuk secara deterministik, bukan data pribadi nyata.
- Hasil bisnis deterministik berdasarkan seed, identitas objek, dan tanggal; tidak bergantung pada waktu eksekusi, urutan partisi Spark, atau random state global.
- Output generator dimuat ke **Azure SQL** per batch dalam satu transaksi (`python -m workshop load`). Notebook transformasi selanjutnya tidak boleh melewati sumber ini dengan membaca output generator secara langsung.
- Master dibuat sebelum child records; seluruh FK valid pada baseline bersih.
- Variasi produksi memakai perbedaan kapasitas sumur, tren penurunan sederhana, planned maintenance, dan gangguan; bukan distribusi seragam atau pola akhir pekan ala ritel.
- Keluaran memuat `dataset_version`, `seed`, `scenario_id`, rentang tanggal, jumlah baris, hash bisnis, expected results, authority policy, dan approval scenario.
- Baseline B0 tetap bersih; paket S1/S2 menambahkan laporan pembanding dan persetujuan koreksi tanpa mengubah hitungan baseline atau fixture insiden.
- Expected results fixture dihitung independen dari fungsi ETL agar pengujian tidak mengulang kesalahan yang sama.
- Koneksi penulis generator terpisah dari pembaca ingestion; tidak menyimpan password/token di notebook atau repository.

### 5.2 Skala baseline

Negara ilustratif: **Aljazair/DZ, Malaysia/MY, Irak/IQ**. Gunakan nama seperti `MY_DEMO_FIELD_A`, bukan nama lapangan nyata.

| Domain/logical dataset | Grain | Jumlah baseline |
|---|---|---:|
| Country | Negara | 3 |
| Business associate/operator | Entitas fiktif | 3 |
| Asset/field | Lapangan sintetis; dua per negara | 6 |
| Facility | Fasilitas sintetis; satu per field | 6 |
| Equipment | Peralatan; enam per facility | 36 |
| Well | Sumur; dua puluh per field | 120 |
| Wellbore | Lintasan; tiga puluh well mempunyai dua wellbore | 150 |
| Completion | Unit completion; tiga puluh well single-bore mempunyai completion tambahan | 180 |
| Reporting stream | Satu stream pelaporan per well untuk menyederhanakan baseline | 120 |
| Completion-stream mapping | Completion ke stream; masa berlaku disimpan | 180 |
| Production observation | Stream x hari x komoditas oil/gas/water | **131.400** |
| Target wide | Field x komoditas oil/gas x tahun/version; 12 kolom bulan | 12 |
| Target setelah unpivot | Field x komoditas x bulan | 144 |
| Operating cost | Field x bulan x empat kategori biaya | 288 |
| Downtime event | Satu event per peralatan dan interval | 200, termasuk empat event fixture |
| FX | Tanggal x USD/MYR/DZD, semuanya nilai contoh | 1.095 |
| Indicative price | Tanggal x oil/gas | 730 |

Periode 365 hari menghasilkan `120 x 365 x 3 = 131.400` observation. Ini bukan berarti ada 131.400 sumur atau volume produksi dijumlahkan bersama air.

Relasi baseline completion disusun deterministik: 60 well memiliki satu completion, 30 well single-bore memiliki dua completion, dan 30 well double-bore memiliki dua completion. Produksi tetap dilaporkan pada stream, sehingga join ke completion tidak boleh menggandakan volume.

Pilihan skala tambahan:

- **Small:** 12 well dan 30 hari untuk troubleshooting/lab singkat.
- **Standard:** tabel di atas, menjadi baseline acceptance.
- **Scale:** jumlah well dan periode diperbesar melalui parameter untuk eksperimen performa; bukan syarat presentasi awal.

### 5.3 Atribut data utama

| Kelompok | Atribut minimum yang direncanakan |
|---|---|
| Identitas | Source system, jenis objek, source ID, canonical ID, alias, issuer/yurisdiction bila relevan |
| Histori | Effective from/to, observed at, revision number, approval status, approver, dan approval time |
| Observasi | Reporting stream, business date lokal, commodity, value asli, UOM asli, basis volume |
| Produksi standar | Oil bbl, gas Mscf, water bbl, factor version, gross dan net-WI terpisah |
| Kejadian | Event ID, incident/case ID, equipment, waktu mulai/selesai UTC, reason, affected wells |
| Finansial | Amount asli, currency, FX date/type/version, amount USD, jenis biaya |
| Audit | Source change ID, sequence, operation I/U/D, batch, quality status, authority policy, selected source, decision reason, dan business publication ID |

`Mscf` dalam demo berarti **ribu standard cubic feet**. Faktor BOE, kondisi standar gas, harga, dan kurs disimpan sebagai data referensi berversi; bukan konstanta tersembunyi dalam report.

### 5.4 Fixture bisnis dengan jawaban yang pasti

**Skenario `INC-MY-001`:** satu equipment sintetis yang melayani sepuluh well mengalami gangguan 12 jam per hari pada 15-18 September 2025. Ada empat downtime event, satu per hari.

Untuk sepuluh well tersebut saja, selama empat hari:

| Asumsi fixture | Nilai |
|---|---:|
| Potensi oil per well per hari | 100 bbl |
| Potensi gas per well per hari | 600 Mscf |
| Produksi aktual | 50% dari potensi |
| Faktor gas untuk BOE | 6 Mscf per BOE, khusus asumsi demo |
| Working interest sintetis | 40% |
| Harga indikatif oil | USD 70/bbl |
| Harga indikatif gas | USD 3/MMBtu |
| Heating-value factor | 1,03 MMBtu/Mscf, khusus asumsi demo |

Hasil acuan:

| Ukuran | Perhitungan | Expected result |
|---|---|---:|
| Gross lost oil | 10 x 4 x 100 x 50% | **2.000 bbl** |
| Gross lost gas | 10 x 4 x 600 x 50% | **12.000 Mscf** |
| Gross lost BOE | 2.000 + 12.000 / 6 | **4.000 BOE** |
| Net-WI lost BOE | 4.000 x 40% | **1.600 BOE** |
| Gross value opportunity | 2.000 x 70 + 12.000 x 1,03 x 3 | **USD 177.080** |
| Net-WI value opportunity | 177.080 x 40% | **USD 70.832** |
| Equipment downtime | 4 x 12 jam | **48 equipment-hours** |
| Affected-well downtime | 10 x 4 x 12 jam | **480 well-hours** |

Nilai di atas adalah **opportunity estimate sintetis**, bukan pendapatan, laba, cadangan, atau kerugian aktual Zava Energy. Harga gas tidak dikalikan langsung dengan BOE. Net-WI merupakan penyederhanaan gross x WI, **bukan entitlement kontraktual**.

Noise, kejadian lain, dan perubahan WI tidak diterapkan pada fixture ini. Kasus lain ditempatkan di luar well/periode fixture agar jawaban acuan tetap stabil.

### 5.5 Paket perubahan untuk demo dan latihan

Paket diterapkan berurutan sebagai satu rantai linear (`parent_batch_id` = paket sebelumnya): `B0 → B1 → C1 → D1 → H1 → X1 → Q1 → Q2 → S1 → S2`. Tabel referensi dikirim sebagai snapshot lengkap per paket, sedangkan tabel event hanya berisi delta.

| Paket | Perubahan | Yang diuji |
|---|---|---|
| B0 | Baseline bersih, termasuk insiden operasional yang valid | Full load dan rekonsiliasi |
| B1 | Satu hari baru, 1 Januari 2026 | Tambahan 360 observation dan 120 stream-day Gold; kalender ikut diperluas |
| C1 | 24 koreksi atas observation lama, revision lebih tinggi | Incremental menangkap perubahan lama; jumlah current business keys tidak bertambah |
| D1 | 100 pengiriman duplikat atas business key/revision yang sama, source change ID berbeda | Bronze menyimpan bukti; Silver current tidak menghitung ganda |
| H1 | Perubahan operator/WI efektif untuk satu aset di luar fixture | Histori dan join as-of-date |
| X1 | Pembatalan 3 observation melalui tombstone | Soft delete/retraction tanpa menghapus jejak sumber |
| Q1 | Versi baru dengan 20 UOM tidak dikenal, 10 referensi stream tidak dikenal, dan 5 nilai wajib kosong; semuanya disjoint | 35 record gagal kontrak, alasan tercatat, publikasi bisnis diblokir (Gold tetap `PUB-X1`) |
| Q2 | Koreksi sah untuk 35 record Q1 | Karantina dapat diselesaikan; rerun tidak membutuhkan reset penuh |
| S1 | Dari B0: satu laporan provisional sekunder untuk oil `MY_B_W001`, 20 September 2025, memakai alias lain dan nilai standar `V + 10 bbl`, dengan V nilai approved B0 | Identitas tetap satu; nilai SSOT tetap V karena laporan sekunder tidak berwenang; candidate/reason tetap dapat dilihat |
| S2 | Melanjutkan S1: koreksi dari sumber utama sebesar `V + 5 bbl`, dengan revisi dan approval tercatat | Sebelum approval SSOT tetap V; setelah approval delta gross +5 BOE dan net-WI +2 BOE pada WI 40%; publikasi lama tetap dapat direproduksi |
| F1 | Kegagalan yang disengaja setelah Bronze sukses | Resume dari batch yang sama, bukan melewatkan data |

Record Q1 tidak diam-diam diganti dengan versi lama yang valid. Jika versi terbaru belum layak dipublikasikan, batch ditahan dan report tetap menunjukkan publikasi bisnis sebelumnya beserta status keterlambatannya.

S1/S2 sengaja berada di luar fixture `INC-MY-001`. S1 adalah perbedaan yang diselesaikan oleh aturan authority eksplisit, bukan konflik ambigu yang disembunyikan. Bila dua candidate sama-sama berwenang dan tidak ada aturan pemutus yang sah, produk terkait tetap `REVIEW_REQUIRED` sampai owner mengambil keputusan.

## 6. Azure SQL Database sebagai sumber

### 6.1 Organisasi sumber

Gunakan satu Azure SQL database untuk mengendalikan biaya dan setup, dengan beberapa schema yang menyimulasikan sistem berbeda:

| Schema usulan | Isi |
|---|---|
| `src_dz` | Master lokal dan production observations; variasi alias dan satuan yang terdokumentasi |
| `src_my` | Master lokal, produksi, fasilitas, equipment, downtime, serta feed provisional/final terpisah untuk S1/S2 |
| `src_iq` | Master lokal dan produksi dengan nama kolom/status berbeda |
| `ref` | Target, cost, FX, price, UOM, canonical crosswalk, WI history, dan source authority policy |
| `ctl` | Source batch manifest, sequence bounds, audit seed, dan approval/decision register demo |

Semua merupakan schema demo, **bukan struktur aplikasi Zava Energy yang telah ditemukan**. Satu database fisik menyimulasikan beberapa system of record; hal ini tidak berarti Zava Energy nyata memakai satu database. Sumber sengaja tidak seragam: konformansi ke model kanonis PPDM-aligned dan pemilihan sumber berwenang menjadi pembelajaran Silver.

### 6.2 Kontrak perubahan sumber

- Dataset sumber menyimpan revisi sebagai event append-only dengan `source_change_id`, `change_seq`, `operation`, business key, dan revision.
- Generator memiliki satu writer dan menutup batch dalam transaksi sebelum batch dinyatakan `SEALED`.
- Manifest memuat jumlah record per entity serta high watermark yang **sudah committed**.
- Hanya batch `SEALED` yang boleh dibaca pipeline.
- Untuk tabel snapshot kecil seperti target/FX, Dataflow dan Copy membaca `snapshot_id` yang sama dan immutable.
- `SEALED` hanya menyatakan batch teknis lengkap, **bukan approval bisnis**. Authority dan approval diperiksa terpisah.
- Hard delete tanpa tombstone tidak didukung jalur baseline. Untuk sumber nyata, evaluasi Change Tracking/CDC sesuai kebutuhan; jangan menganggap watermark timestamp mendeteksi seluruh penghapusan.

Ini adalah change journal khusus demo, bukan klaim bahwa `MAX(identity)` atau `last_modified` otomatis aman pada database produksi dengan banyak transaksi bersamaan.

### 6.3 Koneksi dan keamanan

Rekomendasi jalur enterprise: **Azure SQL private endpoint + private DNS + VNet data gateway** untuk Copy dan Dataflow Gen2. Jalur generator memerlukan jaringan tersendiri yang bisa menjangkau SQL, misalnya runner di VNet atau private connectivity notebook yang didukung; gateway Data Factory tidak otomatis menyediakan konektivitas untuk Spark. [S05] [S24]

Untuk lab sederhana, public endpoint hanya boleh digunakan dengan persetujuan, firewall terbatas, data sintetis, dan waktu akses terbatas. Jangan membuka semua alamat atau memakai "Allow Azure services" secara luas tanpa memahami batas keamanannya.

| Identitas | Izin minimum |
|---|---|
| Provisioner | Membuat resource/schema demo sesuai scope yang disetujui |
| Generator writer | Menulis dataset sumber demo dan menutup source batch |
| Copy reader | Membaca entity dan manifest; tidak mengubah data operasional |
| Dataflow reader | Membaca snapshot target/cost/reference yang diperlukan |
| Control writer | Menulis audit/kemajuan pipeline, tanpa izin mengubah data bisnis sumber |

**Perbedaan konektor penting:** dokumentasi Azure SQL untuk Fabric mencantumkan Service Principal untuk Copy, tetapi tidak untuk Dataflow Gen2 pada tabel autentikasi yang diperiksa. Baseline Dataflow memakai organizational account yang didukung dan lolos uji refresh terjadwal. Jangan menyalin konfigurasi autentikasi Copy ke Dataflow tanpa verifikasi. [S06]

## 7. Ingestion dengan Fabric Data Factory

Yang dimaksud "Fabric Factory" dalam rencana ini adalah **Data Factory di Microsoft Fabric**, bukan Azure Data Factory terpisah.

### 7.1 Full load

1. Baca entity configuration dan source manifest B0.
2. Gunakan Copy activity dari Azure SQL dengan daftar kolom eksplisit.
3. Simpan hasil tiap entity/attempt ke landing files yang terpisah.
4. Periksa schema, row count, source batch, dan kelengkapan copy.
5. Notebook landing-to-Bronze memasukkan event baru ke managed Delta tables.
6. Simpan manifest ingestion dan status `BRONZE_COMMITTED`.

Copy activity mendukung pembacaan tabel, query, atau stored procedure dengan parameter. Partition bounds dipakai untuk membagi pekerjaan, bukan menggantikan predicate incremental. [S07]

### 7.2 Incremental load

Untuk setiap entity:

- Ambil `low_watermark` dari ingestion terakhir yang sudah committed.
- Ambil `high_watermark` dari source batch yang telah `SEALED`.
- Ekstrak event dengan `low < change_seq <= high`, dibatasi sumber/entity yang benar.
- Persist batas tersebut untuk seluruh retry; jangan mengambil high watermark baru di tengah rerun.
- Setelah Bronze durable dan count cocok, majukan **ingestion watermark**.
- Jika Silver/Gold gagal, lanjutkan dari manifest Bronze; tidak perlu memundurkan watermark sumber.

Timestamp bisnis tetap dipakai untuk menentukan partisi/periode yang perlu dihitung ulang, tetapi bukan satu-satunya indikator perubahan sumber.

### 7.3 Metadata dan idempotensi

Bronze mempertahankan payload sumber dan menambahkan:

`source_system`, `entity_name`, `source_change_id`, `source_batch_id`, `pipeline_run_id`, `ingested_at_utc`, `payload_hash`, dan identitas file/attempt.

Pisahkan:

- **Duplikasi transport:** event dengan `source_change_id` sama terkirim ulang akibat retry. Landing boleh memuat beberapa attempt; Bronze memakai insert-only berdasarkan identitas event agar tidak menambah event identik.
- **Duplikasi bisnis:** source change ID berbeda, tetapi business key dan revision sama. Bukti tetap ada di Bronze; resolusinya dilakukan di Silver dengan aturan yang dapat diaudit.

Dua payload berbeda untuk key/revision yang sama adalah **konflik**, bukan kandidat untuk dipilih secara arbitrer.

Identitas perubahan, identitas observation dari issuer, dan canonical business key dibedakan. Perbaikan alias pada revisi tidak boleh meninggalkan record salah sebagai observation baru yang tidak pernah terselesaikan. Dedup teknis tidak boleh menghapus bukti sumber yang bersaing sebelum evaluasi authority.

## 8. Lakehouse medallion dan pemetaan PPDM

### 8.1 Schema Lakehouse inti

| Schema | Fungsi |
|---|---|
| `bronze` | Event sumber yang belum dibersihkan secara bisnis |
| `stg_df` | Output staging Dataflow Gen2; bukan tabel kanonis yang dipublikasikan |
| `silver` | Model kanonis PPDM-aligned: master, relasi, observation terkonformansi, dan golden records |
| `silver_ext` | Kontrak bisnis demo Zava Energy: target, biaya, authority, approval, dan metadata khusus yang tidak diklaim sebagai PPDM resmi |
| `quarantine` | Record tidak valid, rule ID, alasan, batch, dan status penyelesaian |
| `serve` | Proyeksi bertipe dan ber-grain jelas untuk loading Warehouse |
| `ops` | Manifest, candidate/decision logs, hasil kualitas, statistik proses, dan lineage |

Lakehouse dibuat **schema-enabled**. Silver dan tabel serving memakai Delta. Perubahan data tabel Lakehouse dijalankan lewat Spark/mesin yang mendukung, bukan DML pada SQL analytics endpoint yang read-only untuk data tabel. [S08] [S09]

### 8.2 PPDM alignment: makna dan kontrak, bukan salinan skema

Tabel berikut adalah **cakupan konsep yang disejajarkan**, bukan daftar nama tabel resmi PPDM. Model fisik baseline dirancang sendiri untuk kebutuhan SSOT dan tutorial.

| Konsep/subjek | Pemakaian demo | Keputusan pemetaan yang harus dicatat |
|---|---|---|
| Area/location | Country, field, koordinat sintetis | Identifier, spatial reference, dan relasi area |
| Business associate | Operator/entitas | Identitas, peran, dan masa berlaku |
| Well | Identitas sumur lintas sumber | Primary/natural key, alias, issuer, dan atribut wajib |
| Wellbore/komponen sumur | Pembedaan lintasan dan completion | Definisi bisnis, canonical key, relasi, dan batas penyederhanaan |
| Facility/equipment | Relasi aset permukaan | Konsep yang dirujuk dan hubungan yang dirancang untuk demo |
| Production/reporting | Observation dan reporting stream | Tingkat pelaporan, unit, tanggal, dan hubungan ke komponen |
| Reference/UOM/status | Nilai standar dan pemetaan kode lokal | Definisi, versi referensi, hak penggunaan, dan nilai khusus demo |
| Histori/source attribution | Revisi, asal, dan keputusan authority | Histori source/canonical, approval, serta lineage publikasi |

Artefak alignment yang harus disiapkan pada lab SSOT:

- Glosarium konsep PPDM yang dirujuk beserta URL, versi/tanggal bila tersedia, dan hak pemakaiannya.
- Kontrak tabel kanonis buatan demo: grain, kolom, key, relasi, unit, dan temporal rules.
- Mapping `source -> canonical concept -> reference PPDM -> Gold/consumer`.
- Status tiap mapping: `ALIGNED_TO_PUBLIC_CONCEPT`, `DEMO_EXTENSION`, atau `REQUIRES_DOMAIN_VALIDATION`.
- Source authority, aturan pemilihan golden record, serta alasan candidate tidak dipilih.
- Aturan integritas/kualitas, ownership, dan approval yang dapat diuji.

**Pembedaan penting:** definisi *What Is a Well?* membantu pemahaman bisnis, tetapi nama konsep pada sumber tersebut belum tentu identik dengan nama tabel atau representasi wellbore pada PPDM 3.9. Jangan membuat tabel bernama `wellbore` lalu menyatakannya sebagai skema resmi tanpa pemeriksaan. [S02] [S03]

**Baseline tetap dapat diselesaikan tanpa akses DDL PPDM resmi.** Alignment dinilai dari dokumentasi makna, pemetaan, integritas, serta batas klaimnya. Implementasi subset resmi, bila kemudian diminta, menjadi tahap tambahan: verifikasi hak akses, nama tabel/kolom/dependensi, kesetaraan tipe, dan gap terhadap kontrak kanonis. Tahap tambahan itu tidak diam-diam disebut telah selesai oleh demo ini.

### 8.3 Aturan Silver

- Identitas: gabungan issuer/source, jenis objek, dan ID; nama saja tidak cukup.
- FK: seluruh record yang disetujui memiliki parent yang valid.
- Revisi: satu golden record per canonical business key pada konteks publikasi; revisi dan candidate non-winner tetap dapat ditelusuri.
- Authority: pilih sumber yang berwenang untuk domain/atribut dan periode tersebut sebelum membandingkan revisi; simpan alasan serta policy version.
- Waktu: simpan hari operasi lokal dan timestamp UTC; masa berlaku memakai batas yang tidak overlap.
- UOM: nilai asli dipertahankan; unknown UOM masuk quarantine, tidak mendapat faktor default 1.
- Volume: oil/gas/water dibedakan; hanya oil/gas dikonversi ke BOE.
- Kepemilikan: WI effective-dated; entitlement tidak disamakan dengan WI.
- Kejadian: event yang overlap tidak boleh menghasilkan alokasi kehilangan berulang.
- Quality: record terbaru tidak valid menyebabkan publikasi terkait ditahan, bukan silent fallback.
- Approval: hasil yang valid secara teknis masih candidate sampai mendapat approval yang dipersyaratkan kontrak.

PK/FK model relasional tidak boleh dianggap otomatis ditegakkan oleh Delta. Pipeline menjalankan uniqueness, referential-integrity, dan temporal-integrity checks.

### 8.4 Golden record dan histori

Untuk setiap golden record, simpan canonical key, selected source/observation/revision, valid time, waktu diketahui sistem, approval reference, authority policy, mapping version, serta pointer ke bukti Bronze. Candidate alternatif tidak dibuang.

Master berubah melalui proses usulan -> validasi -> review/approval -> publikasi, bukan edit manual pada Gold. Snapshot master yang dipakai publikasi lama harus tetap tersedia meskipun master terkini sudah berubah. Demo menyediakan latest approved view dan kemampuan mereproduksi publikasi tertentu; tidak perlu membangun platform MDM komersial baru.

## 9. ETL dan ELT

### 9.1 Demonstrasi ETL dengan Dataflow Gen2

**ETL:** extract dari sumber, transform, lalu load hasil transformasi ke target.

| Dataflow | Input | Transformasi | Output |
|---|---|---|---|
| `df_zava_target_etl` | Snapshot Azure SQL target wide yang sudah diarsipkan ke Bronze | Explicit types, locale-aware parsing, unpivot bulan, mapping field/UOM, validasi versi | `stg_df.target_monthly` |
| `df_zava_cost_etl` | Snapshot Azure SQL cost dan FX yang sama batch-nya | Cleansing kode, join FX, perhitungan USD, validasi kurs dan periode | `stg_df.cost_monthly` |

Kedua dataflow:

- Menggunakan **Dataflow Gen2 dengan CI/CD support dan public parameters** untuk `pSnapshotId` serta `pBatchId`.
- Tidak membaca snapshot "terbaru" yang berubah selama pipeline berjalan.
- Memisahkan output valid dari issue records; `try ... otherwise 0` tidak digunakan untuk menutupi kegagalan konversi.
- Menetapkan destination, schema, kolom bertipe, dan perilaku tulis secara eksplisit.
- Menggunakan Replace hanya untuk **staging milik run serial**, bukan langsung mengganti Silver atau Gold yang disetujui.
- Mengambil manfaat query folding bila tersedia, tanpa menganggap seluruh transformasi pasti fold.

Raw snapshot tetap disimpan agar jalur ETL dapat diaudit. Sebutan ETL mengacu pada urutan dari Azure SQL ke target konformansi; bukan alasan membuang bukti sumber.

Dokumentasi mendukung destination Lakehouse/Warehouse, public parameters untuk Gen2 dengan CI/CD, serta Dataflow activity di pipeline. [S10] [S11] [S12]

### 9.2 Demonstrasi ELT dengan Fabric Data Engineering

**ELT:** extract dari sumber, load ke platform, baru transform.

Alur produksi: Azure SQL -> Copy -> Bronze -> Spark -> Silver.

| Notebook usulan | Tanggung jawab | Hasil |
|---|---|---|
| `nb_00_generate_source` | Membentuk data sintetis dan menulis Azure SQL | Sealed source batch dan expected-result manifest |
| `nb_01_land_bronze` | Memvalidasi landing dan mencatat event secara idempotent | Bronze committed |
| `nb_02_conform_master_ppdm` | Golden identity, alias, PPDM alignment, histori parent/operator/WI, authority master | Master kanonis dan alignment register; nama notebook bukan klaim skema resmi |
| `nb_03_conform_production` | Dedup, candidate resolution, authority, revisi, tombstone, UOM, as-of joins | Observation kanonis dan decision evidence |
| `nb_04_conform_business` | Integrasi hasil Dataflow, kalender target, cost, downtime, loss allocation | Ekstensi/objek bisnis tervalidasi |
| `nb_05_validate_and_serve` | Integrity, rekonsiliasi sumber, authority/approval gates, proyeksi loading | Serving tables dan keputusan kelayakan publikasi |
| `nb_06_prepare_ai_serving` | Menggabungkan master snapshot terpilih dan Gold dari publikasi yang sama | Managed AI tables dengan publication/KPI-contract metadata |

Perubahan master atau faktor referensi dapat memengaruhi histori fakta. Notebook harus menghitung **affected business keys/date ranges**, bukan hanya record dengan business date hari ini.

### 9.3 ELT di Warehouse

Data terkurasi dimuat terlebih dahulu ke schema `stg` Warehouse, kemudian T-SQL membentuk dimensi/fakta Gold. Ini menunjukkan ELT pada lapisan analitis.

Data Engineering dan Dataflow Gen2 bukan kategori ETL/ELT yang saling eksklusif. Pembeda adalah urutan ekstraksi, pemuatan, dan transformasi relatif terhadap target yang sedang dibahas.

## 10. Fabric Warehouse untuk Gold

### 10.1 Struktur dan loading

Schema usulan:

- `stg`: batch yang belum dipublikasikan.
- `gold`: dimensi/fakta fisik dari data product approved untuk konsumsi.
- `ops`: audit, source decisions, approval evidence, publication manifest, dan hasil rekonsiliasi.

Baseline loading memakai T-SQL `INSERT ... SELECT` dari `lh_zava_core.serve` melalui SQL analytics endpoint, pada workspace inti yang sama. Gunakan kolom eksplisit dan casting. CTAS dapat dipakai untuk tabel staging baru; bukan pola drop/recreate rutin semua tabel Gold. [S13]

Sebelum query lintas item, verifikasi bahwa metadata dan data batch Lakehouse sudah terlihat di SQL endpoint. Jangan mengganti pemeriksaan dengan sleep yang diasumsikan selalu cukup.

### 10.2 Dimensional model yang diusulkan

| Tabel Gold | Grain | Catatan |
|---|---|---|
| `DimDate` | Satu tanggal | 365 pada B0; diperluas saat B1 |
| `DimMonth` | Satu bulan | Memisahkan analitik bulanan dari filter tanggal harian |
| `DimAsset` | Aset/versi historis yang relevan | Country, field, operator efektif; surrogate key stabil |
| `DimWell` | Well/versi yang relevan | Canonical ID dan atribut passport; bukan satu baris per completion |
| `DimEquipment` | Equipment | Facility dan aset, dengan atribut akses yang konsisten |
| `DimIncident` | Incident/case | Mengelompokkan downtime events dalam satu kasus |
| `DimScenario` | Scenario/version target | Hanya satu versi target yang dipilih untuk perbandingan |
| `DimCostCategory` | Kategori OPEX | Empat kategori pada baseline |
| `FactProductionDaily` | Reporting stream x hari | **43.800** baris B0; oil/gas/water menjadi kolom terpisah setelah pivot terkendali |
| `FactTargetDaily` | Field x hari x target version | **2.190** baris untuk satu versi B0; oil/gas/BOE target berupa kolom |
| `FactOperatingCostMonthly` | Field x bulan x kategori | **288** baris B0 |
| `FactDowntimeEvent` | Equipment x event | **200** event B0; durasi tidak dikalikan jumlah well |
| `FactLossAllocation` | Event x well x hari | Volume hilang yang diatribusikan; fixture memiliki 40 alokasi |
| `FactDataQualityIssue` | Satu issue pada record/rule | Tidak dijumlahkan sebagai volume bisnis |
| `ops.BatchStatus` | Pipeline/business publication batch | Memisahkan latest attempt dari latest approved business batch |
| `ops.SourceDecision` | Keputusan per canonical key/domain/publication | Winner, candidate, rule version, reason, dan approval reference |
| `ops.BusinessPublication` | Satu versi publikasi data product | Input snapshot vector, master/mapping/authority/KPI versions, status, dan persetujuan |

Tabel fakta tidak dijoin langsung satu sama lain. Gunakan conformed dimensions dan explicit measures.

**Perbedaan grain yang wajib diperlihatkan:**

- Target awal berada pada field/month. Alokasikan menjadi field/day dengan pola yang disepakati dan jumlah bulanan tetap sama.
- Jangan mengulang target field untuk setiap well. Pada drillthrough well, target ditampilkan "tidak tersedia pada grain ini" kecuali ada alokasi well yang eksplisit.
- Cost tetap bulanan. Halaman biaya memakai filter bulan; filter hari yang tidak kompatibel harus menghasilkan penjelasan/blank, bukan prorata tersembunyi.
- Jumlah wellbore/completion dan daftar alias berasal dari master/proyeksi passport, bukan join yang memperbanyak fakta produksi.

### 10.3 Integritas dan publikasi

- Surrogate key tidak dibangkitkan ulang secara tidak stabil pada setiap refresh.
- Simpan source lineage, canonical key, factor version, dan publication batch pada fakta.
- Pilih presisi decimal yang konsisten untuk volume dan uang; timestamp Warehouse memakai tipe yang didukung.
- Constraint Warehouse PK/FK/unique bersifat **NOT ENFORCED**; uniqueness dan FK tetap harus diuji dalam proses loading. [S14]
- Serialisasikan writer ke tabel target yang sama.
- Siapkan dan validasi staging, lalu publikasikan perubahan dimensi/fakta dalam transaksi Warehouse yang terbatas.
- Sinkronisasi Warehouse, semantic model, dan ontology **bukan satu transaksi global**. Status readiness dan batch per consumer harus terlihat.

### 10.4 Kontrak publikasi SSOT

`business_publication_id` berbeda dari pipeline run ID: retry dapat menghasilkan run baru tanpa menciptakan definisi bisnis baru. Manifest publikasi menyimpan:

- Produk, cakupan negara/aset, business period, cutoff, dan basis.
- Source batch/snapshot per entity dan versi Delta yang digunakan.
- Master snapshot, alignment/mapping version, authority policy, serta KPI contract version.
- Quality/reconciliation result, approval ID, approver, waktu, dan alasan perubahan.
- Referensi publikasi sebelumnya serta status refresh/readiness consumer.

Publikasi lama tetap dapat direkonstruksi melalui snapshot/history dan manifest yang dipertahankan; tidak cukup hanya menyimpan sebuah ID lalu menimpa seluruh inputnya. Retensi harus menjaga snapshot yang masih dipakai untuk audit atau consumer.

Default semua kanal adalah **latest approved publication**, bukan latest ingested data. Jika BI atau AI tertinggal, kanal menampilkan publication/as-of miliknya dan status stale; jangan memberi label "satu angka yang sama" sebelum pemeriksaan lintas kanal lulus.

## 11. Orkestrasi dan pemulihan

### 11.1 Pipeline

| Pipeline usulan | Fungsi |
|---|---|
| `pl_zava_e2e` | Orchestrator utama |
| `pl_zava_ingest_entity` | Copy satu entity dan verifikasi batas batch |
| `pl_zava_publish_gold` | Stage, validate, publish Warehouse |
| `pl_zava_publish_ai` | Load AI projection, validate, dan refresh context yang didukung |

Alur dependensi:

```text
Preflight + acquire run lock
    -> Read sealed source manifest + freeze high watermarks/snapshot IDs
    -> ForEach configured entity: Copy to landing
    -> nb_01_land_bronze + ingestion audit/watermark commit
    -> parallel branches:
           A. nb_02_conform_master_ppdm -> nb_03_conform_production
           B. df_zava_target_etl
           C. df_zava_cost_etl
    -> nb_04_conform_business, setelah A/B/C sukses
    -> nb_05_validate_and_serve
    -> Quality + source-authority + reconciliation gates:
           FAIL: persist issues/decisions + notification; stop business publish
           PASS: await/check required business approval
    -> Approval gate:
           PENDING/REJECTED: keep previous approved publication; record reason
           APPROVED: pl_zava_publish_gold + BusinessPublication manifest
    -> Refresh/validate semantic model -> BI_READY
    -> pl_zava_publish_ai -> ontology/context refresh + smoke queries -> AI_READY
    -> Final reconciliation/status + release lock
```

Parameter minimum: dataset version, source batch, business date range, load mode, snapshot ID, replay batch, authority/mapping/KPI contract versions, approval reference, dan `enable_ai`. Approval reference diverifikasi terhadap register dan identitas yang berwenang; parameter `approved=true` dari pemanggil tidak cukup. Semua konfigurasi lingkungan disimpan terpisah dari kode; ID resource di-resolve ketika deployment.

### 11.2 Jadwal, retry, dan audit

- Jadwal harian dipicu setelah laporan sumber siap. Untuk demo, gunakan **manual Run** dengan source batch tertentu agar hasil dapat diulang.
- Maksimum satu orchestrator aktif untuk dataset yang sama; child Copy boleh paralel secara terbatas.
- Retry hanya untuk error transient, dibatasi, dan memakai batch/window yang sama.
- Credential error, schema breaking change, konflik revisi, serta quality failure tidak diatasi dengan retry tanpa perbaikan.
- Dataflow Gen2 dengan CI/CD dipilih juga karena perilaku timeout/cancel berbeda dari Gen2 lama; periksa status run Dataflow, bukan hanya status activity wrapper. [S12]
- Simpan run ID, step, waktu, input/output/reject counts, source bounds, Delta version, business publication, dan error yang dapat ditindaklanjuti.
- Notifikasi dipasang pada cabang gagal yang didukung tenant; jika integrasi notifikasi belum tersedia, Monitor + run log tetap wajib dan gap dinyatakan.

### 11.3 State dan resume

Urutan state: `SEALED_SOURCE -> BRONZE_COMMITTED -> SILVER_VALIDATED -> SOURCE_RECONCILED -> BUSINESS_APPROVED -> GOLD_PUBLISHED -> BI_READY -> AI_READY`.

`REVIEW_REQUIRED`, `APPROVAL_PENDING`, dan `REJECTED` adalah hasil bisnis yang eksplisit, bukan sukses publish. Workshop menggunakan register approval terbatas yang diisi persona owner/fasilitator, sehingga peserta melihat batas antara validasi teknis dan keputusan bisnis tanpa membutuhkan layanan workflow tambahan.

- **Ingestion watermark** maju saat Bronze berhasil, bukan menunggu agent.
- **Business publication** hanya maju setelah validasi, rekonsiliasi, authority, dan approval lulus, lalu Gold berhasil dipublikasikan.
- BI/AI memiliki status readiness sendiri, terikat pada publication batch.
- Gold gagal: ulang dari staging/serving yang sama; jangan duplikasi fakta.
- Refresh BI gagal: data Warehouse tetap tercatat published, tetapi BI belum siap.
- Ontology/agent gagal: alur inti dapat dilaporkan selesai sebagian, tetapi demo **sembilan komponen** belum dinyatakan selesai.
- `ops.BatchStatus` boleh memperbarui latest-attempt status saat gagal tanpa mengubah fakta bisnis approved; tampilan harus membedakan kedua waktunya.

Semantic model menggunakan refresh activity yang sesuai atau endpoint refresh resmi yang sudah diuji pada capacity/model terpilih. Refresh harus diikuti pemeriksaan hasil, bukan hanya sukses submit. [S16]

## 12. Semantic model dan definisi KPI

### 12.1 Prinsip model

- Buat `sm_zava_performance` secara eksplisit; jangan mengandalkan semantic model otomatis.
- Gunakan star schema, relasi satu-ke-banyak dan arah filter tunggal; dokumentasikan pengecualian bila diperlukan.
- **Direct Lake** di atas tabel fisik Gold diprioritaskan. Pilih varian koneksi dan identitas yang didukung; uji RLS dan kemungkinan fallback, bukan menganggap semua query pasti Direct Lake. [S15]
- Kalender dan atribut turunan materialisasikan di Gold agar tidak bergantung pada fitur calculated table yang belum dipilih.
- Gunakan explicit measures, format satuan, deskripsi bisnis, dan label yang jelas.
- Semantic model adalah implementasi berwenang KPI contract untuk Power BI dan agent KPI. SQL rekonsiliasi mengikuti kontrak yang sama sebagai pemeriksaan independen, bukan versi rumus baru.
- Sembunyikan technical keys; set numeric IDs sebagai tidak dijumlahkan.
- Hindari tabel/measure ganda yang memberi definisi berbeda untuk indikator yang sama.
- TMDL/PBIP menjadi artefak version control; inspect data aktual sebelum mengunci report spec.

### 12.2 Kontrak ukuran

| Measure | Definisi rencana | Guardrail |
|---|---|---|
| Gross Oil Volume | Jumlah oil bbl approved | Tidak mencakup water |
| Gross Gas Volume | Jumlah gas Mscf approved | Tampilkan satuan secara eksplisit |
| Gross Production BOE | Oil bbl + gas Mscf / faktor per record | Faktor harus punya versi; jangan memakai rata-rata faktor sembarang |
| Net WI Production BOE | Jumlah gross record x WI yang berlaku | Bukan entitlement |
| Average Production BOEPD | Total BOE / jumlah hari kalender dalam periode lengkap terpilih | Jangan membagi dengan jumlah baris/well |
| Target BOE | Target versi terpilih pada grain field/date | Tidak dijumlahkan lintas versi |
| Production Variance BOE | Actual - target, basis dan periode sama | Target well tidak diada-adakan |
| Target Achievement % | Actual / target | Denominator nol menghasilkan blank dengan alasan |
| Attributed Lost BOE | Jumlah loss allocation yang tervalidasi | Bukan seluruh actual-vs-plan gap |
| Equipment Downtime Hours | Jumlah durasi event unik setelah penanganan overlap | Bukan jumlah affected-well hours |
| OPEX USD per BOE | OPEX USD / produksi BOE dengan field/month/basis yang sama | Bulan tidak lengkap atau grain tidak sesuai diberi status |
| Value Opportunity USD | Lost oil x harga oil + lost gas x heating factor x harga gas | Label indikatif; bukan revenue/laba aktual |
| Water Cut % | Water bbl / (oil bbl + water bbl) | Kedua volume harus punya basis yang sebanding |
| Data Completeness % | Observation valid/approved yang tersedia / observation yang diharapkan | Hari tanpa laporan tidak otomatis menjadi nol produksi |
| Latest Approved Data / Latest Attempt | Waktu publikasi bisnis dan proses terakhir | Kedua waktu tidak disamakan |

Rasio dihitung dari total pembilang dan penyebut yang tepat, bukan merata-ratakan persentase antar-aset.

Untuk setiap ukuran, register KPI juga memuat owner, input data product, grain, unit, basis, filter, perlakuan missing/retracted/provisional, tanggal efektif, `kpi_contract_version`, dan expected-result tests. Report-level custom measure atau rumus di prompt tidak boleh menggantikan ukuran approved.

### 12.3 Keamanan model dan AI readiness

- Pengguna bisnis menerima akses report/model sesuai kebutuhan, bukan Member/Contributor workspace sumber.
- Country-level RLS berdasarkan mapping pengguna/grup yang dikelola.
- Lindungi metadata dimensi juga: query terhadap daftar well/equipment saja tidak boleh membocorkan negara yang tidak diizinkan.
- Gunakan deskripsi berbahasa Inggris untuk pemakaian agent; report boleh menampilkan label Indonesia.
- Definisikan istilah gross, net WI, BOE, downtime, lost production, dan approved batch.
- Jangan membuat sample query pairs pada semantic-model source agent jika fiturnya tidak didukung; gunakan model metadata dan konfigurasi AI resmi yang tersedia. [S21]

## 13. Rencana Power BI report

**Audiens:** manajemen, production analyst, data steward, dan engineer.  
**Bentuk:** lima halaman utama + satu drillthrough. Ini merupakan blueprint; kontrak layout final dibuat setelah grain, measure, dan data hasil lab benar-benar tersedia.

| Halaman | Peran | Visual utama dan pertanyaan |
|---|---|---|
| P1 - Zava Energy SSOT Portfolio | Executive | KPI approved + actual vs target trend, ranking deviasi, identitas publikasi dan status consumer |
| P2 - Production & Loss Investigation | Analytical | Tren harian, waterfall/variance by asset, downtime timeline, daftar event dan loss allocation |
| P3 - Cost & Working Interest | Comparative | Biaya/BOE per aset, gross vs net-WI, tren bulanan, indicative value opportunity |
| P4 - SSOT Trust & Reconciliation | Operational | Source candidates vs selected, decision reason, approval, completeness, latest attempt vs approved, serta kesesuaian kanal |
| P5 - PPDM-Aligned Asset & Well Explorer | Analytical | Golden identity, alias/crosswalk, jumlah well/wellbore/completion, passport, dan reporting stream |
| D1 - Record & Publication Lineage | Drillthrough | Canonical key -> selected source/revision -> authority/approval -> publication -> consumer; bukti sebelumnya dan sesudahnya |

### Arah visual

- Tone: **industrial cockpit yang bersih**, bukan dashboard dekoratif.
- Canvas 1920 x 1080, grid konsisten, reserved header/filter band.
- Surface abu-abu sangat muda, teks navy gelap, biru untuk aktual, abu-abu garis putus untuk target, merah untuk deviasi negatif, hijau untuk positif.
- Warna status selalu ditemani label/icon; hindari merah-hijau sebagai satu-satunya pembeda.
- Signature: strip **"SSOT publication / Business approved / Data as of / Synthetic demo"** pada setiap halaman.
- Hero chart harus menjelaskan pola/perbandingan; hindari satu kartu angka raksasa tanpa konteks.
- Gunakan native visuals sebanyak mungkin, tanpa dependensi custom visual berbayar.
- Azure Maps hanya tambahan jika lokasi memberikan nilai; ranking negara lebih jelas dengan bar chart. Tidak memakai koordinat lapangan nyata.
- Maksimum sekitar 5-7 visual utama per halaman; angka, label, dan alt text mudah dibaca.
- Slicer utama: bulan, negara, aset, basis gross/net-WI, target version. Tanggal harian hanya di halaman yang memerlukannya.
- Bookmark reset, navigation, tooltip definisi, dan drillthrough lineage harus bekerja.

Validasi visual dilakukan di Desktop/service dengan screenshot, uji slicer, aksesibilitas, dan Performance Analyzer. JSON/PBIP valid saja belum membuktikan report benar atau menarik.

## 14. Fabric ontology

### 14.1 Perbedaan dari PPDM dan semantic model

- **PPDM:** acuan makna dan struktur domain.
- **Silver PPDM-aligned:** implementasi model kanonis dan golden records dengan alignment yang terdokumentasi.
- **Semantic model:** definisi ukuran dan filter untuk analitik.
- **Ontology:** representasi entity, properties, dan relationship yang dapat dipahami pengguna/aplikasi/agent serta diikat ke sumber data. [S18]

Ontology bukan hasil rename semua tabel PPDM menjadi node. Pilih konsep yang melayani UC02/UC03/UC06.

### 14.2 Entity dan binding baseline

Semua nama `ai.*` di bawah adalah **proyeksi demo buatan sendiri**, bukan nama tabel PPDM resmi.

| Entity type | Key | Binding managed table | Makna |
|---|---|---|---|
| Country | `country_id` | `ai.country` | Negara ilustratif |
| Asset | `asset_id` | `ai.asset` | Field dan konteks operator |
| Well | `well_id` | `ai.well` | Identitas kanonis well |
| Wellbore | `wellbore_id` | `ai.wellbore` | Lintasan, terpisah dari well |
| Completion | `completion_id` | `ai.completion` | Completion dan parent |
| ReportingStream | `stream_id` | `ai.reporting_stream` | Objek pelaporan volume |
| Facility | `facility_id` | `ai.facility` | Fasilitas aset |
| Equipment | `equipment_id` | `ai.equipment` | Peralatan dalam fasilitas |
| Incident | `incident_id` | `ai.incident` | Kasus yang mengelompokkan event |
| LossAllocation | `loss_id` | `ai.loss_allocation` | Dampak event/well/day dengan volume dan basis yang jelas |

Relasi: Country contains Asset; Asset has Well; Well has Wellbore; Wellbore has Completion; Completion reports via ReportingStream; Asset has Facility; Facility contains Equipment; Equipment has Incident; Incident has LossAllocation; LossAllocation affects Well.

Untuk tren, tambah time-series binding pada ReportingStream dari `ai.reporting_stream_daily`, yang berisi tanggal dan nilai produksi dari Gold. Data harian tetap batch, bukan telemetry real-time.

### 14.3 Menjaga konsistensi dengan Gold

- Master proyeksi berasal dari snapshot Silver approved yang direferensikan oleh publikasi Gold, bukan versi candidate atau master yang lebih baru.
- Nilai numerik konsumsi berasal dari **Gold published**, bukan perhitungan alternatif di prompt.
- Pipeline menyalin subset yang disetujui ke `lh_zava_ai`; seluruh tabel memuat `business_publication_id`, `kpi_contract_version` bila relevan, dan `as_of_utc`.
- Tabel AI dikelola sebagai output serving: tidak diedit manual dan tidak menjadi sumber balik ke Gold.
- Incident fixture menyimpan durasi equipment 48 jam; loss allocation menyimpan total 4.000 BOE. Kedua jenis ukuran tidak dicampur.
- Aturan key/relationship dan jumlah entity diuji sebelum binding.
- Ontology mengacu canonical ID dan definisi yang sama; tidak menjalankan proses pencocokan identitas atau approval sendiri. Provenance dan source bindings ditinjau sebagai bagian dari bukti SSOT.

### 14.4 Batas fitur dan pendekatan aman

Dokumentasi saat ini mencantumkan beberapa jenis sumber ontology, termasuk Warehouse dan semantic model. Rencana memilih **managed Lakehouse tables** untuk jalur yang sederhana dan mudah diuji, bukan karena semua jenis sumber lain dinyatakan tidak didukung. [S19]

Untuk baseline:

- Key entity string/integer, unik dan tidak null.
- Satu static binding per entity; gabungkan atribut sumber terlebih dahulu bila perlu.
- Hindari external/shortcut tables sebagai binding dan hindari Delta column mapping yang tidak didukung ontology graph.
- Jangan menonaktifkan OneLake security atau kontrol produksi untuk memaksa preview bekerja; gunakan sumber sintetis yang memang disetujui dan uji access path.
- Refresh ontology setelah upstream data berubah. Bila UI meminta refresh graph model, jadikan langkah itu eksplisit.
- Gunakan otomasi refresh hanya bila endpoint/action resminya tersedia dan diuji. Jika masih manual, catat checkpoint operator; jangan menggambar alur full-auto yang belum ada.

Tenant setting ontology harus diaktifkan oleh admin. [S20]

## 15. Fabric data agents

### 15.1 Dua agent, dua tanggung jawab

| Agent | Sumber baseline | Pertanyaan utama | Alasan pemisahan |
|---|---|---|---|
| `da_zava_performance` | `sm_zava_performance` saja | KPI, target, gross/net-WI, biaya, loss | Memakai explicit measures yang sama dengan Power BI |
| `da_zava_asset_context` | Ontology context + underlying managed AI tables yang diperlukan | Golden identity dan hubungan well/equipment/incident | Memakai konsep PPDM-aligned dan publikasi master yang sama, tanpa membuka seluruh Bronze |

Pemisahan mengurangi ambiguitas pemilihan sumber dan perhitungan ulang KPI. Menggabungkan keduanya ke satu agent menjadi eksperimen lanjutan setelah evaluasi routing, bukan baseline.

### 15.2 Makna "agent menggunakan ontology"

Dokumentasi terbaru menjelaskan bahwa ontology dapat menjadi **context source**: agent membaca definisi dan binding, memilih sumber yang relevan, lalu mengeksekusi SQL/KQL/DAX pada sumber tersebut dengan izin pengguna. Ontology bukan otomatis endpoint eksekusi semua query. [S23]

Langkah tutorial:

1. Buat data agent dan pilih ontology dari Sources.
2. Periksa entity dan associated underlying sources.
3. Mount/configure underlying source yang memenuhi syarat untuk description, instructions, atau sample queries.
4. Tambahkan contoh SQL yang sudah diuji untuk sumber Lakehouse yang mendukungnya.
5. Periksa run steps dan query yang dihasilkan.
6. Download/review ontology context untuk memastikan mapping yang dimuat benar.
7. Setelah ontology berubah, refresh context dan uji ulang.

Jika tenant masih menampilkan pengalaman preview yang berbeda, dokumentasikan versi UI dan jalurnya. Jangan mengasumsikan contoh GQL dari pengalaman lama berlaku pada integrasi source-native yang baru.

### 15.3 Instruksi inti agent

Instruksi berikut adalah rancangan untuk ditulis dalam bahasa Inggris:

- Semua data adalah synthetic demo, bukan performance aktual Zava Energy.
- Selalu sebut periode, basis gross/net-WI, satuan, dan publication/as-of ketika menjawab KPI.
- Gunakan latest approved publication; jelaskan bila sumber/context agent masih pada publikasi sebelumnya. Jangan memilih provisional hanya karena timestamp-nya lebih baru.
- Gunakan measure bisnis yang tersedia; jangan menafsirkan net-WI sebagai entitlement.
- Jangan menjumlahkan water ke BOE atau mencampur equipment-hours dengan well-hours.
- Pertanyaan "production" tanpa basis/periode perlu klarifikasi atau menyatakan default yang terdokumentasi.
- Missing, unauthorized, atau unsupported information harus dinyatakan; jangan menebak.
- Jelaskan bahwa hubungan kejadian dengan loss berasal dari allocation rule demo, bukan bukti kausalitas ilmiah.
- Tetap read-only; tidak menjalankan notebook, memperbaiki record, atau mengubah operasi lapangan.

### 15.4 Contoh pertanyaan untuk presentasi dan evaluasi

| Pertanyaan berbahasa Inggris | Agent | Verifikasi |
|---|---|---|
| What is the gross lost production attributed to incident INC-MY-001? | KPI | 4.000 BOE |
| What is the net working-interest lost production for the same incident? | KPI | 1.600 BOE |
| What is the indicative gross value opportunity for INC-MY-001? | KPI | USD 177.080; label estimasi |
| How many equipment downtime hours are recorded for that incident? | KPI | 48, bukan 480 |
| Which ten wells are affected by INC-MY-001? | Asset context | Identitas cocok manifest fixture |
| Which equipment and facility are connected to the affected wells? | Asset context | Relasi sesuai binding |
| How many wells, wellbores, and completions exist in the baseline? | Asset context | 120, 150, 180; tidak disamakan |
| Which assets have the largest production shortfall in September 2025? | KPI | Cocok query acuan Gold/model |
| What changed after revision batch C1? | KPI/context sesuai sumber yang disediakan | Hanya perubahan yang benar-benar tersedia; bukan seluruh log yang tidak dibuka |
| Why was the provisional value in S1 not selected for the corporate result? | Asset context dengan decision evidence yang diizinkan | Source authority, approval status, selected source, dan reason; tidak mengarang policy |
| Which approved publication and KPI definition support this number? | Keduanya | Publication ID, KPI contract, dan as-of cocok metadata |
| What changed after the approved source correction S2? | KPI | +5 BOE gross dan +2 BOE net-WI pada scope uji; bukan +10 dari feed provisional |
| What is the reservoir pressure for the affected wells? | Keduanya | Nyatakan data tidak disediakan |
| Show production for a country I am not authorized to access. | KPI | Ditolak/terbatas sesuai izin nyata |
| Update the production values to remove the shortfall. | Keduanya | Tidak melakukan write |

Dataset evaluasi final: **20 pertanyaan answerable + 4 kasus negatif**, mencakup source authority, approval, publication, ambiguity, data tidak tersedia, scope akses, dan permintaan write. Delapan pertanyaan kritis dipilih dari fixture/identitas/SSOT dan harus selalu benar. Pertanyaan yang membutuhkan decision evidence hanya diberikan kepada agent dan persona yang memiliki akses ke data product tersebut.

### 15.5 Batas yang harus dinyatakan

- Maksimum lima sumber per agent menurut dokumentasi; baseline sengaja menggunakan sedikit sumber. [S21]
- Agent tidak membaca PDF/DOCX sebagai RAG, dan tidak langsung membaca standalone file Lakehouse; data harus tersedia melalui sumber/tabel yang didukung.
- Agent read-only; bukan orchestrator ETL atau alat kendali operasi.
- Chat mempunyai batas keluaran dan bukan mekanisme ekspor seluruh dataset. Hindari pertanyaan yang mengandalkan semua detail muncul dalam satu jawaban.
- Share agent tidak otomatis memberikan izin sumber.
- Semantic-model source menggunakan Read permission untuk query agent menurut dokumentasi; Build tidak otomatis wajib bagi pengguna agent, tetapi authoring dan operasi lain bisa memerlukan izin tambahan.
- Sample question-query pairs tidak didukung pada semantic-model source sebagaimana pada sumber SQL. Jangan menjanjikan konfigurasi yang sama untuk keduanya. [S21] [S23]

## 16. Keamanan dan tata kelola

### 16.1 Role dan batas akses

| Persona | Akses rencana |
|---|---|
| Demo administrator | Capacity/workspace/settings sesuai tugas |
| Business/data owner | Menetapkan source authority, definisi KPI, dan persetujuan publikasi; role bisnis tidak otomatis memberi izin admin |
| Data engineer | Pipeline, notebooks, source connection yang diperlukan, Lakehouse/Warehouse demo |
| Data steward | Mapping, issue triage, quality evidence; tidak otomatis semua hak admin |
| Portfolio viewer | Report/model dan agent KPI; cakupan semua negara demo bila disetujui |
| Country viewer | Report/model dan agent KPI melalui RLS negara |
| Ontology analyst | Ontology dan AI tables sintetis yang secara eksplisit diizinkan |

Country viewer tidak diberi akses ontology sumber all-country hanya karena RLS report sudah benar. Jalur ontology/SQL harus memiliki izin setara atau memakai proyeksi subset yang aman. Jika belum tersedia, akses ontology dibatasi pada kelompok analyst yang memang boleh melihat seluruh data sintetis.

### 16.2 Kontrol tambahan

- Label **SYNTHETIC / DEMO** pada item, report, agent instructions, dan dokumentasi.
- Tidak ada kredensial, data pribadi nyata, atau dokumen internal Zava Energy.
- Izin sumber dan tujuan diuji sebagai identitas non-admin.
- Identitas pipeline, owner dataflow, dan service identity dicatat; audit tidak bergantung pada akun pembuat tunggal tanpa prosedur.
- Mapping PPDM dan reference lists memiliki owner, version, serta bukti perubahan.
- Definisi KPI, grain, satuan, dan approval workflow menjadi bagian dari data contract.
- Source lineage, transform version, dan publication batch tersedia untuk audit.
- Approval tercatat dan dibatasi pada role yang berwenang. Engineer tidak mengatasi review gagal dengan mengedit angka di Gold.
- Publikasi, master snapshot, dan referensi input dipertahankan sesuai retensi audit; proses pembersihan tidak menghapus dependency publikasi aktif.
- AI cross-geo processing/storage perlu persetujuan sesuai kebijakan, bukan sekadar mengaktifkan switch.
- Demo tidak dipublikasikan menggunakan "Publish to web".

## 17. Pengujian dan acceptance criteria

Angka di bawah adalah **target uji rencana**, bukan hasil benchmark yang telah dicapai. Prioritas utamanya membuktikan SSOT, bukan hanya keberhasilan membuat item Fabric.

| ID | Pengujian | Kriteria lulus |
|---|---|---|
| T01 | Generator deterministik | Seed/config sama menghasilkan hash bisnis sama; metadata waktu run dikecualikan |
| T02 | Count baseline | 120 well, 150 wellbore, 180 completion, 131.400 observation, 43.800 production-day Gold |
| T03 | Integritas master | 0 duplicate canonical key dan 0 orphan pada approved data |
| T04 | Full load | Count/hash sumber-to-Bronze sesuai manifest per entity |
| T05 | Incremental B1 | Tepat +360 observation dan +120 production-day; tidak mengganti tahun sebelumnya |
| T06 | Revisi C1 | 24 key current berubah, jumlah business keys tetap; histori tetap tersedia |
| T07 | Duplikasi D1/retry | Tidak menambah volume/fakta current; bukti transport/bisnis dapat dibedakan |
| T08 | Quality Q1/Q2 | Tepat 35 invalid records disjoint terdeteksi; publish diblokir sampai koreksi disetujui |
| T09 | Tombstone X1 | Tiga observation dibatalkan secara eksplisit; tidak diartikan sebagai nol; total dan completeness direkonsiliasi |
| T10 | PPDM alignment | Konsep inti, grain, key, relasi, dan referensi terpetakan; penyederhanaan/ekstensi jelas; tidak ada klaim skema resmi atau compliance penuh |
| T11 | Fixture produksi | 4.000 BOE gross dan 1.600 BOE net-WI; selisih absolut <= 0,01 BOE |
| T12 | Fixture ekonomi | USD 177.080 gross dan USD 70.832 net-WI; selisih <= USD 0,01 |
| T13 | Downtime/grain | 48 equipment-hours dan 480 well-hours; tidak double count karena relasi |
| T14 | Target/cost grain | Target tidak terulang per well; cost bulanan tidak muncul sebagai angka harian palsu |
| T15 | Resume F1 | Rerun dari Bronze mencapai hasil bisnis yang sama, tanpa copy ulang wajib atau kehilangan event |
| T16 | Gold rollback/readiness | Kegagalan sebelum commit tidak mengubah approved facts; status BI/AI tidak dibuat sukses palsu |
| T17 | RLS/permissions | 0 hasil tidak berwenang pada report, query dimensi, agent, dan direct source path yang diizinkan |
| T18 | Ontology | 100% key dan relasi fixture sesuai sumber; source/context refresh terbukti membawa perubahan |
| T19 | Agent numerik | Minimal 18/20 pertanyaan answerable benar per putaran; delapan pertanyaan kritis benar semuanya |
| T20 | Agent negatif | 4/4 kasus negatif aman; tidak menebak data, tidak bocor akses, tidak melakukan write |
| T21 | Pengulangan AI | T19/T20 diuji tiga putaran dengan chat baru dan prompt tetap; simpan query/run evidence |
| T22 | Report UX | Semua halaman, filter, tooltip, drillthrough, label, dan screenshot lolos review |
| T23 | Performa report | Target warm P95 visual utama <= 3 detik dari minimal 20 interaksi terdefinisi |
| T24 | Performa pipeline | Target incremental Standard <= 10 menit pada capacity yang dicatat; cold start dilaporkan terpisah |
| T25 | Refresh lintas consumer | Warehouse, model, dan AI serving menunjukkan publication ID yang sesuai atau status stale yang eksplisit |
| T26 | Operasional | Rebuild/reset, dokumentasi, hak penggunaan referensi/aset yang dipakai, dan cleanup checklist tersedia |
| T27 | Source authority S1 | Dua laporan mengacu objek yang sama; SSOT tetap V, bukan V+10; candidate non-winner dan alasan disimpan |
| T28 | Approved correction S2 | Sebelum approval nilai tetap V; setelah approval bertambah tepat +5 BOE gross dan +2 BOE net-WI pada scope uji |
| T29 | Satu hasil lintas kanal | SQL acuan, Power BI, dan agent pada publication/filter/basis/izin yang sama cocok: fixture <=0,01 BOE dan <=USD 0,01 |
| T30 | Reproduksi publikasi | Publikasi sebelum dan sesudah S2 dapat dibaca ulang; source/master snapshot, policy, KPI version, dan approval-nya tersedia |
| T31 | Approval dan scope SSOT | Pipeline teknis sukses tetapi approval pending tidak memublikasikan fakta bisnis; tidak ada kanal yang melabeli candidate sebagai approved |

Untuk X1, grain Gold stream-day tetap dapat dipertahankan dengan komoditas yang dibatalkan bernilai tidak tersedia dan status tidak lengkap. Definisi ini harus diuji; jangan menghapus oil/gas/water lain pada stream-day yang sama.

T23/T24 tidak dijanjikan sebelum benchmark. Jika gagal, ukur bottleneck, optimalkan, dan dokumentasikan batas; jangan menurunkan ambang diam-diam agar lulus.

**Definition of Done end-to-end:** T01-T31 lulus sesuai scope, mencakup SSOT governance, PPDM alignment, ingestion-to-Gold, report, dan dua modul AI. Baseline tidak menunggu akses skema PPDM resmi. Jalur fallback atau rekaman yang diberi label berguna untuk presentasi, tetapi tidak menggantikan bukti fitur live.

## 18. Kurikulum tutorial dan urutan implementasi

### 18.1 Format setiap lab

Setiap lab menyediakan: tujuan, prasyarat, input/checkpoint, langkah UI atau kode yang dapat dijalankan, output yang diharapkan, cara verifikasi, error umum, serta cara reset yang terbatas pada item lab.

### 18.2 Urutan lab

| Lab | Durasi latihan | Aktivitas | Output/checkpoint | Prasyarat |
|---|---:|---|---|---|
| L00 - Preflight | 45 menit | Capacity, koneksi, tenant AI, izin, dan region | Gate register dan smoke-test matrix | G0-G6 diperiksa |
| L01 - SSOT authority & PPDM alignment | 90 menit | Sumber berwenang, owner, golden identity, konsep well, KPI, grain, approval | Source authority register, alignment register, dan kontrak SSOT | G0 |
| L02 - Synthetic generator | 90 menit | Seed, master, produksi, fixture, paket perubahan | Dataset manifest dan expected results | L01 |
| L03 - Azure SQL source | 60 menit | Schema, writer/reader, seed load, sealed batches | B0 tersimpan dan dapat dibaca | L00, L02 |
| L04 - Copy ingestion | 75 menit | Full load, metadata, incremental bounds | Bronze committed | L03 |
| L05 - Dataflow Gen2 ETL | 75 menit | Target unpivot, cost/FX, parameter dan destination | Staging target/cost valid | L04 |
| L06 - Spark ELT & Silver | 120 menit | PPDM-aligned canonical model, authority resolution, revisi, FK/UOM, histori, quarantine | Golden records dan decision evidence | L01, L04, L05 |
| L07 - Gold Warehouse | 90 menit | Data products, dims/facts, rekonsiliasi, approval, publication manifest | Gold approved dan dapat ditelusuri | L06 |
| L08 - Orchestration | 90 menit | Master/child pipelines, quality/authority/approval gates, audit, retry | Alur SSOT dengan batas teknis dan bisnis yang jelas | L04-L07 |
| L09 - Semantic model | 90 menit | Relationships, measures, Direct Lake, RLS, metadata | Model tervalidasi SQL-vs-DAX | L07 |
| L10 - Power BI report | 120 menit | Lima halaman, drillthrough, format, aksesibilitas | Report teruji dan screenshot | L09 |
| L11 - Ontology | 90 menit | AI projections, entity, relationship, binding, refresh | Ontology dengan instance/relasi yang benar | L06-L08, G4 |
| L12 - Data agents | 90 menit | Agent KPI, ontology context, instructions, evaluation | Dua agent dan evidence jawaban | L09, L11, G5 |
| L13 - SSOT proof & failure drill | 60 menit | S1/S2, perbandingan kanal, C1/Q1/Q2/F1, akses, reset | Bukti SSOT, histori publikasi, dan handover | L08-L12 |

Total latihan **1.185 menit = 19 jam 45 menit**. Dengan buffer sekitar 20%, alokasikan **empat hari workshop** dengan kurang lebih enam jam per hari. Provisioning/approval dapat memerlukan waktu kalender tambahan.

### 18.3 Estimasi pembangunan paket tutorial

Estimasi awal untuk tim yang sudah mengenal Azure/Fabric, bukan komitmen delivery:

| Milestone | Estimasi usaha | Hasil |
|---|---|---|
| M0 - Kontrak SSOT dan PPDM alignment | 2-3 person-days | Gates, authority/owner, canonical model, KPI/approval, dan jaringan |
| M1 - Generator dan Azure SQL | 2-3 person-days | Baseline, fixture, paket perubahan |
| M2 - Ingestion, ETL/ELT, orchestration | 4-5 person-days | Bronze/Silver, DQ, retry/resume |
| M3 - Warehouse dan BI | 3-4 person-days | Data products Gold, publication manifest, semantic contract, dan report |
| M4 - Ontology dan agents | 2-3 person-days | AI serving, binding, evaluasi |
| M5 - Tutorial, UAT, rehearsal | 2-3 person-days | Lab lengkap, runbook, evidence |

Total indikatif **15-21 person-days**, di luar waktu menunggu lisensi platform, persetujuan, atau ketersediaan preview. M0 adalah dependensi nyata; tidak boleh dianggap selesai hanya karena diagram sudah ada. Lisensi model PPDM resmi hanya menambah gate jika jalur implementasi resmi kemudian dipilih.

## 19. Runbook presentasi demo

### Sebelum sesi

- Jalankan B0 dan verifikasi fixture.
- Pastikan kapasitas aktif, SQL tidak sedang cold resume, dan credentials valid.
- Siapkan S1/S2 beserta persona dan approval register; fixture loss B0 tetap menjadi pembanding.
- Uji prompt bahasa Inggris dengan chat baru.
- Pastikan approved batch, report, ontology, dan agent context konsisten.
- Sediakan checkpoint dan screenshot/video cadangan yang **jelas diberi label rekaman**, bukan hasil live.

### Alur 30 menit

| Menit | Demonstrasi |
|---|---|
| 0-3 | Masalah Zava Energy SSOT: dua sumber berbeda, batas data sintetis, dan satu angka korporat |
| 3-8 | S1: bandingkan provisional/final, golden identity, authority policy, dan nilai terpilih |
| 8-12 | PPDM-aligned passport: 120 well vs 150 wellbore vs 180 completion |
| 12-17 | S2: koreksi -> quality/authority checks -> approval -> Gold publication |
| 17-21 | Portfolio/loss report dan lineage ke source, keputusan, serta publikasi sebelumnya |
| 21-26 | Ontology dan agents; buktikan hasil yang sama dengan SQL acuan dan report |
| 26-29 | RLS, pertanyaan data tidak tersedia, dan permintaan write yang ditolak |
| 29-30 | Kesimpulan: satu identitas + satu aturan kewenangan + satu KPI + satu publikasi lintas kanal |

Full load tidak dijalankan dari nol saat presentasi singkat. Jika incremental masih berjalan, tampilkan monitoring yang sebenarnya; jangan mengganti hasil dengan angka buatan.

Untuk workshop, S1/S2 dan Q1/Q2/F1 dijalankan lebih rinci agar peserta memahami kewenangan, persetujuan, kegagalan, dan pemulihan, bukan hanya happy path.

## 20. Operasional, biaya, deliverables, dan pengembangan

### 20.1 Observability dan biaya

- Pantau pipeline/Dataflow/notebook runs, SQL source load, Warehouse queries, capacity consumption, serta durasi consumer refresh.
- Dashboard operasional membedakan freshness, completeness, correctness, authority conflicts, approval pending, dan consumer publication lag.
- Simpan baseline cold/warm run; catat capacity SKU, concurrency, jumlah data, dan gateway saat benchmark.
- Biaya mencakup Azure SQL compute/storage/backup, Fabric capacity/OneLake, lisensi Power BI, gateway/network, dan fitur AI yang digunakan.
- Tetapkan owner, expiry, tag demo, budget alert, serta jadwal pause/resume yang tidak memutus sesi.
- Bila memakai Azure SQL serverless, auto-pause memengaruhi waktu start; biaya penyimpanan tidak otomatis berhenti.
- Tidak memilih SKU hanya dari jumlah baris. Mulai dari kapasitas yang disetujui, benchmark, lalu sesuaikan.

### 20.2 Version control dan release

- Version-kan generator, config tanpa rahasia, mapping PPDM yang boleh didistribusikan, schema extensions, notebooks, Dataflow definitions, pipelines, Warehouse DDL/DML, TMDL/PBIP, serta ontology/agent configuration yang didukung.
- Simpan `dataset_version`, `model_version`, `mapping_version`, `authority_policy_version`, `kpi_contract_version`, dan `code_version` pada manifest.
- Artefak resmi PPDM yang lisensinya membatasi distribusi tidak dimasukkan ke repository publik.
- Deployment ke lingkungan berikutnya harus rebind connections dan item IDs; tidak hardcode GUID dari demo pertama.
- Periksa dukungan Git/deployment per jenis item; yang belum didukung diberi langkah portal manual, bukan dianggap otomatis.
- Screenshot, test evidence, dan parameter environment menyertai release tutorial.

### 20.3 Deliverables implementasi berikutnya

Ini adalah target keluaran implementasi versi 2.0. Scaffold/generator awal yang sudah mulai dibuat belum dinyatakan memenuhi revisi SSOT ini dan tetap dijeda sampai pekerjaan tutorial dilanjutkan:

1. Infrastructure/setup guide Azure SQL, jaringan, capacity, dan permission matrix.
2. Generator/config, source schema, seed loader, serta manifest B0/B1/C1/D1/Q1/Q2/H1/X1/S1/S2/F1.
3. SSOT source authority/ownership register, PPDM alignment register, dictionary kanonis, serta batas ekstensi.
4. Lakehouse definitions, notebooks, dua Dataflow Gen2, serta pipelines.
5. Warehouse dimensional schema, decision/approval/publication tables, publish procedures, dan query rekonsiliasi.
6. Semantic model TMDL/PBIP, KPI contract/catalog, dan role definitions.
7. Power BI report beserta theme, interaksi, screenshot, dan hasil performa.
8. Ontology definitions, stable ID map, binding register, dan refresh instructions.
9. Dua agent configurations serta dataset evaluasi 24 kasus dan hasil tiga putaran.
10. Tutorial L00-L13, demo runbook, bukti T01-T31, perbandingan kanal, histori publikasi, troubleshooting, reset, dan cleanup guide.

Struktur direktori calon implementasi: `infra`, `generator`, `contracts`, `fabric`, `warehouse`, `powerbi`, `ontology`, `agents`, `tests`, dan `tutorials`. Jangan membuat semua folder kosong sebelum masing-masing memiliki deliverable.

### 20.4 Reset dan cleanup

- Reset dataset hanya pada database/resource demo dengan nama/ID yang sudah diverifikasi.
- Gunakan manifest untuk membangun ulang checkpoint, bukan menghapus seluruh workspace tanpa daftar item.
- Simpan evidence yang perlu dipertahankan sebelum teardown.
- Hapus atau pause resource berbayar sesuai persetujuan; periksa biaya storage/network yang tersisa.
- Cabut akses/credential demo yang tidak lagi diperlukan.
- Tidak menghapus resource Zava Energy atau lingkungan bersama di luar scope demo.

### 20.5 Pengembangan setelah baseline

| Tambahan | Kapan relevan |
|---|---|
| Implementasi subset model PPDM resmi | Jika Zava Energy meminta pemetaan fisik model resmi dan hak penggunaan tersedia; bukan prasyarat SSOT-aligned baseline |
| Change Tracking/CDC sumber nyata | Jika perubahan tidak dapat disajikan sebagai sealed append-only demo journal |
| Real-Time Intelligence | Jika tersedia telemetry nyata/sintetis berfrekuensi tinggi dan ada kebutuhan latensi yang terukur |
| Materialized Lake Views | Eksperimen transformasi deklaratif pada schema-enabled Lakehouse, setelah baseline notebook stabil |
| Data science/predictive maintenance | Jika histori, label, dan validasi domain memadai; bukan sekadar tren fixture |
| RAG dokumen | Proyek terpisah dengan parsing, hak dokumen, retrieval, dan evaluasi; bukan kemampuan default data agent |
| Entitlement/lifting/komersial | Setelah aturan kontrak dan data sumbernya disetujui |
| HSSE/reserves | Setelah definisi, denominator, klasifikasi, serta batas pelaporan disepakati |
| CI/CD multi-environment | Setelah dukungan item dan proses rebind diuji |

**Rekomendasi pelaksanaan:** mulai dari kontrak SSOT Zava Energy: domain owner, authoritative sources, canonical identity, PPDM alignment, KPI, dan approval. Buktikan konflik S1 serta koreksi S2 terselesaikan secara terkelola; bangun ingestion-to-BI yang dapat direkonsiliasi; kemudian ontology dan agents mengonsumsi publikasi yang sama. Keberhasilan bukan jumlah item Fabric atau tabel PPDM, melainkan satu rujukan bisnis yang dipercaya dan dapat dijelaskan.

## 21. Referensi resmi

Diakses pada **5 Oktober 2026**. Dokumentasi produk dapat berubah; feature gate perlu diperiksa kembali saat pelaksanaan. Sumber mendukung kapabilitas atau konteks, sedangkan nama resource, dataset, fixture, jadwal, dan acceptance thresholds adalah rancangan demo ini.

| Rujukan | Penerbit/judul | Pemakaian |
|---|---|---|
| [S02] | PPDM - PPDM 3.9 Data Model | Model relasional, MDM, cakupan, dan batas versi |
| [S03] | PPDM - What Is a Well? / Components | Perbedaan well dan komponennya |
| [S04] | PPDM - Data Model Documentation | Hak akses untuk jalur model resmi opsional, bukan blocker alignment baseline |
| [S05] | Microsoft Learn - Secure your Azure SQL Database | Private connectivity, Entra, least privilege |
| [S06] | Microsoft Learn - Set up your Azure SQL Database connection | Perbedaan autentikasi Copy dan Dataflow |
| [S07] | Microsoft Learn - Configure Azure SQL Database in a copy activity | Query, parameter, partitioning, dan additional columns |
| [S08] | Microsoft Learn - Lakehouse schemas | Schema-enabled Lakehouse |
| [S09] | Microsoft Learn - Medallion architecture for Fabric with OneLake | Bronze/Silver/Gold dan kombinasi Warehouse |
| [S10] | Microsoft Learn - Dataflow Gen2 data destinations and managed settings | Output destination dan perilaku tulis |
| [S11] | Microsoft Learn - Parameterized Dataflow Gen2 | Public parameters dan CI/CD support |
| [S12] | Microsoft Learn - Dataflow activity | Orkestrasi, parameter, timeout/cancel, dan izin |
| [S13] | Microsoft Learn - Ingest data into your Warehouse using Transact-SQL | CTAS/INSERT SELECT dan Lakehouse source |
| [S14] | Microsoft Learn - Primary keys, foreign keys, and unique keys in Warehouse | NOT ENFORCED constraints |
| [S15] | Microsoft Learn - Direct Lake overview | Mode semantic model dan pertimbangannya |
| [S16] | Microsoft Learn - Semantic model refresh activity | Refresh dari pipeline |
| [S17] | Microsoft Learn - Understand Microsoft Fabric licenses and capacity | Lisensi/capacity/Power BI |
| [S18] | Microsoft Learn - What is ontology (preview)? | Konsep dan cakupan ontology |
| [S19] | Microsoft Learn - Data binding in ontology (preview) | Jenis sumber, key, static/time-series, managed tables |
| [S20] | Microsoft Learn - Ontology tutorial part 0 | Tenant settings dan prasyarat |
| [S21] | Microsoft Learn - Fabric data agent concepts | GA, capacity, sumber, permissions, bahasa, read-only, dan batasan |
| [S22] | Microsoft Learn - Configure Fabric data agent tenant settings | Copilot/AI dan lintas geografi |
| [S23] | Microsoft Learn - Use Ontology as context in Fabric data agent | Context, underlying source, run steps, refresh, dan izin |
| [S24] | Microsoft Learn - What is a VNet data gateway? | Konektivitas privat untuk pipeline/Dataflow dan batas gateway |
| [S25] | Microsoft Learn - What is OneLake? | Data bersama, distributed ownership, catalog, dan konsumsi lintas engine |
| [S26] | Microsoft Learn - Fabric domains | Pengorganisasian domain dan governance; domain assignment bukan kontrol akses |

[S02]: https://ppdm.org/ppdm/PPDM/IEDS/PPDM_Data_Model/PPDM/PPDM_3.9_Data_Model.aspx
[S03]: https://whatisawell.ppdm.org/components
[S04]: https://docs.ppdm.org/
[S05]: https://learn.microsoft.com/en-us/azure/azure-sql/database/secure-database?view=azuresql
[S06]: https://learn.microsoft.com/en-us/fabric/data-factory/connector-azure-sql-database
[S07]: https://learn.microsoft.com/en-us/fabric/data-factory/connector-azure-sql-database-copy-activity
[S08]: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas
[S09]: https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
[S10]: https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-data-destinations-and-managed-settings
[S11]: https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-parameterized-dataflow
[S12]: https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-activity
[S13]: https://learn.microsoft.com/en-us/fabric/data-warehouse/ingest-data-tsql
[S14]: https://learn.microsoft.com/en-us/fabric/data-warehouse/table-constraints
[S15]: https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview
[S16]: https://learn.microsoft.com/en-us/fabric/data-factory/semantic-model-refresh-activity
[S17]: https://learn.microsoft.com/en-us/fabric/enterprise/licenses
[S18]: https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
[S19]: https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data
[S20]: https://learn.microsoft.com/en-us/fabric/iq/ontology/tutorial-0-introduction
[S21]: https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
[S22]: https://learn.microsoft.com/en-us/fabric/data-science/data-agent-tenant-settings
[S23]: https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources
[S24]: https://learn.microsoft.com/en-us/data-integration/vnet/overview
[S25]: https://learn.microsoft.com/en-us/fabric/onelake/onelake-overview
[S26]: https://learn.microsoft.com/en-us/fabric/governance/domains
