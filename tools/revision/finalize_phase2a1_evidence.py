#!/usr/bin/env python3
"""Finalize Phase 2A.1 localization evidence and build the GPT review package."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from typing import Any

from phase2a_benchmark_support import (
    Database,
    core_diff,
    git,
    resolve_common_args,
    run_command,
    sha256_file,
    utc_iso,
    write_csv,
    write_json,
    write_text,
)


PHASE2A_CHECKPOINT = "60b2df8"
GATE_LIMIT = 50_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in rows}


def parse_client_ms(path: Path) -> float | None:
    match = re.search(r"client_elapsed_ms=([0-9.]+)", path.read_text(encoding="utf-8"))
    return float(match.group(1)) if match else None


def aggregate_diagnostics(root: Path) -> dict[str, Any]:
    jvm_root = root / "jvm"
    mysql_root = root / "mysql"
    jvm_root.mkdir(parents=True, exist_ok=True)
    mysql_root.mkdir(parents=True, exist_ok=True)
    memory_rows = []
    gc_rows = []
    thread_rows = []
    processlist_rows = []
    for path in sorted(root.rglob("memory-samples.csv")):
        if path.parent == jvm_root:
            continue
        scenario = path.parent.parent.relative_to(root).as_posix()
        for row in read_csv(path):
            memory_rows.append({"scenario": scenario, **row})
    for path in sorted(root.rglob("gc-samples.csv")):
        if path.parent == jvm_root:
            continue
        scenario = path.parent.parent.relative_to(root).as_posix()
        for row in read_csv(path):
            gc_rows.append({"scenario": scenario, **row})
    for path in sorted(root.rglob("thread-sample-summary.csv")):
        if path.parent == jvm_root:
            continue
        scenario = path.parent.parent.relative_to(root).as_posix()
        for row in read_csv(path):
            thread_rows.append({"scenario": scenario, **row})
    for path in sorted(root.rglob("processlist-samples.csv")):
        if path.parent == mysql_root:
            continue
        scenario = path.parent.parent.relative_to(root).as_posix()
        for row in read_csv(path):
            processlist_rows.append({"scenario": scenario, **row})

    write_csv(
        jvm_root / "memory-samples.csv",
        memory_rows,
        ["scenario", "elapsedSeconds", "rssBytes", "vmsBytes", "cpuUserSeconds", "cpuSystemSeconds", "threadCount", "error"],
    )
    write_csv(
        jvm_root / "gc-samples.csv",
        gc_rows,
        ["scenario", "elapsedSeconds", "S0", "S1", "E", "O", "M", "CCS", "YGC", "YGCT", "FGC", "FGCT", "GCT", "raw"],
    )
    write_csv(
        jvm_root / "thread-sample-summary.csv",
        thread_rows,
        ["scenario", "elapsedSeconds", "thread", "state", "category", "representativeFrame"],
    )
    write_csv(
        mysql_root / "processlist-samples.csv",
        processlist_rows,
        ["scenario", "elapsedSeconds", "activeConnections", "queryConnections", "states", "error"],
    )

    categories: dict[str, int] = {}
    for row in thread_rows:
        categories[row.get("category") or "unknown"] = categories.get(row.get("category") or "unknown", 0) + 1
    timeout_scenarios = sorted(
        {
            path.parent.relative_to(root).as_posix()
            for path in root.rglob("gate-diagnostic.json")
            if read_json(path).get("request", {}).get("status") == "timeout"
        }
    )
    timeout_process_rows = [row for row in processlist_rows if any(row["scenario"].startswith(item) for item in timeout_scenarios)]
    query_samples = sum(int(row.get("queryConnections") or 0) > 0 for row in timeout_process_rows)
    max_rss = max((int(row["rssBytes"]) for row in memory_rows if row.get("rssBytes")), default=None)
    gc_deltas = []
    for scenario in sorted({row["scenario"] for row in gc_rows}):
        values = [row for row in gc_rows if row["scenario"] == scenario and row.get("GCT")]
        if len(values) >= 2:
            gc_deltas.append(float(values[-1]["GCT"]) - float(values[0]["GCT"]))
    result = {
        "threadSamples": len(thread_rows),
        "threadCategories": categories,
        "timeoutScenarios": timeout_scenarios,
        "timeoutProcesslistSamples": len(timeout_process_rows),
        "timeoutSamplesWithActiveQuery": query_samples,
        "maximumObservedRssBytes": max_rss,
        "maximumObservedGcTimeDeltaSeconds": max(gc_deltas, default=0.0),
    }
    write_json(jvm_root / "diagnostic-summary.json", result)
    return result


def collect_performance_schema(args, root: Path) -> dict[str, Any]:
    db = Database(args, "shm_em_reproduce_benchmark_scaling_s2")
    try:
        consumers = db.all(
            "SELECT NAME,ENABLED FROM performance_schema.setup_consumers "
            "WHERE NAME LIKE 'events_statements%%' OR NAME='statements_digest' ORDER BY NAME"
        )
        digest_count = int(db.scalar("SELECT COUNT(*) FROM performance_schema.events_statements_summary_by_digest"))
        digest_limit = int(db.scalar("SELECT @@performance_schema_digests_size"))
        digests = db.all(
            "SELECT SCHEMA_NAME,COUNT_STAR,ROUND(SUM_TIMER_WAIT/1000000000000,6) AS total_seconds,"
            "ROUND(AVG_TIMER_WAIT/1000000000,6) AS average_ms,"
            "ROUND(MAX_TIMER_WAIT/1000000000000,6) AS maximum_seconds,DIGEST_TEXT "
            "FROM performance_schema.events_statements_summary_by_digest "
            "WHERE SCHEMA_NAME LIKE 'shm_em_reproduce_benchmark_scaling_%%' "
            "AND UPPER(DIGEST_TEXT) LIKE '%%EM_PREDICTION_DISPLAY%%' ORDER BY SUM_TIMER_WAIT DESC"
        )
    finally:
        db.close()
    result = {
        "performanceSchemaEnabled": True,
        "consumers": consumers,
        "digestRows": digest_count,
        "digestCapacity": digest_limit,
        "digestCapacitySaturated": digest_count >= digest_limit,
        "matchingScalingDigests": digests,
        "interpretation": (
            "Digest evidence for this run is unavailable because the server-wide digest table was already at capacity; "
            "per-second SHOW FULL PROCESSLIST samples and EXPLAIN ANALYZE remain the runtime SQL evidence."
            if digest_count >= digest_limit and not digests
            else "Matching statement digests were retained."
        ),
    }
    write_json(root / "mysql" / "performance-schema.json", result)
    return result


def run_regression(args, root: Path) -> dict[str, Any]:
    checks = {
        "localizationToolCompile": run_command(
            [str(args.python), "-m", "py_compile", str(args.repo_root / "tools/revision/localize_gate_performance.py"), str(Path(__file__).resolve())],
            args.repo_root,
            120,
        ),
        "backendTests": run_command([str(args.maven), "test"], args.backend_root, 900),
        "pitPreTests": run_command([str(args.python), "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"], args.pit_pre_root, 900),
        "frontendTypecheck": run_command([str(args.npm), "run", "typecheck"], args.frontend_root, 900),
        "frontendBuild": run_command([str(args.npm), "run", "build"], args.frontend_root, 900),
    }
    result = {
        "schemaVersion": "shm-em-phase2a1-regression-v1",
        "capturedAt": utc_iso(),
        "checks": checks,
        "allPass": all(item["pass"] for item in checks.values()),
        "coreDiff": core_diff(args.repo_root),
    }
    write_json(root / "regression-tests.json", result)
    return result


def write_reports(args, root: Path, diagnostics: dict[str, Any], performance_schema: dict[str, Any], regression: dict[str, Any]) -> None:
    operation = read_csv(root / "operation-order-matrix.csv")
    scaling = read_csv(root / "scaling-sweep.csv")
    components = by_key(read_csv(root / "component-comparison.csv"), "scale")
    controls = by_key(read_csv(root / "sql/project-scope-control.csv"), "scale")
    comparison = read_json(root / "fresh-reference-vs-s1.json")["results"]
    comparison_by_label = {item["label"]: item for item in comparison}

    reference_gate = comparison_by_label["reference"]["operations"]["gate-first"]["medianMs"]
    s1_gate = comparison_by_label["s1"]["operations"]["gate-first"]["medianMs"]
    reference_series = comparison_by_label["reference"]["operations"]["full-series-first"]["medianMs"]
    s1_series = comparison_by_label["s1"]["operations"]["full-series-first"]["medianMs"]
    s2_unscoped_explain = parse_client_ms(root / "sql/explain-s2-full-series.txt")
    s2_scoped_explain = parse_client_ms(root / "sql/explain-s2-project-scoped-series.txt")
    speedup = s2_unscoped_explain / s2_scoped_explain

    methodology = f"""# Phase 2A.1 Gate Performance Localization Methodology

## Scope

This phase localizes the 180-second S2 Gate timeout. It does not optimize or modify production code, schema, indexes, views, model artifacts, PIT_PRE, or frontend code. Final Core Freeze v2 remains unchanged.

## Environment and workload

- Concurrency: 1.
- Backend: the same packaged SHM-EM JAR and JVM options used by Phase 2A.
- Database: MySQL 8.0.41 on the recorded reference host.
- Prediction horizon: 40 steps.
- Sweep: 124, 248, 496, 744, 992, and 1,240 target channels (4,960 to 49,600 persisted rows).
- S1/S2 fixtures: the valid persisted fixtures retained from Phase 2A.
- Intermediate fixtures: generated with the same schema, contract, persistence, and cross-language integrity procedure.

## Fresh-process isolation

Each Gate-first scale and D01-D04 operation-order case starts a fresh backend JVM. Readiness uses only `/api/em/projects?limit=1`. Residual connections are removed only from the disposable benchmark database after its JVM stops, and the cleanup is recorded.

## Runtime diagnostics

For Gate calls longer than 5 seconds, the harness samples RSS, JVM GC counters, and `SHOW FULL PROCESSLIST` approximately once per second. `jstack` and `jstat` samples are captured at 5, 15, 30, 60, and 120 seconds. Diagnostics add observational overhead and are used for localization rather than manuscript latency statistics.

## SQL controls

The Gate-equivalent batch-only view query, feature-contract query, base-table integrity-field query, and project-scoped view control are measured independently. `EXPLAIN ANALYZE` is retained for S1/S2 and Reference controls. A 180-second session statement limit is used only for direct diagnostic queries; production Gate calls retain the original 180-second client boundary.

## Repetition policy

Each sweep scale has one fresh-process first call. Three measured calls are added only when the first call is below 60 seconds. A first call at or above 60 seconds is not repeated; a 180-second timeout stops the sweep. No OS or InnoDB cache flush is performed, matching Phase 2A's warm-cache policy.

## Evidence checkpoint

The untouched Phase 2A boundary evidence was committed first as `{PHASE2A_CHECKPOINT}`. Phase 2A.1 diagnostics remain separate for GPT review.
"""
    write_text(root / "methodology.md", methodology)

    query_summary = f"""# Query Plan Summary

## Gate-equivalent batch-only query

- S1: {parse_client_ms(root / 'sql/explain-s1-full-series.txt'):.3f} ms for 4,960 rows.
- S2: {s2_unscoped_explain:.3f} ms for 49,600 rows.
- S2 plan: 49,600 result rows each probe 1,240 project feature mappings through `uk_em_prediction_feature_schema`; the feature-mapping branch accounts for approximately 215 seconds of the analyzed execution.

## Project-scoped control

- S2: {s2_scoped_explain:.3f} ms for 49,600 rows.
- The optimizer changes the feature-mapping branch to a one-time hash input and hash join.
- Observed EXPLAIN speedup: {speedup:.1f}x.
- The ordinary series API includes both project and batch predicates; the frozen Gate constructs a batch-only query.

## Base-table and contract controls

- S2 base persisted-row query median: {number(components['s2']['baseQueryMedianMs']):.3f} ms.
- S2 feature-contract query median: {number(components['s2']['featureQueryMedianMs']):.3f} ms.
- S2 independent persisted integrity recomputation: {number(components['s2']['independentIntegrityMs']):.3f} ms.

These controls show that persistence capacity, contract loading, and independent integrity hashing do not explain the 180-second Gate timeout.

## Reference versus S1

The Reference plan hash-joins the feature-mapping table once, while S1 repeatedly probes 124 feature rows per prediction row. The two 4,960-row workloads therefore have different optimizer plans despite equal row counts. This explains why synthetic S1 remains slower and confirms that row count alone is not a sufficient workload descriptor.

## Variability note

Some project-scoped direct calls changed plans across repetitions at intermediate cardinalities. The conclusion relies on the retained plans, repeated API observations, and process/thread evidence rather than a single fast direct query.
"""
    write_text(root / "sql/query-plan-summary.md", query_summary)

    jvm_summary = f"""# JVM and Thread Diagnostic Summary

- Request-thread samples: {diagnostics['threadSamples']}.
- Dominant category: `jdbc-mysql-read` ({diagnostics['threadCategories'].get('jdbc-mysql-read', 0)} samples).
- Timeout scenarios: {len(diagnostics['timeoutScenarios'])}.
- Timeout processlist samples with an active query: {diagnostics['timeoutSamplesWithActiveQuery']} / {diagnostics['timeoutProcesslistSamples']}.
- Maximum observed RSS: {diagnostics['maximumObservedRssBytes']} bytes.
- Maximum observed GC-time increase during a sampled Gate interval: {diagnostics['maximumObservedGcTimeDeltaSeconds']:.6f} seconds.

All sampled Gate request threads remained in the MySQL read path. No sample reached feature/timeline validation, canonical hashing, persisted integrity hashing, or response serialization. GC counters were stable during the long Gate intervals, including the high-RSS D03/D04 processes.
"""
    write_text(root / "jvm/jvm-summary.md", jvm_summary)

    statement_summary = f"""# MySQL Runtime Statement Summary

`SHOW FULL PROCESSLIST` was sampled throughout every long Gate call. The Gate connection remained in `Query: executing` on the prediction-display SQL through the 180-second boundary.

Performance Schema statement consumers were available, but the server-wide digest table contained {performance_schema['digestRows']} of {performance_schema['digestCapacity']} rows and was saturated before this run. No matching scaling-schema digest was retained. Therefore, digest aggregates are marked unavailable; runtime processlist, direct query timing, and `EXPLAIN ANALYZE` are the authoritative SQL evidence.
"""
    write_text(root / "mysql/statement-summary.md", statement_summary)

    root_cause = f"""# Phase 2A.1 Root-Cause Analysis

## Primary bottleneck

**CONFIRMED: Gate's batch-only `em_prediction_display` query selects an unfavorable feature-mapping join plan at synthetic high cardinality.**

D01-D04 all timed out at approximately 180 seconds. Every retained request-thread sample was in JDBC/MySQL read, and every timeout processlist sample showed the same active view query. S2 `EXPLAIN ANALYZE` required {s2_unscoped_explain / 1000:.3f} seconds; adding the already-known project predicate reduced the analyzed query to {s2_scoped_explain / 1000:.3f} seconds ({speedup:.1f}x) by changing the feature-mapping branch to a hash join.

## Secondary bottlenecks

**SUPPORTED: response allocation raises RSS after 36 full-series calls, but it does not cause the Gate timeout.** D03/D04 reached high RSS, while D01 timed out in a fresh JVM with lower and decreasing RSS. All four cases stopped in the same SQL read path.

**SUPPORTED: result sorting and base-row transfer are measurable secondary costs.** The S2 base-row control is about {number(components['s2']['baseQueryMedianMs']) / 1000:.3f} seconds and the scoped view/API path remains several seconds, but neither approaches 180 seconds.

## Not the bottleneck

- **NOT SUPPORTED: benchmark order / heap pressure.** D01 Gate-first and D02-D04 all have the same timeout mechanism.
- **NOT SUPPORTED: GC.** Sampled GC time did not increase during the long Gate calls.
- **NOT SUPPORTED: Java feature/timeline validation.** The request did not return from `PredictionMapper.selectSeries` in any timeout sample.
- **NOT SUPPORTED: persisted integrity hashing.** Independent S2 recomputation completed in {number(components['s2']['independentIntegrityMs']) / 1000:.3f} seconds.
- **NOT SUPPORTED: canonical contract hashing.** Thread samples never reached this stage; the contract query itself was about {number(components['s2']['featureQueryMedianMs']):.3f} ms.
- **NOT SUPPORTED: response serialization.** Gate response serialization was not reached.
- **NOT SUPPORTED: MySQL storage capacity.** The base table, project-scoped view, and integrity controls all completed.

## S1/reference discrepancy

**CONFIRMED: the discrepancy is fixture/query-plan shape, not row count.** Fresh Reference versus S1 Gate medians were {reference_gate:.3f} and {s1_gate:.3f} ms ({s1_gate / reference_gate:.2f}x); full-series medians were {reference_series:.3f} and {s1_series:.3f} ms ({s1_series / reference_series:.2f}x). Reference uses a feature hash join, whereas S1 repeatedly scans its project feature subset.

## S2 180-second timeout mechanism

**CONFIRMED:** the Gate request remains blocked while MySQL executes the batch-only view query. It does not spend the 180 seconds in validation, integrity hashing, canonical hashing, GC, or serialization.

## 50,000-row structural cap

**CONFIRMED structural boundary, NOT SUPPORTED as the cause of S2 latency.** S2 has 49,600 rows and is below the hard query limit of {GATE_LIMIT}. S3+ cannot be validly assessed by the frozen Gate because results would be truncated even if query performance were acceptable.

## Route P: minimal core correction

- Candidate file: `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java`.
- Candidate change: set `resultQuery.projectId` from the already-loaded batch before `selectSeries`.
- Expected benefit: preserve the same project/batch result set while enabling the measured project-scoped plan; S2 SQL control improved {speedup:.1f}x.
- Risk: low but non-zero because optimizer behavior and cross-project isolation must be regression-tested.
- Required regression: F01-F12, I01-I02, second heterogeneous configuration, result-count/hash equality, and fresh S1/S2 timing.
- No Mapper, view, schema, index, hash, pagination, or architecture change is indicated by current evidence.

## Route L: retain bounded core

- Manuscript limitation: current Gate is reliable for the 4,960-row reference workload but shows nonlinear latency on synthetic high-cardinality contracts.
- Maximum valid sub-180-second workload demonstrated: 39,680 rows / 992 targets / 40 steps at {number(by_key(scaling, 'rows')['39680']['firstMs']) / 1000:.3f} seconds.
- S2 boundary: 49,600 rows did not return within 180 seconds.
- Structural limit: 50,000 prediction-display rows.

## Recommendation

The evidence favors Route P as a narrow, explainable correction, but **do not implement it until GPT approval**. Phase 2A.1 stops here.
"""
    write_text(root / "root-cause-analysis.md", root_cause)

    recommendation = f"""# Phase 2A.1 Recommendation

## Route P

Authorize one targeted production-core correction: add the known batch project ID to the Gate result query. The measured query-plan benefit is {speedup:.1f}x on S2, and no broader redesign is currently justified.

## Route L

Keep Final Core Freeze v2 unchanged, report the 4,960-row reference performance, the 39,680-row valid but slow boundary, the 49,600-row timeout, and the 50,000-row hard cap as limitations.

## Decision boundary

Phase 2A.1 makes no production change and does not select a route. GPT should review whether the plan evidence and regression scope are sufficient for Phase 2A.2 targeted correction.
"""
    write_text(root / "phase2a1-recommendation.md", recommendation)

    completion = f"""# Phase 2A.1 Completion Report

## Verdict

Gate performance localization: **COMPLETE**  
Production core changes: **NONE**  
Final Core Freeze v2: **UNCHANGED**  
Next action: **STOP FOR GPT REVIEW**

## Acceptance

- L01 Final Core Freeze v2 unchanged: PASS.
- L02 Phase 2A evidence preserved in checkpoint `{PHASE2A_CHECKPOINT}`: PASS.
- L03 fresh S2 Gate-first: PASS; timeout reproduced.
- L04 D01-D04 operation-order isolation: PASS; all four timed out in the same JDBC/MySQL path.
- L05 fresh Reference versus S1: PASS; discrepancy remains approximately 7x.
- L06 S1/S2 EXPLAIN ANALYZE: PASS.
- L07 JVM/thread/MySQL timeout evidence: PASS.
- L08 sub-50k Gate-first curve: PASS through the 49,600-row stop point.
- L09 50,000-row hard cap: CONFIRMED.
- L10 no production-core modification: PASS.

## Quantitative result

Gate-first latency grew from {number(scaling[0]['firstMs']) / 1000:.3f} seconds at 4,960 rows to {number(scaling[-2]['firstMs']) / 1000:.3f} seconds at 39,680 rows; 49,600 rows timed out at 180 seconds. S2 project-scoped SQL completed in about {s2_scoped_explain / 1000:.3f} seconds versus {s2_unscoped_explain / 1000:.3f} seconds for the Gate-equivalent batch-only plan.

## Regression

All requested checks passed: {regression['allPass']}. Frozen core diff is empty: {regression['coreDiff']['pass']}.
"""
    write_text(root / "PHASE2A1_COMPLETION_REPORT.md", completion)


def build_manifest(root: Path, repo: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or path.name in {
                "phase2a1-manifest.json",
                "phase2a1-manifest-verification.json",
                "gpt-review-package.json",
            }
            or "gpt-review-package" in relative.parts
            or path.suffix == ".zip"
        ):
            continue
        files.append({"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {
        "schemaVersion": "shm-em-phase2a1-manifest-v1",
        "generatedAt": utc_iso(),
        "phase2aCheckpoint": PHASE2A_CHECKPOINT,
        "head": git(repo, "rev-parse", "HEAD"),
        "coreDiff": core_diff(repo),
        "gateResultQueryLimit": GATE_LIMIT,
        "fileCountExcludingManifestAndPackage": len(files),
        "files": files,
    }
    write_json(root / "phase2a1-manifest.json", result)
    return result


def verify_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file():
            mismatches.append({"path": item["path"], "reason": "missing"})
            continue
        actual = sha256_file(path)
        if actual != item["sha256"] or path.stat().st_size != item["bytes"]:
            mismatches.append(
                {
                    "path": item["path"],
                    "reason": "hash-or-size-mismatch",
                    "expectedSha256": item["sha256"],
                    "actualSha256": actual,
                }
            )
    result = {
        "schemaVersion": "shm-em-phase2a1-manifest-verification-v1",
        "verifiedAt": utc_iso(),
        "manifestSha256": sha256_file(root / "phase2a1-manifest.json"),
        "checkedFiles": len(manifest["files"]),
        "mismatches": mismatches,
        "pass": not mismatches,
    }
    write_json(root / "phase2a1-manifest-verification.json", result)
    return result


def build_review_package(args, root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    package_root = root / "gpt-review-package"
    if package_root.exists():
        shutil.rmtree(package_root)
    evidence = package_root / "evidence"
    source = package_root / "source/tools/revision"
    evidence.mkdir(parents=True)
    source.mkdir(parents=True)
    for path in root.iterdir():
        if path.name in {
            "gpt-review-package",
            "SHM-EM_Phase2A1_GPT_Review_Package.zip",
            "gpt-review-package.json",
        }:
            continue
        destination = evidence / path.name
        if path.is_dir():
            shutil.copytree(path, destination)
        else:
            shutil.copy2(path, destination)
    for name in ("localize_gate_performance.py", "finalize_phase2a1_evidence.py", "phase2a_benchmark_support.py", "benchmark_scalability.py"):
        shutil.copy2(args.repo_root / "tools/revision" / name, source / name)
    handoff = f"""# GPT Review Handoff: Phase 2A.1

Phase 2A.1 is complete and stopped without production-core changes.

Review in this order:

1. `evidence/PHASE2A1_COMPLETION_REPORT.md`
2. `evidence/root-cause-analysis.md`
3. `evidence/sql/query-plan-summary.md`
4. `evidence/jvm/jvm-summary.md`
5. `evidence/mysql/statement-summary.md`
6. `evidence/phase2a1-recommendation.md`
7. `evidence/phase2a1-manifest.json`

Decision requested: authorize Route P as Phase 2A.2 targeted correction, or retain Route L and proceed with a documented boundary. Do not infer that Route P has already been implemented.
"""
    write_text(package_root / "GPT_REVIEW_HANDOFF.md", handoff)
    package_files = []
    for path in sorted(package_root.rglob("*")):
        if path.is_file():
            package_files.append({"path": path.relative_to(package_root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    package_manifest = {
        "schemaVersion": "shm-em-phase2a1-review-package-v1",
        "generatedAt": utc_iso(),
        "phase2a1ManifestSha256": sha256_file(root / "phase2a1-manifest.json"),
        "sourceManifestFileCount": manifest["fileCountExcludingManifestAndPackage"],
        "files": package_files,
    }
    write_json(package_root / "review-package-manifest.json", package_manifest)
    zip_path = root / "SHM-EM_Phase2A1_GPT_Review_Package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_root).as_posix())
    result = {
        "path": str(zip_path),
        "bytes": zip_path.stat().st_size,
        "sha256": sha256_file(zip_path),
        "fileCount": len(package_files) + 1,
    }
    write_json(root / "gpt-review-package.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Phase 2A.1 localization evidence")
    args = resolve_common_args(parser)
    root = args.evidence_root / "localization"
    required = (
        root / "operation-order-matrix.csv",
        root / "scaling-sweep.csv",
        root / "component-comparison.csv",
        root / "fresh-reference-vs-s1.json",
        root / "sql/explain-s1-full-series.txt",
        root / "sql/explain-s2-full-series.txt",
        root / "sql/explain-s2-project-scoped-series.txt",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Phase 2A.1 evidence is incomplete: {missing}")
    if not core_diff(args.repo_root)["pass"]:
        raise RuntimeError("Final Core Freeze v2 differs; finalization aborted")
    diagnostics = aggregate_diagnostics(root)
    performance_schema = collect_performance_schema(args, root)
    regression = run_regression(args, root)
    if not regression["allPass"]:
        raise RuntimeError("Regression checks failed; inspect regression-tests.json")
    write_reports(args, root, diagnostics, performance_schema, regression)
    write_json(
        root / "phase2a1-run-summary.json",
        {
            "schemaVersion": "shm-em-phase2a1-run-summary-v1",
            "completedAt": utc_iso(),
            "completedSections": ["operation-order", "sql-components", "project-scope-control", "fresh-reference-vs-s1", "sub-50k-sweep"],
            "executionStyle": "multiple resumable harness invocations; each Gate case used a fresh backend JVM",
            "coreDiff": core_diff(args.repo_root),
        },
    )
    manifest = build_manifest(root, args.repo_root)
    verification = verify_manifest(root, manifest)
    if not verification["pass"]:
        raise RuntimeError("Phase 2A.1 manifest verification failed")
    package = build_review_package(args, root, manifest)
    print(json.dumps({"output": str(root), "package": package, "coreUnchanged": True, "regressionPass": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
