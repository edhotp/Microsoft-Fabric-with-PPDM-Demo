# Spesifikasi semantic model dan laporan `Zava Energy SSOT`

Dokumen ini adalah kontrak build untuk Lab 09 (semantic model) dan Lab 10 (report). Semua nama tabel dan kolom sesuai `assets/sql/warehouse/01_create_objects.sql`.

## Semantic model `sm_zava_performance`

- **Mode:** Direct Lake, sumber `wh_zava_gold`.
- **Tabel dari schema `gold`:** `dim_date`, `dim_asset`, `dim_well`, `dim_equipment`, `dim_incident`, `dim_scenario`, `dim_cost_category`, `fact_production_daily`, `fact_target_daily`, `fact_operating_cost_monthly`, `fact_downtime_event`, `fact_loss_allocation`, dan `source_decision`.
- **Tabel dari schema `ops`:** `publication`. Gunakan tabel fisik, jangan view, supaya Direct Lake tidak fallback ke DirectQuery.
- **Tabel stg tidak dipakai:** jangan pilih tabel `stg.*`. Tabel tersebut berisi kandidat yang belum disetujui.

### Relasi

Gunakan model bintang (*star schema*). Semua relasi *many-to-one* dengan arah filter *single*.

| Dari (many) | Ke (one) | Catatan |
|---|---|---|
| `fact_production_daily[DateKey]` | `dim_date[DateKey]` | |
| `fact_production_daily[WellKey]` | `dim_well[WellKey]` | |
| `fact_production_daily[AssetKey]` | `dim_asset[AssetKey]` | |
| `fact_target_daily[DateKey]` | `dim_date[DateKey]` | |
| `fact_target_daily[AssetKey]` | `dim_asset[AssetKey]` | |
| `fact_target_daily[ScenarioKey]` | `dim_scenario[ScenarioKey]` | |
| `fact_operating_cost_monthly[MonthDateKey]` | `dim_date[DateKey]` | Grain bulanan (tanggal 1) |
| `fact_operating_cost_monthly[AssetKey]` | `dim_asset[AssetKey]` | |
| `fact_operating_cost_monthly[CostCategoryKey]` | `dim_cost_category[CostCategoryKey]` | |
| `fact_downtime_event[StartDateKey]` | `dim_date[DateKey]` | |
| `fact_downtime_event[IncidentKey]` | `dim_incident[IncidentKey]` | |
| `fact_downtime_event[EquipmentKey]` | `dim_equipment[EquipmentKey]` | |
| `fact_downtime_event[AssetKey]` | `dim_asset[AssetKey]` | |
| `fact_loss_allocation[DateKey]` | `dim_date[DateKey]` | |
| `fact_loss_allocation[WellKey]` | `dim_well[WellKey]` | |
| `fact_loss_allocation[AssetKey]` | `dim_asset[AssetKey]` | |
| `fact_loss_allocation[IncidentKey]` | `dim_incident[IncidentKey]` | |
| `fact_loss_allocation[EquipmentKey]` | `dim_equipment[EquipmentKey]` | |
| `source_decision[WellId]` | `dim_well[WellId]` | |
| `source_decision[BusinessDate]` | `dim_date[Date]` | |

> [!IMPORTANT]
> Jangan buat relasi `dim_well → dim_asset` atau `dim_equipment → dim_asset`. Fakta sudah terhubung langsung ke `dim_asset`, jadi relasi tambahan menimbulkan jalur ambigu. Atribut negara dan aset sudah tersedia di `dim_well` dan `dim_equipment`.

### Pengaturan model

- Tandai `dim_date` sebagai *date table* dengan kolom `Date`.
- Sembunyikan semua kolom kunci (`*Key`) dan kolom `PublicationId` di **semua** tabel `gold`. Model hanya berisi satu publikasi; kolom ini yang terlihat terbukti membuat data agent mencoba memfilter publikasi dan mengembalikan hasil kosong.
- Urutkan `dim_date[MonthName]` berdasarkan `MonthNumber`.

| Measure | Format |
|---|---|
| Measure BOE dan volume | `#,0` |
| Measure `%` | Persentase dengan 1 desimal |
| Measure USD | Mata uang `$#,0` |

### Measure

Tambahkan semua measure dari [`measures.dax`](measures.dax) melalui DAX query view dengan **Update model with changes**.

### Row-level security (RLS) demo

| Role | Tabel | Ekspresi DAX |
|---|---|---|
| `Country DZ` | `dim_asset` | `[CountryCode] = "DZ"` |
| `Country DZ` | `dim_well` | `[CountryCode] = "DZ"` |
| `Country MY` | `dim_asset` | `[CountryCode] = "MY"` |
| `Country MY` | `dim_well` | `[CountryCode] = "MY"` |
| `Country IQ` | `dim_asset` | `[CountryCode] = "IQ"` |
| `Country IQ` | `dim_well` | `[CountryCode] = "IQ"` |

Uji role dengan **View as**. Role tidak menggantikan izin workspace; workspace Viewer tetap memerlukan izin *Build* atau *Read* sesuai skenario.

## Laporan `Zava Energy SSOT - Performance & Data Trust`

Terapkan tema [`zava-ssot-theme.json`](zava-ssot-theme.json). Tema ini adalah palet workshop, bukan brand resmi perusahaan mana pun. Kanvas 16:9 (1280 × 720).

| # | Halaman | Pertanyaan bisnis | Visual utama |
|---|---|---|---|
| 1 | **SSOT Overview** | Berapa produksi dan pencapaian target menurut satu versi kebenaran? | Card (Gross BOE, Net WI BOE, Target Achievement %, Data Completeness %), line chart Gross BOE vs Target BOE per `dim_date[Date]`, clustered bar Gross BOE per `dim_asset[CountryName]`, card `Trust Banner` di header |
| 2 | **Asset Performance** | Aset dan sumur mana yang di bawah target? | Matrix `dim_asset[CountryName] > dim_asset[AssetName]` dengan Gross BOE, Target BOE, Variance, Achievement %; bar top 10 `dim_well[WellName]` by Gross BOE; slicer `dim_date[YearMonth]` |
| 3 | **Data Trust** | Seberapa bisa dipercaya angka ini? | Card Current Publication, Approved By, Published At UTC, Gold Matches Publication; bar Data Completeness % per country; table `source_decision` (WellId, BusinessDate, Commodity, DecisionStatus, SelectedSourceSystem, Reason); table `publication` (PublicationId, Status, DecidedBy, PublishedAtUtc) |
| 4 | **Incident INC-MY-001** | Berapa dampak insiden manifold terhadap produksi dan nilai? | Slicer `dim_incident[IncidentId]` (default INC-MY-001), card Affected Wells, Lost BOE Gross, Lost BOE Net WI, Loss Value USD Gross, Downtime Hours; column chart Lost BOE Gross per `dim_well[WellName]`; table `fact_downtime_event` |
| 5 | **Cost** | Berapa opex dan opex per BOE? | Stacked column Opex USD per `dim_date[YearMonth]` dan `dim_cost_category[CostCategory]`; card Opex per BOE USD; matrix per country |
| D | **Well Detail** (drillthrough) | Apa riwayat sumur ini? | Drillthrough field `dim_well[WellId]`; card WellName, AliasList, WellboreCount, CompletionCount; line chart Oil/Gas/Water per tanggal; table `source_decision` sumur tersebut |

Aturan desain:

- Header setiap halaman memuat `Trust Banner`, sehingga setiap angka selalu terlihat bersama ID publikasinya.
- Gunakan warna `bad` hanya untuk angka di bawah target atau isu kualitas.
- Tampilkan satuan pada judul visual, misalnya “Gross production (BOE)”.
