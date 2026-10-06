"""Run the data agent evaluation cases against published Fabric data agents (Lab 12-13).

Uses the published agent's OpenAI-compatible Assistants endpoint and the `az login` session.
Numeric answers and the publication ID are scored automatically; explanation, refusal and redirect
cases are marked REVIEW so a person confirms them, as the evidence template requires.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.request
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from workshop.fabric_pipelines import API, _call, _token

VERSION = "2024-05-01-preview"


def _request(method: str, url: str, token: str, body=None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "ActivityId": str(uuid.uuid4())})
    with urllib.request.urlopen(request, timeout=180) as response:
        content = response.read()
        return json.loads(content) if content else {}


def ask(workspace_id: str, agent_id: str, question: str, token: str, timeout: int = 300) -> tuple[str, str]:
    base = f"{API}/workspaces/{workspace_id}/dataagents/{agent_id}/aiassistant/openai"
    assistant = _request("POST", f"{base}/assistants?api-version={VERSION}", token, {"model": "not-used"})
    thread = _request("POST", f"{base}/threads?api-version={VERSION}", token, {})
    _request("POST", f"{base}/threads/{thread['id']}/messages?api-version={VERSION}", token,
             {"role": "user", "content": question})
    run = _request("POST", f"{base}/threads/{thread['id']}/runs?api-version={VERSION}", token,
                   {"assistant_id": assistant["id"]})
    start = time.time()
    while run.get("status") in ("queued", "in_progress", "requires_action") and time.time() - start < timeout:
        time.sleep(4)
        run = _request("GET", f"{base}/threads/{thread['id']}/runs/{run['id']}?api-version={VERSION}", token)
    messages = _request("GET", f"{base}/threads/{thread['id']}/messages?api-version={VERSION}&order=desc", token)
    for message in messages.get("data", []):
        if message["role"] == "assistant":
            text = " ".join(c["text"]["value"] for c in message["content"] if c.get("type") == "text")
            return run.get("status", "unknown"), text
    return run.get("status", "unknown"), ""


def _numbers(text: str) -> list[Decimal]:
    values = []
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            values.append(Decimal(raw.replace(",", "")))
        except InvalidOperation:
            pass
    return values


def _tolerance(text: str) -> Decimal:
    if text.startswith("±"):
        number = _numbers(text)
        return number[0] if number else Decimal(0)
    return Decimal(0) if text.startswith("exact") else Decimal("0.5")


def score(case: dict, answer: str) -> str:
    if not answer:
        return "FAIL"
    if case["type"] not in ("NUMERIC", "LIST", "LOOKUP", "LINEAGE"):
        return "REVIEW"
    mentions_publication = case["publication_id"] in answer
    if case["type"] == "LOOKUP" or case["type"] == "LINEAGE":
        tokens = re.findall(r"[A-Z][A-Z0-9_-]{3,}", case["expected_answer"])
        return "PASS" if tokens and all(t in answer for t in tokens) else "REVIEW"
    expected = [n for n in _numbers(re.sub(r"\(.*?\)", "", case["expected_answer"])) if n > 1]
    actual = _numbers(answer)
    tolerance = _tolerance(case["tolerance"])
    ok = all(any(abs(a - e) <= max(tolerance, Decimal("0.5")) for a in actual) for e in expected)
    if ok and mentions_publication:
        return "PASS"
    return "FAIL" if not ok else "REVIEW"


def evaluate(config: dict, cases_path: Path, output: Path, rounds: int = 1) -> dict:
    token = _token()
    workspaces = _call("GET", "/workspaces", token=token)["value"]
    ai = next(w["id"] for w in workspaces if w["displayName"] == config["fabric"]["ai_workspace_name"])
    agents = {i["displayName"]: i["id"] for i in _call("GET", f"/workspaces/{ai}/items?type=DataAgent", token=token)["value"]}
    cases = list(csv.DictReader(cases_path.open(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["round", "case_id", "agent", "type", "question", "expected_answer", "run_status",
                         "actual_answer", "auto_check"])
        for round_number in range(1, rounds + 1):
            for case in cases:
                if case["agent"] not in agents:
                    raise SystemExit(f"Data agent {case['agent']} is not in {config['fabric']['ai_workspace_name']}.")
                status, answer = ask(ai, agents[case["agent"]], case["question"], token)
                result = score(case, answer)
                summary[result] += 1
                writer.writerow([round_number, case["case_id"], case["agent"], case["type"], case["question"],
                                 case["expected_answer"], status, answer, result])
                print(f"round {round_number} {case['case_id']} {result}")
    return summary
