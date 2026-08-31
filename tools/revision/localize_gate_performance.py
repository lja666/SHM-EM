#!/usr/bin/env python3
"""Localize frozen SHM-EM Gate latency without changing production code.

The harness deliberately treats the packaged backend JAR as a black box. It
creates or reuses benchmark-only databases, starts a fresh JVM per diagnostic
case, and records API, JVM, OS-process, and MySQL evidence.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request

import psutil

from benchmark_scalability import (
    PERSISTED_FIELDS,
    STEPS,
    create_fixture,
    finalize_integrity,
    persist_results,
    persisted_result_hash_from_database,
)
from phase2a_benchmark_support import (
    Backend,
    Database,
    cleanup_runtime,
    core_diff,
    initialize_database,
    resolve_common_args,
    summary,
    utc_iso,
    write_csv,
    write_json,
    write_text,
)


REFERENCE_DB = "shm_em_reproduce_benchmark_reference"
S1_DB = "shm_em_reproduce_benchmark_scaling_s1"
S2_DB = "shm_em_reproduce_benchmark_scaling_s2"
GATE_LIMIT = 50_000
DIAGNOSTIC_SECONDS = (5, 15, 30, 60, 120)
SWEEP_TARGETS = (124, 248, 496, 744, 992, 1_240)


def raw_api(port: int, path: str, timeout_seconds: int = 180) -> dict[str, Any]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc
    if value.get("code") != 0:
        raise RuntimeError(f"API failure GET {path}: {value}")
    return value


def time_call(call: Callable[[], dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    started = time.perf_counter_ns()
    value = call()
    return (time.perf_counter_ns() - started) / 1_000_000, value


def discover_workload(args, database: str) -> dict[str, Any]:
    db = Database(args, database)
    try:
        row = db.one(
            "SELECT b.id AS batch_id,b.project_id,b.batch_code,"
            "(SELECT COUNT(*) FROM em_prediction_run r WHERE r.batch_id=b.id) AS run_count,"
            "(SELECT COUNT(DISTINCT x.feature_code) FROM em_prediction_result x WHERE x.batch_id=b.id) AS target_count,"
            "(SELECT COUNT(*) FROM em_prediction_result x WHERE x.batch_id=b.id) AS row_count "
            "FROM em_prediction_batch b WHERE b.status='success' "
            "ORDER BY row_count DESC,b.id DESC LIMIT 1"
        )
        if row is None or int(row["row_count"] or 0) == 0:
            raise RuntimeError(f"No persisted prediction workload found in {database}")
        feature = db.scalar(
            "SELECT feature_code FROM em_prediction_result WHERE batch_id=%s "
            "ORDER BY feature_code,step LIMIT 1",
            (row["batch_id"],),
        )
        return {
            "database": database,
            "batchId": int(row["batch_id"]),
            "projectId": int(row["project_id"]),
            "batchCode": row["batch_code"],
            "runCount": int(row["run_count"] or 0),
            "targetCount": int(row["target_count"] or 0),
            "rowCount": int(row["row_count"] or 0),
            "featureCode": feature,
        }
    finally:
        db.close()


def gate_path(workload: dict[str, Any]) -> str:
    return f"/api/em/predictions/batches/{workload['batchId']}/execution-gate?mode=REPRODUCTION"


def series_path(workload: dict[str, Any], full: bool) -> str:
    values: dict[str, Any] = {
        "projectId": workload["projectId"],
        "batchId": workload["batchId"],
        "includeObserved": "false",
        "valueMode": "ENGINEERING",
        "limit": GATE_LIMIT if full else 100,
    }
    if not full:
        values["featureCode"] = workload["featureCode"]
    return "/api/em/predictions/series?" + urllib.parse.urlencode(values)


def capture_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "available": completed.returncode == 0,
            "exitCode": completed.returncode,
            "elapsedMs": round((time.perf_counter() - started) * 1000, 3),
            "output": completed.stdout or "",
        }
    except Exception as exc:
        return {
            "available": False,
            "exitCode": None,
            "elapsedMs": round((time.perf_counter() - started) * 1000, 3),
            "output": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def classify_stack(block: str) -> tuple[str, str | None]:
    frames = [line.strip() for line in block.splitlines() if line.lstrip().startswith("at ")]
    joined = "\n".join(frames)
    categories = (
        ("integrity-hash", "PersistedPredictionIntegrityHashService"),
        ("feature-timeline-validation", "PredictionExecutionGateServiceImpl.validateFeaturesAndTimeline"),
        ("contract-canonical-hash", "CanonicalHashService"),
        ("mapper-select-series", "PredictionMapper.selectSeries"),
        ("jdbc-mysql-read", "com.mysql"),
        ("response-serialization", "MappingJackson2HttpMessageConverter"),
        ("gate-service-other", "PredictionExecutionGateServiceImpl"),
    )
    category = "other-request-thread"
    for candidate, token in categories:
        if token in joined:
            category = candidate
            break
    relevant = next(
        (
            frame
            for frame in frames
            if "mybatis.iem.em" in frame
            or "org.apache.ibatis" in frame
            or "com.mysql" in frame
            or "com.fasterxml.jackson" in frame
        ),
        frames[0] if frames else None,
    )
    return category, relevant


def summarize_thread_dump(text: str, elapsed_seconds: float) -> list[dict[str, Any]]:
    result = []
    for block in re.split(r"\r?\n\r?\n", text):
        first = block.splitlines()[0] if block.splitlines() else ""
        match = re.match(r'^"([^"]+)"', first)
        if not match or "http-nio" not in match.group(1):
            continue
        state_match = re.search(r"java\.lang\.Thread\.State:\s+([^\r\n]+)", block)
        category, frame = classify_stack(block)
        if "PredictionExecutionGateServiceImpl" not in block and category == "other-request-thread":
            continue
        result.append(
            {
                "elapsedSeconds": round(elapsed_seconds, 3),
                "thread": match.group(1),
                "state": state_match.group(1).strip() if state_match else "unknown",
                "category": category,
                "representativeFrame": frame,
            }
        )
    return result


def parse_jstat(output: str, elapsed_seconds: float) -> dict[str, Any]:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    row: dict[str, Any] = {"elapsedSeconds": round(elapsed_seconds, 3)}
    if len(lines) >= 2 and len(lines[0]) == len(lines[1]):
        row.update(dict(zip(lines[0], lines[1])))
    else:
        row["raw"] = output.strip()
    return row


def save_backend_log(backend: Backend, output: Path) -> None:
    if backend.stdout_path.is_file():
        content = backend.stdout_path.read_text(encoding="utf-8", errors="replace")
        write_text(output / "backend.log", content)


def cleanup_benchmark_connections(args, database: str, output: Path) -> None:
    """Remove only residual connections to one disposable benchmark database."""
    db = Database(args, database)
    cleanup_rows = []
    try:
        own_id = int(db.scalar("SELECT CONNECTION_ID()"))
        active = [
            row
            for row in db.all("SHOW FULL PROCESSLIST")
            if int(row.get("Id") or -1) != own_id and row.get("db") == database
        ]
        for row in active:
            connection_id = int(row["Id"])
            status = "killed"
            error = None
            try:
                db.execute(f"KILL CONNECTION {connection_id}")
            except Exception as exc:
                status = "already-closed" if "unknown thread" in str(exc).lower() else "failed"
                error = f"{type(exc).__name__}: {exc}"
            cleanup_rows.append(
                {
                    "connectionId": connection_id,
                    "command": row.get("Command"),
                    "timeSeconds": row.get("Time"),
                    "state": row.get("State"),
                    "info": str(row.get("Info") or "")[:500],
                    "status": status,
                    "error": error,
                }
            )
    finally:
        db.close()
    write_json(
        output / "residual-connection-cleanup.json",
        {
            "database": database,
            "capturedAt": utc_iso(),
            "scope": "disposable benchmark database only",
            "connections": cleanup_rows,
        },
    )


def diagnostic_gate(
    args,
    backend: Backend,
    workload: dict[str, Any],
    output: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    jvm_root = output / "jvm"
    dump_root = jvm_root / "thread-dumps"
    mysql_root = output / "mysql" / "processlist"
    dump_root.mkdir(parents=True, exist_ok=True)
    mysql_root.mkdir(parents=True, exist_ok=True)
    if backend.process is None:
        raise RuntimeError("Backend process is not running")
    pid = backend.process.pid
    process = psutil.Process(pid)
    jstack = args.java.parent / ("jstack.exe" if args.java.suffix.lower() == ".exe" else "jstack")
    jstat = args.java.parent / ("jstat.exe" if args.java.suffix.lower() == ".exe" else "jstat")
    db = Database(args, workload["database"])
    diagnostic_connection_id = int(db.scalar("SELECT CONNECTION_ID()"))
    memory_rows: list[dict[str, Any]] = []
    gc_rows: list[dict[str, Any]] = []
    processlist_rows: list[dict[str, Any]] = []
    thread_rows: list[dict[str, Any]] = []
    captured_thresholds: set[int] = set()

    def request_gate() -> dict[str, Any]:
        try:
            elapsed_ms, response = time_call(
                lambda: raw_api(backend.port, gate_path(workload), timeout_seconds)
            )
            gate = response.get("data") or {}
            return {
                "status": "completed",
                "elapsedMs": round(elapsed_ms, 6),
                "actualPointCount": gate.get("actualPointCount"),
                "resultIntegrityValid": gate.get("resultIntegrityValid"),
                "executionEligible": gate.get("executionEligible"),
                "issues": gate.get("issues"),
            }
        except Exception as exc:
            return {
                "status": "timeout" if isinstance(exc, TimeoutError) else "failed",
                "elapsedMs": round((time.perf_counter() - started) * 1000, 6),
                "errorType": type(exc).__name__,
                "error": str(exc),
            }

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(request_gate)
        while not future.done():
            elapsed = time.perf_counter() - started
            try:
                with process.oneshot():
                    memory = process.memory_info()
                    cpu = process.cpu_times()
                    memory_rows.append(
                        {
                            "elapsedSeconds": round(elapsed, 3),
                            "rssBytes": memory.rss,
                            "vmsBytes": memory.vms,
                            "cpuUserSeconds": round(cpu.user, 6),
                            "cpuSystemSeconds": round(cpu.system, 6),
                            "threadCount": process.num_threads(),
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                memory_rows.append({"elapsedSeconds": round(elapsed, 3), "error": str(exc)})

            try:
                rows = db.all("SHOW FULL PROCESSLIST")
                active = [
                    row
                    for row in rows
                    if int(row.get("Id") or -1) != diagnostic_connection_id
                    and row.get("db") == workload["database"]
                ]
                processlist_rows.append(
                    {
                        "elapsedSeconds": round(elapsed, 3),
                        "activeConnections": len(active),
                        "queryConnections": sum(1 for row in active if row.get("Command") == "Query"),
                        "states": " | ".join(
                            sorted(
                                {
                                    f"{row.get('Command')}:{row.get('State') or ''}:"
                                    f"{str(row.get('Info') or '')[:160]}"
                                    for row in active
                                }
                            )
                        ),
                    }
                )
            except Exception as exc:
                processlist_rows.append(
                    {"elapsedSeconds": round(elapsed, 3), "error": f"{type(exc).__name__}: {exc}"}
                )

            for threshold in DIAGNOSTIC_SECONDS:
                if elapsed < threshold or threshold in captured_thresholds:
                    continue
                captured_thresholds.add(threshold)
                current_processlist = db.all("SHOW FULL PROCESSLIST")
                write_json(mysql_root / f"processlist-{threshold:03d}s.json", current_processlist)
                if jstat.is_file():
                    sample = capture_command([str(jstat), "-gcutil", str(pid)], timeout=20)
                    write_text(jvm_root / f"jstat-{threshold:03d}s.txt", sample.get("output") or sample.get("error", ""))
                    gc_rows.append(parse_jstat(sample.get("output", ""), elapsed))
                if jstack.is_file():
                    sample = capture_command([str(jstack), "-l", str(pid)], timeout=30)
                    write_text(dump_root / f"thread-dump-{threshold:03d}s.txt", sample.get("output") or sample.get("error", ""))
                    thread_rows.extend(summarize_thread_dump(sample.get("output", ""), elapsed))
            if elapsed > timeout_seconds + 5:
                break
            time.sleep(1)
        request_result = future.result(timeout=10)

    elapsed_total = time.perf_counter() - started
    try:
        final_processlist = db.all("SHOW FULL PROCESSLIST")
        write_json(mysql_root / "processlist-final.json", final_processlist)
    finally:
        db.close()

    write_csv(
        jvm_root / "memory-samples.csv",
        memory_rows,
        ["elapsedSeconds", "rssBytes", "vmsBytes", "cpuUserSeconds", "cpuSystemSeconds", "threadCount", "error"],
    )
    gc_fields = ["elapsedSeconds", "S0", "S1", "E", "O", "M", "CCS", "YGC", "YGCT", "FGC", "FGCT", "GCT", "raw"]
    write_csv(jvm_root / "gc-samples.csv", gc_rows, gc_fields)
    write_csv(
        jvm_root / "thread-sample-summary.csv",
        thread_rows,
        ["elapsedSeconds", "thread", "state", "category", "representativeFrame"],
    )
    write_csv(
        output / "mysql" / "processlist-samples.csv",
        processlist_rows,
        ["elapsedSeconds", "activeConnections", "queryConnections", "states", "error"],
    )
    category_counts: dict[str, int] = {}
    for row in thread_rows:
        category = str(row["category"])
        category_counts[category] = category_counts.get(category, 0) + 1
    result = {
        "schemaVersion": "shm-em-phase2a1-gate-diagnostic-v1",
        "capturedAt": utc_iso(),
        "workload": workload,
        "timeoutSeconds": timeout_seconds,
        "jvmPid": pid,
        "request": request_result,
        "wallElapsedSeconds": round(elapsed_total, 6),
        "diagnosticThresholdsCaptured": sorted(captured_thresholds),
        "threadCategoryCounts": category_counts,
        "memorySampleCount": len(memory_rows),
        "mysqlProcesslistSampleCount": len(processlist_rows),
    }
    write_json(output / "gate-diagnostic.json", result)
    return result


def run_preparation_call(port: int, workload: dict[str, Any], full: bool) -> dict[str, Any]:
    elapsed_ms, response = time_call(lambda: raw_api(port, series_path(workload, full), 180))
    return {
        "operation": "series-full-batch" if full else "series-single-target",
        "elapsedMs": round(elapsed_ms, 6),
        "rowCount": len(response.get("data") or []),
    }


def run_operation_order(args, root: Path, workload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = [
        ("D01-gate-first", 0, 0),
        ("D02-one-full-series-then-gate", 0, 1),
        ("D03-36-full-series-then-gate", 0, 36),
        ("D04-36-single-and-36-full-then-gate", 36, 36),
    ]
    requested = {item.strip().upper() for item in args.operation_cases.split(",") if item.strip()}
    cases = [item for item in cases if item[0].split("-", 1)[0].upper() in requested]
    summary_path = root / "operation-order-summary.json"
    previous_rows = []
    if summary_path.is_file():
        previous_rows = json.loads(summary_path.read_text(encoding="utf-8")).get("cases") or []
    rows = []
    for index, (name, single_count, full_count) in enumerate(cases):
        output = root / "fresh-s2" / name
        backend = Backend(args, workload["database"], args.backend_port + index, args.runtime_root / name)
        preparations = []
        preparation_error = None
        try:
            backend.start()
            try:
                for _ in range(single_count):
                    preparations.append(run_preparation_call(backend.port, workload, False))
                for _ in range(full_count):
                    preparations.append(run_preparation_call(backend.port, workload, True))
            except Exception as exc:
                preparation_error = f"{type(exc).__name__}: {exc}"
            diagnostic = None if preparation_error else diagnostic_gate(
                args, backend, workload, output, args.gate_timeout
            )
            row = {
                "case": name,
                "freshProcess": True,
                "singleTargetCallsBeforeGate": single_count,
                "fullSeriesCallsBeforeGate": full_count,
                "preparationElapsedMs": round(sum(item["elapsedMs"] for item in preparations), 6),
                "preparationCompletedCalls": len(preparations),
                "preparationError": preparation_error,
                "gateStatus": "not-run-preparation-failed" if diagnostic is None else diagnostic["request"]["status"],
                "gateElapsedMs": None if diagnostic is None else diagnostic["request"]["elapsedMs"],
                "maximumRssBytes": None,
                "threadDominantCategory": max(
                    diagnostic["threadCategoryCounts"],
                    key=diagnostic["threadCategoryCounts"].get,
                ) if diagnostic is not None and diagnostic["threadCategoryCounts"] else None,
            }
            memory_path = output / "jvm" / "memory-samples.csv"
            if memory_path.is_file():
                import csv

                with memory_path.open(encoding="utf-8", newline="") as handle:
                    rss = [int(item["rssBytes"]) for item in csv.DictReader(handle) if item.get("rssBytes")]
                row["maximumRssBytes"] = max(rss) if rss else None
            preparations_path = output / "preparation-calls.json"
            write_json(preparations_path, preparations)
            rows.append(row)
        finally:
            backend.stop()
            save_backend_log(backend, output)
            cleanup_benchmark_connections(args, workload["database"], output)
    combined = {str(row["case"]): row for row in previous_rows}
    combined.update({str(row["case"]): row for row in rows})
    rows = [combined[key] for key in sorted(combined)]
    write_csv(
        root / "operation-order-matrix.csv",
        rows,
        [
            "case", "freshProcess", "singleTargetCallsBeforeGate", "fullSeriesCallsBeforeGate",
            "preparationCompletedCalls", "preparationElapsedMs", "preparationError", "gateStatus", "gateElapsedMs", "maximumRssBytes",
            "threadDominantCategory",
        ],
    )
    write_json(
        summary_path,
        {"schemaVersion": "shm-em-phase2a1-operation-order-v1", "workload": workload, "cases": rows},
    )
    return rows


def timed_query(
    db: Database,
    sql: str,
    params: tuple[Any, ...],
    repetitions: int = 4,
    timeout_ms: int = 180_000,
) -> dict[str, Any]:
    values = []
    row_counts = []
    for repetition in range(repetitions):
        started = time.perf_counter_ns()
        try:
            with db.connection.cursor() as cursor:
                cursor.execute(f"SET SESSION MAX_EXECUTION_TIME={timeout_ms}")
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        except Exception as exc:
            return {
                "status": "timeout" if "maximum statement execution time" in str(exc).lower() else "failed",
                "errorType": type(exc).__name__,
                "error": str(exc),
                "elapsedMs": round((time.perf_counter_ns() - started) / 1_000_000, 6),
                "firstMs": round(values[0], 6) if values else None,
                **summary(values[1:]),
                "rowCounts": row_counts,
                "completedRepetitions": len(values),
            }
        values.append((time.perf_counter_ns() - started) / 1_000_000)
        row_counts.append(len(rows))
        if repetition == 0 and values[0] > 60_000:
            break
    return {
        "status": "completed",
        "firstMs": round(values[0], 6),
        **summary(values[1:]),
        "rowCounts": row_counts,
        "completedRepetitions": len(values),
    }


def explain_analyze(db: Database, sql: str, params: tuple[Any, ...]) -> tuple[float, str]:
    started = time.perf_counter_ns()
    try:
        db.execute("SET SESSION MAX_EXECUTION_TIME=300000")
        rows = db.all("EXPLAIN ANALYZE " + sql, params)
    except Exception as exc:
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return elapsed_ms, f"status=failed\nerror_type={type(exc).__name__}\nerror={exc}"
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return elapsed_ms, "\n".join(str(next(iter(row.values()))) for row in rows)


def query_components(args, root: Path, workloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sql_root = root / "sql"
    sql_root.mkdir(parents=True, exist_ok=True)
    view_sql = (
        "SELECT d.*,r.result_hash AS run_result_hash,b.output_hash AS batch_output_hash "
        "FROM em_prediction_display d "
        "LEFT JOIN em_prediction_run r ON r.id=d.run_id "
        "LEFT JOIN em_prediction_batch b ON b.id=d.batch_id "
        "WHERE d.batch_id=%s "
        "ORDER BY d.future_time ASC,d.target_type ASC,d.feature_code ASC,d.step ASC LIMIT 50000"
    )
    base_sql = (
        "SELECT run_id," + ",".join(PERSISTED_FIELDS) + " FROM em_prediction_result "
        "WHERE batch_id=%s ORDER BY future_time ASC,target_type ASC,feature_code ASC,step ASC LIMIT 50000"
    )
    feature_sql = (
        "SELECT * FROM em_prediction_feature_mapping WHERE project_id=%s AND enabled=1 "
        "ORDER BY target_type,feature_order,id LIMIT 50000"
    )
    rows = []
    raw_rows = []
    for workload in workloads:
        db = Database(args, workload["database"])
        label = (
            "reference" if workload["database"] == REFERENCE_DB
            else "s1" if workload["database"] == S1_DB
            else "s2" if workload["database"] == S2_DB
            else f"n{workload['targetCount']}"
        )
        try:
            view = timed_query(db, view_sql, (workload["batchId"],))
            base = timed_query(db, base_sql, (workload["batchId"],))
            feature = timed_query(db, feature_sql, (workload["projectId"],))
            hash_ms = 0.0
            hash_rows = 0
            run_hashes = []
            for run in db.all("SELECT id FROM em_prediction_run WHERE batch_id=%s ORDER BY id", (workload["batchId"],)):
                digest, count, elapsed = persisted_result_hash_from_database(db, int(run["id"]))
                hash_ms += elapsed
                hash_rows += count
                run_hashes.append({"runId": int(run["id"]), "rows": count, "sha256": digest, "elapsedMs": round(elapsed, 6)})
            item = {
                "scale": label,
                "database": workload["database"],
                "targets": workload["targetCount"],
                "rows": workload["rowCount"],
                "viewQueryFirstMs": view["firstMs"],
                "viewQueryMedianMs": view["medianMs"],
                "viewQueryStatus": view["status"],
                "baseQueryFirstMs": base["firstMs"],
                "baseQueryMedianMs": base["medianMs"],
                "baseQueryStatus": base["status"],
                "featureQueryFirstMs": feature["firstMs"],
                "featureQueryMedianMs": feature["medianMs"],
                "featureQueryStatus": feature["status"],
                "independentIntegrityMs": round(hash_ms, 6),
                "independentIntegrityRows": hash_rows,
            }
            rows.append(item)
            raw_rows.append({"scale": label, "view": view, "base": base, "feature": feature, "hashes": run_hashes})
            if label in ("s1", "s2"):
                view_explain_ms, view_explain = explain_analyze(db, view_sql, (workload["batchId"],))
                feature_explain_ms, feature_explain = explain_analyze(db, feature_sql, (workload["projectId"],))
                base_explain_ms, base_explain = explain_analyze(db, base_sql, (workload["batchId"],))
                write_text(
                    sql_root / f"explain-{label}-full-series.txt",
                    f"client_elapsed_ms={view_explain_ms:.6f}\n{view_explain}",
                )
                write_text(
                    sql_root / f"explain-{label}-feature-contract.txt",
                    f"client_elapsed_ms={feature_explain_ms:.6f}\n{feature_explain}",
                )
                write_text(
                    sql_root / f"explain-{label}-base-row.txt",
                    f"client_elapsed_ms={base_explain_ms:.6f}\n{base_explain}",
                )
                write_json(
                    sql_root / f"indexes-{label}.json",
                    {
                        "featureMapping": db.all("SHOW INDEX FROM em_prediction_feature_mapping"),
                        "predictionResult": db.all("SHOW INDEX FROM em_prediction_result"),
                    },
                )
                view_definition = db.one("SHOW CREATE VIEW em_prediction_display") or {}
                write_json(sql_root / f"view-definition-{label}.json", view_definition)
        finally:
            db.close()
    write_csv(
        root / "component-comparison.csv",
        rows,
        [
            "scale", "database", "targets", "rows", "viewQueryFirstMs", "viewQueryMedianMs", "viewQueryStatus",
            "baseQueryFirstMs", "baseQueryMedianMs", "baseQueryStatus", "featureQueryFirstMs", "featureQueryMedianMs", "featureQueryStatus",
            "independentIntegrityMs", "independentIntegrityRows",
        ],
    )
    write_json(sql_root / "component-query-raw.json", raw_rows)
    write_csv(
        sql_root / "base-row-query-timing.csv",
        rows,
        ["scale", "database", "targets", "rows", "baseQueryFirstMs", "baseQueryMedianMs"],
    )
    return rows


def project_scope_control(args, root: Path, workloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare Gate's batch-only query with the API's project-and-batch shape."""
    sql_root = root / "sql"
    sql_root.mkdir(parents=True, exist_ok=True)
    scoped_sql = (
        "SELECT d.*,r.result_hash AS run_result_hash,b.output_hash AS batch_output_hash "
        "FROM em_prediction_display d "
        "LEFT JOIN em_prediction_run r ON r.id=d.run_id "
        "LEFT JOIN em_prediction_batch b ON b.id=d.batch_id "
        "WHERE d.project_id=%s AND d.batch_id=%s "
        "ORDER BY d.future_time ASC,d.target_type ASC,d.feature_code ASC,d.step ASC LIMIT 50000"
    )
    batch_only_sql = (
        "SELECT d.*,r.result_hash AS run_result_hash,b.output_hash AS batch_output_hash "
        "FROM em_prediction_display d "
        "LEFT JOIN em_prediction_run r ON r.id=d.run_id "
        "LEFT JOIN em_prediction_batch b ON b.id=d.batch_id "
        "WHERE d.batch_id=%s "
        "ORDER BY d.future_time ASC,d.target_type ASC,d.feature_code ASC,d.step ASC LIMIT 50000"
    )
    selected = {item.strip().lower() for item in args.control_scales.split(",") if item.strip()}
    control_path = sql_root / "project-scope-control.csv"
    previous_rows = []
    if control_path.is_file():
        with control_path.open(encoding="utf-8", newline="") as handle:
            previous_rows = list(csv.DictReader(handle))
    rows = []
    for workload in workloads:
        label = (
            "reference" if workload["database"] == REFERENCE_DB
            else "s1" if workload["database"] == S1_DB
            else "s2" if workload["database"] == S2_DB
            else f"n{workload['targetCount']}"
        )
        if "all" not in selected and label.lower() not in selected:
            continue
        db = Database(args, workload["database"])
        try:
            timing = timed_query(
                db,
                scoped_sql,
                (workload["projectId"], workload["batchId"]),
            )
            rows.append(
                {
                    "scale": label,
                    "database": workload["database"],
                    "targets": workload["targetCount"],
                    "rows": workload["rowCount"],
                    "status": timing["status"],
                    "firstMs": timing["firstMs"],
                    "medianMs": timing["medianMs"],
                    "p95Ms": timing["p95Ms"],
                    "completedRepetitions": timing["completedRepetitions"],
                }
            )
            if label in ("reference", "s1", "s2"):
                explain_ms, explain = explain_analyze(
                    db,
                    scoped_sql,
                    (workload["projectId"], workload["batchId"]),
                )
                write_text(
                    sql_root / f"explain-{label}-project-scoped-series.txt",
                    f"client_elapsed_ms={explain_ms:.6f}\n{explain}",
                )
            if label == "reference":
                explain_ms, explain = explain_analyze(db, batch_only_sql, (workload["batchId"],))
                write_text(
                    sql_root / "explain-reference-full-series.txt",
                    f"client_elapsed_ms={explain_ms:.6f}\n{explain}",
                )
        finally:
            db.close()
    combined = {str(row["scale"]): row for row in previous_rows}
    combined.update({str(row["scale"]): row for row in rows})
    rows = [combined[key] for key in sorted(combined)]
    write_csv(
        control_path,
        rows,
        ["scale", "database", "targets", "rows", "status", "firstMs", "medianMs", "p95Ms", "completedRepetitions"],
    )
    return rows


def repetitions(
    backend: Backend,
    operation: str,
    path: str,
    expected_rows: int,
    output: Path,
) -> dict[str, Any]:
    rows = []
    phases = (("first", 1), ("warmup", 5), ("measured", 10))
    for phase, count in phases:
        for repetition in range(1, count + 1):
            elapsed_ms, response = time_call(lambda: raw_api(backend.port, path, 180))
            data = response.get("data")
            actual_rows = data.get("actualPointCount") if isinstance(data, dict) else len(data or [])
            rows.append(
                {
                    "operation": operation,
                    "phase": phase,
                    "repetition": repetition,
                    "elapsedMs": round(elapsed_ms, 6),
                    "rowCount": actual_rows,
                    "pass": actual_rows == expected_rows,
                }
            )
    measured = [row["elapsedMs"] for row in rows if row["phase"] == "measured"]
    write_csv(output, rows, ["operation", "phase", "repetition", "elapsedMs", "rowCount", "pass"])
    return {"operation": operation, "firstMs": rows[0]["elapsedMs"], **summary(measured), "allValid": all(row["pass"] for row in rows)}


def run_fresh_comparison(args, root: Path, workloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for workload_index, workload in enumerate(workloads):
        label = "reference" if workload["database"] == REFERENCE_DB else "s1"
        output = root / f"fresh-{label}"
        output.mkdir(parents=True, exist_ok=True)
        item = {"label": label, "workload": workload, "operations": {}}
        for operation_index, (operation, path) in enumerate(
            (
                ("gate-first", gate_path(workload)),
                ("full-series-first", series_path(workload, True)),
            )
        ):
            backend = Backend(
                args,
                workload["database"],
                args.backend_port + 20 + workload_index * 4 + operation_index,
                args.runtime_root / f"fresh-{label}-{operation}",
            )
            try:
                backend.start()
                item["operations"][operation] = repetitions(
                    backend,
                    operation,
                    path,
                    workload["rowCount"],
                    output / f"{operation}-raw.csv",
                )
            finally:
                backend.stop()
                save_backend_log(backend, output / operation)
                cleanup_benchmark_connections(args, workload["database"], output / operation)
        write_json(output / "comparison-summary.json", item)
        results.append(item)
    write_json(root / "fresh-reference-vs-s1.json", {"schemaVersion": "shm-em-phase2a1-fresh-comparison-v1", "results": results})
    return results


def prepare_sweep_workloads(args, root: Path) -> list[dict[str, Any]]:
    workloads = []
    existing = {
        124: discover_workload(args, S1_DB),
        1_240: discover_workload(args, S2_DB),
    }
    for targets in SWEEP_TARGETS:
        if targets in existing:
            workloads.append(existing[targets])
            continue
        database = f"shm_em_reproduce_benchmark_localization_{targets:04d}"
        try:
            reusable = discover_workload(args, database)
            if reusable["targetCount"] == targets and reusable["rowCount"] == targets * STEPS:
                workloads.append(reusable)
                continue
        except Exception:
            pass
        imports = initialize_database(args, database)
        db = Database(args, database)
        try:
            fixture = create_fixture(db, f"L{targets:04d}", targets)
            persistence = persist_results(db, fixture)
            integrity = finalize_integrity(db, fixture)
            workload = discover_workload(args, database)
            write_json(
                root / "fixtures" / f"n{targets}.json",
                {
                    "sqlImports": imports,
                    "fixture": {key: value for key, value in fixture.items() if key != "baseTime"},
                    "baseTime": fixture["baseTime"].isoformat(),
                    "persistence": persistence,
                    "integrity": integrity,
                    "discoveredWorkload": workload,
                },
            )
            workloads.append(workload)
        finally:
            db.close()
    return workloads


def run_scaling_sweep(args, root: Path, workloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, workload in enumerate(workloads):
        output = root / "scaling" / f"n{workload['targetCount']}"
        backend = Backend(
            args,
            workload["database"],
            args.backend_port + 40 + index,
            args.runtime_root / f"sweep-{workload['targetCount']}",
        )
        try:
            backend.start()
            diagnostic = diagnostic_gate(args, backend, workload, output / "first", args.gate_timeout)
            request = diagnostic["request"]
            row = {
                "targets": workload["targetCount"],
                "rows": workload["rowCount"],
                "database": workload["database"],
                "firstStatus": request["status"],
                "firstMs": request["elapsedMs"],
                "measuredCount": 0,
                "medianMs": None,
                "p95Ms": None,
                "stopPoint": request["status"] != "completed",
            }
            if request["status"] == "completed" and float(request["elapsedMs"]) < 60_000:
                measured = []
                measured_rows = []
                for repetition in range(1, 4):
                    elapsed_ms, response = time_call(lambda: raw_api(backend.port, gate_path(workload), 180))
                    gate = response.get("data") or {}
                    valid = gate.get("actualPointCount") == workload["rowCount"]
                    measured.append(elapsed_ms)
                    measured_rows.append(
                        {
                            "repetition": repetition,
                            "elapsedMs": round(elapsed_ms, 6),
                            "actualPointCount": gate.get("actualPointCount"),
                            "resultIntegrityValid": gate.get("resultIntegrityValid"),
                            "executionEligible": gate.get("executionEligible"),
                            "pass": valid,
                        }
                    )
                stats = summary(measured)
                row.update({"measuredCount": 3, "medianMs": stats["medianMs"], "p95Ms": stats["p95Ms"]})
                write_csv(
                    output / "measured-raw.csv",
                    measured_rows,
                    ["repetition", "elapsedMs", "actualPointCount", "resultIntegrityValid", "executionEligible", "pass"],
                )
            rows.append(row)
        finally:
            backend.stop()
            save_backend_log(backend, output)
            cleanup_benchmark_connections(args, workload["database"], output)
        if rows[-1]["stopPoint"]:
            break
    write_csv(
        root / "scaling-sweep.csv",
        rows,
        ["targets", "rows", "database", "firstStatus", "firstMs", "measuredCount", "medianMs", "p95Ms", "stopPoint"],
    )
    write_json(
        root / "scaling-sweep-summary.json",
        {
            "schemaVersion": "shm-em-phase2a1-scaling-sweep-v1",
            "fixedSteps": STEPS,
            "gateResultQueryLimit": GATE_LIMIT,
            "rows": rows,
        },
    )
    return rows


def ensure_output_root(args) -> Path:
    root = (args.evidence_root / "localization").resolve()
    evidence_root = args.evidence_root.resolve()
    if evidence_root not in root.parents:
        raise RuntimeError(f"Unsafe localization output root: {root}")
    if args.reset and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="Localize frozen SHM-EM Gate performance")
    parser.add_argument("--backend-port", type=int, default=5210)
    parser.add_argument("--gate-timeout", type=int, default=180)
    parser.add_argument("--operation-cases", default="D01,D02,D03,D04")
    parser.add_argument("--control-scales", default="all")
    parser.add_argument(
        "--sections",
        default="operation,sql,control,comparison,sweep",
        help="Comma-separated: operation,sql,control,comparison,sweep",
    )
    parser.add_argument("--reset", action="store_true")
    args = resolve_common_args(parser)
    sections = {item.strip() for item in args.sections.split(",") if item.strip()}
    unsupported = sections - {"operation", "sql", "control", "comparison", "sweep"}
    if unsupported:
        raise ValueError(f"Unsupported sections: {sorted(unsupported)}")
    root = ensure_output_root(args)
    write_json(
        root / "run-context.json",
        {
            "schemaVersion": "shm-em-phase2a1-run-context-v1",
            "startedAt": utc_iso(),
            "sections": sorted(sections),
            "gateTimeoutSeconds": args.gate_timeout,
            "gateResultQueryLimit": GATE_LIMIT,
            "coreDiff": core_diff(args.repo_root),
            "backendJar": str(args.backend_jar),
            "java": str(args.java),
        },
    )
    if not core_diff(args.repo_root)["pass"]:
        raise RuntimeError("Final Core Freeze v2 differs; localization aborted")

    reference = discover_workload(args, REFERENCE_DB)
    s1 = discover_workload(args, S1_DB)
    s2 = discover_workload(args, S2_DB)
    write_json(root / "workloads.json", {"reference": reference, "s1": s1, "s2": s2})
    all_workloads = None
    try:
        if "operation" in sections:
            run_operation_order(args, root, s2)
        if "comparison" in sections:
            run_fresh_comparison(args, root, [reference, s1])
        if "sweep" in sections or "sql" in sections or "control" in sections:
            all_workloads = prepare_sweep_workloads(args, root)
        if "sweep" in sections:
            run_scaling_sweep(args, root, all_workloads or [])
        if "sql" in sections:
            query_components(args, root, [reference, *(all_workloads or [])])
        if "control" in sections:
            project_scope_control(args, root, [reference, *(all_workloads or [])])
        write_json(root / "run-complete.json", {"finishedAt": utc_iso(), "sections": sorted(sections), "coreDiff": core_diff(args.repo_root)})
        print(json.dumps({"output": str(root), "sections": sorted(sections), "coreUnchanged": True}, indent=2))
        return 0
    finally:
        cleanup_runtime(args)


if __name__ == "__main__":
    raise SystemExit(main())
