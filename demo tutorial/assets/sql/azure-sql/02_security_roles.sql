/*
    Zava Energy SSOT workshop - Azure SQL source security (least privilege)
    Jalankan sebagai Microsoft Entra admin database, SETELAH 01_create_source_schema.sql.

    Ganti placeholder sebelum menjalankan:
      <LOADER_ENTRA_PRINCIPAL>  : UPN fasilitator/peserta yang memuat data (mis. user@contoso.com)
      <FABRIC_READER_PRINCIPAL> : identitas koneksi Fabric (user organizational account,
                                  workspace identity, atau service principal untuk Copy)
    Semua akun memakai autentikasi Microsoft Entra; tidak ada SQL login/password.
*/
SET NOCOUNT ON;
GO

IF DATABASE_PRINCIPAL_ID(N'zava_source_reader') IS NULL
    CREATE ROLE zava_source_reader AUTHORIZATION dbo;
GO
IF DATABASE_PRINCIPAL_ID(N'zava_source_loader') IS NULL
    CREATE ROLE zava_source_loader AUTHORIZATION dbo;
GO

-- Reader: hanya baca untuk Fabric Copy activity dan Dataflow Gen2
GRANT SELECT ON SCHEMA::ref    TO zava_source_reader;
GRANT SELECT ON SCHEMA::src_dz TO zava_source_reader;
GRANT SELECT ON SCHEMA::src_my TO zava_source_reader;
GRANT SELECT ON SCHEMA::src_iq TO zava_source_reader;
GRANT SELECT ON SCHEMA::ctl    TO zava_source_reader;
GO

-- Loader: memuat batch sintetis lewat `python -m workshop load` (tanpa hak DDL)
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ref    TO zava_source_loader;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::src_dz TO zava_source_loader;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::src_my TO zava_source_loader;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::src_iq TO zava_source_loader;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ctl    TO zava_source_loader;
GO

-- Hapus tanda komentar (--) pada empat baris berikut dan ganti placeholder untuk membuat user dari Microsoft Entra ID.
-- CREATE USER [<LOADER_ENTRA_PRINCIPAL>] FROM EXTERNAL PROVIDER;
-- ALTER ROLE zava_source_loader ADD MEMBER [<LOADER_ENTRA_PRINCIPAL>];
-- CREATE USER [<FABRIC_READER_PRINCIPAL>] FROM EXTERNAL PROVIDER;
-- ALTER ROLE zava_source_reader ADD MEMBER [<FABRIC_READER_PRINCIPAL>];
GO

SELECT r.name AS role_name, m.name AS member_name
FROM sys.database_role_members AS drm
JOIN sys.database_principals AS r ON r.principal_id = drm.role_principal_id
JOIN sys.database_principals AS m ON m.principal_id = drm.member_principal_id
WHERE r.name IN (N'zava_source_reader', N'zava_source_loader')
ORDER BY r.name, m.name;
GO
