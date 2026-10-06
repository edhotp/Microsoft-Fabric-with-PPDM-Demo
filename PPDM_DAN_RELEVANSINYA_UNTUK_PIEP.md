# PPDM dan Relevansinya untuk Pertamina PIEP

**Tanggal penyusunan dan akses sumber:** 5 Oktober 2026  
**Tujuan:** menjelaskan Professional Petroleum Data Management (PPDM), kaitannya dengan PIEP, dan posisinya dalam diskusi SSOT serta Microsoft Fabric.  
**Dokumen pendamping:** [Gambaran umum PIEP, konteks data, dan Microsoft Fabric](./PERTAMINA_PIEP_KONTEKS_BISNIS_DATA_DAN_FABRIC.md).

> **Batas penting:** terdapat bukti publik mengenai komitmen historis Direktorat Hulu Pertamina terhadap PPDM. Namun, sumber yang ditinjau belum memverifikasi implementasi, versi model, cakupan penggunaan, atau keanggotaan PPDM yang spesifik untuk PIEP. Bagian penerapan di PIEP dalam dokumen ini merupakan analisis dan rekomendasi, bukan inventaris sistem internal.

## 1. Apa itu PPDM?

**PPDM**, yang dikenal sebagai **Professional Petroleum Data Management**, berkaitan dengan standardisasi dan praktik pengelolaan data industri migas. Istilah ini sering dipakai untuk menyebut asosiasinya, standar yang dikembangkan, atau model datanya. Ketiganya berkaitan, tetapi tidak sama. [S1] [S3] [S8]

**PPDM Association** adalah organisasi global nirlaba yang mengembangkan dan menyebarluaskan standar, praktik pengelolaan data, pendidikan, sertifikasi, dan pengembangan profesional. Cakupan asosiasi saat ini lebih luas daripada petroleum saja: energi dan sumber daya alam, termasuk bidang energi baru dan lingkungan. [S1] [S2]

Secara sederhana, PPDM membantu menjawab:

- Apa arti suatu istilah teknis, misalnya *well* dan *wellbore*?
- Objek data apa yang perlu dibedakan, dan bagaimana hubungannya?
- Bagaimana kode, kategori, dan nilai referensi dipahami secara konsisten?
- Bagaimana data dari organisasi atau aplikasi berbeda dapat digunakan bersama tanpa kehilangan maknanya?

### 1.1 Tiga pengertian yang perlu dibedakan

| Istilah | Maksud | Bukan berarti |
|---|---|---|
| PPDM Association | Organisasi dan komunitas profesional yang mengembangkan standar serta praktik pengelolaan data | Perusahaan operator migas atau regulator yang menerbitkan izin operasi |
| Standar dan sumber daya PPDM | Definisi, model, referensi, serta panduan yang membantu konsistensi dan interoperabilitas data | Satu paket aplikasi yang otomatis menyelesaikan seluruh masalah data |
| PPDM Data Model | Model data relasional untuk mendukung pengelolaan data dan pengembangan aplikasi bisnis | Database berisi seluruh data migas dunia, dashboard, atau layanan cloud siap pakai |

Dengan demikian, **PPDM bukan Microsoft Fabric, bukan Power BI, dan bukan produk database tertentu**. PPDM dapat menjadi acuan makna dan struktur data; perangkat lunak menyediakan sarana untuk menerapkan, mengelola, dan menggunakan data tersebut. [S2] [S3]

## 2. Apa saja yang disediakan PPDM?

### 2.1 PPDM Data Model

Halaman resmi PPDM menjelaskan model datanya sebagai **model relasional** yang mendukung strategi *Master Data Management* (MDM) dan pengembangan aplikasi berorientasi bisnis. Model dikembangkan secara kolaboratif oleh ahli domain, profesional data, pengembang, regulator, serta penyedia data dan aplikasi. [S3]

Model relasional mengorganisasikan informasi dalam entitas atau tabel yang saling berhubungan. Manfaat utamanya bukan sekadar keseragaman nama kolom, tetapi kejelasan objek, atribut, hubungan, dan konteks data.

Halaman PPDM 3.9 menyatakan cakupannya lebih dari 60 area subjek, dan sebagian area bersifat lintas industri. Halaman tersebut juga menyebut penggunaan PPDM 3.9 sebagai dasar pengembangan *Data Objects* yang netral terhadap teknologi. Artinya, pembahasan PPDM tidak perlu dibatasi menjadi sekadar struktur satu produk database. [S3]

**Catatan versi:** dokumen ini merujuk halaman resmi PPDM 3.9 yang dapat diverifikasi. Ini bukan pernyataan bahwa semua implementasi memakai 3.9 atau bahwa tidak ada pengembangan lain. Versi dan sumber daya yang akan digunakan harus dikonfirmasi saat implementasi.

MDM sendiri adalah disiplin pengelolaan identitas dan atribut utama objek bisnis agar dapat dipakai secara konsisten. Memiliki skema PPDM belum otomatis menghasilkan MDM yang berjalan: organisasi tetap membutuhkan pemilik data, mekanisme pencocokan identitas, persetujuan, pengelolaan konflik, dan pemeliharaan.

### 2.2 Definisi bersama: contoh "What Is a Well?"

Salah satu sumber daya PPDM adalah **What Is a Well?**, yang menjelaskan komponen sumur dan hubungan maknanya. Ini penting karena kata "sumur" dalam aplikasi berbeda dapat menunjuk objek yang berbeda pula. [S4]

Berikut penjelasan ringkas dengan bahasa sederhana, bukan pengganti definisi formal PPDM:

| Konsep | Penjelasan sederhana | Mengapa perlu dibedakan? |
|---|---|---|
| Well | Objek sumur yang menaungi komponen-komponennya | Menjadi dasar untuk menentukan apa yang sebenarnya dihitung sebagai satu sumur |
| Well Origin | Lokasi awal penetrasi ke bumi pada permukaan tanah atau dasar laut | Tidak sama dengan titik akhir lintasan pengeboran |
| Wellbore | Jalur pengeboran dari titik awal sampai titik akhir | Satu well dapat memiliki lebih dari satu wellbore |
| Wellbore Segment | Bagian lintasan pengeboran yang unik, termasuk bagian tambahan dari lintasan yang sudah ada | Membantu membedakan lintasan keseluruhan dari bagian yang dibor |
| Wellbore Completion | Kelompok interval kontak yang berfungsi bersama untuk produksi atau injeksi | Tidak sama dengan keseluruhan sumur atau satu catatan kegiatan pengeboran |
| Well Reporting Stream | Aliran pelaporan turunan untuk alokasi atau agregasi volume | Angka produksi dapat dilaporkan pada objek yang berbeda dari objek fisik sumurnya |

PPDM juga menjelaskan bahwa kemiripan lokasi tidak selalu berarti objek sumur yang sama. Karena itu, penyatuan data tidak boleh hanya mengandalkan nama atau koordinat. Identitas, sejarah, dan hubungan komponen perlu diperiksa. [S4]

**Dampak bisnis:** perbedaan jumlah "sumur" pada dua laporan bisa berasal dari perbedaan definisi objek, bukan sekadar kesalahan penjumlahan.

### 2.3 Reference lists dan tata kelola nilainya

*Reference data* adalah daftar nilai atau kategori yang digunakan untuk menafsirkan data, misalnya kategori objek atau jenis status yang telah disepakati.

PPDM menyediakan sumber daya *reference lists*. Halaman resminya menjelaskan metadata, nilai yang disetujui, daftar seluruh nilai, mekanisme pemeliharaan, dan pengajuan daftar atau nilai baru. Jadi, standardisasi bukan hanya membuat daftar kode, tetapi juga mengatur definisi serta perubahan daftar tersebut. [S5]

Untuk suatu organisasi, penerapannya perlu mencakup:

- Menjaga kode asli dari sumber.
- Memetakan kode sumber ke konsep yang telah disetujui.
- Menyimpan versi pemetaan dan masa berlakunya.
- Menangani nilai yang tidak dikenal sebagai pengecualian, bukan memaksanya ke kategori yang keliru.

Daftar nilai internal PIEP tidak boleh langsung disebut "kode resmi PPDM" tanpa pemeriksaan terhadap referensi dan versi yang digunakan.

### 2.4 Aturan dan praktik pengelolaan data

PPDM menekankan perlunya arti istilah teknis yang jelas dan konsisten sebagai dasar aturan pengelolaan data. [S6]

Dalam penerapan organisasi, prinsip itu dapat diterjemahkan menjadi pemeriksaan identitas, hubungan antar-objek, kelengkapan, satuan, konsistensi waktu, serta jejak perubahan. Namun, aturan bisnis spesifik tetap perlu disepakati oleh pemilik proses.

Contohnya, aturan alokasi produksi, hak atas volume, atau definisi KPI korporat tidak otomatis menjadi seragam hanya karena model datanya mengacu PPDM.

## 3. Apa hubungannya dengan PIEP?

Hubungannya paling tepat dijelaskan dalam **tiga tingkat: konteks bisnis PIEP, bukti historis tingkat Pertamina, dan relevansi implementasi di PIEP**.

### 3.1 Konteks bisnis PIEP: data hulu lintas negara

PIEP berfokus pada pengelolaan aset dan bisnis migas di luar negeri. Publikasi RUPST tahun buku 2025, terbit 5 Juni 2026, menyebut portofolio di 10 negara dan empat benua, serta PT Pertamina Hulu Energi dan PT Pertamina Pedeve Indonesia sebagai pemegang saham. [S9] [S10]

Karakter ini menjadikan konsistensi data lintas aset, entitas, mitra, dan negara relevan untuk dibahas. Akan tetapi, daftar aplikasi sumber, format laporan operator, dan tingkat akses PIEP terhadap data setiap aset belum diverifikasi dalam riset ini.

PPDM relevan karena menyediakan acuan untuk menyelaraskan makna dan struktur data hulu, sementara PIEP membutuhkan informasi yang dapat dibandingkan dan dikonsolidasikan secara benar.

### 3.2 Ada bukti historis pada tingkat Direktorat Hulu Pertamina

Rilis resmi **PPDM Association tanggal 7 Januari 2020**, berjudul *Indonesian Ministry of Energy and Mineral Resources endorses PPDM Data Model as Industry Standard*, memuat pernyataan yang diatribusikan kepada pejabat pengelola aplikasi petroteknikal Direktorat Hulu Pertamina. [S8, halaman 1][S8]

Inti pernyataannya adalah komitmen Direktorat Hulu Pertamina untuk menggunakan PPDM sebagai:

- Model data tingkat korporat.
- Acuan *corporate master data repository*.
- Landasan pertukaran dan integrasi informasi antara korporat dan anak perusahaan hulu melalui kosakata serta makna yang disepakati.

Ini menunjukkan bahwa hubungan PPDM dengan konteks Pertamina **bukan semata-mata usulan teknologi baru dalam dokumen ini**. Sudah ada pernyataan publik historis mengenai arah standardisasi data pada tingkat Direktorat Hulu.

Namun, bukti tersebut adalah **pernyataan komitmen yang dikutip dalam rilis PPDM pada 2020**, bukan laporan audit penyelesaian implementasi di setiap anak perusahaan.

### 3.3 Batas kesimpulan untuk PIEP

| Kesimpulan | Status berdasarkan sumber yang ditinjau |
|---|---|
| PPDM relevan secara domain dengan bisnis hulu internasional PIEP | Analisis yang didukung karakter bisnis dan fungsi PPDM |
| Ada komitmen historis Direktorat Hulu Pertamina menggunakan PPDM | Terdokumentasi dalam rilis resmi PPDM 7 Januari 2020 |
| PIEP telah mengimplementasikan seluruh skema PPDM | Belum terverifikasi |
| PIEP menggunakan PPDM 3.9 pada seluruh aset internasional | Belum terverifikasi |
| PIEP memiliki keanggotaan atau lisensi tertentu dari PPDM | Belum terverifikasi |
| Seluruh data operator/JV PIEP sudah mengikuti PPDM | Belum terverifikasi |
| PIEP menggunakan PPDM bersama Microsoft Fabric | Belum terverifikasi |

**PIEP tidak boleh disamakan dengan PT Pertamina EP atau entitas Pertamina lainnya.** Bukti mengenai satu entitas atau arah kebijakan grup tidak otomatis membuktikan kondisi implementasi teknis entitas lain.

Tidak ditemukannya bukti spesifik juga **bukan bukti bahwa PIEP tidak menggunakan PPDM**. Konfirmasi memerlukan kebijakan data internal, arsitektur, model yang digunakan, perjanjian penggunaan, atau keterangan pemilik data.

Dokumen ini tidak menyimpulkan bahwa suatu ketentuan pengelolaan data Indonesia otomatis berlaku dengan cakupan yang sama terhadap seluruh aset luar negeri PIEP. Kewajiban negara, kontrak, dan hak atas data harus diperiksa tersendiri.

## 4. Manfaat potensial PPDM untuk konteks data PIEP

Tabel berikut merupakan **analisis penerapan**, bukan daftar masalah yang telah terbukti terjadi di PIEP atau daftar tabel resmi PPDM.

| Kebutuhan PIEP yang perlu dikaji | Kontribusi acuan PPDM | Keputusan internal yang tetap diperlukan |
|---|---|---|
| Mengenali aset dan sumur lintas sumber | Definisi objek dan struktur hubungan yang konsisten | Otoritas penerbit identitas, pemilik master, serta aturan pencocokan |
| Menghubungkan laporan operator dengan data korporat | Kosakata, pemetaan, dan model integrasi bersama | Hak akses, frekuensi, sumber berwenang, serta tata cara persetujuan |
| Membandingkan status objek | Definisi dan reference lists yang dapat dirujuk | Pemetaan istilah lokal, konteks status, dan masa berlaku |
| Menghindari salah tingkat agregasi produksi | Pembedaan well, wellbore, completion, dan reporting stream | Tingkat pelaporan, metode alokasi, serta aturan agregasi |
| Mengelola perubahan operator atau kepemilikan | Acuan objek dan hubungan untuk mendukung integrasi | Tanggal efektif, histori perubahan, kontrak, dan aturan konsolidasi |
| Menelusuri asal data dan koreksi | Praktik pengelolaan data yang konsisten | Metadata lineage, versi, bukti sumber, dan proses koreksi |
| Mengurangi integrasi satu-per-satu antar-aplikasi | Model acuan bersama untuk pemetaan sumber | Prioritas domain, batas model, antarmuka, dan pengelolaan perubahan |

**Batas manfaat:** PPDM tidak otomatis menentukan hak ekonomi produksi, kebijakan akuntansi, faktor konversi BOE, definisi HSSE, atau seluruh struktur ERP PIEP. Acuan domain perlu dilengkapi aturan bisnis dan standar lain yang sesuai.

## 5. Contoh praktis: satu identitas sumur untuk beberapa sumber

Bagian ini adalah ilustrasi konseptual, bukan data PIEP dan bukan salinan struktur PPDM.

Misalkan terdapat tiga kelompok data:

- Laporan operasi menggunakan identitas pada tingkat **well**.
- Aplikasi teknis menyimpan catatan pada tingkat **wellbore**.
- Laporan produksi mengirim volume pada tingkat **reporting stream**.

Jika semuanya digabung menggunakan satu kolom bernama `well_name`, dapat terjadi:

- Objek berbeda dianggap satu karena namanya mirip.
- Objek yang sama dihitung berulang karena menggunakan alias berbeda.
- Volume digandakan ketika satu catatan produksi bergabung ke beberapa catatan komponen.
- Jumlah wellbore dilaporkan sebagai jumlah well.

### Pendekatan yang lebih tepat

1. **Tetapkan arti objek.** Sepakati konsep well, wellbore, completion, dan objek pelaporan menggunakan referensi yang dipilih.
2. **Pisahkan identitas sumber dan identitas kanonis.** Identitas kanonis adalah identitas internal yang disepakati untuk integrasi, bukan pengganti otomatis identitas regulator.
3. **Simpan pemetaan beserta konteks.** Catat sistem sumber, jenis objek, identitas lokal, negara/yurisdiksi bila relevan, masa berlaku, dan status persetujuan.
4. **Kelola hubungan antar-objek secara eksplisit.** Jangan menganggap semua hubungan satu-ke-satu atau menghilangkan histori.
5. **Gabungkan data sesuai granularitas.** Granularitas adalah tingkat detail satu catatan, misalnya satu reporting stream per hari operasi.
6. **Rekonsiliasi sebelum publikasi.** Pastikan penyatuan identitas dan agregasi tidak menambah atau menghilangkan volume secara tidak sah.

PPDM membantu pada landasan makna dan struktur. Proses pencocokan, persetujuan, pengolahan pengecualian, dan implementasi teknis tetap harus dibangun.

## 6. Hubungan PPDM, SSOT, dan Microsoft Fabric

### 6.1 Peran masing-masing

| Unsur | Pertanyaan yang dijawab |
|---|---|
| PIEP sebagai pemilik kebutuhan bisnis | Keputusan apa yang perlu didukung, siapa yang berwenang, dan data apa yang boleh digunakan? |
| PPDM sebagai acuan domain | Apa arti objek, bagaimana hubungan data dipahami, dan referensi mana yang digunakan? |
| Tata kelola internal | Sumber mana yang dipercaya, bagaimana konflik diselesaikan, dan versi mana yang disetujui? |
| Microsoft Fabric | Bagaimana data diintegrasikan, disimpan, diolah, dan disediakan untuk analitik? |
| Power BI | Bagaimana KPI dan informasi analitis disajikan kepada pengguna? |

Microsoft mendokumentasikan Fabric sebagai platform analitik terintegrasi dengan berbagai workload dan OneLake sebagai lapisan data bersama. PPDM berada pada peran yang berbeda dan dapat melengkapi platform tersebut. [S11]

**Ringkasnya: PPDM membantu menyamakan makna data; Fabric membantu menjalankan pengolahan data; tata kelola PIEP menentukan data yang sah dan dipercaya.**

### 6.2 Posisi dalam alur data konseptual

```text
Sumber yang diizinkan: laporan operator, database, file, API
                          |
                          v
Bronze: data sumber beserta identitas, waktu, dan versinya
                          |
                          v
Silver: penyelarasan identitas, definisi, referensi, dan kualitas
        berdasarkan acuan PPDM + keputusan bisnis PIEP
                          |
                          v
Gold: produk data analitis dan KPI yang disetujui
                          |
                          v
             Semantic model dan Power BI
```

Pemisahan Bronze, Silver, dan Gold mengikuti pola medallion yang dijelaskan Microsoft. Penempatan acuan PPDM pada alur tersebut adalah rekomendasi konseptual, bukan arsitektur resmi PIEP. [S12]

Hal penting dalam desain:

- **Jangan ubah bukti sumber tanpa jejak.** Kode dan identitas asli tetap disimpan untuk rekonsiliasi.
- **Jangan menyalin model relasional secara buta.** Tipe data, relasi, aturan integritas, histori, dan kemampuan penyimpanan target perlu dievaluasi.
- **Model integrasi tidak harus sama dengan model dashboard.** Struktur yang kaya hubungan dapat diolah menjadi tabel fakta/dimensi atau agregat sesuai kebutuhan analitik.
- **Satu nama kolom tidak menjamin satu makna.** Pemetaan semantik harus terdokumentasi, bukan hanya mengganti nama.
- **SSOT bukan sekadar satu lakehouse.** Sumber berwenang, definisi, versi, persetujuan, dan akses tetap harus dikelola.

PPDM dan Fabric tidak saling menggantikan. Fabric juga tidak otomatis menjadi "PPDM-compliant" hanya karena sebuah tabel diberi nama `well`.

## 7. Pendekatan awal yang disarankan untuk PIEP

### 7.1 Mulai dari satu domain dan pertanyaan bisnis

Kandidat yang relevan adalah **identitas sumur/aset dan kaitannya dengan pelaporan produksi**, dengan syarat data dan hak akses tersedia.

Jika PIEP hanya menerima data agregat pada tingkat lapangan atau aset, jangan memaksakan model sampai tingkat completion. Kedalaman model harus sesuai kebutuhan dan data yang benar-benar tersedia.

### 7.2 Susun hasil discovery yang konkret

| Hasil | Isi minimum |
|---|---|
| Inventaris sumber | Pemilik, cakupan, hak penggunaan, frekuensi, dan granularitas |
| Glosarium bisnis | Definisi objek dan istilah yang dipilih, sumber referensi, serta perbedaannya dari istilah lokal |
| Model konseptual | Objek dan hubungan yang memang diperlukan, tanpa langsung mengambil seluruh model |
| Pemetaan sumber | Identitas/kode sumber, konsep tujuan, aturan transformasi, versi, dan masa berlaku |
| Aturan kualitas | Pemeriksaan, tingkat keparahan, penanggung jawab, dan proses perbaikan |
| Tata kelola master | Otoritas sumber, persetujuan, penanganan konflik, histori, dan audit |

### 7.3 Bedakan penggunaan sebagai acuan dari implementasi penuh

Ada perbedaan antara:

1. **Menggunakan definisi PPDM:** istilah dan konsep dipakai sebagai referensi glosarium.
2. **Menyelaraskan model internal:** model organisasi dipetakan ke konsep PPDM yang relevan.
3. **Mengimplementasikan model atau komponen PPDM tertentu:** memakai artefak teknis sesuai versi dan hak penggunaan.

Jangan menyebut pendekatan pertama sebagai implementasi penuh atau menyatakan kepatuhan formal tanpa kriteria dan bukti yang jelas.

### 7.4 Ukur keberhasilan dari hasil data, bukan jumlah tabel

Contoh bukti keberhasilan pilot:

- Identitas sumur yang sama dikenali lintas sumber tanpa menggabungkan objek berbeda.
- Record yang lolos validasi memiliki hubungan ke master yang benar.
- Nilai referensi yang belum terpetakan terlihat sebagai pengecualian.
- Agregasi produksi tidak menggandakan volume akibat relasi antar-komponen.
- Koreksi dan pergantian identitas/operator dapat ditelusuri menurut waktu.
- Angka laporan dapat direkonsiliasi ke sumber dan versi yang dipakai.
- Hak akses tetap menghormati batas negara, kontrak, dan organisasi.

Ambang kualitas, toleransi rekonsiliasi, dan waktu penyelesaian pengecualian perlu disetujui pemilik bisnis.

### 7.5 Periksa akses, versi, dan hak penggunaan

Portal dokumentasi teknis PPDM meminta login dan menjelaskan bahwa sebagian sumber daya hanya tersedia bagi anggota. Ketersediaan halaman publik tidak boleh disamakan dengan izin bebas menyalin seluruh model atau mendistribusikan materi teknis. [S7]

Sebelum implementasi, pastikan:

- Versi model dan reference lists yang disetujui.
- Hak akses serta ketentuan penggunaan untuk organisasi, vendor, dan afiliasi terkait.
- Cakupan adaptasi dan distribusi dokumentasi atau artefak teknis.
- Kebijakan perubahan agar pemetaan tetap dapat dipelihara.

Dokumen ini hanya menjelaskan konsep dan relevansi; tidak memuat salinan DDL, kamus data lengkap, atau artefak PPDM yang aksesnya dibatasi.

## 8. Kesimpulan

**PPDM adalah acuan pengelolaan data yang lebih luas daripada satu model database.** Asosiasinya menyediakan standar, definisi, model, reference lists, dan pengembangan profesional untuk membantu data dipahami serta dipakai secara konsisten.

Hubungannya dengan PIEP memiliki dua landasan:

1. **Landasan bisnis:** karakter hulu internasional PIEP membuat konsistensi identitas, definisi, dan hubungan data lintas aset menjadi relevan.
2. **Landasan historis:** rilis resmi PPDM pada 2020 mengutip komitmen Direktorat Hulu Pertamina menggunakan PPDM untuk model data dan master data korporat.

Kedua landasan tersebut **belum membuktikan implementasi teknis spesifik di PIEP**. Langkah yang tepat adalah mengonfirmasi standar internal yang berlaku, memilih domain prioritas, lalu membuktikan manfaatnya melalui pemetaan, kualitas, dan rekonsiliasi data.

Dalam diskusi Microsoft Fabric, PPDM dapat menjadi landasan makna dan struktur data, sedangkan Fabric menjadi platform pelaksanaannya. Kombinasi keduanya baru menghasilkan SSOT yang dapat dipercaya apabila disertai kepemilikan dan tata kelola data yang jelas.

## 9. Sumber resmi dan batas verifikasi

Semua sumber diakses pada **5 Oktober 2026**. Penjelasan ditulis ulang dan disederhanakan; definisi formal tetap mengikuti dokumen resmi yang berlaku.

| Rujukan | Sumber | Penggunaan dan batasnya |
|---|---|---|
| [S1] | PPDM Association - *About Us* | Status organisasi nirlaba, cakupan energi/sumber daya alam, pendidikan, sertifikasi, dan standar |
| [S2] | PPDM - *IEDS (International Energy Data Standards)* | Cakupan standar yang melampaui model data, termasuk semantik, taksonomi, dan reference lists |
| [S3] | PPDM - *PPDM 3.9 Data Model* | Sifat relasional, dukungan MDM, lebih dari 60 area subjek, dan kaitan dengan Data Objects; bukan klaim versi terbaru |
| [S4] | PPDM - *What Is a Well? / Well Components* | Perbedaan well, origin, wellbore, segment, completion, dan reporting stream |
| [S5] | PPDM - *Reference Lists / Reference List Usage Guide* | Metadata, nilai yang disetujui, serta tata kelola daftar referensi |
| [S6] | PPDM - *Data Rules* | Pentingnya arti istilah teknis yang konsisten untuk pengelolaan data |
| [S7] | PPDM - *Data Model Documentation* | Halaman akses menyatakan perlunya login dan pembatasan sebagian sumber daya bagi anggota; bukan pemeriksaan kontrak lisensi tertentu |
| [S8] | PPDM - *Indonesian Ministry of Energy and Mineral Resources endorses PPDM Data Model as Industry Standard* | Rilis 7 Januari 2020, PDF dua halaman; halaman 1 memuat pernyataan komitmen Direktorat Hulu Pertamina. Bukti historis, bukan verifikasi implementasi PIEP tahun 2026 |
| [S9] | PIEP - *About Us* | Fokus bisnis dan aset internasional |
| [S10] | PIEP - *RUPST PIEP 2025: Delivering Tangible Contributions Amid Global Geopolitical Dynamics* | Terbit 5 Juni 2026; konteks portofolio tahun buku 2025 dan pemegang saham |
| [S11] | Microsoft Learn - *What is Microsoft Fabric?* | Peran Fabric sebagai platform analitik terintegrasi |
| [S12] | Microsoft Learn - *Understand medallion architecture for Fabric with OneLake* | Konsep lapisan Bronze/Silver/Gold |

**Batas riset:** tidak ada akses ke sistem internal, bukti keanggotaan, kontrak lisensi, atau repositori model PIEP. Penelusuran publik belum memverifikasi penggunaan PPDM yang spesifik di PIEP; hal ini tidak membuktikan penggunaan maupun ketidakgunaannya. Sumber 2020 dibaca sebagai bukti historis sesuai penerbit dan tanggalnya, bukan penetapan kewajiban hukum terkini.

[S1]: https://ppdm.org/ppdm/PPDM/About_Us/PPDM/About_Us.aspx?hkey=f49acebd-3319-46f2-9844-67e862a4d298
[S2]: https://ppdm.org/ppdm/PPDM/IEDS/PPDM/IEDS.aspx
[S3]: https://ppdm.org/ppdm/PPDM/IEDS/PPDM_Data_Model/PPDM/PPDM_3.9_Data_Model.aspx
[S4]: https://whatisawell.ppdm.org/components
[S5]: https://ppdm.org/ppdm/PPDM/IEDS/Reference_Lists/PPDM/Reference_Lists.aspx
[S6]: https://ppdm.org/ppdm/PPDM/IPDS/Data_Rules/PPDM/Data_Rules.aspx?hkey=cf530f4d-67a5-4997-afc2-4252811df4db
[S7]: https://docs.ppdm.org/
[S8]: https://dl.ppdm.org/dl/2654
[S9]: https://piep.pertamina.com/en/about-us
[S10]: https://piep.pertamina.com/en/berita/rupst-piep-2025-piep-berkontribusi-nyata-di-tengah-dinamika-geopolitik-global
[S11]: https://learn.microsoft.com/en-us/fabric/fundamentals/microsoft-fabric-overview
[S12]: https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
