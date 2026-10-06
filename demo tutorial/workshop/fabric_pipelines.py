"""Fabric pipeline definitions for the Zava Energy SSOT workshop (tested against Fabric Data Factory).

The tutorial builds the pipelines in the UI (Lab 04 and Lab 08). These builders produce the same
activities as JSON so a facilitator can deploy them with `python -m workshop deploy-pipelines`, and so
participants on a private network can create and load the Azure SQL source through a VNet data gateway.
Item IDs are resolved by name through the Fabric REST API using the `az login` session.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

API = "https://api.fabric.microsoft.com/v1"
ROOT = Path(__file__).resolve().parents[1]
BATCH = "pipeline().parameters.p_batch_id"


# ---------------------------------------------------------------- activity builders

def expr(value: str) -> dict:
    return {"value": value, "type": "Expression"}


def policy(retry: int = 0, interval: int = 30) -> dict:
    return {"timeout": "0.12:00:00", "retry": retry, "retryIntervalInSeconds": interval,
            "secureOutput": False, "secureInput": False}


def dep(*names: str, condition: str = "Succeeded") -> list:
    return [{"activity": n, "dependencyConditions": [condition]} for n in names]


def pipeline(activities: list, parameters: dict | None = None) -> dict:
    return {"properties": {"activities": activities, "parameters": parameters or {}, "variables": {}}}


class Builder:
    def __init__(self, ids: dict):
        self.ids = ids

    def sql_dataset(self) -> dict:
        return {"annotations": [], "type": "AzureSqlTable", "schema": [],
                "typeProperties": {"database": self.ids["sql_database"]},
                "externalReferences": {"connection": self.ids["sql_connection"]}}

    def lakehouse(self) -> dict:
        return {"name": "lh_zava_core", "properties": {"annotations": [], "type": "Lakehouse", "typeProperties": {
            "workspaceId": self.ids["core_workspace"], "artifactId": self.ids["lakehouse"], "rootFolder": "Files"}}}

    def warehouse(self) -> dict:
        return {"name": "wh_zava_gold", "properties": {"annotations": [], "type": "DataWarehouse", "typeProperties": {
            "endpoint": self.ids["warehouse_endpoint"], "artifactId": self.ids["warehouse"],
            "workspaceId": self.ids["core_workspace"]}}}

    def script(self, name: str, texts: list, depends=None, query: bool = False) -> dict:
        return {"name": name, "type": "Script", "dependsOn": depends or [], "policy": policy(),
                "externalReferences": {"connection": self.ids["sql_connection"]},
                "typeProperties": {"database": self.ids["sql_database"],
                                   "scripts": [{"type": "Query" if query else "NonQuery", "text": t} for t in texts],
                                   "scriptBlockExecutionTimeout": "02:00:00"}}

    def lookup(self, name: str, query, first_row: bool, depends) -> dict:
        return {"name": name, "type": "Lookup", "dependsOn": depends, "policy": policy(),
                "typeProperties": {"source": {"type": "AzureSqlSource", "sqlReaderQuery": query,
                                              "queryTimeout": "02:00:00", "partitionOption": "None"},
                                   "firstRowOnly": first_row, "datasetSettings": self.sql_dataset()}}

    def notebook(self, name: str, notebook: str, params: dict, depends, workspace: str = "core_workspace") -> dict:
        return {"name": name, "type": "TridentNotebook", "dependsOn": depends, "policy": policy(),
                "typeProperties": {"notebookId": self.ids[f"notebook:{notebook}"], "workspaceId": self.ids[workspace],
                                   "parameters": {k: {"value": expr(v) if v.startswith("@") else v, "type": "string"}
                                                  for k, v in params.items()}}}

    def dataflow(self, name: str, depends) -> dict:
        return {"name": name, "type": "RefreshDataflow", "dependsOn": depends, "policy": policy(),
                "typeProperties": {"dataflowId": self.ids[f"dataflow:{name}"], "workspaceId": self.ids["core_workspace"],
                                   "notifyOption": "NoNotification", "dataflowType": "DataflowFabric",
                                   "parameters": {"pBatchId": {"value": expr(f"@{BATCH}"), "type": "string"}}}}

    def proc(self, name: str, procedure: str, params: dict, depends, retry: int = 0, interval: int = 30) -> dict:
        return {"name": name, "type": "SqlServerStoredProcedure", "dependsOn": depends, "policy": policy(retry, interval),
                "linkedService": self.warehouse(),
                "typeProperties": {"storedProcedureName": procedure, "storedProcedureParameters": {
                    k: {"value": expr(v) if v.startswith("@") else v, "type": "String"} for k, v in params.items()}}}

    @staticmethod
    def fail(name: str, message: str, code: str, depends) -> dict:
        return {"name": name, "type": "Fail", "dependsOn": depends,
                "typeProperties": {"message": expr(message), "errorCode": code}}


# ---------------------------------------------------------------- pipelines

def sql_batches(path: Path) -> list[str]:
    batches, current = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().upper() == "GO":
            batches.append("\n".join(current)); current = []
        else:
            current.append(line)
    batches.append("\n".join(current))
    return [b for b in batches if re.sub(r"--[^\n]*", "", b).strip()]


def setup_source(b: Builder) -> dict:
    """Create the source schema through the gateway connection (private Azure SQL)."""
    sql = ROOT / "assets" / "sql" / "azure-sql"
    return pipeline([b.script("sql_create_schema", sql_batches(sql / "01_create_source_schema.sql")),
                     b.script("sql_security_roles", sql_batches(sql / "02_security_roles.sql"), dep("sql_create_schema")),
                     b.script("sql_validate_source", sql_batches(sql / "03_validate_source.sql"),
                              dep("sql_security_roles"), query=True)])


PREPARE_BATCH_SQL = """DECLARE @b varchar(10) = '{batch}';
DECLARE @parent varchar(10) = (SELECT parent_batch_id FROM (VALUES {chain}) AS v(batch_id, parent_batch_id) WHERE batch_id = @b);
IF @parent IS NOT NULL AND NOT EXISTS (SELECT 1 FROM ctl.source_batch WHERE batch_id = @parent AND state = 'SEALED')
    THROW 50001, 'Parent batch is not SEALED. Load batches in order.', 1;
DECLARE @sql nvarchar(max) = N'';
SELECT @sql = @sql + N'DELETE FROM ' + QUOTENAME(source_schema) + N'.' + QUOTENAME(source_table) + N' WHERE batch_id = @b;'
FROM ctl.entity_config;
EXEC sys.sp_executesql @sql, N'@b varchar(10)', @b = @b;"""
SEAL_BATCH_SQL = """UPDATE ctl.source_batch SET sealed_at_utc = SYSUTCDATETIME() WHERE batch_id = '{batch}';
SELECT entity_name, row_count FROM ctl.batch_entity WHERE batch_id = '{batch}' ORDER BY entity_name;"""


def _batch_sql(template: str) -> dict:
    from workshop.contracts import PACKS

    chain = ", ".join(f"('{p}', {('NULL' if i == 0 else repr(PACKS[i - 1]))})" for i, p in enumerate(PACKS))
    text = template.replace("{chain}", chain)
    return expr("@replace('" + text.replace("'", "''") + f"', '{{batch}}', {BATCH})")


def load_source(b: Builder) -> dict:
    """Load one generated batch from lh_zava_core Files/source_packs/<batch>/ into Azure SQL, sealing it last."""
    def copy_csv(name, file_name, schema, table, depends):
        return {"name": name, "type": "Copy", "dependsOn": depends, "policy": policy(retry=1), "typeProperties": {
            "source": {"type": "DelimitedTextSource",
                       "storeSettings": {"type": "LakehouseReadSettings", "recursive": False, "enablePartitionDiscovery": False},
                       "formatSettings": {"type": "DelimitedTextReadSettings"},
                       "datasetSettings": {"annotations": [], "linkedService": b.lakehouse(), "type": "DelimitedText",
                                           "typeProperties": {"location": {"type": "LakehouseLocation",
                                                                           "folderPath": expr(f"@concat('source_packs/', {BATCH})"),
                                                                           "fileName": file_name},
                                                              "columnDelimiter": ",", "escapeChar": "\"",
                                                              "firstRowAsHeader": True, "quoteChar": "\""}, "schema": []}},
            "sink": {"type": "AzureSqlSink", "writeBehavior": "insert", "sqlWriterUseTableLock": False,
                     "datasetSettings": {**b.sql_dataset(), "typeProperties": {
                         "schema": schema, "table": table, "database": b.ids["sql_database"]}}},
            "enableStaging": False,
            "translator": {"type": "TabularTranslator", "typeConversion": True,
                           "typeConversionSettings": {"allowDataTruncation": False, "treatBooleanAsNumber": False}}}}

    prepare = b.script("sql_prepare_batch", ["x"])
    prepare["typeProperties"]["scripts"][0]["text"] = _batch_sql(PREPARE_BATCH_SQL)
    seal = b.script("sql_seal_and_report", ["x"], dep("cp_source_batch_seal"), query=True)
    seal["typeProperties"]["scripts"][0]["text"] = _batch_sql(SEAL_BATCH_SQL)
    entities = b.lookup("lkp_entities", "SELECT entity_name, source_schema, source_table FROM ctl.entity_config "
                        "WHERE enabled = 1 AND entity_name <> 'ctl__source_batch' ORDER BY ordinal", False,
                        dep("sql_prepare_batch"))
    inner = copy_csv("cp_csv_to_sql", expr("@concat(item().source_schema, '.', item().source_table, '.csv')"),
                     expr("@item().source_schema"), expr("@item().source_table"), [])
    foreach = {"name": "fe_load_entities", "type": "ForEach", "dependsOn": dep("lkp_entities"),
               "typeProperties": {"items": expr("@activity('lkp_entities').output.value"), "isSequential": False,
                                  "batchCount": 8, "activities": [inner]}}
    return pipeline([prepare, entities, foreach,
                     copy_csv("cp_source_batch_seal", "ctl.source_batch.csv", "ctl", "source_batch", dep("fe_load_entities")),
                     seal], {"p_batch_id": {"type": "string", "defaultValue": "B0"}})


# Expressions E1-E13 as printed in assets/fabric/pipelines/pipeline-activity-sheet.md
P = "pipeline().parameters"
E = {
    "E1": f"@concat('SELECT batch_id, period_end, content_sha256 FROM ctl.source_batch WHERE state = ''SEALED'' AND batch_id = ''', {P}.p_batch_id, '''')",
    "E2": "@contains(activity('lkp_sealed_batch').output, 'firstRow')",
    "E3": f"@concat('Batch ', {P}.p_batch_id, ' is not SEALED in ctl.source_batch. Load it with python -m workshop load first.')",
    "E4": "SELECT entity_name, source_schema, source_table FROM ctl.entity_config WHERE enabled = 1 ORDER BY ordinal",
    "E5": "@activity('lkp_entities').output.value",
    "E6": f"@concat('SELECT * FROM [', item().source_schema, '].[', item().source_table, '] WHERE batch_id = ''', {P}.p_batch_id, '''')",
    "E7": f"@concat('landing/', {P}.p_batch_id, '/', item().entity_name)",
    "E8": "@concat(item().entity_name, '.parquet')",
    "E9": f"@{P}.p_batch_id",
    "E10": "@pipeline().RunId",
    "E11": f"@{P}.p_fail_after_bronze",
    "E12": f"@concat('PUB-', {P}.p_batch_id)",
    "E13": f"@concat('Batch ', {P}.p_batch_id, ' failed the SSOT quality gate. Gold is unchanged. Check ops.quality_evidence and ops.dq_issue_summary in wh_zava_gold.')",
    "P1": f"@{P}.p_publication_id",
}


def e2e(b: Builder) -> dict:
    copy_entity = {"name": "cp_entity_to_landing", "type": "Copy", "dependsOn": [], "policy": policy(retry=1),
                   "typeProperties": {
                       "source": {"type": "AzureSqlSource", "sqlReaderQuery": expr(E["E6"]), "queryTimeout": "02:00:00",
                                  "partitionOption": "None", "datasetSettings": b.sql_dataset()},
                       "sink": {"type": "ParquetSink", "storeSettings": {"type": "LakehouseWriteSettings"},
                                "formatSettings": {"type": "ParquetWriteSettings"},
                                "datasetSettings": {"annotations": [], "linkedService": b.lakehouse(), "type": "Parquet",
                                                    "typeProperties": {"location": {"type": "LakehouseLocation",
                                                                                    "folderPath": expr(E["E7"]),
                                                                                    "fileName": expr(E["E8"])},
                                                                       "compressionCodec": "snappy"}, "schema": []}},
                       "enableStaging": False,
                       "translator": {"type": "TabularTranslator", "typeConversion": True,
                                      "typeConversionSettings": {"allowDataTruncation": True, "treatBooleanAsNumber": False}}}}
    base = {"p_batch_id": E["E9"], "p_run_id": E["E10"]}
    activities = [
        b.lookup("lkp_sealed_batch", expr(E["E1"]), True, []),
        {"name": "if_batch_sealed", "type": "IfCondition", "dependsOn": dep("lkp_sealed_batch"),
         "typeProperties": {"expression": expr(E["E2"]), "ifTrueActivities": [],
                            "ifFalseActivities": [b.fail("fail_batch_not_sealed", E["E3"], "BATCH_NOT_SEALED", [])]}},
        b.lookup("lkp_entities", E["E4"], False, dep("if_batch_sealed")),
        {"name": "fe_copy_entities", "type": "ForEach", "dependsOn": dep("lkp_entities"),
         "typeProperties": {"items": expr(E["E5"]), "isSequential": False, "batchCount": 8, "activities": [copy_entity]}},
        b.notebook("nb_01_land_bronze", "nb_01_land_bronze", base, dep("fe_copy_entities")),
        b.notebook("nb_02_conform_master_ppdm", "nb_02_conform_master_ppdm", {**base, "p_fail_after_bronze": E["E11"]},
                   dep("nb_01_land_bronze")),
        b.notebook("nb_03_conform_production", "nb_03_conform_production", base, dep("nb_02_conform_master_ppdm")),
        b.dataflow("df_zava_target_etl", dep("nb_01_land_bronze")),
        b.dataflow("df_zava_cost_etl", dep("nb_01_land_bronze")),
        b.notebook("nb_04_conform_business", "nb_04_conform_business", base,
                   dep("nb_03_conform_production", "df_zava_target_etl", "df_zava_cost_etl")),
        b.notebook("nb_05_validate_and_serve", "nb_05_validate_and_serve", base, dep("nb_04_conform_business")),
        b.proc("sp_stage_candidate", "[ops].[usp_stage_candidate]", {"PublicationId": E["E12"], "RunId": E["E10"]},
               dep("nb_05_validate_and_serve"), retry=3, interval=120),
        b.proc("sp_sync_quality_evidence_ok", "[ops].[usp_sync_quality_evidence]", {"BatchId": E["E9"], "RunId": E["E10"]},
               dep("sp_stage_candidate")),
        b.proc("sp_sync_quality_evidence_fail", "[ops].[usp_sync_quality_evidence]", {"BatchId": E["E9"], "RunId": E["E10"]},
               dep("nb_05_validate_and_serve", condition="Failed")),
        b.fail("fail_quality_gate", E["E13"], "QUALITY_GATE", dep("sp_sync_quality_evidence_fail", condition="Completed")),
    ]
    return pipeline(activities, {"p_batch_id": {"type": "string", "defaultValue": "B0"},
                                 "p_fail_after_bronze": {"type": "string", "defaultValue": "false"}})


def publish_gold(b: Builder) -> dict:
    acts = [b.proc("sp_publish_publication", "[ops].[usp_publish_publication]",
                   {"PublicationId": E["P1"], "RunId": E["E10"]}, [])]
    if b.ids.get("semantic_model") and b.ids.get("semantic_model_connection"):
        acts.append({"name": "sm_refresh_zava_performance", "type": "PBISemanticModelRefresh",
                     "dependsOn": dep("sp_publish_publication"), "policy": policy(),
                     "typeProperties": {"method": "post", "groupId": b.ids["core_workspace"],
                                        "datasetId": b.ids["semantic_model"], "commitMode": "Transactional",
                                        "waitOnCompletion": True, "operationType": "SemanticModelRefresh"},
                     "externalReferences": {"connection": b.ids["semantic_model_connection"]}})
        acts.append(b.proc("sp_consumer_semantic_model", "[ops].[usp_record_consumer_status]",
                           {"PublicationId": E["P1"], "Consumer": "SEMANTIC_MODEL", "Status": "REFRESHED"},
                           dep("sm_refresh_zava_performance")))
    if b.ids.get("notebook:nb_06_prepare_ai_serving"):
        acts.append(b.notebook("nb_06_prepare_ai_serving", "nb_06_prepare_ai_serving",
                               {"p_publication_id": E["P1"], "p_run_id": E["E10"],
                                "p_source_prefix": f"`{b.ids['core_workspace_name']}`.`lh_zava_core`.`serve`"},
                               dep("sp_publish_publication"), workspace="ai_workspace"))
        acts.append(b.proc("sp_consumer_ai_serving", "[ops].[usp_record_consumer_status]",
                           {"PublicationId": E["P1"], "Consumer": "AI_SERVING", "Status": "READY"},
                           dep("nb_06_prepare_ai_serving")))
    return pipeline(acts, {"p_publication_id": {"type": "string", "defaultValue": "PUB-B0"}})


PIPELINES = {"pl_zava_setup_source": setup_source, "pl_zava_load_source": load_source,
             "pl_zava_e2e": e2e, "pl_zava_publish_gold": publish_gold}


# ---------------------------------------------------------------- Fabric REST (az login)

def _token(resource: str = "https://api.fabric.microsoft.com") -> str:
    az = shutil.which("az") or shutil.which("az.cmd")
    if not az:
        raise SystemExit("Azure CLI is required (az login).")
    return subprocess.run([az, "account", "get-access-token", "--resource", resource, "--query", "accessToken",
                           "-o", "tsv"], capture_output=True, text=True, check=True).stdout.strip()


def _call(method: str, path: str, body=None, token: str | None = None):
    import urllib.error
    import urllib.request

    request = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {token or _token()}",
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            location = response.headers.get("Location")
            content = response.read()
            if response.status == 202 and location:
                return _poll(location, token)
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{method} {path} failed: {error.code} {error.read().decode()[:800]}")


def _poll(location: str, token: str | None):
    import urllib.request

    for _ in range(120):
        time.sleep(3)
        request = urllib.request.Request(location, headers={"Authorization": f"Bearer {token or _token()}"})
        with urllib.request.urlopen(request, timeout=180) as response:
            content = response.read()
            data = json.loads(content) if content else {}
        if data.get("status") in ("Succeeded", None):
            return data
        if data.get("status") in ("Failed", "Cancelled"):
            raise SystemExit(f"Operation failed: {json.dumps(data)[:800]}")
    raise SystemExit("Operation timed out")


def _named(values: list, name: str, what: str) -> dict:
    for value in values:
        if value.get("displayName") == name:
            return value
    raise SystemExit(f"{what} '{name}' not found. Create it first (see the tutorial).")


def resolve_ids(config: dict, token: str) -> dict:
    fabric, sql = config["fabric"], config["azure_sql"]
    workspaces = _call("GET", "/workspaces", token=token)["value"]
    core = _named(workspaces, fabric["core_workspace_name"], "Workspace")["id"]
    ids = {"core_workspace": core, "core_workspace_name": fabric["core_workspace_name"],
           "sql_database": sql["database"]}
    items = _call("GET", f"/workspaces/{core}/items", token=token)["value"]

    def item(kind, name, required=True):
        for value in items:
            if value["type"] == kind and value["displayName"] == name:
                return value["id"]
        if required:
            raise SystemExit(f"{kind} '{name}' not found in {fabric['core_workspace_name']}.")
        return None

    ids["lakehouse"] = item("Lakehouse", fabric.get("lakehouse_name", "lh_zava_core"))
    ids["warehouse"] = item("Warehouse", fabric.get("warehouse_name", "wh_zava_gold"))
    ids["warehouse_endpoint"] = _call("GET", f"/workspaces/{core}/warehouses/{ids['warehouse']}",
                                      token=token)["properties"]["connectionString"]
    for notebook in ["nb_01_land_bronze", "nb_02_conform_master_ppdm", "nb_03_conform_production",
                     "nb_04_conform_business", "nb_05_validate_and_serve"]:
        ids[f"notebook:{notebook}"] = item("Notebook", notebook, required=False)
    for dataflow in ["df_zava_target_etl", "df_zava_cost_etl"]:
        ids[f"dataflow:{dataflow}"] = item("Dataflow", dataflow, required=False)
    ids["semantic_model"] = item("SemanticModel", fabric.get("semantic_model_name", "sm_zava_performance"), required=False)
    connections = _call("GET", "/connections", token=token)["value"]

    def connection(name, kind):
        typed = [c for c in connections if c.get("connectionDetails", {}).get("type") == kind]
        return _named(typed, name, f"{kind} connection")["id"]

    ids["sql_connection"] = connection(fabric.get("sql_connection_name", "conn_sql_zava_source"), "SQL")
    if fabric.get("semantic_model_connection_name"):
        ids["semantic_model_connection"] = connection(fabric["semantic_model_connection_name"], "PowerBIDatasets")
    ai_name = fabric.get("ai_workspace_name")
    ai = next((w["id"] for w in workspaces if w["displayName"] == ai_name), None)
    if ai:
        ids["ai_workspace"] = ai
        for value in _call("GET", f"/workspaces/{ai}/items?type=Notebook", token=token)["value"]:
            if value["displayName"] == "nb_06_prepare_ai_serving":
                ids["notebook:nb_06_prepare_ai_serving"] = value["id"]
    return ids


def render(ids: dict, names=None) -> dict:
    builder = Builder(ids)
    selected = names or list(PIPELINES)
    missing = [k for k, v in ids.items() if v is None and (k.startswith("notebook:nb_0") and "nb_06" not in k
                                                           or k.startswith("dataflow:"))]
    if missing and any(n == "pl_zava_e2e" for n in selected):
        raise SystemExit(f"pl_zava_e2e needs these items first: {', '.join(m.split(':')[1] for m in missing)}")
    return {name: PIPELINES[name](builder) for name in selected}


def deploy(config: dict, names=None) -> dict:
    token = _token()
    ids = resolve_ids(config, token)
    deployed = {}
    for name, body in render(ids, names).items():
        core = ids["core_workspace"]
        existing = [i for i in _call("GET", f"/workspaces/{core}/items?type=DataPipeline", token=token)["value"]
                    if i["displayName"] == name]
        item_id = existing[0]["id"] if existing else _call("POST", f"/workspaces/{core}/items",
                                                           {"displayName": name, "type": "DataPipeline"}, token=token)["id"]
        payload = base64.b64encode(json.dumps(body, indent=1).encode()).decode()
        _call("POST", f"/workspaces/{core}/items/{item_id}/updateDefinition",
              {"definition": {"parts": [{"path": "pipeline-content.json", "payload": payload,
                                         "payloadType": "InlineBase64"}]}}, token=token)
        deployed[name] = item_id
    return deployed
