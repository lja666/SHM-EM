#!/usr/bin/env python3
"""Validate the disposable Docker Compose public-reference workflow."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib import request


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5101")
    parser.add_argument("--compose-file", type=Path, default=Path("compose.yaml"))
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("artifacts/revision/portability/linux-reference-reproduction.json"))
    return parser.parse_args()


def api(base_url: str, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = request.Request(base_url + path, data=payload, method=method)
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


class ComposeDatabase:
    def __init__(self, repo: Path, compose_file: Path) -> None:
        self.repo = repo
        self.command = ["docker", "compose", "--file", str(compose_file)]

    def query(self, sql: str) -> str:
        command = [
            *self.command,
            "exec",
            "-T",
            "mysql",
            "sh",
            "-ec",
            'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql --user="$MYSQL_USER" --database="$MYSQL_DATABASE" --default-character-set=utf8mb4 --batch --raw --skip-column-names',
        ]
        result = subprocess.run(command, cwd=self.repo, input=sql, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Compose MySQL query failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def scalar(self, sql: str) -> str:
        return self.query(sql).splitlines()[0].strip()

    def count(self, sql: str) -> int:
        return int(self.scalar(sql))


def formal_counts(db: ComposeDatabase, project_id: int) -> dict[str, int]:
    return {
        "events": db.count(f"SELECT COUNT(*) FROM em_monitoring_event WHERE project_id={project_id};"),
        "notifications": db.count(f"SELECT COUNT(*) FROM em_notification_task WHERE project_id={project_id};"),
        "responses": db.count(f"SELECT COUNT(*) FROM em_event_response_workflow WHERE project_id={project_id};"),
        "reports": db.count(f"SELECT COUNT(*) FROM em_report_instance WHERE project_id={project_id};"),
        "links": db.count(f"SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id WHERE e.project_id={project_id};"),
    }


def compose_json(repo: Path, compose_file: Path, *args: str) -> Any:
    result = subprocess.run(["docker", "compose", "--file", str(compose_file), *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    text = result.stdout.strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> int:
    args = arguments()
    repo = Path(__file__).resolve().parents[2]
    compose_file = (repo / args.compose_file).resolve()
    db = ComposeDatabase(repo, compose_file)
    project_id = args.project_id
    project = api(args.base_url, "GET", f"/api/em/projects/{project_id}")
    batch_id = int(db.scalar(f"SELECT id FROM em_prediction_batch WHERE project_id={project_id} AND status='success' ORDER BY base_time DESC,id DESC LIMIT 1;"))
    batch = api(args.base_url, "GET", f"/api/em/predictions/batches/{batch_id}")
    gate = api(args.base_url, "GET", f"/api/em/predictions/batches/{batch_id}/execution-gate?mode=REPLAY")
    future = api(args.base_url, "GET", f"/api/em/projects/{project_id}/future-state?batchId={batch_id}&executionMode=REPLAY")
    rule_id = int(db.scalar(f"SELECT id FROM em_event_rule WHERE project_id={project_id} AND UPPER(input_source)='PREDICTION' AND enabled=1 ORDER BY id LIMIT 1;"))
    before = formal_counts(db, project_id)
    evaluate = api(args.base_url, "POST", f"/api/em/projects/{project_id}/rules/{rule_id}/evaluate", {"inputSource": "PREDICTION", "predictionBatchId": batch_id, "predictionExecutionMode": "REPLAY", "seriesQualityFilter": "normal"})
    after_evaluate = formal_counts(db, project_id)
    execute = api(args.base_url, "POST", f"/api/em/projects/{project_id}/rules/{rule_id}/execute", {"inputSource": "PREDICTION", "predictionBatchId": batch_id, "predictionExecutionMode": "REPRODUCTION", "seriesQualityFilter": "normal"})
    event_id = int(execute["data"]["event"]["id"])
    trace = api(args.base_url, "GET", f"/api/em/predictions/events/{event_id}/trace")
    execute_gate_id = int(trace["data"]["predictionGateId"])
    after_execute = formal_counts(db, project_id)
    model_count = db.count(f"SELECT COUNT(*) FROM em_prediction_run WHERE batch_id={batch_id} AND status='success';")
    result_count = db.count(f"SELECT COUNT(*) FROM em_prediction_result WHERE batch_id={batch_id};")
    target_count = db.count(f"SELECT COUNT(DISTINCT feature_code) FROM em_prediction_result WHERE batch_id={batch_id};")
    step_count = db.count(f"SELECT COUNT(DISTINCT step) FROM em_prediction_result WHERE batch_id={batch_id};")
    conversion_failures = db.count(f"SELECT COUNT(*) FROM em_prediction_result WHERE batch_id={batch_id} AND (engineering_value IS NULL OR conversion_status<>'success');")
    input_hash = db.scalar(f"SELECT input_hash FROM em_prediction_batch WHERE id={batch_id};")
    output_hash = db.scalar(f"SELECT output_hash FROM em_prediction_batch WHERE id={batch_id};")
    expected_input_hash = db.scalar("SELECT JSON_UNQUOTE(JSON_EXTRACT(expected_output_json,'$.inputHash')) FROM em_dataset_manifest WHERE enabled=1 ORDER BY id LIMIT 1;")
    expected_output_hash = db.scalar("SELECT expected_result_hash FROM em_dataset_manifest WHERE enabled=1 ORDER BY id LIMIT 1;")
    persisted_hash_count = db.count(f"SELECT COUNT(*) FROM em_prediction_run WHERE batch_id={batch_id} AND LENGTH(persisted_result_hash)=64 AND persisted_result_hash_version='prediction-persisted-integrity-v1';")
    execute_gate_row = db.query(f"SELECT execution_mode,result_integrity_valid,execution_eligible,batch_id FROM em_prediction_execution_gate WHERE id={execute_gate_id};").split("\t")
    link_count = db.count(f"SELECT COUNT(*) FROM em_event_prediction_link WHERE event_id={event_id} AND prediction_batch_id={batch_id} AND prediction_gate_id IS NOT NULL;")
    response_count = db.count(f"SELECT COUNT(*) FROM em_event_response_workflow WHERE event_id={event_id};")
    step_response_count = db.count(f"SELECT COUNT(*) FROM em_event_response_step s JOIN em_event_response_workflow w ON w.id=s.workflow_id WHERE w.event_id={event_id};")
    report_count = db.count(f"SELECT COUNT(*) FROM em_report_instance WHERE event_id={event_id};")
    notification_count = db.count(f"SELECT COUNT(*) FROM em_notification_task WHERE event_id={event_id};")
    model_rows = []
    for line in db.query("SELECT model_code,artifact_hash,preprocessor_hash,inference_script_hash,input_schema_hash,runtime_manifest_hash,required_history_rows FROM em_prediction_model WHERE status='active' ORDER BY model_code;").splitlines():
        code, artifact, preprocessor, script_hash, schema_hash, runtime_hash, history = line.split("\t")
        model_rows.append({"modelCode": code, "artifactHash": artifact, "preprocessorHash": preprocessor, "inferenceScriptHash": script_hash, "inputSchemaHash": schema_hash, "runtimeManifestHash": runtime_hash, "requiredHistoryRows": int(history)})
    checks = {
        "projectApi": project.get("code") == 0,
        "modelSet": model_count == 6 and len(model_rows) == 6,
        "resultCompleteness": result_count == 4960 and target_count == 124 and step_count == 40,
        "engineeringConversion": conversion_failures == 0,
        "predictionInputHash": input_hash == expected_input_hash,
        "predictionOutputHash": output_hash == expected_output_hash,
        "persistedIntegrity": bool(gate["data"]["resultIntegrityValid"]) and int(gate["data"]["actualPointCount"]) == int(gate["data"]["expectedPointCount"]) == 4960 and persisted_hash_count == 6,
        "replayGate": gate.get("code") == 0 and bool(gate["data"]["executionEligible"]),
        "futureState": future.get("code") == 0 and bool(future["data"]["executionEligible"]) and len(future["data"]["stateHash"]) == 64,
        "evaluateCandidate": evaluate.get("code") == 0 and int(evaluate["data"]["eventCount"]) >= 1,
        "evaluateFormalSideEffectFree": before == after_evaluate,
        "executeFormalEvent": execute.get("code") == 0 and link_count == 1,
        "executeGate": execute_gate_row == ["REPRODUCTION", "1", "1", str(batch_id)],
        "responseEvidence": response_count == 1 and step_response_count >= 4 and report_count == 1 and notification_count == 0,
        "eventTrace": trace.get("code") == 0 and int(trace["data"]["predictionBatchId"]) == batch_id,
    }
    result = {
        "schemaVersion": "shm-em-phase2c-linux-reference-reproduction-v1",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "executionEnvironment": "Docker Compose Linux containers",
        "database": os.environ.get("SHM_EM_DATABASE", "shm_em_reproduce_compose"),
        "projectCode": project["data"]["projectCode"],
        "batchId": batch_id,
        "batchCode": batch["data"]["batch"]["batchCode"],
        "modelCount": model_count,
        "targetCount": target_count,
        "predictionSteps": step_count,
        "resultCount": result_count,
        "predictionInputHash": input_hash,
        "expectedPredictionInputHash": expected_input_hash,
        "predictionOutputHash": output_hash,
        "expectedPredictionOutputHash": expected_output_hash,
        "models": model_rows,
        "gate": {"resultIntegrityValid": bool(gate["data"]["resultIntegrityValid"]), "executionEligible": bool(gate["data"]["executionEligible"]), "actualPointCount": int(gate["data"]["actualPointCount"]), "expectedPointCount": int(gate["data"]["expectedPointCount"]), "persistedRunHashCount": persisted_hash_count, "gateHash": gate["data"]["gateHash"]},
        "futureState": {"stateHash": future["data"]["stateHash"], "aggregationPolicyHash": future["data"]["aggregationPolicyHash"], "observedRisk": future["data"].get("observedRisk"), "forecastRisk": future["data"].get("forecastRisk")},
        "evaluate": {"eventCount": int(evaluate["data"]["eventCount"]), "formalStateBefore": before, "formalStateAfter": after_evaluate},
        "execute": {"eventId": event_id, "eventCode": execute["data"]["event"]["eventCode"], "predictionGateId": execute_gate_id, "predictionGateMode": execute_gate_row[0], "formalStateAfter": after_execute, "predictionLinkCount": link_count, "responseWorkflowCount": response_count, "responseStepCount": step_response_count, "reportCount": report_count, "notificationCount": notification_count},
        "composeServices": compose_json(repo, compose_file, "ps", "--format", "json"),
        "checks": checks,
        "pass": all(checks.values()),
    }
    output = repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"models": model_count, "targets": target_count, "steps": step_count, "rows": result_count, "inputHashMatch": checks["predictionInputHash"], "outputHashMatch": checks["predictionOutputHash"], "gateEligible": checks["replayGate"], "futureState": checks["futureState"], "evaluateSideEffectFree": checks["evaluateFormalSideEffectFree"], "execute": checks["executeFormalEvent"], "provenance": checks["eventTrace"], "pass": result["pass"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
