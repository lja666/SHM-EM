#!/usr/bin/env python3
"""Benchmark the frozen six-model SHM-EM public reference workflow."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any
import urllib.parse

from phase2a_benchmark_support import (
    Backend,
    Database,
    cleanup_runtime,
    initialize_database,
    run_api_repetitions,
    resolve_common_args,
    summary,
    table_storage,
    write_csv,
    write_json,
    write_text,
)


PROJECT_CODE = "SHM_EM_PUBLIC_SAMPLE"
FORMAL_TABLES = (
    "em_event_evidence_link",
    "em_notification_delivery_log",
    "em_event_response_step",
    "em_event_prediction_link",
    "em_event_metric_snapshot",
    "em_report_instance",
    "em_evidence_resource",
    "em_notification_task",
    "em_event_response_workflow",
    "em_event_handling_log",
    "em_monitoring_event",
    "em_event_evaluation_run",
)
PERSISTED_FIELDS = (
    "target_type, feature_code, project_id, station_id, instrument_id, "
    "metric_code, engineering_metric_code, step, horizon_minutes, "
    "base_time, future_time, raw_predicted_value, raw_predicted_unit, "
    "predicted_value, predicted_unit, engineering_value, engineering_unit, "
    "lower_bound, upper_bound, engineering_lower_bound, engineering_upper_bound, "
    "confidence, conversion_operator_code, conversion_version, conversion_status, "
    "quality_flag, source_record_key"
)


def pit_pre_config(args, database: str) -> Path:
    path = args.runtime_root / "pit-pre-reference.json"
    path.write_text(
        json.dumps(
            {
                "database": {
                    "host": args.db_host,
                    "port": args.db_port,
                    "user": args.db_user,
                    "password": args.db_password,
                    "database": database,
                    "charset": "utf8mb4",
                },
                "working_directory": str(args.pit_pre_root),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def benchmark_pit_pre(args, database: str, output: Path) -> dict[str, Any]:
    sys.path.insert(0, str(args.pit_pre_root))
    from pit_pre.cached_model_runner import CachedModelRunner
    from pit_pre.config import load_config
    from pit_pre.contract import load_app_config
    from pit_pre.pipeline import PredictionPipeline

    config_path = pit_pre_config(args, database)
    started = time.perf_counter_ns()
    bootstrap = load_config(config_path)
    bootstrap_ms = (time.perf_counter_ns() - started) / 1_000_000
    started = time.perf_counter_ns()
    config = load_app_config(bootstrap, PROJECT_CODE)
    contract_ms = (time.perf_counter_ns() - started) / 1_000_000
    model_codes = list(config.models)
    started = time.perf_counter_ns()
    runner = CachedModelRunner(config.models)
    model_cache_ms = (time.perf_counter_ns() - started) / 1_000_000
    started = time.perf_counter_ns()
    pipeline = PredictionPipeline(config, runner)
    pipeline_init_ms = (time.perf_counter_ns() - started) / 1_000_000

    current: dict[str, Any] = {}
    original_build = pipeline.wide_builder.build_with_diagnostics
    original_run = runner.run
    original_create = pipeline.result_writer.create_batch
    original_write = pipeline.result_writer.write
    original_finish = pipeline.result_writer.finish_batch
    original_convert = pipeline.result_writer._apply_engineering_conversion
    original_result_hash = pipeline.result_writer._persisted_result_hash
    original_output_hash = pipeline.result_writer._persisted_output_hash

    def timed_build(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_build(*values, **keywords)
        current["inputAssemblyMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_model(model, frame):
        started_ns = time.perf_counter_ns()
        result = original_run(model, frame)
        elapsed = (time.perf_counter_ns() - started_ns) / 1_000_000
        current["modelInferenceMs"][model.code] += elapsed
        return result

    def timed_create(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_create(*values, **keywords)
        current["predictionWriteTotalMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_write(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_write(*values, **keywords)
        current["predictionWriteTotalMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_finish(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_finish(*values, **keywords)
        current["predictionWriteTotalMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_convert(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_convert(*values, **keywords)
        current["engineeringConversionMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_result_hash(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_result_hash(*values, **keywords)
        current["persistedIntegrityHashMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    def timed_output_hash(*values, **keywords):
        started_ns = time.perf_counter_ns()
        result = original_output_hash(*values, **keywords)
        current["persistedIntegrityHashMs"] += (time.perf_counter_ns() - started_ns) / 1_000_000
        return result

    pipeline.wide_builder.build_with_diagnostics = timed_build
    runner.run = timed_model
    pipeline.result_writer.create_batch = timed_create
    pipeline.result_writer.write = timed_write
    pipeline.result_writer.finish_batch = timed_finish
    pipeline.result_writer._apply_engineering_conversion = timed_convert
    pipeline.result_writer._persisted_result_hash = timed_result_hash
    pipeline.result_writer._persisted_output_hash = timed_output_hash

    db = Database(args, database)
    raw: list[dict[str, Any]] = []
    per_model: list[dict[str, Any]] = []
    try:
        phases = [("first", 1), ("warmup", args.warmups), ("measured", args.measured)]
        for phase, count in phases:
            for repetition in range(1, count + 1):
                current.clear()
                current.update(
                    {
                        "inputAssemblyMs": 0.0,
                        "modelInferenceMs": defaultdict(float),
                        "predictionWriteTotalMs": 0.0,
                        "engineeringConversionMs": 0.0,
                        "persistedIntegrityHashMs": 0.0,
                    }
                )
                started_ns = time.perf_counter_ns()
                results = pipeline.run_models(model_codes)
                full_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
                batch_ids = {item.batch_id for item in results}
                if len(batch_ids) != 1:
                    raise RuntimeError(f"PIT_PRE produced inconsistent batch ids: {batch_ids}")
                batch_id = int(next(iter(batch_ids)))
                persisted_rows = int(db.scalar("SELECT COUNT(*) FROM em_prediction_result WHERE batch_id=%s", (batch_id,)))
                valid_runs = int(
                    db.scalar(
                        "SELECT COUNT(*) FROM em_prediction_run WHERE batch_id=%s AND status='success' "
                        "AND persisted_result_hash IS NOT NULL AND persisted_result_hash_version IS NOT NULL",
                        (batch_id,),
                    )
                )
                batch = db.one("SELECT * FROM em_prediction_batch WHERE id=%s", (batch_id,))
                valid = (
                    persisted_rows == 4960
                    and valid_runs == 6
                    and batch is not None
                    and batch["status"] == "success"
                    and batch["persisted_output_hash"] is not None
                )
                if not valid:
                    raise RuntimeError(
                        f"Invalid reference PIT_PRE result batch={batch_id}, rows={persisted_rows}, runs={valid_runs}"
                    )
                inference_ms = sum(current["modelInferenceMs"].values())
                persistence_exclusive = max(
                    0.0,
                    current["predictionWriteTotalMs"]
                    - current["engineeringConversionMs"]
                    - current["persistedIntegrityHashMs"],
                )
                raw.append(
                    {
                        "phase": phase,
                        "repetition": repetition,
                        "batchId": batch_id,
                        "modelCount": 6,
                        "targetCount": 124,
                        "rowCount": persisted_rows,
                        "inputAssemblyMs": round(current["inputAssemblyMs"], 6),
                        "allModelInferenceMs": round(inference_ms, 6),
                        "engineeringConversionMs": round(current["engineeringConversionMs"], 6),
                        "predictionWriteTotalMs": round(current["predictionWriteTotalMs"], 6),
                        "predictionPersistenceExclusiveEstimateMs": round(persistence_exclusive, 6),
                        "persistedIntegrityHashMs": round(current["persistedIntegrityHashMs"], 6),
                        "fullBatchMs": round(full_ms, 6),
                        "valid": True,
                    }
                )
                for model_code in model_codes:
                    per_model.append(
                        {
                            "phase": phase,
                            "repetition": repetition,
                            "batchId": batch_id,
                            "modelCode": model_code,
                            "inferenceMs": round(current["modelInferenceMs"][model_code], 6),
                        }
                    )
    finally:
        db.close()

    raw_fields = [
        "phase", "repetition", "batchId", "modelCount", "targetCount", "rowCount",
        "inputAssemblyMs", "allModelInferenceMs", "engineeringConversionMs",
        "predictionWriteTotalMs", "predictionPersistenceExclusiveEstimateMs",
        "persistedIntegrityHashMs", "fullBatchMs", "valid",
    ]
    write_csv(output / "pitpre-raw.csv", raw, raw_fields)
    write_csv(output / "pitpre-per-model-raw.csv", per_model, ["phase", "repetition", "batchId", "modelCode", "inferenceMs"])
    measured_rows = [item for item in raw if item["phase"] == "measured"]
    component_fields = [
        "inputAssemblyMs", "allModelInferenceMs", "engineeringConversionMs",
        "predictionWriteTotalMs", "predictionPersistenceExclusiveEstimateMs",
        "persistedIntegrityHashMs", "fullBatchMs",
    ]
    result = {
        "schemaVersion": "shm-em-phase2a-pitpre-v1",
        "workload": {"projectCode": PROJECT_CODE, "models": 6, "targets": 124, "steps": 40, "rows": 4960},
        "method": {
            "cacheMode": "one in-process CachedModelRunner; model artifacts loaded once",
            "firstRuns": 1,
            "warmups": args.warmups,
            "measured": args.measured,
            "concurrency": 1,
            "overlapNote": "predictionWriteTotal includes engineering conversion and persisted-integrity hashing; the exclusive estimate subtracts these measured nested intervals",
        },
        "oneTimeSetup": {
            "bootstrapConfigLoadMs": round(bootstrap_ms, 6),
            "databaseContractLoadMs": round(contract_ms, 6),
            "modelLoadingCachePreparationMs": round(model_cache_ms, 6),
            "pipelineInitializationMs": round(pipeline_init_ms, 6),
        },
        "components": {field.removesuffix("Ms"): summary([item[field] for item in measured_rows]) for field in component_fields},
        "perModelInference": {
            model: summary([item["inferenceMs"] for item in per_model if item["phase"] == "measured" and item["modelCode"] == model])
            for model in model_codes
        },
        "lastBatchId": raw[-1]["batchId"],
        "pass": len(measured_rows) == args.measured and all(item["valid"] for item in raw),
    }
    write_json(output / "pitpre-summary.json", result)
    return result


def formal_state(db: Database) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    available = {next(iter(row.values())) for row in db.all("SHOW TABLES")}
    for table in FORMAL_TABLES:
        if table not in available:
            continue
        row = db.one(f"SELECT COUNT(*) AS count, COALESCE(MAX(id),0) AS max_id FROM `{table}`")
        result[table] = {"count": int(row["count"]), "maxId": int(row["max_id"])}
    return result


def restore_formal_state(db: Database, baseline: dict[str, dict[str, int]]) -> None:
    for table in FORMAL_TABLES:
        if table in baseline:
            db.execute(f"DELETE FROM `{table}` WHERE id > %s", (baseline[table]["maxId"],))
    current = formal_state(db)
    if current != baseline:
        raise RuntimeError(f"Execute baseline restore mismatch: expected={baseline}, actual={current}")


def formal_delta(before: dict[str, dict[str, int]], after: dict[str, dict[str, int]]) -> dict[str, int]:
    return {table: after[table]["count"] - before[table]["count"] for table in before}


def formal_effect_state(state: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """Exclude the expected audit-only record produced by Evaluate."""
    return {table: value for table, value in state.items() if table != "em_event_evaluation_run"}


def rule_payload(rule_id: int, batch_id: int) -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "inputSource": "PREDICTION",
        "predictionBatchId": batch_id,
        "predictionModelCode": "settlement",
        "predictionTargetType": "settlement",
        "predictionFeatureCode": "dtu1_point1_settlement_value",
        "forecastHorizonMinutes": 120,
        "minimumConsecutiveSteps": 2,
        "seriesQualityFilter": "normal",
        "predictionExecutionMode": "REPRODUCTION",
    }


def benchmark_integrity(args, database: str, batch_id: int, output: Path) -> dict[str, Any]:
    sys.path.insert(0, str(args.pit_pre_root))
    from pit_pre.result_writer import persisted_output_hash, persisted_result_hash

    db = Database(args, database)
    raw: list[dict[str, Any]] = []
    try:
        phases = [("first", 1), ("warmup", args.warmups), ("measured", args.measured)]
        for phase, count in phases:
            for repetition in range(1, count + 1):
                started = time.perf_counter_ns()
                runs = db.all(
                    "SELECT id, model_code, model_version, persisted_result_hash FROM em_prediction_run "
                    "WHERE batch_id=%s ORDER BY model_code, model_version",
                    (batch_id,),
                )
                run_hashes = {}
                row_count = 0
                all_match = True
                for run in runs:
                    rows = db.all(
                        f"SELECT {PERSISTED_FIELDS} FROM em_prediction_result WHERE run_id=%s "
                        "ORDER BY feature_code, step, source_record_key",
                        (run["id"],),
                    )
                    row_count += len(rows)
                    calculated = persisted_result_hash(rows)
                    all_match = all_match and calculated == run["persisted_result_hash"]
                    run_hashes[f"{run['model_code']}@{run['model_version']}"] = calculated
                batch = db.one("SELECT persisted_output_hash FROM em_prediction_batch WHERE id=%s", (batch_id,))
                calculated_output = persisted_output_hash(run_hashes)
                all_match = all_match and batch is not None and calculated_output == batch["persisted_output_hash"]
                elapsed = (time.perf_counter_ns() - started) / 1_000_000
                if not all_match or row_count != 4960 or len(runs) != 6:
                    raise RuntimeError("Reference persisted-integrity recomputation failed")
                raw.append(
                    {
                        "phase": phase,
                        "repetition": repetition,
                        "batchId": batch_id,
                        "runCount": len(runs),
                        "rowCount": row_count,
                        "elapsedMs": round(elapsed, 6),
                        "allHashesMatch": all_match,
                    }
                )
    finally:
        db.close()
    write_csv(output / "integrity-raw.csv", raw, ["phase", "repetition", "batchId", "runCount", "rowCount", "elapsedMs", "allHashesMatch"])
    result = {
        "schemaVersion": "shm-em-phase2a-integrity-v1",
        "scope": "DB fetch plus cross-language canonical persisted-result and batch-output hash recomputation",
        "firstMs": raw[0]["elapsedMs"],
        **summary([item["elapsedMs"] for item in raw if item["phase"] == "measured"]),
        "allHashesMatch": all(item["allHashesMatch"] for item in raw),
        "pass": len([item for item in raw if item["phase"] == "measured"]) == args.measured and all(item["allHashesMatch"] for item in raw),
    }
    write_json(output / "integrity-summary.json", result)
    return result


def benchmark_backend(args, database: str, batch_id: int, output: Path) -> dict[str, Any]:
    runtime = args.runtime_root / "reference-backend"
    backend = Backend(args, database, args.backend_port, runtime)
    db = Database(args, database)
    all_raw: list[dict[str, Any]] = []
    operation_summaries: dict[str, Any] = {}
    execute_rows: list[dict[str, Any]] = []
    try:
        project_id = int(db.scalar("SELECT id FROM em_project WHERE project_code=%s", (PROJECT_CODE,)))
        rule = db.one("SELECT id FROM em_event_rule WHERE project_id=%s AND rule_code='PRED_GROUND_SETTLEMENT_WARNING'", (project_id,))
        if rule is None:
            raise RuntimeError("Public prediction rule is missing")
        rule_id = int(rule["id"])
        feature_code = str(db.scalar("SELECT feature_code FROM em_prediction_result WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,)))
        backend.start()

        operations = [
            (
                "gate-inspect",
                "GET",
                f"/api/em/predictions/batches/{batch_id}/execution-gate?mode=REPRODUCTION",
                None,
                lambda value: {
                    "pass": value["data"]["batchId"] == batch_id and value["data"]["executionEligible"] is True and value["data"]["resultIntegrityValid"] is True,
                    "projectId": value["data"]["projectId"],
                    "batchId": value["data"]["batchId"],
                    "rowCount": value["data"]["actualPointCount"],
                    "resultIntegrityValid": value["data"]["resultIntegrityValid"],
                    "executionEligible": value["data"]["executionEligible"],
                },
            ),
            (
                "gate-evaluate",
                "POST",
                f"/api/em/predictions/batches/{batch_id}/execution-gate/evaluate?mode=REPRODUCTION",
                {},
                lambda value: {
                    "pass": value["data"]["batchId"] == batch_id and value["data"]["executionEligible"] is True and value["data"]["resultIntegrityValid"] is True,
                    "projectId": value["data"]["projectId"],
                    "batchId": value["data"]["batchId"],
                    "rowCount": value["data"]["actualPointCount"],
                    "resultIntegrityValid": value["data"]["resultIntegrityValid"],
                    "executionEligible": value["data"]["executionEligible"],
                },
            ),
            (
                "future-state",
                "GET",
                f"/api/em/projects/{project_id}/future-state?batchId={batch_id}&horizonMinutes=120&executionMode=REPRODUCTION",
                None,
                lambda value: {
                    "pass": value["data"]["projectId"] == project_id and value["data"]["batchId"] == batch_id and value["data"]["executionEligible"] is True,
                    "projectId": value["data"]["projectId"],
                    "batchId": value["data"]["batchId"],
                    "rowCount": value["data"]["executionGate"]["actualPointCount"],
                    "resultIntegrityValid": value["data"]["executionGate"]["resultIntegrityValid"],
                    "executionEligible": value["data"]["executionEligible"],
                },
            ),
            (
                "series-single-target",
                "GET",
                "/api/em/predictions/series?" + urllib.parse.urlencode({"projectId": project_id, "batchId": batch_id, "featureCode": feature_code, "includeObserved": "false", "valueMode": "ENGINEERING", "limit": 100}),
                None,
                lambda value: {
                    "pass": len(value["data"]) == 40 and all(item["sourceBatchId"] == batch_id for item in value["data"]),
                    "projectId": project_id,
                    "batchId": batch_id,
                    "rowCount": len(value["data"]),
                    "resultIntegrityValid": "not_applicable",
                    "executionEligible": "not_applicable",
                },
            ),
            (
                "series-full-batch",
                "GET",
                "/api/em/predictions/series?" + urllib.parse.urlencode({"projectId": project_id, "batchId": batch_id, "includeObserved": "false", "valueMode": "ENGINEERING", "limit": 50000}),
                None,
                lambda value: {
                    "pass": len(value["data"]) == 4960 and all(item["sourceBatchId"] == batch_id for item in value["data"]),
                    "projectId": project_id,
                    "batchId": batch_id,
                    "rowCount": len(value["data"]),
                    "resultIntegrityValid": "not_applicable",
                    "executionEligible": "not_applicable",
                },
            ),
            (
                "evaluate",
                "POST",
                f"/api/em/projects/{project_id}/rules/{rule_id}/evaluate",
                rule_payload(rule_id, batch_id),
                lambda value: {
                    "pass": value["data"]["eventCount"] > 0 and value["data"]["executionEligible"] is True,
                    "projectId": project_id,
                    "batchId": batch_id,
                    "rowCount": value["data"]["eventCount"],
                    "resultIntegrityValid": value["data"]["predictionGate"]["resultIntegrityValid"],
                    "executionEligible": value["data"]["executionEligible"],
                },
            ),
        ]
        evaluate_formal_before = formal_state(db)
        for operation, method, path, payload, validator in operations:
            rows, operation_summary = run_api_repetitions(
                args.backend_port,
                operation,
                method,
                path,
                payload,
                validator,
                args.warmups,
                args.measured,
                {"workload": "reference"},
            )
            all_raw.extend(rows)
            operation_summaries[operation] = operation_summary
        evaluate_formal_after = formal_state(db)
        if formal_effect_state(evaluate_formal_after) != formal_effect_state(evaluate_formal_before):
            raise RuntimeError("Evaluate benchmark changed formal event/response state")

        baseline = formal_state(db)
        final_event_id = None
        for repetition in range(1, args.execute_repetitions + 1):
            restore_formal_state(db, baseline)
            started_ns = time.perf_counter_ns()
            from phase2a_benchmark_support import api_request

            response = api_request(
                args.backend_port,
                "POST",
                f"/api/em/projects/{project_id}/rules/{rule_id}/execute",
                rule_payload(rule_id, batch_id),
            )
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
            after = formal_state(db)
            deltas = formal_delta(baseline, after)
            event = response["data"].get("event")
            steps = response["data"].get("responseSteps") or []
            evaluation = response["data"].get("evaluation") or {}
            valid = (
                evaluation.get("executionEligible") is True
                and event is not None
                and deltas.get("em_monitoring_event") == 1
                and deltas.get("em_event_response_workflow") == 1
                and deltas.get("em_event_response_step") == 4
                and deltas.get("em_event_prediction_link") == 1
                and len(steps) == 4
            )
            if not valid:
                raise RuntimeError(f"Execute benchmark repetition {repetition} invalid: deltas={deltas}")
            final_event_id = int(event["id"])
            execute_rows.append(
                {
                    "phase": "measured",
                    "repetition": repetition,
                    "baselineRestored": True,
                    "elapsedMs": round(elapsed_ms, 6),
                    "eventId": final_event_id,
                    "eventDelta": deltas.get("em_monitoring_event"),
                    "workflowDelta": deltas.get("em_event_response_workflow"),
                    "stepDelta": deltas.get("em_event_response_step"),
                    "predictionLinkDelta": deltas.get("em_event_prediction_link"),
                    "reportDelta": deltas.get("em_report_instance"),
                    "stepStatuses": json.dumps({item["stepCode"]: item["status"] for item in steps}, sort_keys=True),
                    "valid": valid,
                }
            )
        if final_event_id is None:
            raise RuntimeError("Execute benchmark produced no event")
        provenance_rows, provenance_summary = run_api_repetitions(
            args.backend_port,
            "provenance-trace",
            "GET",
            f"/api/em/predictions/events/{final_event_id}/trace",
            None,
            lambda value: {
                "pass": value["data"]["eventId"] == final_event_id and value["data"]["predictionBatchId"] == batch_id and value["data"]["artifactHash"] is not None,
                "projectId": project_id,
                "batchId": value["data"]["predictionBatchId"],
                "rowCount": 1,
                "resultIntegrityValid": "gate_revalidated_separately",
                "executionEligible": "not_applicable",
            },
            args.warmups,
            args.measured,
            {"workload": "reference"},
        )
        all_raw.extend(provenance_rows)
        operation_summaries["provenance-trace"] = provenance_summary
        operation_summaries["execute"] = {
            "operation": "execute",
            **summary([item["elapsedMs"] for item in execute_rows]),
            "baselineIsolation": "same isolated DB; all append-only formal tables restored to recorded max-id/count baseline before each call",
        }
        write_json(
            output / "execute-case-evidence" / "baseline.json",
            {"formalState": baseline, "ruleId": rule_id, "batchId": batch_id, "repetitions": args.execute_repetitions},
        )
        write_json(
            output / "execute-case-evidence" / "last-response.json",
            {"eventId": final_event_id, "formalStateAfter": formal_state(db)},
        )
        restore_formal_state(db, baseline)
    finally:
        backend.stop()
        if backend.stdout_path.is_file():
            lines = backend.stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
            write_text(output / "backend-log-tail.txt", "\n".join(lines[-200:]))
        db.close()

    write_csv(
        output / "backend-raw.csv",
        all_raw,
        ["operation", "phase", "repetition", "elapsedMs", "httpCode", "workload", "projectId", "batchId", "rowCount", "resultIntegrityValid", "executionEligible", "pass"],
    )
    write_csv(
        output / "execute-raw.csv",
        execute_rows,
        ["phase", "repetition", "baselineRestored", "elapsedMs", "eventId", "eventDelta", "workflowDelta", "stepDelta", "predictionLinkDelta", "reportDelta", "stepStatuses", "valid"],
    )
    result = {
        "schemaVersion": "shm-em-phase2a-backend-reference-v1",
        "batchId": batch_id,
        "method": {"firstCalls": 1, "warmups": args.warmups, "measured": args.measured, "executeMeasured": args.execute_repetitions, "concurrency": 1},
        "operations": operation_summaries,
        "evaluateFormalSideEffects": 0,
        "executeAllBaselinesRestored": all(item["baselineRestored"] for item in execute_rows),
        "executeAllValid": all(item["valid"] for item in execute_rows),
        "pass": len(execute_rows) == args.execute_repetitions and all(item["valid"] for item in execute_rows),
    }
    write_json(output / "backend-summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the SHM-EM public reference workflow")
    parser.add_argument("--database", default="shm_em_reproduce_benchmark_reference")
    parser.add_argument("--backend-port", type=int, default=5196)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--measured", type=int, default=30)
    parser.add_argument("--execute-repetitions", type=int, default=10)
    args = resolve_common_args(parser)
    if not args.database.startswith("shm_em_reproduce_benchmark_"):
        parser.error("Database must match shm_em_reproduce_benchmark_*")
    output = args.evidence_root / "reference"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    started_at = datetime.now().astimezone()
    try:
        imports = initialize_database(args, args.database)
        write_json(output / "sql-imports.json", imports)
        db = Database(args, args.database)
        try:
            write_json(output / "storage-before.json", table_storage(db))
        finally:
            db.close()
        pitpre = benchmark_pit_pre(args, args.database, output)
        integrity = benchmark_integrity(args, args.database, int(pitpre["lastBatchId"]), args.evidence_root / "integrity")
        backend = benchmark_backend(args, args.database, int(pitpre["lastBatchId"]), output)
        db = Database(args, args.database)
        try:
            write_json(output / "storage-after.json", table_storage(db))
        finally:
            db.close()
        result = {
            "schemaVersion": "shm-em-phase2a-reference-result-v1",
            "database": args.database,
            "startedAt": started_at.isoformat(),
            "finishedAt": datetime.now().astimezone().isoformat(),
            "pitPre": pitpre,
            "integrity": integrity,
            "backend": backend,
            "pass": pitpre["pass"] and integrity["pass"] and backend["pass"],
        }
        write_json(output / "reference-summary.json", result)
        print(json.dumps({"pass": result["pass"], "lastBatchId": pitpre["lastBatchId"], "output": str(output)}, indent=2))
        return 0 if result["pass"] else 1
    finally:
        cleanup_runtime(args)


if __name__ == "__main__":
    raise SystemExit(main())
