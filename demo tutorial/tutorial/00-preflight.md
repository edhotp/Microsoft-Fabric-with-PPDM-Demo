# Lab 00 - Preflight lingkungan workshop

Sebelum membangun apa pun, pastikan kapasitas Fabric, pengaturan tenant, izin Azure, dan tool lokal siap. Banyak kegagalan workshop berasal dari pengaturan tenant yang belum aktif, kapasitas trial yang tidak mendukung data agent, atau region yang berbeda. Lab ini mendeteksi masalah tersebut di awal.

Dalam lab ini Anda akan:

- [ ] Memeriksa gate G0–G6 dari rencana demo.
- [ ] Memastikan kapasitas, workspace, dan pengaturan tenant Fabric.
- [ ] Menyiapkan tool lokal: Python, ODBC Driver 18, dan Azure CLI dengan Bicep.
- [ ] Menyalin file konfigurasi workshop.

## Prasyarat

- Sudah membaca [Overview](overview.md).
- Akun Microsoft Entra ID organisasi dengan akses ke Microsoft Fabric dan subscription Azure.
- Laptop Windows, macOS, atau Linux dengan hak instalasi software.

## 1. Periksa gate workshop

| Gate | Pemeriksaan | Siapa | Status |
|---|---|---|---|
| G0 - Kontrak SSOT | Peserta membaca [Lab 01](01-ssot-authority-ppdm-alignment.md); fasilitator menyetujui register authority demo | Fasilitator | ☐ |
| G1 - Azure | Subscription dan resource group `rg-piep-ppdm-demo`, peran **Contributor** pada resource group. Periksa apakah kebijakan organisasi melarang endpoint publik Azure SQL; jika ya, siapkan [opsi B jaringan privat](03-azure-sql-source.md#opsi-b---jaringan-privat-tanpa-endpoint-publik) | Admin Azure | ☐ |
| G2 - Fabric | Kapasitas F aktif, workspace bisa dibuat, peserta **Admin/Member** di workspace | Admin Fabric | ☐ |
| G3 - Power BI | Lisensi Power BI Pro/PPU untuk author bila kapasitas < F64 | Admin M365 | ☐ |
| G4 - Ontology | Tenant setting **Users can create ontology (preview) items** dan **Users can create Fabric items** aktif | Admin Fabric | ☐ |
| G5 - Data agent | Kapasitas **berbayar F2+** (atau P1+ dengan Fabric aktif); tenant setting data agent dan Copilot/Azure OpenAI aktif; cross-geo processing/storing jika region memerlukannya | Admin Fabric | ☐ |
| G6 - Keamanan | Data sintetis disetujui; koneksi menggunakan Microsoft Entra ID; tidak ada password di repo | Fasilitator | ☐ |

> [!IMPORTANT]
> **Fabric Trial tidak cukup untuk Lab 12.** Data agent memerlukan kapasitas berbayar F2 atau lebih tinggi. Lab 00–11 dapat berjalan di trial, tetapi capacity, data agent, dan sumber datanya harus berada di region yang sama.

## 2. Siapkan Fabric

1. Buka [Microsoft Fabric](https://app.fabric.microsoft.com) dan masuk dengan akun organisasi.
2. Pilih **Workspaces** > **+ New workspace**.
3. Buat workspace **`ws-piep-ppdm-demo`**. Di **Advanced**, pilih kapasitas F yang disiapkan fasilitator.
4. Ulangi untuk workspace AI **`ws-piep-ppdm-ai-demo`** pada kapasitas dan region yang **sama**.
5. Minta admin Fabric memastikan pengaturan tenant berikut di **Admin portal** > **Tenant settings**:

   | Pengaturan | Dipakai di |
   |---|---|
   | Users can create Fabric items | Semua lab |
   | Users can create ontology (preview) items | Lab 11 |
   | Pengaturan Fabric data agent | Lab 12 |
   | Users can use Copilot and other features powered by Azure OpenAI | Lab 12 |
   | Data sent to Azure OpenAI can be processed/stored outside your capacity's geographic region (jika diperlukan region Anda) | Lab 12 |

> [!TIP]
> Anda dapat memeriksa wilayah kapasitas di **Workspace settings** > **License info**. Catat region ini untuk membuat Azure SQL di region yang sama atau terdekat.

## 3. Siapkan tool lokal

1. Instal [Python 3.11+](https://www.python.org/downloads/).
2. Instal [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
3. Instal [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), lalu jalankan `az bicep install`.
4. Buka terminal di folder `demo tutorial`, lalu jalankan:

   ```powershell
   python --version
   az version --query '"azure-cli"'
   az bicep version
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements-azure.txt
   python -m workshop --help
   ```

5. Salin file konfigurasi:

   ```powershell
   Copy-Item config\workshop.example.json config\local.json
   ```

   `config/local.json` sudah tercantum di `.gitignore`. Isi nilainya di Lab 03.

## Verifikasi

- `python -m workshop --help` menampilkan perintah `generate`, `expected`, `render-sql`, `render-warehouse`, `render-contracts`, `build-notebooks`, `run-sql`, `load`, `status`, dan `verify`.
- Dua workspace terlihat di Fabric dengan ikon kapasitas yang sama.
- Semua gate di tabel langkah 1 bertanda ☑ atau memiliki rencana mitigasi yang ditulis fasilitator.

## Pemecahan masalah

| Gejala | Penyebab umum | Solusi |
|---|---|---|
| `pyodbc` gagal diinstal | Build tool tidak ada | Gunakan Python 64-bit resmi; pada Linux instal `unixodbc-dev` |
| Tidak bisa memilih kapasitas saat membuat workspace | Tidak punya izin *contributor* kapasitas | Minta admin kapasitas menambahkan Anda |
| Item **Ontology (preview)** tidak muncul | Tenant setting belum aktif | Lihat langkah 2.5 |

## Langkah berikutnya

> [!div class="nextstepaction"]
> [Lab 01 - Kontrak SSOT dan PPDM alignment](01-ssot-authority-ppdm-alignment.md)

## Referensi

- [Microsoft Fabric licenses](https://learn.microsoft.com/fabric/enterprise/licenses)
- [Create a workspace](https://learn.microsoft.com/fabric/fundamentals/create-workspaces)
- [Ontology tutorial prerequisites](https://learn.microsoft.com/fabric/iq/ontology/tutorial-0-introduction)
- [Create a Fabric data agent - prerequisites](https://learn.microsoft.com/fabric/data-science/how-to-create-data-agent)
- [Fabric data agent tenant settings](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings)
