# Panduan fasilitator

Panduan ini membantu fasilitator menyiapkan, menjalankan, dan memulihkan workshop **PIEP SSOT di Microsoft Fabric**.

## Agenda dua hari

| Waktu | Hari 1 | Hari 2 |
|---|---|---|
| 08.30–09.15 | Pembukaan, konteks PIEP dan PPDM, Lab 00 | Rekap; mulai batch express H1/X1 |
| 09.15–10.15 | Lab 01 - Kontrak SSOT | Lab 09 - Semantic model |
| 10.30–11.15 | Lab 02 - Generator | Lab 10 - Report |
| 11.15–12.15 | Lab 03 - Azure SQL | Lab 10 (lanjutan) |
| 13.15–14.30 | Lab 04 - Copy ke Bronze | Lab 11 - Ontology |
| 14.30–15.30 | Lab 05 - Dataflow Gen2 | Lab 12 - Data agents |
| 15.45–17.15 | Lab 06 - Spark Silver | Lab 13 - Bukti SSOT dan drill |
| 17.15–18.45 | Lab 07 - Gold dan publikasi; Lab 08 dimulai | Penutupan dan diskusi |

> [!TIP]
> Lab 08 dapat diselesaikan pada pagi hari 2 jika hari 1 berjalan lambat. Pipeline berjalan di latar belakang selama peserta mengerjakan semantic model.

## Persiapan T-7 hari

1. Pastikan gate G1–G6 di [Lab 00](tutorial/00-preflight.md) terpenuhi, terutama **kapasitas berbayar F2+** untuk data agent dan tenant setting ontology.
2. Uji seluruh jalur sekali di tenant workshop dengan satu akun peserta.
3. Siapkan resource group `rg-piep-ppdm-demo` dan beri peserta peran Contributor. Alternatifnya, deploy satu Azure SQL per peserta sebelum sesi.
4. Bagikan folder `demo tutorial` melalui zip atau repository Git.
5. Jalankan pemeriksaan lokal paket:

   ```powershell
   pip install -r requirements-test.txt
   python -m pytest tests -m "not spark"
   ```

## Model penyelenggaraan

| Model | Cocok untuk | Catatan |
|---|---|---|
| **Satu workspace per peserta** | Kelas ≤ 15 orang | Paling realistis; kapasitas F8+ disarankan agar notebook tidak antre |
| **Workspace per kelompok (3 orang)** | Kelas besar | Peran dibagi: engineer, owner/approver, analyst |
| **Demo fasilitator + latihan terpilih** | Sesi eksekutif 2–3 jam | Gunakan runbook demo 30 menit di rencana demo |

## Peran dalam kelompok

| Peran | Tanggung jawab di lab |
|---|---|
| Data engineer | Pipeline, notebook, Dataflow, staging |
| Production data owner | Menjalankan `ops.usp_approve_publication` setelah review |
| BI/AI analyst | Semantic model, report, ontology, agent, evaluasi |

Bila memakai peran terpisah, tambahkan UPN owner ke `ops.authorized_approver`. Owner memerlukan izin pada Warehouse untuk menjalankan prosedur.

## Titik pemeriksaan kelas

| Setelah | Angka yang harus sama untuk semua peserta |
|---|---|
| Lab 04 | `new_bronze_rows = 134597` untuk B0 |
| Lab 06 | 131.400 observasi Silver; 0 quarantine |
| Lab 07 | `PUB-B0` Gross BOE 23.840.575,796184 |
| Lab 08 | `PUB-D1` Gross BOE 23.902.231,190928 |
| Lab 10 | `PUB-X1` Gross BOE 23.901.259,782757 |
| Lab 13 | `PUB-S2` Gross BOE 23.901.264,782757 |

Sumber angka: [`assets/expected/expected-results-standard.json`](assets/expected/expected-results-standard.json).

## Waktu eksekusi terukur (kapasitas F8, data standard)

Angka berikut diukur saat seluruh rangkaian B0–S2 dijalankan end-to-end di Fabric. Gunakan sebagai patokan saat menyusun agenda.

| Langkah | Durasi |
|---|---|
| `pl_piep_load_source` (opsi B) per batch | 3–5 menit (B0 ±5 menit) |
| `pl_piep_e2e` per batch (Copy + 5 notebook + 2 Dataflow + staging) | 26–30 menit |
| `pl_piep_publish_gold` (publish + refresh model + `nb_06`) | 4–6 menit |
| Refresh graph ontology | ±5 menit |
| Evaluasi 24 kasus data agent (`evaluate-agents`, 1 putaran) | ±20 menit |

> [!WARNING]
> Beberapa lingkungan demo, misalnya subscription *managed environment*, mem-*pause* kapasitas F secara otomatis pada jam tertentu. Run yang sedang berjalan akan dibatalkan. Prosedur publish bersifat atomik, jadi Gold tetap konsisten. Jalankan ulang pipeline yang terputus setelah kapasitas aktif kembali.

## Jalur pemulihan cepat

| Situasi | Tindakan |
|---|---|
| Peserta tertinggal di Lab 04–06 | Jalankan `pl_piep_e2e` lengkap dari Lab 08 untuk batch berjalan, lalu lanjutkan |
| Azure SQL peserta bermasalah | Arahkan koneksi ke database fasilitator **hanya-baca**; peserta tidak menjalankan `load` |
| Kapasitas penuh atau notebook antre | Aktifkan high concurrency dan session tag; kurangi paralelisme ForEach menjadi 4 |
| Data agent tidak tersedia (G5 gagal) | Demokan dari tenant fasilitator; peserta tetap mengerjakan evaluasi lintas kanal SQL vs DAX |
| Ontology preview bermasalah | Gunakan diagram relasi di Lab 11 dan query SQL contoh agent sebagai pengganti eksplorasi graf |

## Pesan kunci yang perlu ditekankan

1. **SSOT adalah kontrak, bukan lokasi.** Data di OneLake belum menjadi SSOT tanpa authority, quality gate, dan approval.
2. **PPDM-aligned, bukan PPDM-compliant.** Register alignment menunjukkan batas klaim secara jujur.
3. **Satu ID publikasi di semua kanal.** Report, SQL, ontology, dan agent harus menyebut ID yang sama.
4. **Gagal dengan aman.** `Q1` membuktikan bahwa data rusak tidak pernah masuk Gold.
5. **AI mengikuti governance, bukan sebaliknya.** Agent tidak menghitung KPI sendiri dan tidak membaca kandidat yang belum disetujui.

## Pertanyaan diskusi

- Siapa pemilik nyata setiap baris di `source_authority_register.csv` di organisasi Anda?
- Proses approval apa yang sudah ada, misalnya untuk laporan produksi bulanan ke SKK Migas atau mitra, dan bagaimana proses itu dipetakan ke `usp_approve_publication`?
- Area PPDM mana yang paling bernilai untuk distandarkan pertama kali?
