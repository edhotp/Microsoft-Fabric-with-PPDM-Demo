/*
    PIEP SSOT workshop - reproduksi angka publikasi sebelumnya dengan time travel Warehouse.
    Time travel: OPTION (FOR TIMESTAMP AS OF 'yyyy-MM-ddTHH:mm:ss.fff'), sekali per SELECT,
    dalam periode retensi (default 30 hari). Tidak dapat dipakai di dalam definisi VIEW.

    Langkah:
      1. Jalankan query 1. Kolom TimeTravelTimestamp adalah satu detik sebelum publikasi tersebut digantikan
         (atau waktu sekarang untuk publikasi yang masih berlaku) - saat itu Gold pasti berisi publikasi tersebut.
      2. Salin TimeTravelTimestamp publikasi lama (mis. PUB-S1), tempel ke query 2 dan 3.
*/

-- 1. Kapan setiap publikasi berlaku di Gold
SELECT p.PublicationId, p.Status, p.PublishedAtUtc, p.SupersededBy,
       CONVERT(varchar(23), DATEADD(SECOND, -1, COALESCE(n.PublishedAtUtc, SYSUTCDATETIME())), 126) AS TimeTravelTimestamp
FROM ops.publication AS p
LEFT JOIN ops.publication AS n ON n.PublicationId = p.SupersededBy
WHERE p.PublishedAtUtc IS NOT NULL
ORDER BY p.PublishedAtUtc;

-- 2. Total Gold pada saat PUB-S1 berlaku (ganti timestamp dengan hasil query 1)
SELECT MIN(PublicationId) AS PublicationId, SUM(GrossBoe) AS GrossBoe, SUM(NetWiBoe) AS NetWiBoe
FROM gold.fact_production_daily
OPTION (FOR TIMESTAMP AS OF '2025-10-05T10:00:00.000');

-- 3. Nilai minyak MY_B_W001 pada 2025-09-20 saat PUB-S1 berlaku (expected: nilai provisional terpilih S1)
SELECT f.PublicationId, w.WellId, f.DateKey, f.OilBbl, f.SelectedSources, f.MaxRevision
FROM gold.fact_production_daily AS f
JOIN gold.dim_well AS w ON w.WellKey = f.WellKey
WHERE w.WellId = 'MY_B_W001' AND f.DateKey = 20250920
OPTION (FOR TIMESTAMP AS OF '2025-10-05T10:00:00.000');

-- 4. Nilai saat ini (PUB-S2) untuk perbandingan
SELECT f.PublicationId, w.WellId, f.DateKey, f.OilBbl, f.SelectedSources, f.MaxRevision
FROM gold.fact_production_daily AS f
JOIN gold.dim_well AS w ON w.WellKey = f.WellKey
WHERE w.WellId = 'MY_B_W001' AND f.DateKey = 20250920;
