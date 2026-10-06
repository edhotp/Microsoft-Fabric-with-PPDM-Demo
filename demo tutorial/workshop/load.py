"""Load a sealed workshop pack into Azure SQL Database with Microsoft Entra authentication."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .contracts import PACKS, TABLE_BY_NAME, TABLES

DATA_TABLE_NAMES = [t.full_name for t in TABLES if t.kind != "CONTROL"]


def read_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    sql = config["azure_sql"]
    needs_user = sql.get("authentication", "ActiveDirectoryInteractive") != "AzureCli"
    if "REPLACE" in sql["server"] or (needs_user and "REPLACE" in sql.get("username", "")):
        raise SystemExit(f"Update {path} with your Azure SQL server and Microsoft Entra user first.")
    return config


SQL_COPT_SS_ACCESS_TOKEN = 1256


def _azure_cli_token() -> bytes:
    """Access token from `az login` packed for the ODBC driver (no browser popup)."""
    import shutil
    import struct
    import subprocess

    az = shutil.which("az") or shutil.which("az.cmd")
    if not az:
        raise SystemExit("Azure CLI not found. Install it or use authentication ActiveDirectoryInteractive.")
    token = subprocess.run([az, "account", "get-access-token", "--resource", "https://database.windows.net/",
                            "--query", "accessToken", "-o", "tsv"], capture_output=True, text=True, check=True).stdout.strip()
    raw = token.encode("utf-16-le")
    return struct.pack("=i", len(raw)) + raw


def connect(config: dict):
    import pyodbc  # imported lazily so offline commands do not need the driver

    sql = config["azure_sql"]
    authentication = sql.get("authentication", "ActiveDirectoryInteractive")
    parts = [f"Driver={{{sql.get('driver', 'ODBC Driver 18 for SQL Server')}}}",
             f"Server=tcp:{sql['server']},1433", f"Database={sql['database']}",
             "Encrypt=yes", "TrustServerCertificate=no", "Connection Timeout=60"]
    attrs = {}
    if authentication == "AzureCli":
        attrs[SQL_COPT_SS_ACCESS_TOKEN] = _azure_cli_token()
    else:
        parts.append(f"Authentication={authentication}")
        if sql.get("username"):
            parts.append(f"UID={sql['username']}")
    connection = pyodbc.connect(";".join(parts), autocommit=False, attrs_before=attrs)
    database = connection.cursor().execute("SELECT DB_NAME()").fetchone()[0]
    expected = config.get("safety", {}).get("expected_database", sql["database"])
    if database != expected:
        connection.close()
        raise SystemExit(f"Connected to '{database}', expected '{expected}'. Nothing was changed.")
    return connection



def convert(value: str, sql_type: str, nullable: bool):
    if value == "":
        if nullable:
            return None
        if sql_type.startswith(("varchar", "char")):
            return value
        raise ValueError(f"Empty value for NOT NULL {sql_type}")
    base = sql_type.split("(")[0]
    if base in ("int", "bigint"):
        return int(value)
    if base == "decimal":
        return Decimal(value)
    if base == "date":
        return date.fromisoformat(value)
    if base == "datetime2":
        return datetime.fromisoformat(value)
    if base == "bit":
        return value in ("1", "true", "True")
    return value


def read_rows(path: Path, table_name: str) -> list[tuple]:
    table = TABLE_BY_NAME[table_name]
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != table.column_names:
            raise ValueError(f"{path.name}: header does not match the contract")
        return [tuple(convert(v, c.sql_type, c.nullable) for v, c in zip(row, table.columns))
                for row in reader]


def insert_sql(table_name: str) -> str:
    table = TABLE_BY_NAME[table_name]
    columns = ", ".join(f"[{c}]" for c in table.column_names)
    return (f"INSERT INTO [{table.schema}].[{table.name}] ({columns}) "
            f"VALUES ({', '.join('?' for _ in table.column_names)})")


def batch_state(cursor, batch: str):
    row = cursor.execute("SELECT state, content_sha256 FROM ctl.source_batch WHERE batch_id = ?",
                         batch).fetchone()
    return (row[0], row[1]) if row else (None, None)


def load_pack(config: dict, source_root: Path, batch: str, chunk: int = 5000) -> str:
    if batch not in PACKS:
        raise SystemExit(f"Unknown batch {batch}. Use one of {', '.join(PACKS)}.")
    folder = source_root / batch
    if not folder.is_dir():
        raise SystemExit(f"{folder} not found. Run `python -m workshop generate` first.")
    source_batch = read_rows(folder / "ctl.source_batch.csv", "ctl.source_batch")[0]
    columns = TABLE_BY_NAME["ctl.source_batch"].column_names
    meta = dict(zip(columns, source_batch))
    connection = connect(config)
    cursor = connection.cursor()
    try:
        state, digest = batch_state(cursor, batch)
        if state == "SEALED":
            if digest == meta["content_sha256"]:
                return f"{batch} is already sealed with identical content. No changes made."
            raise SystemExit(f"{batch} is sealed with different content. Reset the workshop source first.")
        parent = meta["parent_batch_id"]
        if parent and batch_state(cursor, parent)[0] != "SEALED":
            raise SystemExit(f"Load {parent} before {batch}; batches are applied in order.")
        later = [p for p in PACKS[PACKS.index(batch) + 1:] if batch_state(cursor, p)[0]]
        if later:
            raise SystemExit(f"Later batch {later[0]} already exists. Batches must be loaded in order.")
        cursor.fast_executemany = True
        for table_name in DATA_TABLE_NAMES + ["ctl.batch_entity", "ctl.source_batch"]:
            table = TABLE_BY_NAME[table_name]
            cursor.execute(f"DELETE FROM [{table.schema}].[{table.name}] WHERE batch_id = ?", batch)
        for table_name in DATA_TABLE_NAMES + ["ctl.batch_entity"]:
            rows = read_rows(folder / f"{table_name}.csv", table_name)
            statement = insert_sql(table_name)
            for start in range(0, len(rows), chunk):
                cursor.executemany(statement, rows[start:start + chunk])
            print(f"  {table_name:<34} {len(rows):>8,} rows")
        cursor.execute(insert_sql("ctl.source_batch"), source_batch)
        cursor.execute("UPDATE ctl.source_batch SET sealed_at_utc = SYSUTCDATETIME() WHERE batch_id = ?", batch)
        connection.commit()
        return f"{batch} loaded and sealed in one transaction."
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def batch_status(config: dict) -> list[tuple]:
    connection = connect(config)
    try:
        return connection.cursor().execute(
            "SELECT batch_id, parent_batch_id, state, period_end, sealed_at_utc "
            "FROM ctl.source_batch ORDER BY sealed_at_utc").fetchall()
    finally:
        connection.close()


def verify_pack(config: dict, batch: str) -> list[tuple]:
    """Compare loaded row counts with ctl.batch_entity for one batch."""
    connection = connect(config)
    cursor = connection.cursor()
    try:
        results = []
        expected = cursor.execute("SELECT entity_name, row_count FROM ctl.batch_entity WHERE batch_id = ?",
                                  batch).fetchall()
        by_entity = {t.entity: t for t in TABLES}
        for entity, count in expected:
            table = by_entity[entity]
            actual = cursor.execute(f"SELECT COUNT_BIG(*) FROM [{table.schema}].[{table.name}] "
                                    "WHERE batch_id = ?", batch).fetchone()[0]
            results.append((entity, count, actual, "OK" if count == actual else "MISMATCH"))
        return results
    finally:
        connection.close()


def run_sql_file(config: dict, path: Path) -> None:
    """Execute a script that uses GO batch separators."""
    batches, current = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().upper() == "GO":
            batches.append("\n".join(current))
            current = []
        else:
            current.append(line)
    batches.append("\n".join(current))
    connection = connect(config)
    connection.autocommit = True
    try:
        cursor = connection.cursor()
        for batch in (b for b in batches if b.strip()):
            cursor.execute(batch)
            while cursor.nextset():
                pass
        print(f"Executed {path.name}: {sum(1 for b in batches if b.strip())} batches.")
    finally:
        connection.close()
