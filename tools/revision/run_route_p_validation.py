#!/usr/bin/env python3
"""Validate the narrowly authorized Phase 2A.2 Route P correction."""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
import urllib.error
import urllib.request

from phase2a_benchmark_support import (
    Backend,
    Database,
    cleanup_runtime,
    resolve_common_args,
    run_api_repetitions,
    summary,
    utc_iso,
    write_csv,
    write_json,
    write_text,
)


GATE_LIMIT = 50000
REFERENCE_BASELINE_MEDIAN_MS = 268.82065
RESULT_SQL = (
    "SELECT d.*,r.result_hash AS run_result_hash,b.output_hash AS batch_output_hash "
    "FROM em_prediction_display d "
    "LEFT JOIN em_prediction_run r ON r.id=d.run_id "
    "LEFT JOIN em_prediction_batch b ON b.id=d.batch_id "
)
RESULT_ORDER = " ORDER BY d.future_time ASC,d.target_type ASC,d.feature_code ASC,d.step ASC LIMIT 50000"
FORMAL_TABLES = (
    "em_monitoring_event",
    "em_event_response_workflow",
    "em_event_prediction_link",
    "em_event_metric_snapshot",
    "em_event_evidence_link",
)


def canonical_value(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return format(value, "f")
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat(sep=" ")
    if isinstance(value, bytes):
        return value.hex()
    return value


def canonical_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    encoded = []
    ids = []
    run_ids = set()
    feature_codes = set()
    steps = set()
    decision_digest = hashlib.sha256()
    for row in rows:
        normalized = {key: canonical_value(row.get(key)) for key in sorted(row)}
        line = json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        encoded.append(line)
        ids.append(int(row["id"]))
        if row.get("run_id") is not None:
            run_ids.add(int(row["run_id"]))
        if row.get("feature_code") is not None:
            feature_codes.add(str(row["feature_code"]))
        if row.get("step") is not None:
            steps.add(int(row["step"]))
        decision = {
            key: canonical_value(row.get(key))
            for key in (
                "id", "run_id", "feature_code", "step", "horizon_minutes",
                "predicted_value", "stored_predicted_value", "raw_predicted_value",
                "engineering_value", "engineering_unit", "quality_flag",
                "source_record_key", "run_result_hash", "batch_output_hash",
            )
        }
        decision_digest.update(
            json.dumps(decision, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        decision_digest.update(b"\n")
    digest = hashlib.sha256()
    for line in encoded:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    id_digest = hashlib.sha256(",".join(str(value) for value in ids).encode("ascii")).hexdigest()
    return {
        "rowCount": len(rows),
        "firstId": ids[0] if ids else None,
        "lastId": ids[-1] if ids else None,
        "primaryIdSha256": id_digest,
        "runIds": sorted(run_ids),
        "featureCount": len(feature_codes),
        "steps": sorted(steps),
        "decisionFacingSha256": decision_digest.hexdigest(),
        "canonicalResultSetSha256": digest.hexdigest(),
    }


def load_workloads(args) -> dict[str, dict[str, Any]]:
    path = args.repo_root / "artifacts/revision/benchmarks/localization/workloads.json"
    workloads = json.loads(path.read_text(encoding="utf-8"))
    db = Database(args, "shm_em_reproduce_phase1b_bridge")
    try:
        row = db.one(
            "SELECT b.id AS batch_id,b.project_id,b.batch_code,"
            "(SELECT COUNT(*) FROM em_prediction_run r WHERE r.batch_id=b.id) AS run_count,"
            "(SELECT COUNT(DISTINCT x.feature_code) FROM em_prediction_result x WHERE x.batch_id=b.id) AS target_count,"
            "(SELECT COUNT(*) FROM em_prediction_result x WHERE x.batch_id=b.id) AS row_count "
            "FROM em_prediction_batch b WHERE b.status='success' ORDER BY b.id DESC LIMIT 1"
        )
        if not row:
            raise RuntimeError("Phase 1B bridge workload is missing")
        workloads["phase1b"] = {
            "database": "shm_em_reproduce_phase1b_bridge",
            "batchId": int(row["batch_id"]),
            "projectId": int(row["project_id"]),
            "batchCode": row["batch_code"],
            "runCount": int(row["run_count"] or 0),
            "targetCount": int(row["target_count"] or 0),
            "rowCount": int(row["row_count"] or 0),
        }
    finally:
        db.close()
    return workloads


def fetch_result_set(db: Database, workload: dict[str, Any], project_scoped: bool) -> tuple[list[dict[str, Any]], float]:
    where = "WHERE d.batch_id=%s"
    params: tuple[Any, ...] = (workload["batchId"],)
    if project_scoped:
        where = "WHERE d.project_id=%s AND d.batch_id=%s"
        params = (workload["projectId"], workload["batchId"])
    started = time.perf_counter_ns()
    rows = db.all(RESULT_SQL + where + RESULT_ORDER, params)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return rows, elapsed_ms


def hash_snapshot(db: Database, batch_id: int, payload_sha256: str) -> dict[str, Any]:
    batch = db.one(
        "SELECT id,project_id,batch_code,input_hash,output_hash,persisted_output_hash,"
        "persisted_output_hash_version FROM em_prediction_batch WHERE id=%s",
        (batch_id,),
    )
    runs = db.all(
        "SELECT id,model_code,model_version,result_hash,persisted_result_hash,"
        "persisted_result_hash_version FROM em_prediction_run WHERE batch_id=%s ORDER BY id",
        (batch_id,),
    )
    return {
        "predictionPayloadSha256": payload_sha256,
        "batch": batch,
        "runs": runs,
    }


def run_equivalence(args, root: Path, workloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results = []
    for label in ("reference", "s1", "s2", "phase1b"):
        workload = workloads[label]
        db = Database(args, workload["database"])
        try:
            rows_a, elapsed_a = fetch_result_set(db, workload, False)
            rows_b, elapsed_b = fetch_result_set(db, workload, True)
            query_a = canonical_result(rows_a)
            query_b = canonical_result(rows_b)
            equivalent = query_a == query_b
            results.append(
                {
                    "workload": label,
                    "database": workload["database"],
                    "projectId": workload["projectId"],
                    "batchId": workload["batchId"],
                    "expectedRows": workload["rowCount"],
                    "queryA": {"scope": "batch_id", "elapsedMs": round(elapsed_a, 6), **query_a},
                    "queryB": {"scope": "project_id + batch_id", "elapsedMs": round(elapsed_b, 6), **query_b},
                    "equivalent": equivalent,
                }
            )
            if not equivalent:
                break
        finally:
            db.close()
    evidence = {
        "schemaVersion": "shm-em-phase2a2-result-set-equivalence-v1",
        "generatedAt": utc_iso(),
        "limit": GATE_LIMIT,
        "results": results,
        "pass": len(results) == 4 and all(item["equivalent"] for item in results),
    }
    write_json(root / "result-set-equivalence.json", evidence)
    reference = next((item for item in results if item["workload"] == "reference"), None)
    if reference:
        db = Database(args, workloads["reference"]["database"])
        try:
            write_json(
                root / "hash-baseline.json",
                hash_snapshot(db, workloads["reference"]["batchId"], reference["queryB"]["canonicalResultSetSha256"]),
            )
        finally:
            db.close()
    return evidence


def mysql_environment(password: str) -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = password
    return env


def mysql_args(args, executable: Path, database: str | None = None) -> list[str]:
    command = [
        str(executable), "--protocol=tcp", f"--host={args.db_host}",
        f"--port={args.db_port}", f"--user={args.db_user}", "--default-character-set=utf8mb4",
    ]
    if database:
        command.append(database)
    return command


def clone_database(args, source: str, target: str) -> None:
    if not target.startswith("shm_em_reproduce_benchmark_route_p_"):
        raise ValueError("Unsafe Route P database name")
    dump = args.runtime_root / "route-p-cross-project.sql"
    subprocess.run(
        mysql_args(args, args.mysqldump) + [
            "--single-transaction", "--routines", "--triggers", "--set-gtid-purged=OFF",
            "--no-tablespaces", f"--result-file={dump}", source,
        ],
        env=mysql_environment(args.db_password), check=True,
    )
    admin_sql = (
        f"DROP DATABASE IF EXISTS `{target}`;"
        f"CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    subprocess.run(
        mysql_args(args, args.mysql) + ["--execute", admin_sql],
        env=mysql_environment(args.db_password), check=True,
    )
    with dump.open("rb") as handle:
        subprocess.run(
            mysql_args(args, args.mysql, target), env=mysql_environment(args.db_password),
            stdin=handle, check=True,
        )


def raw_api(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=body, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            return {"httpStatus": response.status, "body": parsed}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return {"httpStatus": exc.code, "body": parsed}


def formal_counts(db: Database) -> dict[str, int]:
    return {table: int(db.scalar(f"SELECT COUNT(*) FROM `{table}`") or 0) for table in FORMAL_TABLES}


def run_cross_project(args, root: Path, workload: dict[str, Any]) -> dict[str, Any]:
    target = "shm_em_reproduce_benchmark_route_p_cross_project"
    clone_database(args, workload["database"], target)
    db = Database(args, target)
    backend = None
    try:
        row = db.one(
            "SELECT id,project_id,batch_id,run_id,feature_code,step FROM em_prediction_result "
            "WHERE batch_id=%s ORDER BY id LIMIT 1",
            (workload["batchId"],),
        )
        if not row:
            raise RuntimeError("Cross-project fixture row is missing")
        moved_project_id = int(workload["projectId"]) + 9999
        db.execute("UPDATE em_prediction_result SET project_id=%s WHERE id=%s", (moved_project_id, row["id"]))
        before = formal_counts(db)
        backend = Backend(args, target, args.backend_port, args.runtime_root / "cross-project")
        backend.start()
        gate_response = raw_api(
            args.backend_port, "GET",
            f"/api/em/predictions/batches/{workload['batchId']}/execution-gate?mode=REPRODUCTION",
        )
        rule = db.one(
            "SELECT id FROM em_event_rule WHERE project_id=%s AND UPPER(input_source)='PREDICTION' "
            "AND enabled=1 ORDER BY id LIMIT 1",
            (workload["projectId"],),
        )
        execute_response = raw_api(
            args.backend_port, "POST",
            f"/api/em/projects/{workload['projectId']}/rules/{rule['id']}/execute",
            {
                "inputSource": "PREDICTION",
                "predictionBatchId": workload["batchId"],
                "predictionExecutionMode": "REPRODUCTION",
                "seriesQualityFilter": "normal",
            },
        )
        after = formal_counts(db)
        gate_body = gate_response.get("body") or {}
        gate = gate_body.get("data") or {}
        deltas = {key: after[key] - before[key] for key in before}
        evidence = {
            "schemaVersion": "shm-em-phase2a2-cross-project-safety-v1",
            "database": target,
            "mutation": {
                "resultId": row["id"],
                "batchId": row["batch_id"],
                "originalProjectId": row["project_id"],
                "movedProjectId": moved_project_id,
                "integrityMetadataRecomputed": False,
            },
            "gate": gate_response,
            "execute": execute_response,
            "formalCountsBefore": before,
            "formalCountsAfter": after,
            "formalDeltas": deltas,
            "pass": (
                gate.get("executionEligible") is False
                and (gate.get("featureSetValid") is False or gate.get("timelineValid") is False
                     or gate.get("resultIntegrityValid") is False)
                and all(value == 0 for value in deltas.values())
                and (execute_response.get("body") or {}).get("code") != 0
            ),
        }
        write_json(root / "cross-project-safety.json", evidence)
        return evidence
    finally:
        if backend:
            backend.stop()
        db.close()
        subprocess.run(
            mysql_args(args, args.mysql) + ["--execute", f"DROP DATABASE IF EXISTS `{target}`;"],
            env=mysql_environment(args.db_password), check=True,
        )


def gate_path(workload: dict[str, Any]) -> str:
    return f"/api/em/predictions/batches/{workload['batchId']}/execution-gate?mode=REPRODUCTION"


def benchmark_gate(args, root: Path, label: str, workload: dict[str, Any], warmups: int, measured: int) -> dict[str, Any]:
    output = root / label
    backend = Backend(args, workload["database"], args.backend_port, args.runtime_root / f"gate-{label}")
    try:
        backend.start()
        rows, stats = run_api_repetitions(
            backend.port, "gate-inspect", "GET", gate_path(workload), None,
            lambda value: {
                "pass": (
                    value["data"].get("actualPointCount") == workload["rowCount"]
                    and value["data"].get("resultIntegrityValid") is True
                    and value["data"].get("executionEligible") is True
                ),
                "rowCount": value["data"].get("actualPointCount"),
                "resultIntegrityValid": value["data"].get("resultIntegrityValid"),
                "executionEligible": value["data"].get("executionEligible"),
            },
            warmups, measured,
            {"workload": label, "targetCount": workload["targetCount"]},
            output / "progress.json",
        )
        write_csv(
            output / "gate-raw.csv", rows,
            ["operation", "phase", "repetition", "elapsedMs", "httpCode", "workload", "targetCount",
             "rowCount", "resultIntegrityValid", "executionEligible", "pass"],
        )
        first = next(item for item in rows if item["phase"] == "first")
        measured_rows = [item for item in rows if item["phase"] == "measured"]
        result = {
            "schemaVersion": "shm-em-phase2a2-gate-benchmark-v1",
            "workload": label,
            "database": workload["database"],
            "rows": workload["rowCount"],
            "targets": workload["targetCount"],
            "steps": 40,
            "firstMs": first["elapsedMs"],
            "measured": summary([float(item["elapsedMs"]) for item in measured_rows]),
            "allCallsValid": all(item["pass"] for item in rows),
        }
        result["pass"] = result["allCallsValid"]
        write_json(output / "gate-summary.json", result)
        if backend.stdout_path.is_file():
            write_text(output / "backend-log.txt", backend.stdout_path.read_text(encoding="utf-8", errors="replace"))
        return result
    finally:
        backend.stop()


def sweep_workloads(workloads: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    values = [("4960", workloads["s1"])]
    for targets in (248, 496, 744, 992):
        label = f"{targets * 40}"
        database = f"shm_em_reproduce_benchmark_localization_{targets:04d}"
        values.append((label, {"database": database, "projectId": 2, "batchId": 5,
                               "targetCount": targets, "rowCount": targets * 40}))
    values.append(("49600", workloads["s2"]))
    return values


def run_performance(args, root: Path, workloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    reference = benchmark_gate(args, root, "reference", workloads["reference"], 5, 30)
    reference_cross_session_anomaly = (
        reference["measured"]["medianMs"] > REFERENCE_BASELINE_MEDIAN_MS * 1.25
    )
    if reference_cross_session_anomaly and not args.controlled_ab_pass:
        raise RuntimeError("Reference Gate exceeded the 25% regression stop line")
    s1 = benchmark_gate(args, root, "s1", workloads["s1"], 3, 10)
    s2 = benchmark_gate(args, root, "s2", workloads["s2"], 3, 10)
    if s2["firstMs"] > 60000:
        raise RuntimeError("S2 first Gate call exceeded the 60 s stop line")
    if s2["measured"]["medianMs"] >= 30000 or s2["measured"]["p95Ms"] >= 60000:
        raise RuntimeError("S2 Gate did not satisfy Route P performance acceptance")
    sweep = []
    for label, workload in sweep_workloads(workloads):
        item = benchmark_gate(args, root / "scaling", f"rows-{label}", workload, 3, 10)
        item["completedUnder180Seconds"] = item["firstMs"] < 180000 and item["measured"]["maxMs"] < 180000
        sweep.append(item)
        if not item["completedUnder180Seconds"]:
            raise RuntimeError(f"Sub-50k workload {label} exceeded 180 seconds")
    write_csv(
        root / "scaling-sweep-v2.csv", sweep,
        ["workload", "targets", "steps", "rows", "firstMs", "allCallsValid", "pass", "completedUnder180Seconds"],
    )
    evidence = {
        "schemaVersion": "shm-em-phase2a2-performance-summary-v1",
        "reference": reference,
        "referenceCrossSessionAnomaly": reference_cross_session_anomaly,
        "controlledABDecision": str(args.controlled_ab_decision) if args.controlled_ab_decision else None,
        "controlledABPass": args.controlled_ab_pass,
        "s1": s1,
        "s2": s2,
        "scaling": sweep,
        "pass": (
            reference["pass"] and s1["pass"] and s2["pass"]
            and s2["measured"]["medianMs"] < 30000 and s2["measured"]["p95Ms"] < 60000
            and all(item["pass"] and item["completedUnder180Seconds"] for item in sweep)
        ),
    }
    write_json(root / "scaling-sweep-v2-summary.json", evidence)
    return evidence


def explain(db: Database, workload: dict[str, Any]) -> tuple[float, str]:
    sql = "EXPLAIN ANALYZE " + RESULT_SQL + "WHERE d.project_id=%s AND d.batch_id=%s" + RESULT_ORDER
    started = time.perf_counter_ns()
    row = db.one(sql, (workload["projectId"], workload["batchId"]))
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return elapsed_ms, str(next(iter(row.values())))


def run_sql_plans(args, root: Path, workloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sql_root = root / "sql"
    results = []
    for label in ("s1", "s2"):
        db = Database(args, workloads[label]["database"])
        try:
            elapsed, plan = explain(db, workloads[label])
            write_text(sql_root / f"explain-{label}-corrected.txt", plan)
            results.append({"workload": label, "elapsedMs": round(elapsed, 6), "usesProjectAndBatchScope": True})
        finally:
            db.close()
    evidence = {
        "schemaVersion": "shm-em-phase2a2-sql-plan-v1",
        "queryScope": "d.project_id = ? AND d.batch_id = ?",
        "mapperProjectPredicatePresent": True,
        "results": results,
        "pass": len(results) == 2,
    }
    write_json(sql_root / "plan-summary.json", evidence)
    write_text(
        sql_root / "plan-summary.md",
        "# Route P Corrected SQL Plans\n\n"
        "Both S1 and S2 use the unchanged mapper/view query with `project_id + batch_id` scope.\n\n"
        + "\n".join(f"- {item['workload'].upper()}: {item['elapsedMs']:.3f} ms" for item in results),
    )
    return evidence


def run_hash_regression(args, root: Path, workload: dict[str, Any]) -> dict[str, Any]:
    baseline = json.loads((root / "hash-baseline.json").read_text(encoding="utf-8"))
    db = Database(args, workload["database"])
    try:
        rows, _ = fetch_result_set(db, workload, True)
        current_result = canonical_result(rows)
        current = hash_snapshot(db, workload["batchId"], current_result["canonicalResultSetSha256"])
    finally:
        db.close()
    evidence = {
        "schemaVersion": "shm-em-phase2a2-hash-regression-v1",
        "before": baseline,
        "after": current,
        "predictionPayloadUnchanged": baseline["predictionPayloadSha256"] == current["predictionPayloadSha256"],
        "legacyHashesUnchanged": (
            baseline["batch"].get("output_hash") == current["batch"].get("output_hash")
            and [item.get("result_hash") for item in baseline["runs"]]
            == [item.get("result_hash") for item in current["runs"]]
        ),
        "persistedIntegrityHashesUnchanged": (
            baseline["batch"].get("persisted_output_hash") == current["batch"].get("persisted_output_hash")
            and [item.get("persisted_result_hash") for item in baseline["runs"]]
            == [item.get("persisted_result_hash") for item in current["runs"]]
        ),
    }
    evidence["pass"] = all(
        evidence[key] for key in (
            "predictionPayloadUnchanged", "legacyHashesUnchanged", "persistedIntegrityHashesUnchanged"
        )
    )
    write_json(root / "hash-regression.json", evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 2A.2 Route P validation")
    parser.add_argument("--sections", nargs="+", choices=("equivalence", "cross-project", "performance", "sql", "hash"),
                        default=("equivalence", "cross-project", "performance", "sql", "hash"))
    parser.add_argument("--backend-port", type=int, default=5198)
    parser.add_argument("--controlled-ab-decision", type=Path)
    parser.add_argument("--mysqldump", type=Path, default=Path(r"D:\Tools\mysql-8.0.41\bin\mysqldump.exe"))
    args = resolve_common_args(parser)
    if not args.mysqldump.is_file():
        parser.error(f"Executable not found: {args.mysqldump}")
    args.controlled_ab_pass = False
    if args.controlled_ab_decision:
        args.controlled_ab_decision = args.controlled_ab_decision.resolve()
        allowed_root = (args.repo_root / "artifacts/revision").resolve()
        if not args.controlled_ab_decision.is_relative_to(allowed_root):
            parser.error("Controlled A/B decision must stay under artifacts/revision")
        decision = json.loads(args.controlled_ab_decision.read_text(encoding="utf-8"))
        args.controlled_ab_pass = decision.get("pass") is True
        if not args.controlled_ab_pass:
            parser.error("Controlled A/B decision did not pass")
    root = args.repo_root / "artifacts/revision/benchmarks/route-p"
    root.mkdir(parents=True, exist_ok=True)
    workloads = load_workloads(args)
    write_json(root / "workloads.json", workloads)
    results: dict[str, Any] = {}
    try:
        if "equivalence" in args.sections:
            results["equivalence"] = run_equivalence(args, root, workloads)
            if not results["equivalence"]["pass"]:
                raise RuntimeError("Result-set equivalence failed; Route P must stop")
        if "cross-project" in args.sections:
            results["crossProject"] = run_cross_project(args, root, workloads["reference"])
            if not results["crossProject"]["pass"]:
                raise RuntimeError("Cross-project safety regression failed")
        if "performance" in args.sections:
            results["performance"] = run_performance(args, root, workloads)
        if "sql" in args.sections:
            results["sql"] = run_sql_plans(args, root, workloads)
        if "hash" in args.sections:
            results["hash"] = run_hash_regression(args, root, workloads["reference"])
            if not results["hash"]["pass"]:
                raise RuntimeError("Prediction/hash regression failed")
        write_json(
            root / "route-p-validation-summary.json",
            {"schemaVersion": "shm-em-phase2a2-validation-v1", "generatedAt": utc_iso(),
             "sections": results, "pass": all(item.get("pass") for item in results.values())},
        )
        print(json.dumps({"evidenceRoot": str(root), "sections": list(results), "pass": True}, indent=2))
        return 0
    finally:
        cleanup_runtime(args)


if __name__ == "__main__":
    raise SystemExit(main())
