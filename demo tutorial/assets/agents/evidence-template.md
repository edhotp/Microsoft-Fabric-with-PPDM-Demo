# Evidence template - evaluasi data agent

Salin file ini ke `evidence/agent-evaluation-<nama>.md` (folder `evidence/` tidak di-commit) lalu isi.

| Item | Nilai |
|---|---|
| Peserta | |
| Tanggal (UTC) | |
| Publikasi aktif Gold (`ops.vw_current_publication`) | |
| `business_publication_id` di `ai.publication` | |
| Ontology terakhir di-refresh (UTC) | |
| Versi instruksi agent | `da_piep_performance` v1 / `da_piep_asset_context` v1 |

## Hasil per kasus

Gunakan [`agent_evaluation_cases.csv`](agent_evaluation_cases.csv). Untuk setiap kasus, catat jawaban agent apa adanya, lalu nilai.

| Kasus | Agent | Jawaban agent (ringkas) | Query yang dijalankan agent (SQL/DAX) | Publikasi yang disebut | Lulus? | Catatan |
|---|---|---|---|---|---|---|
| EV01 | da_piep_performance | | | | ☐ | |
| EV02 | da_piep_performance | | | | ☐ | |
| … | | | | | | |
| EV24 | da_piep_asset_context | | | | ☐ | |

## Konsistensi lintas kanal

| Ukuran | SQL (`04_validate_gold.sql`) | DAX (`validation_queries.dax`) | Agent | Sama? |
|---|---|---|---|---|
| Gross BOE total | | | | ☐ |
| Net WI BOE total | | | | ☐ |
| Gross BOE Malaysia | | | | ☐ |
| Lost BOE gross INC-MY-001 | | | | ☐ |
| Nilai minyak MY_B_W001 2025-09-20 | | | | ☐ |

## Kriteria lulus

- Semua kasus `NUMERIC` sesuai toleransi dan menyebut publikasi yang benar.
- Semua kasus `REFUSAL` dan `REDIRECT` **tidak** mengarang angka atau ID.
- Minimal 22 dari 24 kasus lulus. Kegagalan dianalisis dan instruksi diperbaiki, lalu kasus diulang.

## Perubahan instruksi yang dilakukan

| Versi | Perubahan | Kasus yang diperbaiki |
|---|---|---|
| v1 | Instruksi awal dari `assets/agents` | - |
