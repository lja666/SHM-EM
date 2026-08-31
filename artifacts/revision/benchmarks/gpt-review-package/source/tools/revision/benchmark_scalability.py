#!/usr/bin/env python3
"""Benchmark frozen SHM-EM backend/storage scaling with valid persisted fixtures."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
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
    api_request,
    cleanup_runtime,
    initialize_database,
    run_api_repetitions,
    resolve_common_args,
    summary,
    table_storage,
    time_api,
    write_csv,
    write_json,
    write_text,
)


SCALES = (
    ("S1", 124),
    ("S2", 1_240),
    ("S3", 2_480),
    ("S4", 12_400),
    ("S5", 24_800),
)
STEPS = 40
STEP_MINUTES = 3
METRIC_CODE = "earth_pressure_p"
UNIT = "MPa"
RESULT_HASH_VERSION = "prediction-persisted-integrity-v1"
OUTPUT_HASH_VERSION = "prediction-persisted-output-integrity-v1"
PERSISTED_FIELDS = (
    "target_type", "feature_code", "project_id", "station_id", "instrument_id",
    "metric_code", "engineering_metric_code", "step", "horizon_minutes",
    "base_time", "future_time", "raw_predicted_value", "raw_predicted_unit",
    "predicted_value", "predicted_unit", "engineering_value", "engineering_unit",
    "lower_bound", "upper_bound", "engineering_lower_bound", "engineering_upper_bound",
    "confidence", "conversion_operator_code", "conversion_version", "conversion_status",
    "quality_flag", "source_record_key",
)


def chunks(values, size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def fixture_hash(label: str, purpose: str) -> str:
    return hashlib.sha256(f"phase2a:{label}:{purpose}".encode("utf-8")).hexdigest()


def create_fixture(db: Database, label: str, targets: int) -> dict[str, Any]:
    base_time = datetime(2026, 6, 24, 10, 0, 0)
    project_id = db.insert(
        "INSERT INTO em_project (project_code, project_name, infrastructure_type, scenario_label, "
        "location_text, status, description) VALUES (%s,%s,'generic','phase2a_scalability',%s,'active',%s)",
        (
            f"SHM_EM_PHASE2A_{label}",
            f"Phase 2A persisted workload {label}",
            "Synthetic benchmark-only configuration",
            "Synthetic backend/storage scalability fixture; no predictive-accuracy claim",
        ),
    )
    station_ids: list[int] = []
    instrument_ids: list[int] = []
    for index in range(1, 11):
        station_id = db.insert(
            "INSERT INTO em_station (project_id,station_code,station_name,station_type,position_desc,"
            "layout_x,layout_y,status,enabled,metadata_json) VALUES (%s,%s,%s,'earth_pressure',%s,%s,%s,'active',1,%s)",
            (
                project_id,
                f"{label}-P{index:02d}",
                f"Benchmark point {index}",
                "Fixed topology for target/row scaling",
                Decimal(index) / Decimal(11),
                Decimal(index % 3) / Decimal(3),
                json.dumps({"fixtureScope": "phase2a_scalability"}),
            ),
        )
        instrument_id = db.insert(
            "INSERT INTO em_instrument (project_id,station_id,instrument_code,instrument_name,instrument_type,"
            "sampling_mode,raw_unit_desc,status,enabled,metadata_json) VALUES (%s,%s,%s,%s,'earth_pressure',"
            "'low_frequency',%s,'online',1,%s)",
            (
                project_id,
                station_id,
                f"{label}-I{index:02d}",
                f"Benchmark instrument {index}",
                UNIT,
                json.dumps({"fixtureScope": "phase2a_scalability"}),
            ),
        )
        station_ids.append(station_id)
        instrument_ids.append(instrument_id)

    model_code = f"PHASE2A_{label}_MODEL"
    model_version = "fixture-v1"
    target_type = f"phase2a_{label.lower()}_pressure"
    hashes = {
        name: fixture_hash(label, name)
        for name in (
            "artifact", "preprocessor", "inference-script", "runtime-manifest",
            "environment", "artifact-bundle", "input-schema",
        )
    }
    model_id = db.insert(
        "INSERT INTO em_prediction_model (project_id,model_code,model_name,model_type,target_type,"
        "target_metric_code,input_metrics_json,artifact_uri,artifact_hash,preprocessor_uri,preprocessor_hash,"
        "inference_script_hash,runtime_manifest_hash,environment_digest,artifact_bundle_hash,model_version,"
        "runtime_config_json,required_history_rows,input_schema_hash,contract_version,expected_steps,"
        "time_step_minutes,max_operational_age_minutes,status) VALUES ("
        "%s,%s,%s,'persisted_scalability_fixture',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,16,%s,"
        "'phase2a-contract-v1',40,3,15,'active')",
        (
            project_id,
            model_code,
            f"Phase 2A {label} persisted workload model contract",
            target_type,
            METRIC_CODE,
            json.dumps({"fixtureScope": "backend_storage_only", "predictiveAccuracyClaim": False}),
            f"benchmark://{label}/model",
            hashes["artifact"],
            f"benchmark://{label}/preprocessor",
            hashes["preprocessor"],
            hashes["inference-script"],
            hashes["runtime-manifest"],
            hashes["environment"],
            hashes["artifact-bundle"],
            model_version,
            json.dumps({"fixtureScope": "backend_storage_only", "expectedSteps": STEPS}),
            hashes["input-schema"],
        ),
    )

    mapping_sql = (
        "INSERT INTO em_prediction_feature_mapping (project_id,model_id,feature_code,feature_name,feature_label,"
        "training_feature_code,feature_group,target_type,feature_role,station_id,instrument_id,source_metric_code,"
        "source_field,source_value_column,input_value_mode,schema_version,feature_order,required,prediction_target,"
        "transform_json,metadata_json,enabled) VALUES ("
        "%s,%s,%s,%s,%s,%s,%s,%s,'model_input',%s,%s,%s,'metric_value','metric_value','ENGINEERING',"
        "'phase2a_scalability_v1',%s,1,1,%s,%s,1)"
    )
    mapping_rows = []
    for index in range(1, targets + 1):
        feature = f"{label.lower()}_target_{index:05d}"
        object_index = (index - 1) % len(station_ids)
        mapping_rows.append(
            (
                project_id, model_id, feature, feature, f"{label} target {index}", feature,
                target_type, target_type, station_ids[object_index], instrument_ids[object_index],
                METRIC_CODE, index, json.dumps({"identity": True}),
                json.dumps({"fixtureScope": "backend_storage_only", "predictiveAccuracyClaim": False}),
            )
        )
    for group in chunks(mapping_rows, 2_000):
        db.executemany(mapping_sql, group)

    rule_id = db.insert(
        "INSERT INTO em_event_rule (project_id,rule_code,rule_name,metric_code,source_instrument_type,input_source,"
        "prediction_model_code,prediction_target_type,prediction_feature_code,forecast_horizon_minutes,"
        "minimum_consecutive_steps,series_quality_filter,station_scope,rule_mode,event_type,event_level,time_window,"
        "aggregation_method,operator,threshold_value,threshold_unit,baseline_strategy,quality_policy,missing_data_policy,"
        "result_policy,continuous_count,cooldown_minutes,current_version,rule_snapshot_json,enabled) VALUES ("
        "%s,%s,%s,%s,'earth_pressure','PREDICTION',%s,%s,%s,120,1,'normal','all','threshold',"
        "'forecast_warning','yellow','forecast','latest','>=',0.5,%s,'none','normal_only','fail','highest_level',"
        "1,0,'phase2a-v1',%s,1)",
        (
            project_id, f"PHASE2A_{label}_RULE", f"Phase 2A {label} assessment rule", METRIC_CODE,
            model_code, target_type, f"{label.lower()}_target_00001", UNIT,
            json.dumps({"fixtureScope": "backend_storage_only", "assessedTargetShare": 1.0}),
        ),
    )
    level_id = db.insert(
        "INSERT INTO em_event_rule_level (rule_id,level_code,level_rank,combine_logic,explanation_template) "
        "VALUES (%s,'yellow',10,'any','Phase 2A deterministic assessment threshold')",
        (rule_id,),
    )
    db.insert(
        "INSERT INTO em_event_rule_condition (rule_id,level_id,condition_code,metric_code,feature_code,window_type,"
        "window_size,aggregation_method,operator,threshold_value,threshold_unit,reference_value_source,required,"
        "condition_json) VALUES (%s,%s,%s,%s,%s,'forecast','120m','latest','>=',0.5,%s,"
        "'prediction_engineering_value',1,%s)",
        (
            rule_id, level_id, f"PHASE2A_{label}_THRESHOLD", METRIC_CODE,
            f"{label.lower()}_target_00001", UNIT,
            json.dumps({"fixtureScope": "backend_storage_only", "thresholdPurpose": "deterministic assessment"}),
        ),
    )

    batch_id = db.insert(
        "INSERT INTO em_prediction_batch (batch_code,project_id,base_time,time_step_minutes,horizon_minutes,rolling_steps,"
        "model_count,feature_count,pipeline_version,feature_mapping_version,input_hash,output_hash,status,message,"
        "started_at,finished_at) VALUES (%s,%s,%s,3,120,40,1,%s,'phase2a_fixture_v1','phase2a_scalability_v1',"
        "%s,%s,'success','Synthetic persisted workload; not model inference',%s,%s)",
        (
            f"PHASE2A_{label}_20260624100000", project_id, base_time, targets,
            fixture_hash(label, "batch-input"), fixture_hash(label, "batch-output"), base_time, base_time,
        ),
    )
    run_id = db.insert(
        "INSERT INTO em_prediction_run (project_id,batch_id,model_id,model_code,model_version,target_type,artifact_hash,"
        "preprocessor_hash,inference_script_hash,runtime_manifest_hash,environment_digest,artifact_bundle_hash,"
        "input_schema_hash,required_history_rows,station_id,instrument_id,metric_code,input_window_start,input_window_end,"
        "horizon_seconds,horizon_minutes,rolling_steps,input_snapshot_json,status,message,result_hash,runtime_seconds,"
        "started_at,finished_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,16,%s,%s,%s,%s,%s,7200,120,40,"
        "%s,'success','Synthetic persisted workload; no inference claim',%s,0,%s,%s)",
        (
            project_id, batch_id, model_id, model_code, model_version, target_type,
            hashes["artifact"], hashes["preprocessor"], hashes["inference-script"], hashes["runtime-manifest"],
            hashes["environment"], hashes["artifact-bundle"], hashes["input-schema"],
            station_ids[0], instrument_ids[0], METRIC_CODE, base_time - timedelta(minutes=48), base_time,
            json.dumps({"fixtureScope": "backend_storage_only", "targetCount": targets}),
            fixture_hash(label, "logical-result"), base_time, base_time,
        ),
    )
    return {
        "label": label,
        "projectId": project_id,
        "modelId": model_id,
        "modelCode": model_code,
        "modelVersion": model_version,
        "targetType": target_type,
        "targetCount": targets,
        "rowCount": targets * STEPS,
        "stationCount": len(station_ids),
        "instrumentCount": len(instrument_ids),
        "ruleId": rule_id,
        "batchId": batch_id,
        "runId": run_id,
        "baseTime": base_time,
    }


def persist_results(db: Database, fixture: dict[str, Any]) -> dict[str, Any]:
    sql = (
        "INSERT INTO em_prediction_result (run_id,batch_id,model_id,target_type,feature_code,feature_name,project_id,"
        "station_id,instrument_id,metric_code,step,horizon_minutes,base_time,future_time,predicted_at,prediction_time,"
        "raw_predicted_value,raw_predicted_unit,predicted_value,predicted_unit,engineering_metric_code,engineering_value,"
        "engineering_unit,confidence,conversion_operator_code,conversion_version,conversion_status,conversion_remark,"
        "quality_flag,source_record_key) VALUES ("
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'identity','v1','success',"
        "'Synthetic identity engineering mapping','normal',%s)"
    )
    stations = db.all(
        "SELECT s.id AS station_id,i.id AS instrument_id FROM em_station s JOIN em_instrument i ON i.station_id=s.id "
        "WHERE s.project_id=%s ORDER BY s.id",
        (fixture["projectId"],),
    )
    inserted = 0
    started = time.perf_counter_ns()
    pending = []
    for target_index in range(1, fixture["targetCount"] + 1):
        feature = f"{fixture['label'].lower()}_target_{target_index:05d}"
        binding = stations[(target_index - 1) % len(stations)]
        for step in range(1, STEPS + 1):
            future_time = fixture["baseTime"] + timedelta(minutes=step * STEP_MINUTES)
            value = Decimal("1.00000000") + Decimal(target_index % 100) / Decimal("1000") + Decimal(step) / Decimal("10000")
            pending.append(
                (
                    fixture["runId"], fixture["batchId"], fixture["modelId"], fixture["targetType"],
                    feature, feature, fixture["projectId"], binding["station_id"], binding["instrument_id"],
                    METRIC_CODE, step, step * STEP_MINUTES, fixture["baseTime"], future_time,
                    fixture["baseTime"], future_time, value, UNIT, value, UNIT, METRIC_CODE, value, UNIT,
                    Decimal("0.950000"), f"P2A:{fixture['label']}:{target_index:05d}:{step:02d}",
                )
            )
            if len(pending) >= 2_000:
                inserted += db.executemany(sql, pending)
                pending.clear()
    if pending:
        inserted += db.executemany(sql, pending)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    if inserted != fixture["rowCount"]:
        raise RuntimeError(f"{fixture['label']} inserted {inserted}, expected {fixture['rowCount']}")
    return {
        "label": fixture["label"],
        "targetCount": fixture["targetCount"],
        "rowCount": inserted,
        "elapsedMs": round(elapsed_ms, 6),
        "rowsPerSecond": round(inserted / (elapsed_ms / 1000), 3),
        "chunkRows": 2_000,
        "transactionMode": "autocommit per executemany chunk",
    }


def persisted_result_hash_from_database(db: Database, run_id: int) -> tuple[str, int, float]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/pit_pre"))
    from pit_pre.result_writer import PERSISTED_RESULT_HASH_VERSION, _canonical_persisted_value

    fields = ",".join(PERSISTED_FIELDS)
    started = time.perf_counter_ns()
    digest = hashlib.sha256()
    digest.update(PERSISTED_RESULT_HASH_VERSION.encode("utf-8"))
    count = 0
    with db.connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {fields} FROM em_prediction_result WHERE run_id=%s "
            "ORDER BY feature_code ASC, step ASC, source_record_key ASC",
            (run_id,),
        )
        while True:
            rows = cursor.fetchmany(2_000)
            if not rows:
                break
            for row in rows:
                canonical = json.dumps(
                    [_canonical_persisted_value(field, row.get(field)) for field in PERSISTED_FIELDS],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                digest.update(b"\n")
                digest.update(canonical.encode("utf-8"))
                count += 1
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return digest.hexdigest(), count, elapsed_ms


def finalize_integrity(db: Database, fixture: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/pit_pre"))
    from pit_pre.result_writer import persisted_output_hash

    result_hash, count, first_ms = persisted_result_hash_from_database(db, fixture["runId"])
    if count != fixture["rowCount"]:
        raise RuntimeError(f"Persisted hash read {count}, expected {fixture['rowCount']}")
    output_hash = persisted_output_hash({f"{fixture['modelCode']}@{fixture['modelVersion']}": result_hash})
    db.execute(
        "UPDATE em_prediction_run SET persisted_result_hash=%s,persisted_result_hash_version=%s WHERE id=%s",
        (result_hash, RESULT_HASH_VERSION, fixture["runId"]),
    )
    db.execute(
        "UPDATE em_prediction_batch SET persisted_output_hash=%s,persisted_output_hash_version=%s WHERE id=%s",
        (output_hash, OUTPUT_HASH_VERSION, fixture["batchId"]),
    )
    verification_hash, verification_count, verify_ms = persisted_result_hash_from_database(db, fixture["runId"])
    stored = db.one(
        "SELECT r.persisted_result_hash,r.persisted_result_hash_version,b.persisted_output_hash,"
        "b.persisted_output_hash_version FROM em_prediction_run r JOIN em_prediction_batch b ON b.id=r.batch_id "
        "WHERE r.id=%s",
        (fixture["runId"],),
    )
    valid = (
        stored is not None
        and verification_count == fixture["rowCount"]
        and result_hash == verification_hash == stored["persisted_result_hash"]
        and stored["persisted_result_hash_version"] == RESULT_HASH_VERSION
        and stored["persisted_output_hash"] == output_hash
        and stored["persisted_output_hash_version"] == OUTPUT_HASH_VERSION
    )
    if not valid:
        raise RuntimeError(f"Independent persisted-integrity verification failed for {fixture['label']}")
    return {
        "label": fixture["label"],
        "rowCount": count,
        "generationMs": round(first_ms, 6),
        "verificationMs": round(verify_ms, 6),
        "persistedResultHash": result_hash,
        "persistedOutputHash": output_hash,
        "hashVersions": {"result": RESULT_HASH_VERSION, "output": OUTPUT_HASH_VERSION},
        "independentRecomputationMatch": True,
    }


def benchmark_valid_scale(args, backend: Backend, fixture: dict[str, Any], output: Path) -> dict[str, Any]:
    raw: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    feature_code = f"{fixture['label'].lower()}_target_00001"
    operations = [
        (
            "series-single-target", "GET",
            "/api/em/predictions/series?" + urllib.parse.urlencode(
                {
                    "projectId": fixture["projectId"], "batchId": fixture["batchId"],
                    "featureCode": feature_code, "includeObserved": "false",
                    "valueMode": "ENGINEERING", "limit": 100,
                }
            ),
            lambda value: {
                "pass": len(value["data"]) == STEPS,
                "rowCount": len(value["data"]),
                "resultIntegrityValid": "not_applicable",
                "executionEligible": "not_applicable",
            },
        ),
        (
            "series-full-batch", "GET",
            "/api/em/predictions/series?" + urllib.parse.urlencode(
                {
                    "projectId": fixture["projectId"], "batchId": fixture["batchId"],
                    "includeObserved": "false", "valueMode": "ENGINEERING", "limit": 50000,
                }
            ),
            lambda value: {
                "pass": len(value["data"]) == fixture["rowCount"],
                "rowCount": len(value["data"]),
                "resultIntegrityValid": "not_applicable",
                "executionEligible": "not_applicable",
            },
        ),
        (
            "gate-inspect", "GET",
            f"/api/em/predictions/batches/{fixture['batchId']}/execution-gate?mode=REPRODUCTION",
            lambda value: {
                "pass": value["data"]["actualPointCount"] == fixture["rowCount"]
                and value["data"]["resultIntegrityValid"] is True
                and value["data"]["executionEligible"] is True,
                "rowCount": value["data"]["actualPointCount"],
                "resultIntegrityValid": value["data"]["resultIntegrityValid"],
                "executionEligible": value["data"]["executionEligible"],
            },
        ),
        (
            "future-state", "GET",
            f"/api/em/projects/{fixture['projectId']}/future-state?batchId={fixture['batchId']}"
            "&horizonMinutes=120&executionMode=REPRODUCTION",
            lambda value: {
                "pass": value["data"]["executionGate"]["actualPointCount"] == fixture["rowCount"]
                and value["data"]["executionEligible"] is True
                and value["data"]["assessedFeatureCount"] == fixture["targetCount"],
                "rowCount": value["data"]["executionGate"]["actualPointCount"],
                "resultIntegrityValid": value["data"]["executionGate"]["resultIntegrityValid"],
                "executionEligible": value["data"]["executionEligible"],
            },
        ),
    ]
    for operation, method, path, validator in operations:
        rows, operation_summary = run_api_repetitions(
            backend.port, operation, method, path, None, validator,
            args.warmups, args.measured,
            {"scale": fixture["label"], "targetCount": fixture["targetCount"]},
            output / "api-progress.json",
        )
        raw.extend(rows)
        summaries[operation] = operation_summary
    write_csv(
        output / "api-raw.csv", raw,
        ["operation", "phase", "repetition", "elapsedMs", "httpCode", "scale", "targetCount",
         "rowCount", "resultIntegrityValid", "executionEligible", "pass"],
    )
    write_json(output / "api-summary.json", summaries)
    return {"raw": raw, "summaries": summaries, "pass": all(row["pass"] for row in raw)}


def inspect_stop_boundary(backend: Backend, fixture: dict[str, Any], output: Path) -> dict[str, Any]:
    query_path = "/api/em/predictions/series?" + urllib.parse.urlencode(
        {
            "projectId": fixture["projectId"], "batchId": fixture["batchId"],
            "featureCode": f"{fixture['label'].lower()}_target_00001",
            "includeObserved": "false", "valueMode": "ENGINEERING", "limit": 100,
        }
    )
    query_ms, query_response = time_api(backend.port, "GET", query_path)
    gate_ms, gate_response = time_api(
        backend.port, "GET",
        f"/api/em/predictions/batches/{fixture['batchId']}/execution-gate?mode=REPRODUCTION",
    )
    gate = gate_response["data"]
    stop = not (gate.get("resultIntegrityValid") is True and gate.get("executionEligible") is True)
    evidence = {
        "schemaVersion": "shm-em-phase2a-stop-boundary-v1",
        "scale": fixture["label"],
        "databasePersistedRowCount": fixture["rowCount"],
        "databaseTargetCount": fixture["targetCount"],
        "singleTargetQuery": {"elapsedMs": round(query_ms, 6), "rowCount": len(query_response["data"])},
        "gateElapsedMs": round(gate_ms, 6),
        "gate": gate,
        "stopRequired": stop,
        "stopReason": (
            "A valid persisted workload failed frozen Gate validation; no production-core optimization is permitted in Phase 2A"
            if stop else None
        ),
    }
    write_json(output / "stop-boundary.json", evidence)
    return evidence


def run_scale(args, label: str, targets: int, port: int, root: Path) -> dict[str, Any]:
    database = f"shm_em_reproduce_benchmark_scaling_{label.lower()}"
    output = root / label.lower()
    output.mkdir(parents=True, exist_ok=True)
    imports = initialize_database(args, database)
    write_json(output / "sql-imports.json", imports)
    db = Database(args, database)
    backend = Backend(args, database, port, args.runtime_root / f"scaling-{label.lower()}")
    try:
        before = table_storage(db)
        write_json(output / "storage-before.json", before)
        fixture = create_fixture(db, label, targets)
        write_json(
            output / "workload.json",
            {
                **{key: value for key, value in fixture.items() if key != "baseTime"},
                "baseTime": fixture["baseTime"].isoformat(),
                "workloadClass": "synthetic backend/storage scalability fixture",
                "inferenceMeasured": False,
                "predictiveAccuracyClaim": False,
                "topologyScaling": False,
                "scalingAxes": ["prediction target channels", "persisted prediction rows"],
            },
        )
        persistence = persist_results(db, fixture)
        write_json(output / "persistence.json", persistence)
        integrity = finalize_integrity(db, fixture)
        write_json(output / "persisted-integrity.json", integrity)
        actual = {
            "rows": int(db.scalar("SELECT COUNT(*) FROM em_prediction_result WHERE batch_id=%s", (fixture["batchId"],))),
            "features": int(db.scalar("SELECT COUNT(DISTINCT feature_code) FROM em_prediction_result WHERE batch_id=%s", (fixture["batchId"],))),
            "steps": int(db.scalar("SELECT COUNT(DISTINCT step) FROM em_prediction_result WHERE batch_id=%s", (fixture["batchId"],))),
            "duplicateFeatureSteps": int(db.scalar(
                "SELECT COUNT(*) FROM (SELECT feature_code,step,COUNT(*) c FROM em_prediction_result "
                "WHERE batch_id=%s GROUP BY feature_code,step HAVING c<>1) q", (fixture["batchId"],)
            )),
        }
        fixture_valid = (
            actual["rows"] == fixture["rowCount"]
            and actual["features"] == fixture["targetCount"]
            and actual["steps"] == STEPS
            and actual["duplicateFeatureSteps"] == 0
            and integrity["independentRecomputationMatch"] is True
        )
        write_json(output / "database-integrity.json", {**actual, "validBeforeGate": fixture_valid})
        if not fixture_valid:
            raise RuntimeError(f"Scaling fixture {label} is invalid before Gate: {actual}")
        after = table_storage(db)
        write_json(output / "storage-after.json", after)
        backend.start()
        if fixture["rowCount"] <= 50_000:
            try:
                api = benchmark_valid_scale(args, backend, fixture, output)
                stop = False
                boundary = None
            except Exception as exc:
                api = None
                stop = True
                boundary = {
                    "schemaVersion": "shm-em-phase2a-runtime-failure-v1",
                    "scale": label,
                    "databasePersistedRowCount": fixture["rowCount"],
                    "databaseTargetCount": fixture["targetCount"],
                    "fixtureValidBeforeApi": True,
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                    "stopRequired": True,
                    "stopReason": "A valid scaling workload could not complete the frozen backend/API measurement; production-core optimization is forbidden in Phase 2A",
                }
                write_json(output / "runtime-failure.json", boundary)
        else:
            api = None
            boundary = inspect_stop_boundary(backend, fixture, output)
            stop = boundary["stopRequired"]
        result = {
            "schemaVersion": "shm-em-phase2a-scale-result-v1",
            "database": database,
            "scale": label,
            "targetCount": targets,
            "rowCount": targets * STEPS,
            "persistence": persistence,
            "integrity": integrity,
            "databaseIntegrity": actual,
            "storageBefore": before,
            "storageAfter": after,
            "api": None if api is None else api["summaries"],
            "boundary": boundary,
            "pass": api is not None and api["pass"],
            "stopRequired": stop,
        }
        write_json(output / "scale-summary.json", result)
        return result
    finally:
        backend.stop()
        if backend.stdout_path.is_file():
            lines = backend.stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
            write_text(output / "backend-log-tail.txt", "\n".join(lines[-200:]))
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark frozen SHM-EM backend/storage scalability")
    parser.add_argument("--backend-port", type=int, default=5197)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--measured", type=int, default=30)
    parser.add_argument("--through", choices=[item[0] for item in SCALES], default="S5")
    parser.add_argument("--start-at", choices=[item[0] for item in SCALES], default="S1")
    args = resolve_common_args(parser)
    root = args.evidence_root / "scaling"
    if root.exists() and args.start_at == "S1":
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    started = datetime.now().astimezone()
    results: list[dict[str, Any]] = []
    stop_reason = None
    try:
        start_index = next(index for index, item in enumerate(SCALES) if item[0] == args.start_at)
        if start_index > 0:
            for prior_label, _ in SCALES[:start_index]:
                prior_path = root / prior_label.lower() / "scale-summary.json"
                if prior_path.is_file():
                    results.append(json.loads(prior_path.read_text(encoding="utf-8")))
        for label, targets in SCALES[start_index:]:
            result = run_scale(args, label, targets, args.backend_port, root)
            results.append(result)
            if result["stopRequired"]:
                stop_reason = result["boundary"]["stopReason"]
                break
            if label == args.through:
                break
        manifest_rows = [
            {
                "scale": item["scale"], "targets": item["targetCount"], "steps": STEPS,
                "rows": item["rowCount"], "database": item["database"],
                "persistRowsPerSecond": item["persistence"]["rowsPerSecond"],
                "integrityGenerationMs": item["integrity"]["generationMs"],
                "independentIntegrityValid": item["integrity"]["independentRecomputationMatch"],
                "gatePass": item["pass"], "stopRequired": item["stopRequired"],
            }
            for item in results
        ]
        write_csv(
            root / "workload-manifest.csv", manifest_rows,
            ["scale", "targets", "steps", "rows", "database", "persistRowsPerSecond",
             "integrityGenerationMs", "independentIntegrityValid", "gatePass", "stopRequired"],
        )
        aggregate = {
            "schemaVersion": "shm-em-phase2a-scaling-summary-v1",
            "startedAt": started.isoformat(),
            "finishedAt": datetime.now().astimezone().isoformat(),
            "workloadClass": "synthetic backend/storage scalability fixture",
            "inferenceMeasured": False,
            "predictiveAccuracyClaim": False,
            "warmups": args.warmups,
            "measured": args.measured,
            "concurrency": 1,
            "scales": results,
            "maximumAttemptedRows": max(item["rowCount"] for item in results),
            "maximumGateValidRows": max((item["rowCount"] for item in results if item["pass"]), default=0),
            "stopRequired": stop_reason is not None,
            "stopReason": stop_reason,
            "completeThroughRequestedScale": results[-1]["scale"] == args.through and stop_reason is None,
        }
        write_json(root / "scaling-summary.json", aggregate)
        print(json.dumps({"stopRequired": aggregate["stopRequired"], "maximumAttemptedRows": aggregate["maximumAttemptedRows"], "maximumGateValidRows": aggregate["maximumGateValidRows"]}, indent=2))
        return 2 if aggregate["stopRequired"] else 0
    finally:
        cleanup_runtime(args)


if __name__ == "__main__":
    raise SystemExit(main())
