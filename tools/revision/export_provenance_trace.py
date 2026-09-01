#!/usr/bin/env python3
"""Create one reversible public-reference event and export its provenance chain."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from benchmark_reference_workflow import formal_state, restore_formal_state, rule_payload
from phase2a_benchmark_support import Backend, Database, api_request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-host", default="127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default=os.environ.get("SHM_EM_DB_PASSWORD"))
    parser.add_argument("--database", default="shm_em_reproduce_benchmark_reference")
    parser.add_argument("--backend-port", type=int, default=5201)
    parser.add_argument("--java", type=Path, default=Path("java"))
    parser.add_argument("--backend-jar", type=Path, default=Path("src/backend/target/SHM-EM-1.0.1.jar"))
    parser.add_argument(
        "--output", type=Path,
        default=Path("artifacts/revision/manuscript/provenance-trace-final.json"),
    )
    parser.add_argument(
        "--artifact-markdown", type=Path,
        default=Path("artifacts/revision/manuscript/provenance-trace-final.md"),
    )
    parser.add_argument(
        "--documentation", type=Path,
        default=Path("docs/revision/PROVENANCE_TRACE_EXAMPLE.md"),
    )
    args = parser.parse_args()
    if not args.db_password:
        parser.error("--db-password or SHM_EM_DB_PASSWORD is required")
    return args


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")


def parse_json(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return value


def markdown(value: dict[str, Any]) -> str:
    trace = value["eventTraceApi"]
    integrity = value["persistedIntegrity"]
    event = value["formalEvent"]
    rule = value["rule"]
    lines = [
        "# Public Reference Provenance Trace",
        "",
        f"This trace was captured from one formal reproduction event on the public reference database at Final Core Freeze v3 `{value['finalCoreFreezeV3']}`. Formal tables were restored to their pre-run baseline after export.",
        "",
        "## Trace chain",
        "",
        f"1. Event `{event['eventCode']}` (captured database ID `{event['eventId']}`) was created by rule `{rule['ruleCode']}` version `{rule['ruleVersion']}`.",
        f"2. The event resolves to prediction batch `{trace['batchCode']}` (ID `{trace['predictionBatchId']}`), base time `{trace['baseTime']}`.",
        f"3. It resolves to run `{trace['predictionRunId']}`, model `{trace['modelCode']}` version `{trace['modelVersion']}`, artifact SHA-256 `{trace['artifactHash']}`.",
        f"4. The input window is `{trace['inputWindowStart']}` through `{trace['inputWindowEnd']}` and the input-schema SHA-256 is `{trace['inputSchemaHash']}`.",
        f"5. First activated exceedance is `{trace['firstExceedanceTime']}`, lead time `{trace['leadTimeMinutes']}` minutes, peak `{trace['peakPredictedValue']}`, with `{trace['consecutiveExceedanceSteps']}` consecutive steps.",
        f"6. Gate `{trace['predictionGateId']}` was eligible and independently reported persisted-result integrity `{integrity['resultIntegrityValid']}`.",
        "",
        "## API and persisted-integrity boundary",
        "",
        "The Event Trace API exposes event, rule-linked prediction batch/run/model/input-window metadata, artifact and input-schema hashes, forecast snapshot, and gate identity/eligibility. It does **not** expose `persisted_result_hash`. The export therefore reports persisted run/batch hashes in a separate `persistedIntegrity` object queried from the isolated reproduction database; those hashes are independently revalidated by the execution gate.",
        "",
        "## Side-effect boundary",
        "",
        f"The isolated Execute call created deltas `{json.dumps(value['formalDeltas'], sort_keys=True)}`. Evaluate/Execute evidence elsewhere shows Evaluate has zero formal deltas. After this artifact was written, the script restored every append-only formal table to its recorded baseline; the captured event is evidence, not seed data left in the database.",
        "",
        "The complete machine-readable trace and selected 40-step engineering forecast series are in `artifacts/revision/manuscript/provenance-trace-final.json`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    jar = args.backend_jar if args.backend_jar.is_absolute() else repo / args.backend_jar
    if not jar.is_file():
        raise RuntimeError(f"Backend JAR not found: {jar}")
    support_args = SimpleNamespace(
        db_host=args.db_host, db_port=args.db_port, db_user=args.db_user,
        db_password=args.db_password, java=args.java, backend_jar=jar,
    )
    runtime_root = repo / "artifacts/revision/manuscript/runtime-provenance"
    db = Database(support_args, args.database)
    backend = Backend(support_args, args.database, args.backend_port, runtime_root)
    baseline = formal_state(db)
    result: dict[str, Any] | None = None
    try:
        project = db.one("SELECT id, project_code FROM em_project WHERE project_code=%s", ("SHM_EM_PUBLIC_SAMPLE",))
        if project is None:
            raise RuntimeError("Public reference project is missing")
        project_id = int(project["id"])
        batch = db.one(
            "SELECT id, batch_code, base_time FROM em_prediction_batch "
            "WHERE project_id=%s AND status='success' ORDER BY id DESC LIMIT 1",
            (project_id,),
        )
        rule = db.one(
            "SELECT id, rule_code, current_version, rule_snapshot_json FROM em_event_rule "
            "WHERE project_id=%s AND rule_code='PRED_GROUND_SETTLEMENT_WARNING'",
            (project_id,),
        )
        if batch is None or rule is None:
            raise RuntimeError("Public reference batch or prediction rule is missing")
        batch_id = int(batch["id"])
        rule_id = int(rule["id"])
        backend.start()
        execute = api_request(
            args.backend_port, "POST", f"/api/em/projects/{project_id}/rules/{rule_id}/execute",
            rule_payload(rule_id, batch_id),
        )
        event = execute["data"].get("event")
        if not event:
            raise RuntimeError("Execute did not create a formal event")
        event_id = int(event["id"])
        trace_response = api_request(
            args.backend_port, "GET", f"/api/em/predictions/events/{event_id}/trace"
        )
        trace = trace_response["data"]
        after = formal_state(db)
        deltas = {
            table: after[table]["count"] - baseline[table]["count"]
            for table in baseline
        }
        event_row = db.one(
            "SELECT id,event_code,project_id,station_id,instrument_id,metric_code,rule_id,"
            "evaluation_run_id,event_type,event_level,event_status,source_type,run_type,detected_at,"
            "trigger_value,threshold_value,unit,trigger_reason,calculation_snapshot_json "
            "FROM em_monitoring_event WHERE id=%s",
            (event_id,),
        )
        link = db.one("SELECT * FROM em_event_prediction_link WHERE event_id=%s", (event_id,))
        gate = db.one(
            "SELECT id,batch_id,execution_mode,execution_eligible,result_integrity_valid,"
            "actual_point_count,expected_point_count,issues_json,gate_hash,evaluated_at "
            "FROM em_prediction_execution_gate WHERE id=%s",
            (trace["predictionGateId"],),
        )
        run = db.one(
            "SELECT id,result_hash,persisted_result_hash,persisted_result_hash_version,input_snapshot_json "
            "FROM em_prediction_run WHERE id=%s",
            (trace["predictionRunId"],),
        )
        persisted_batch = db.one(
            "SELECT id,input_hash,output_hash,persisted_output_hash,persisted_output_hash_version "
            "FROM em_prediction_batch WHERE id=%s",
            (batch_id,),
        )
        forecast = db.all(
            "SELECT step,future_time,engineering_value,engineering_unit,conversion_operator_code,"
            "conversion_version,conversion_status FROM em_prediction_result "
            "WHERE batch_id=%s AND feature_code=%s ORDER BY step",
            (batch_id, "dtu1_point1_settlement_value"),
        )
        result = {
            "schemaVersion": "shm-em-provenance-trace-final-v1",
            "finalCoreFreezeV3": "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f",
            "source": {"database": args.database, "projectCode": project["project_code"], "isolatedFormalStateRestored": True},
            "formalEvent": {
                "eventId": event_id, "eventCode": event_row["event_code"],
                "eventType": event_row["event_type"], "level": event_row["event_level"],
                "sourceType": event_row["source_type"], "detectedAt": event_row["detected_at"],
                "metricCode": event_row["metric_code"], "triggerValue": event_row["trigger_value"],
                "thresholdValue": event_row["threshold_value"], "unit": event_row["unit"],
                "reason": event_row["trigger_reason"],
                "calculationSnapshot": parse_json(event_row["calculation_snapshot_json"]),
            },
            "rule": {
                "ruleId": rule_id, "ruleCode": rule["rule_code"], "ruleVersion": rule["current_version"],
                "ruleSnapshot": parse_json(rule["rule_snapshot_json"]),
            },
            "eventTraceApi": trace,
            "eventPredictionLink": {key: parse_json(value) for key, value in link.items()},
            "persistedIntegrity": {
                "resultIntegrityValid": bool(gate["result_integrity_valid"]),
                "executionEligible": bool(gate["execution_eligible"]),
                "actualPointCount": int(gate["actual_point_count"]),
                "expectedPointCount": int(gate["expected_point_count"]),
                "gateHash": gate["gate_hash"], "gateIssues": parse_json(gate["issues_json"]),
                "runResultHash": run["result_hash"], "persistedResultHash": run["persisted_result_hash"],
                "persistedResultHashVersion": run["persisted_result_hash_version"],
                "batchInputHash": persisted_batch["input_hash"], "batchOutputHash": persisted_batch["output_hash"],
                "persistedBatchOutputHash": persisted_batch["persisted_output_hash"],
                "persistedBatchOutputHashVersion": persisted_batch["persisted_output_hash_version"],
                "apiBoundaryNote": "persisted_result_hash is independently verified by the Gate and is not exposed by Event Trace API",
            },
            "inputSnapshot": parse_json(run["input_snapshot_json"]),
            "selectedForecastSeries": {
                "featureCode": "dtu1_point1_settlement_value", "pointCount": len(forecast),
                "points": forecast,
            },
            "formalDeltas": deltas,
            "capturedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        if not (
            result["persistedIntegrity"]["resultIntegrityValid"]
            and result["persistedIntegrity"]["executionEligible"]
            and len(forecast) == 40
            and deltas.get("em_monitoring_event") == 1
            and deltas.get("em_event_prediction_link") == 1
        ):
            raise RuntimeError("Exported provenance chain did not satisfy its integrity contract")
        write_json(repo / args.output, result)
        text = markdown(result)
        for relative in (args.artifact_markdown, args.documentation):
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    finally:
        backend.stop()
        restore_formal_state(db, baseline)
        db.close()
    if result is None:
        raise RuntimeError("No provenance artifact was generated")
    print(json.dumps({"eventId": result["formalEvent"]["eventId"], "forecastPoints": result["selectedForecastSeries"]["pointCount"], "restored": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
