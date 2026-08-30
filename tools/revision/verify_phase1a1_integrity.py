#!/usr/bin/env python3
"""Produce Phase 1A.1 numerical-regression and Gate-overhead evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import tempfile
import time

import pymysql

from run_failure_matrix import Backend, api_call


RESULT_COLUMNS = (
    "p.id", "p.run_id", "p.batch_id", "p.model_id", "p.target_type", "p.feature_code",
    "p.project_id", "p.station_id", "p.instrument_id", "p.metric_code", "p.step",
    "p.horizon_minutes", "p.base_time", "p.future_time", "p.raw_predicted_value",
    "p.raw_predicted_unit", "p.predicted_value", "p.predicted_unit",
    "p.engineering_metric_code", "p.engineering_value", "p.engineering_unit",
    "p.lower_bound", "p.upper_bound", "p.engineering_lower_bound",
    "p.engineering_upper_bound", "p.confidence", "p.conversion_operator_code",
    "p.conversion_version", "p.conversion_status", "p.quality_flag", "p.source_record_key",
)


def connect(args, database: str):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.admin_user, password=args.admin_password,
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def rows(connection, sql: str):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


def canonical_hash(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def regression(args) -> dict:
    old = connect(args, args.original_database)
    new = connect(args, args.phase1a1_database)
    try:
        result_sql = "SELECT " + ",".join(RESULT_COLUMNS) + " FROM em_prediction_result p ORDER BY p.id"
        old_results = rows(old, result_sql)
        new_results = rows(new, result_sql)
        old_batch = rows(old, "SELECT id,batch_code,input_hash,output_hash,status FROM em_prediction_batch ORDER BY id")
        new_batch = rows(new, "SELECT id,batch_code,input_hash,output_hash,status FROM em_prediction_batch ORDER BY id")
        old_runs = rows(old, "SELECT id,model_code,model_version,result_hash,status FROM em_prediction_run ORDER BY id")
        new_runs = rows(new, "SELECT id,model_code,model_version,result_hash,status FROM em_prediction_run ORDER BY id")
        integrity = rows(
            new,
            "SELECT b.id,b.persisted_output_hash,b.persisted_output_hash_version,"
            "SUM(r.persisted_result_hash IS NULL) AS missing_run_hashes,"
            "SUM(r.persisted_result_hash_version<>'prediction-persisted-integrity-v1') AS wrong_versions "
            "FROM em_prediction_batch b JOIN em_prediction_run r ON r.batch_id=b.id "
            "WHERE b.status='success' GROUP BY b.id,b.persisted_output_hash,b.persisted_output_hash_version",
        )
        result = {
            "originalDatabase": args.original_database,
            "phase1a1Database": args.phase1a1_database,
            "predictionRowCountBefore": len(old_results),
            "predictionRowCountAfter": len(new_results),
            "predictionPayloadHashBefore": canonical_hash(old_results),
            "predictionPayloadHashAfter": canonical_hash(new_results),
            "legacyBatchHashStateBefore": old_batch,
            "legacyBatchHashStateAfter": new_batch,
            "legacyRunHashStateBefore": old_runs,
            "legacyRunHashStateAfter": new_runs,
            "persistedIntegrityState": integrity,
        }
        result["predictionValuesUnchanged"] = old_results == new_results
        result["legacyBatchHashesUnchanged"] = old_batch == new_batch
        result["legacyRunHashesUnchanged"] = old_runs == new_runs
        result["passed"] = all((
            result["predictionValuesUnchanged"],
            result["legacyBatchHashesUnchanged"],
            result["legacyRunHashesUnchanged"],
            len(old_results) == 4960,
            bool(integrity),
            all(row["persisted_output_hash"] and row["persisted_output_hash_version"] == "prediction-persisted-output-integrity-v1"
                and int(row["missing_run_hashes"]) == 0 and int(row["wrong_versions"]) == 0 for row in integrity),
        ))
        return result
    finally:
        old.close()
        new.close()


def benchmark(args) -> dict:
    runtime_root = Path(tempfile.mkdtemp(prefix="shm-em-phase1a1-benchmark-"))
    backend = Backend(args, args.benchmark_database, args.backend_port, runtime_root)
    try:
        connection = connect(args, args.benchmark_database)
        try:
            batch_id = int(rows(connection, "SELECT id FROM em_prediction_batch WHERE status='success' ORDER BY id DESC LIMIT 1")[0]["id"])
            result_count = int(rows(connection, f"SELECT COUNT(*) AS count FROM em_prediction_result WHERE batch_id={batch_id}")[0]["count"])
        finally:
            connection.close()
        backend.start()
        url = backend.base_url + f"/api/em/predictions/batches/{batch_id}/execution-gate/evaluate?mode=REPRODUCTION"
        for _ in range(3):
            response = api_call("POST", url)
            if response.get("body", {}).get("data", {}).get("resultIntegrityValid") is not True:
                raise RuntimeError(f"Gate warmup failed: {response}")
        elapsed_ms = []
        for _ in range(args.iterations):
            started = time.perf_counter()
            response = api_call("POST", url)
            elapsed_ms.append((time.perf_counter() - started) * 1000)
            data = response.get("body", {}).get("data", {})
            if data.get("resultIntegrityValid") is not True or data.get("executionEligible") is not True:
                raise RuntimeError(f"Gate benchmark call failed: {response}")

        gate_source = (args.repo_root / "src" / "backend" / "src" / "main" / "java" / "mybatis" / "iem" / "em" /
                       "modules" / "engineering" / "application" / "service" / "impl" /
                       "PredictionExecutionGateServiceImpl.java").read_text(encoding="utf-8")
        select_series_calls = gate_source.count("predictionMapper.selectSeries(")
        ordered = sorted(elapsed_ms)
        p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
        return {
            "database": args.benchmark_database,
            "batchId": batch_id,
            "resultRowsRevalidatedPerCall": result_count,
            "warmupCalls": 3,
            "measuredCalls": len(elapsed_ms),
            "medianMs": round(statistics.median(elapsed_ms), 3),
            "p95Ms": round(ordered[p95_index], 3),
            "maxMs": round(max(elapsed_ms), 3),
            "selectSeriesCallsInInspectSource": select_series_calls,
            "nPlusOneDetected": select_series_calls != 1,
            "passed": result_count == 4960 and select_series_calls == 1,
        }
    finally:
        backend.stop()
        shutil.rmtree(runtime_root, ignore_errors=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--admin-user", default="root")
    parser.add_argument("--admin-password", default=os.environ.get("DB_ADMIN_PASSWORD"))
    parser.add_argument("--app-user", default="shm_em_reproduce")
    parser.add_argument("--app-password", default=os.environ.get("MYSQL_PASSWORD"))
    parser.add_argument("--original-database", default="shm_em_reproduce_phase1a_base")
    parser.add_argument("--phase1a1-database", default="shm_em_reproduce_phase1a1_base")
    parser.add_argument("--benchmark-database", default="shm_em_reproduce_phase1a1_p00")
    parser.add_argument("--backend-port", type=int, default=5193)
    parser.add_argument("--backend-start-timeout", type=int, default=90)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--java", type=Path, default=Path(r"C:\Users\nlfdz\.jdks\temurin-1.8.0_482\bin\java.exe"))
    args = parser.parse_args()
    if not args.admin_password or not args.app_password:
        parser.error("Set DB_ADMIN_PASSWORD and MYSQL_PASSWORD")
    args.repo_root = repo_root
    args.backend_jar = next(
        path for path in sorted((repo_root / "src" / "backend" / "target").glob("*.jar"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not path.name.endswith(".original")
    )
    result = {"numericalRegression": regression(args), "gateBenchmark": benchmark(args)}
    result["passed"] = result["numericalRegression"]["passed"] and result["gateBenchmark"]["passed"]
    output = repo_root / "artifacts" / "revision" / "phase1a_1" / "regression-and-performance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
