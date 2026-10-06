# Pengujian paket workshop

Paket workshop diuji tanpa Azure atau Fabric agar fasilitator dapat memastikan semua aset konsisten sebelum sesi.

| File | Isi | Waktu |
|---|---|---|
| `test_assets.py` | Generator deterministik, kunci jawaban terbaru, SQL/notebook/kontrak hasil generate tidak usang, referensi DAX ↔ model, ontology ↔ proyeksi AI, lembar pipeline ↔ aset, link dokumen, dan angka tutorial ↔ kunci jawaban | ± 1 menit |
| `test_notebooks_spark.py` | Menjalankan **notebook Fabric yang sebenarnya** (`nb_01`–`nb_06`) di Spark 3.5 + Delta 3.2 lokal untuk 10 batch profil `small`, termasuk rerun idempoten, drill F1, dan quality gate Q1. Hasilnya dibandingkan dengan kunci jawaban independen dan kontrak kolom Warehouse. | 60–100 menit di laptop |

## Menjalankan pemeriksaan offline

```powershell
pip install -r requirements-test.txt
python -m pytest -m "not spark"
```

## Menjalankan notebook di Spark lokal (opsional)

Prasyarat: Java 17 (`JAVA_HOME`), `pyspark==3.5.3`, dan `delta-spark==3.2.1`.

```powershell
python -m pytest -m spark -x
```

Harness [`notebook_harness.py`](notebook_harness.py) menyimulasikan dua layanan Fabric yang tidak tersedia secara lokal:

- **Copy activity**: CSV paket ditulis sebagai Parquet ke `landing/<batch>/<entity>/` dengan tipe sesuai kontrak sumber.
- **Dataflow Gen2**: aturan yang sama dengan skrip M (`unpivot`, join FX, `dq_status`) ditulis ke `stg_df.*` sebagai `double`.

Selain itu, harness mengganti `notebookutils.notebook.exit` dan menangani `%run nb_00_common`, lalu menyuntikkan parameter setelah parameter cell seperti Notebook activity.

> [!NOTE]
> **Windows tanpa `winutils.exe`:** Hadoop lokal membutuhkan izin file POSIX. Set `PIEP_TEST_CLASSPATH` ke JAR Delta (`delta-spark_2.12-3.2.1.jar`, `delta-storage-3.2.1.jar`) dan JAR uji yang menyediakan kelas `localtest.NoPermissionLocalFileSystem` dan `localtest.NoPermissionLocalFs`. Kelas tersebut adalah turunan `LocalFileSystem` yang mengabaikan `setPermission`. Pengaturan ini **hanya** untuk pengujian lokal dan tidak dipakai di Fabric. Di Linux, macOS, atau WSL, cukup gunakan `configure_spark_with_delta_pip` bawaan tanpa variabel tersebut.

## Kapan menjalankan ulang aset hasil generate

Jika Anda mengubah salah satu sumber berikut, jalankan perintah ini lalu ulangi pengujian:

```powershell
python -m workshop render-sql          # workshop/contracts.py
python -m workshop render-warehouse    # workshop/warehouse.py
python -m workshop build-notebooks     # assets/fabric/notebooks/src/*.py
python -m workshop expected --profile standard; python -m workshop expected --profile small
python -m workshop render-contracts    # kontrak CSV dan kasus evaluasi agent
```
