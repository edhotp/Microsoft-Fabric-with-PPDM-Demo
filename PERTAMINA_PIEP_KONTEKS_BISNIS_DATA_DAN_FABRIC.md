# Pertamina PIEP: Gambaran Umum, Konteks Data, dan Relevansi Microsoft Fabric

**Tanggal penyusunan dan akses sumber:** 5 Oktober 2026  
**Tujuan:** bahan pengantar bisnis dan data untuk diskusi awal Single Source of Truth (SSOT) dan Microsoft Fabric.  
**Lingkup:** riset sumber publik resmi; bukan hasil asesmen sistem internal PIEP.

> **Cara membaca:** bagian profil dan kinerja memuat fakta dengan rujukan sumber. Pemetaan domain data, risiko, use case, dan arsitektur merupakan analisis atau rekomendasi konseptual. Dokumen ini **tidak menyatakan bahwa PIEP telah menggunakan Microsoft Fabric**, maupun menganggap contoh sistem sumber sebagai sistem yang benar-benar dipakai PIEP.

## 1. Ringkasan eksekutif

PT Pertamina Internasional Eksplorasi dan Produksi, disingkat **PIEP**, adalah perusahaan dalam Grup Pertamina yang berfokus pada pengelolaan bisnis dan aset hulu minyak dan gas bumi di luar negeri. PIEP didirikan pada **18 November 2013** dan berada dalam lingkup Subholding Upstream Pertamina Hulu Energi (PHE), sebagai Regional Internasional yang juga disebut Regional 5. [S1] [S2]

Karakter internasional ini penting untuk memahami kebutuhan datanya: informasi bisnis perlu dibaca lintas negara, entitas, aset, mitra, mata uang, satuan, dan periode pelaporan. Sebagai gambaran skala, publikasi RUPST tahun buku 2025 melaporkan produksi migas sebesar **212,8 ribu barel setara minyak per hari**, serta portofolio di **10 negara dan empat benua**. Angka ini adalah konteks tahun buku 2025, bukan pembacaan produksi langsung pada tanggal dokumen ini dibuat. [S3]

Dari perspektif data, peluang utamanya bukan sekadar membuat dashboard, tetapi membangun **angka yang konsisten, memiliki definisi bisnis, dapat direkonsiliasi, dan dapat ditelusuri ke sumbernya**. Microsoft Fabric relevan sebagai calon platform integrasi, pengolahan, penyimpanan analitis, dan konsumsi data melalui Power BI. Kesesuaiannya tetap bergantung pada akses data, tata kelola, kebutuhan pengguna, dan batasan operasional PIEP. [S6]

## 2. PIEP secara umum

### 2.1 Identitas dan posisi dalam Grup Pertamina

| Aspek | Penjelasan | Sumber |
|---|---|---|
| Nama | PT Pertamina Internasional Eksplorasi dan Produksi; juga menggunakan nama Pertamina Internasional EP | [S1] |
| Pendirian | 18 November 2013 | [S1] |
| Fokus | Pengelolaan aset internasional dan kegiatan terkait minyak, gas bumi, dan energi di luar negeri | [S1] |
| Posisi bisnis | Regional Internasional/Regional 5 dalam Subholding Upstream Pertamina | [S2] |
| Pemegang saham yang disebut dalam RUPST 2025 | PT Pertamina Hulu Energi dan PT Pertamina Pedeve Indonesia | [S3] |
| Arah kontribusi | Mendukung ketahanan energi Indonesia sekaligus menciptakan nilai ekonomi dari portofolio internasional | [S3] |

Secara sederhana, posisi bisnisnya dapat dibaca sebagai berikut. Diagram ini bukan daftar lengkap kepemilikan saham:

```text
PT Pertamina (Persero)
    |
    +-- PT Pertamina Hulu Energi / Subholding Upstream
            |
            +-- PIEP / Regional Internasional
                    |
                    +-- Portofolio bisnis dan aset hulu luar negeri
```

PIEP perlu dibedakan dari bisnis ritel BBM atau pengelolaan SPBU. Untuk pembahasan data PIEP, titik berangkat yang lebih tepat adalah **portofolio hulu internasional, produksi, cadangan, proyek, biaya, keselamatan, dan nilai ekonomi**, bukan transaksi penjualan BBM ritel.

### 2.2 Portofolio internasional dan pentingnya tanggal referensi

Publikasi PHE pada 11 Juni 2025 menyebut aset PIEP tersebar di 11 negara: Aljazair, Malaysia, Irak, Prancis, Italia, Tanzania, Gabon, Nigeria, Kolombia, Angola, dan Venezuela. Sementara itu, publikasi PIEP tentang RUPST tahun buku 2025, bertanggal 5 Juni 2026, menyebut portofolio di 10 negara dan empat benua. [S2] [S3]

**Perbedaan ini tidak boleh diabaikan atau dijelaskan dengan dugaan.** Dokumen ini memakai angka 10 negara ketika membahas publikasi kinerja tahun buku 2025, tetapi tidak menyimpulkan negara mana yang keluar atau penyebab perubahan cakupannya. Daftar historis 11 negara juga tidak berarti seluruhnya merupakan negara dengan produksi aktif pada periode yang sama.

Perhatikan pula bahwa **negara, wilayah kerja/blok, lapangan, dan entitas perusahaan adalah konsep berbeda**. Profil perusahaan menggunakan istilah 11 wilayah kerja; angka tersebut tidak boleh otomatis dianggap sama dengan jumlah negara. [S1]

Salah satu contoh sejarah ekspansi PIEP adalah Maurel & Prom (M&P). PHE pada 12 April 2023 menyebut M&P sebagai anak perusahaan dengan kepemilikan mayoritas PIEP, setelah akuisisi oleh Grup Pertamina pada 2017. Publikasi tersebut juga menjelaskan adanya aset produksi dan eksplorasi M&P di Afrika dan Amerika Latin. Informasi ini dipakai sebagai konteks sejarah, bukan penetapan persentase kepemilikan terkini. [S4]

**Implikasi data:** hubungan antara negara, perusahaan, kontrak, blok, lapangan, dan kepemilikan perlu dicatat beserta tanggal berlakunya. Kepemilikan saham suatu perusahaan tidak otomatis sama dengan hak produksi pada setiap lapangan.

### 2.3 Peran strategis: membawa pasokan dan nilai ekonomi

Publikasi RUPST 2025 menjelaskan dua arah kontribusi: [S3]

- **Bring the Barrel Home:** mengarahkan manfaat produksi luar negeri untuk mendukung ketahanan pasokan energi Indonesia.
- **Bring the Value Home:** mengoptimalkan nilai ekonomi portofolio melalui peluang pasar internasional dan pengelolaan aset.

Keduanya berarti keberhasilan tidak cukup dilihat dari volume produksi saja. Analisis juga perlu menghubungkan produksi dengan hak atas volume, pengangkatan atau penjualan, tujuan pasokan, biaya, dan nilai ekonomi. Namun, **tidak boleh diasumsikan bahwa seluruh produksi PIEP selalu dikirim secara fisik ke Indonesia**.

### 2.4 Gambaran kinerja yang dapat dijadikan konteks

Berikut angka yang secara eksplisit disampaikan dalam publikasi resmi RUPST tahun buku 2025, terbit 5 Juni 2026. [S3]

| Indikator | Angka yang dilaporkan | Catatan interpretasi |
|---|---|---|
| Produksi migas | 212,8 ribu barel setara minyak per hari | Laju produksi, bukan volume total tahunan |
| Target RKAP produksi migas | 197,70 ribu barel setara minyak per hari | RKAP adalah Rencana Kerja dan Anggaran Perusahaan |
| Pencapaian target produksi migas | Sekitar 108% | Mengikuti pembulatan dalam publikasi |
| Pencapaian KPI perusahaan | 109,13% | KPI perusahaan tidak identik dengan KPI produksi |
| Cakupan portofolio | 10 negara, empat benua | Cakupan sebagaimana disebut dalam publikasi tersebut |

Sumber memakai singkatan **MBOEPD** untuk ribu barel setara minyak per hari. Agar tidak ambigu, dokumen ini menuliskan satuannya secara lengkap. Definisi cakupan konsolidasi, basis gross/net, dan aturan konversi untuk pemakaian analitis harus dikonfirmasi dari laporan atau pemilik data; tidak disimpulkan hanya dari siaran pers.

## 3. Mengapa konteks bisnis PIEP erat dengan data?

Bagian ini adalah **analisis kebutuhan**, bukan pernyataan bahwa PIEP mengalami semua masalah yang disebutkan.

Dalam bisnis hulu internasional, satu keputusan dapat membutuhkan beberapa kelompok informasi sekaligus:

| Keputusan bisnis | Informasi yang perlu dihubungkan |
|---|---|
| Menilai pencapaian produksi | Aktual, target, periode, aset, komoditas, satuan, basis volume, dan revisi laporan |
| Memahami penyebab deviasi | Downtime, kegiatan pemeliharaan, kondisi operasi, pekerjaan sumur, dan penjelasan operator |
| Menilai efisiensi aset | Volume produksi, biaya yang sebanding, kurs, periode akuntansi, dan batas konsolidasi |
| Memantau kontribusi ke Indonesia | Hak atas produksi, lifting, tujuan kargo, penjualan, dan nilai ekonomi |
| Memprioritaskan proyek | Profil produksi, estimasi cadangan, biaya investasi, jadwal, risiko, dan skenario ekonomi |
| Mengawasi keselamatan dan lingkungan | Kejadian, jam kerja atau denominator lain, batas organisasi, dan metodologi pelaporan |

Karena itu, **SSOT bukan sekadar satu tempat penyimpanan**. SSOT adalah kesepakatan mengenai sumber berwenang, definisi, kualitas, versi, persetujuan, dan hak akses. Sistem operasi dapat tetap menjadi *system of record*, sedangkan platform analitik menyajikan versi data yang konsisten dan disetujui untuk pengambilan keputusan.

## 4. Domain data yang relevan

Tabel berikut merupakan **peta awal untuk discovery**, bukan inventaris aplikasi atau tabel internal PIEP.

| Domain | Contoh data | Granularitas yang perlu disepakati | Kegunaan |
|---|---|---|---|
| Master aset dan portofolio | Negara, entitas, kontrak, blok, lapangan, sumur, operator, kepemilikan | Per objek dan periode berlaku | Menghubungkan data lintas fungsi tanpa salah pemetaan |
| Produksi dan operasi | Volume minyak/gas, produksi air, target, downtime, penyebab kehilangan produksi | Per aset/sumur dan hari operasi | Aktual vs target dan analisis deviasi |
| Cadangan, subsurface, dan pengembangan | Estimasi cadangan, asumsi teknis, hasil evaluasi, rencana pengembangan | Per aset, tanggal evaluasi, kategori, dan versi | Evaluasi keberlanjutan produksi dan investasi |
| Lifting dan komersial | Hak volume, pengangkatan, kargo, tujuan, harga, penjualan | Per transaksi/kargo dan periode | Menghubungkan volume dengan pasokan dan nilai ekonomi |
| Keuangan dan biaya | OPEX, CAPEX, anggaran, realisasi, akun, pusat biaya, mata uang, kurs | Per transaksi/akun, aset, dan periode | Pengendalian biaya dan evaluasi ekonomi |
| Pemeliharaan dan keandalan | Peralatan, work order, kerusakan, jadwal, histori pekerjaan | Per peralatan atau kejadian | Evaluasi downtime dan kinerja pemeliharaan |
| HSSE dan keberlanjutan | Insiden, jam kerja, emisi, energi, air, limbah | Per lokasi, kejadian/periode, dan batas pelaporan | Pemantauan keselamatan dan lingkungan |
| Proyek dan pengadaan | Milestone, komitmen biaya, kontrak, vendor, realisasi pekerjaan | Per proyek, paket, kontrak, dan tanggal status | Pengendalian jadwal dan biaya |
| Dokumen dan pelaporan | Laporan operator/JV, persetujuan, laporan manajemen, lampiran teknis | Per dokumen, periode, versi, dan status | Bukti sumber, audit, serta penjelasan angka |

Kelas sumbernya dapat berupa database, aplikasi bisnis, laporan operator, API, spreadsheet, dokumen, atau data deret waktu. **Nama vendor, keberadaan ERP tertentu, historian/SCADA, pola integrasi, dan ketersediaan akses langsung belum diverifikasi.**

Untuk data subsurface berukuran besar atau berformat khusus, jangan langsung mengasumsikan semuanya harus dipindahkan ke Fabric. Kebutuhan awal mungkin cukup berupa metadata, ringkasan hasil evaluasi, dan tautan ke repositori yang berwenang.

## 5. Prinsip data yang paling penting

### 5.1 Jangan mencampur angka dengan makna berbeda

| Perbedaan | Risiko | Prinsip yang disarankan |
|---|---|---|
| Gross, net working interest, dan entitlement | Produksi total lapangan dianggap seluruhnya milik PIEP | Simpan basis volume dan aturan kontraktual; hak ekonomi tidak selalu cukup dihitung sebagai gross dikali satu persentase |
| Produksi dan lifting | Volume diproduksi dianggap sama dengan volume diangkat/dijual pada periode tersebut | Pisahkan fakta produksi, hak volume, lifting, dan penjualan; rekonsiliasi memakai aturan bisnis |
| Volume dan laju produksi | Angka per hari dijumlahkan lintas hari seolah-olah volume | Agregasikan volume dan durasi yang benar; hitung laju rata-rata dari keduanya |
| Minyak, gas, dan BOE | Penjumlahan memakai konversi yang tidak konsisten | Simpan satuan asli, satuan standar, faktor konversi, sumber faktor, dan periode berlaku |
| Aktual, target, dan forecast | Skenario berbeda tampil sebagai satu angka | Simpan jenis skenario serta versi target/forecast |
| Tanggal operasi dan waktu sistem | Hari operasi lokal bergeser akibat konversi zona waktu | Simpan hari operasi, zona waktu, waktu kejadian, dan waktu penerimaan |
| Mata uang lokal dan pelaporan | Biaya lintas negara dijumlahkan tanpa kurs yang sesuai | Simpan mata uang asli, kurs, jenis kurs, tanggal kurs, dan nilai hasil konversi |
| Laporan awal dan final | Koreksi operator menimpa angka yang pernah dilaporkan | Simpan versi dan status persetujuan; sediakan tampilan terbaru serta tampilan sesuai tanggal pelaporan |

Untuk indikator rasio, seperti biaya per BOE atau tingkat insiden, simpan pembilang dan penyebutnya. Jangan merata-ratakan rasio antar-aset tanpa pembobotan dan definisi yang disetujui.

### 5.2 Data harus bisa dipertanggungjawabkan

Setiap produk data penting sebaiknya memiliki:

- **Pemilik bisnis dan data steward:** pihak yang menyetujui definisi, kualitas, dan perbaikan.
- **Kamus data dan KPI:** arti kolom, satuan, cakupan, rumus, pengecualian, dan aturan agregasi.
- **Identitas sumber:** sistem/file sumber, batch, waktu masuk, dan jejak transformasi.
- **Aturan kualitas:** kelengkapan kunci, duplikasi, referensi aset, kewajaran nilai, dan konsistensi periode.
- **Penanganan pengecualian:** data bermasalah dikarantina atau diberi status jelas, bukan dihilangkan diam-diam.
- **Status publikasi:** provisional, reviewed, atau approved sesuai proses yang disepakati.
- **Indikator kesegaran:** waktu pembaruan terakhir dan keterlambatan sumber terlihat oleh pengguna.

Perbedaan angka negara dalam publikasi resmi pada bagian 2 adalah contoh sederhana mengapa atribut waktu dan definisi cakupan perlu menjadi bagian dari desain data.

## 6. Hubungannya dengan Microsoft Fabric

### 6.1 Posisi Fabric dalam solusi

Microsoft Fabric adalah platform analitik berbasis SaaS yang menyatukan kapabilitas integrasi, rekayasa data, analitik, dan pelaporan. OneLake menjadi lapisan data bersama, sedangkan workload seperti Data Factory, Data Engineering, Data Warehouse, Real-Time Intelligence, dan Power BI menangani kebutuhan yang berbeda. [S6] [S7]

Untuk konteks PIEP, posisi yang masuk akal adalah **lapisan integrasi dan analitik terkelola di atas sumber-sumber yang diizinkan**, bukan penggantian otomatis seluruh aplikasi operasional.

| Kebutuhan potensial | Kapabilitas Fabric yang relevan | Batasan atau prasyarat |
|---|---|---|
| Mengumpulkan data berkala | Data Factory, pipeline, Dataflow Gen2 | Periksa konektor, autentikasi, jaringan/gateway, hak ekstraksi, dan batas API |
| Menyatukan akses data analitis | OneLake dan shortcuts | Penyatuan logis tidak selalu memerlukan penyalinan; dukungan sumber dan hak akses tetap harus diperiksa |
| Membersihkan dan menyelaraskan data | Lakehouse, Data Engineering, Spark/notebook | Pemetaan aset, konversi, deduplikasi, dan aturan revisi tetap harus dirancang |
| Menyediakan data terstruktur untuk SQL/BI | Lakehouse dengan SQL analytics endpoint atau Warehouse | Pilih sesuai kebutuhan transformasi, pola akses, dan kompetensi tim |
| Menstandarkan KPI dan dashboard | Power BI semantic model dan report | Definisi ukuran, relasi, kalender, serta aturan akses perlu disepakati |
| Membaca tabel analitis di OneLake | Direct Lake pada semantic model yang sesuai | Bukan pilihan otomatis untuk semua sumber; pertimbangkan tabel, kapasitas, keamanan, dan batas fitur |
| Analitik data yang mengalir | Eventstreams dan Eventhouse dalam Real-Time Intelligence | Hanya jika data tersedia dengan latensi yang diperlukan dan konektivitasnya diizinkan |
| Pengendalian akses dan tata kelola | Microsoft Entra ID, izin workspace/item, serta kapabilitas Fabric dan Microsoft Purview yang relevan | Kontrol harus dikonfigurasi dan diuji; cakupan fitur serta lisensi perlu divalidasi |

Landasan kapabilitas pada tabel: dokumentasi resmi Fabric, OneLake, Direct Lake, keamanan Fabric, dan Real-Time Intelligence. [S6] [S7] [S9] [S10] [S11]

### 6.2 Pola konseptual: Bronze, Silver, Gold

Microsoft mendokumentasikan pola medallion sebagai pemisahan data mentah, data yang telah dibersihkan/diselaraskan, dan data yang siap dikonsumsi. [S8]

```text
Sumber yang diizinkan
Database / laporan operator / file / API
                  |
                  v
     Ingestion dan orkestrasi terkontrol
                  |
                  v
Bronze: bukti sumber dan metadata penerimaan
                  |
                  v
Silver: data tervalidasi dan selaras lintas aset
                  |
                  v
Gold: produk data dan KPI bisnis yang disetujui
                  |
                  v
       Semantic model -> Power BI

Lintas lapisan:
kepemilikan data, kualitas, lineage, keamanan, dan pemantauan
```

Contoh penerapan konseptual:

- **Bronze:** menyimpan laporan produksi sebagaimana diterima, berikut identitas sumber, waktu masuk, batch, dan versinya. File asli dipertahankan sebagai bukti; tabel terstruktur dapat disimpan sebagai Delta.
- **Silver:** memetakan kode aset ke master yang disepakati, menormalkan satuan, mengelola duplikasi/revisi, dan memisahkan data valid dari pengecualian.
- **Gold:** menyediakan tabel analitis aktual vs target, ringkasan deviasi per aset, serta status kualitas dan kesegaran. Silver/Gold berbasis tabel Delta mendukung konsumsi lintas workload Fabric. [S8]

Untuk demo kecil, pemisahan logis dapat dimulai pada lakehouse yang mendukung schema, misalnya `bronze`, `silver`, dan `gold`. Untuk produksi, pemisahan workspace, lakehouse, domain, atau region harus mengikuti kebutuhan isolasi dan kepemilikan data. **Tiga lapisan tidak otomatis berarti tiga negara, tiga tim, atau satu lokasi fisik penyimpanan.**

Jika dibutuhkan, jalur streaming dapat melengkapi alur tersebut: sumber yang disetujui masuk melalui Eventstreams, dianalisis dalam Eventhouse, lalu dikonsumsi sesuai kebutuhan. Jangan menyebut solusi real-time jika sumbernya hanya tersedia melalui laporan harian. [S11]

### 6.3 Apa yang dimaksud Direct Lake?

Direct Lake adalah mode penyimpanan tabel pada semantic model Power BI yang membaca data dari tabel Delta di OneLake dan memuat data yang diperlukan ke memori untuk analisis. Mekanisme ini mengurangi kebutuhan mengimpor ulang seluruh data seperti pada mode Import. [S9]

Namun, Direct Lake **tidak menghapus kebutuhan transformasi, pemodelan, pengaturan kesegaran, atau pengujian keamanan**. Pilihan Direct Lake, Import, atau DirectQuery perlu mengikuti kebutuhan aktual, bukan hanya nama teknologinya.

### 6.4 Tata kelola lintas negara harus dirancang sejak awal

Microsoft mendokumentasikan dukungan autentikasi Entra ID, izin akses, enkripsi, pengaturan geografis tertentu, dan integrasi perlindungan informasi. Keberadaan fitur ini tidak otomatis menjamin pemenuhan seluruh kewajiban kontrak atau regulasi PIEP. [S10]

Prinsip desain yang disarankan:

1. **Hak berbagi data:** periksa hak PIEP atas data operator/JV dan izin pemanfaatannya untuk analitik.
2. **Klasifikasi:** pisahkan data publik, internal, rahasia komersial, data pribadi, serta informasi teknis terbatas.
3. **Residensi dan transfer lintas batas:** evaluasi lokasi data, pemrosesan, metadata, serta batasan tiap workload. Pemilihan region saja bukan bukti kepatuhan.
4. **Least privilege:** batasi akses per negara/aset/fungsi sesuai kebutuhan bisnis.
5. **Keamanan di semua jalur akses:** pembatasan pada report atau semantic model tidak otomatis membatasi akses langsung ke file, tabel, atau workspace.
6. **Retensi dan audit:** tetapkan lama penyimpanan, penghapusan, bukti persetujuan, dan jejak perubahan.
7. **Pemisahan lingkungan:** pisahkan pengembangan, pengujian, dan produksi sesuai tingkat risikonya.

## 7. Use case yang layak diprioritaskan

Prioritas berikut adalah usulan awal berdasarkan kedekatannya dengan konteks bisnis, bukan roadmap resmi PIEP.

| Prioritas | Use case | Nilai yang ingin dibuktikan | Ketergantungan utama |
|---|---|---|---|
| 1 | Produksi aktual vs target lintas aset | Satu definisi capaian dan kemampuan menjelaskan deviasi | Master aset, data produksi, target, satuan, basis volume, versi |
| 1 | Kualitas dan ketepatan waktu pelaporan | Mengetahui data mana yang lengkap, terlambat, atau belum disetujui | Metadata penerimaan, kalender pelaporan, aturan kualitas |
| 2 | Biaya operasi per BOE | Menghubungkan operasi dengan efisiensi ekonomi | Biaya dan produksi dengan periode serta cakupan yang sebanding |
| 2 | Lifting dan kontribusi portofolio | Menjelaskan hubungan antara hak volume, pengangkatan, tujuan, dan nilai | Data kontraktual dan komersial yang diizinkan |
| 2 | HSSE lintas aset | Memantau kejadian dan indikator yang konsisten | Definisi kejadian, denominator, cakupan personel/lokasi |
| 3 | Analitik keandalan atau prediktif | Mendukung investigasi pola downtime dan risiko peralatan | Histori cukup, identitas peralatan, kualitas label, validasi ahli |

**Rekomendasi awal:** mulai dari produksi aktual vs target dan kualitas pelaporan. Keduanya dapat menunjukkan manfaat SSOT tanpa langsung bergantung pada streaming, seluruh dokumen subsurface, atau model AI.

### Contoh lingkup demo lanjutan

Jika dokumen ini dilanjutkan menjadi demo Fabric, lingkup sederhana dapat berupa:

- Master negara/aset dan basis pelaporan.
- Produksi harian dengan satuan dan versi.
- Target produksi untuk periode yang sama.
- Pemetaan satuan atau faktor konversi yang disetujui.
- Metadata batch, persetujuan, dan hasil pemeriksaan kualitas.

Pertanyaan yang hendak dijawab:

1. Bagaimana capaian produksi terhadap target pada periode dan basis yang sama?
2. Aset mana yang paling berkontribusi pada deviasi?
3. Sumber mana yang belum mengirim atau belum menyetujui laporan?
4. Apa perubahan angka setelah koreksi diterima?
5. Dapatkah angka dashboard ditelusuri sampai ke sumbernya?

Keberhasilan demo sebaiknya dibuktikan melalui rekonsiliasi dengan dataset acuan, perhitungan KPI yang dapat diulang, tidak adanya penghitungan ganda setelah revisi, keterlihatan data terlambat, dan pengujian akses pengguna. Target latensi serta toleransi rekonsiliasi harus disetujui, bukan diasumsikan.

Gunakan data publik, data yang telah dianonimkan dengan persetujuan, atau data sintetis yang jelas diberi label. Angka publik agregat dalam dokumen ini bukan data mentah untuk merekonstruksi kinerja setiap aset.

## 8. Hal yang perlu dikonfirmasi sebelum implementasi

Dokumen publik cukup untuk memahami konteks bisnis, tetapi belum menjawab pertanyaan implementasi berikut:

- **Sistem dan akses:** sumber aktual, konektor, format, pemilik, jaringan, kredensial, dan hak ekstraksi.
- **Definisi bisnis:** basis produksi, faktor konversi BOE, hari operasi, konsolidasi entitas, serta versi RKAP.
- **Kualitas dan riwayat:** kelengkapan, duplikasi, koreksi historis, serta proses persetujuan.
- **Kebutuhan layanan:** frekuensi pembaruan, toleransi keterlambatan, pengguna bersamaan, dan periode retensi.
- **Keamanan:** hak operator/JV, batas negara, klasifikasi informasi, dan pola akses pengguna.
- **Lingkungan teknologi:** tenant, region, kapasitas, lisensi, integrasi yang tersedia, serta biaya operasi yang dapat diterima.

Tanpa informasi tersebut, belum tepat menetapkan desain produksi final, menjanjikan penghematan tertentu, menentukan SKU kapasitas, atau menyatakan semua data dapat dipusatkan.

## 9. Kesimpulan

PIEP adalah bisnis hulu internasional dengan kebutuhan pengambilan keputusan yang melintasi aset, negara, entitas, dan mitra. Konteks tersebut membuat **konsistensi makna data, basis perhitungan, waktu berlaku, persetujuan, dan hak akses** sama pentingnya dengan integrasi teknis.

Microsoft Fabric dapat dipertimbangkan untuk membangun SSOT analitis melalui integrasi sumber, OneLake, lapisan Bronze/Silver/Gold, serta semantic model dan Power BI. Nilai bisnisnya bukan semata-mata data terkumpul, tetapi **angka yang dipercaya, dapat dijelaskan, dan layak dipakai mengambil keputusan**.

Langkah berikut yang paling masuk akal adalah discovery singkat bersama pemilik bisnis dan data, kemudian demo terbatas produksi aktual vs target dengan tata kelola dan rekonsiliasi yang terlihat sejak awal.

## 10. Sumber resmi dan batas penggunaannya

Seluruh sumber berikut diakses pada **5 Oktober 2026**. Rujukan perusahaan berasal dari PIEP/PHE; rujukan teknologi berasal dari Microsoft Learn. Ringkasan ditulis ulang untuk penjelasan, bukan salinan laporan.

| Rujukan | Penerbit dan judul | Tanggal/periode dan pemakaian |
|---|---|---|
| [S1] | PIEP - *About Us* | Halaman profil; digunakan untuk nama, tanggal pendirian, mandat, dan istilah wilayah kerja. Tanggal pembaruan tidak ditampilkan |
| [S2] | PHE - *PIEP Raih Prestasi Gemilang di Optimus Award 2024, Buktikan Komitmen Efisiensi dan Inovasi Regional 5* | 11 Juni 2025; posisi Regional Internasional/Regional 5 dan daftar 11 negara pada publikasi tersebut |
| [S3] | PIEP - *RUPST PIEP 2025: Delivering Tangible Contributions Amid Global Geopolitical Dynamics* | 5 Juni 2026; data tahun buku 2025, pemegang saham, produksi, target, KPI, cakupan portofolio, dan arah kontribusi |
| [S4] | PHE - *Anak Perusahaan Pertamina Internasional EP, Maurel & Prom, Catat Laba Bersih 211 Juta USD* | 12 April 2023; konteks sejarah hubungan PIEP dan M&P serta akuisisi 2017, bukan angka kepemilikan terkini |
| [S5] | PIEP - *Annual Reports* | Portal resmi yang menampilkan laporan tahunan dan keberlanjutan 2024/2025; rujukan pendalaman. Daftar dokumennya diverifikasi, tetapi isi PDF tidak dijadikan dasar klaim tambahan dalam dokumen ini |
| [S6] | Microsoft Learn - *What is Microsoft Fabric?* | Gambaran platform dan workload; dokumentasi daring dapat diperbarui |
| [S7] | Microsoft Learn - *OneLake, the unified data lake* | Penyimpanan logis bersama, workspace, dan shortcuts |
| [S8] | Microsoft Learn - *Understand medallion architecture for Fabric with OneLake* | Konsep Bronze/Silver/Gold dan pilihan penerapannya |
| [S9] | Microsoft Learn - *Direct Lake overview* | Mekanisme, kegunaan, dan pertimbangan Direct Lake |
| [S10] | Microsoft Learn - *Security in Microsoft Fabric* | Identitas, izin, perlindungan informasi, dan pertimbangan geografis |
| [S11] | Microsoft Learn - *What Is Real-Time Intelligence in Microsoft Fabric?* | Eventstreams, Eventhouse, dan analitik data yang mengalir |

**Batas verifikasi:** publikasi resmi merupakan bukti pernyataan perusahaan, bukan pengganti audit independen atau konfirmasi pemilik data. Tidak ada akses ke sistem internal PIEP dalam penyusunan dokumen ini. Perbedaan jumlah negara antar-publikasi dipertahankan dengan konteks tanggal, bukan diselaraskan secara spekulatif. Status fitur, dukungan konektor, ketersediaan region, dan lisensi Fabric perlu diperiksa kembali saat implementasi.

[S1]: https://piep.pertamina.com/en/about-us
[S2]: https://phe.pertamina.com/id/media/piep-raih-prestasi-gemilang-di-optimus-award-2024-buktikan-komitmen-efisiensi-dan-inovasi-regional-5
[S3]: https://piep.pertamina.com/en/berita/rupst-piep-2025-piep-berkontribusi-nyata-di-tengah-dinamika-geopolitik-global
[S4]: https://phe.pertamina.com/id/media/anak-perusahaan-pertamina-internasional-ep-maurel-prom-catat-laba-bersih-211-juta-usd
[S5]: https://piep.pertamina.com/en/laporan-tahunan
[S6]: https://learn.microsoft.com/en-us/fabric/fundamentals/microsoft-fabric-overview
[S7]: https://learn.microsoft.com/en-us/fabric/onelake/onelake-overview
[S8]: https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
[S9]: https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview
[S10]: https://learn.microsoft.com/en-us/fabric/security/security-overview
[S11]: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/overview
