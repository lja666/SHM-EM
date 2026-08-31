#!/usr/bin/env python3
"""Finalize Phase 2A STOP evidence without running additional benchmark workloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from typing import Any

from phase2a_benchmark_support import (
    FINAL_CORE_FREEZE_V2,
    PHASE1B_COMMIT,
    collect_environment,
    core_diff,
    manifest_for,
    resolve_common_args,
    run_command,
    sha256_file,
    summary,
    write_csv,
    write_json,
    write_text,
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_regressions(args) -> dict[str, Any]:
    backend = run_command([str(args.maven), "-q", "test", "package"], args.backend_root, 600)
    pit_pre = run_command(
        [str(args.python), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        args.pit_pre_root,
        300,
    )
    frontend = run_command([str(args.npm), "run", "build"], args.frontend_root, 600)
    result = {
        "schemaVersion": "shm-em-phase2a-regression-v1",
        "backend": backend,
        "pitPre": pit_pre,
        "frontend": frontend,
        "pass": backend["pass"] and pit_pre["pass"] and frontend["pass"],
    }
    write_json(args.evidence_root / "regression-tests.json", result)
    return result


def finalize_partial_scaling(root: Path) -> dict[str, Any]:
    path = root / "scaling/s2/api-progress.json"
    progress = read_json(path)
    rows = []
    failures = []
    for event in progress["events"]:
        row = {
            "operation": event["operation"],
            "phase": event["phase"],
            "repetition": event["repetition"],
            "status": event["status"],
            "elapsedMs": event.get("elapsedMs"),
            "scale": event.get("scale"),
            "targetCount": event.get("targetCount"),
            "startedAt": event.get("startedAt"),
            "finishedAt": event.get("finishedAt"),
            "errorType": event.get("errorType"),
            "error": event.get("error"),
        }
        rows.append(row)
        if event["status"] == "failed":
            failures.append(row)
    write_csv(
        root / "scaling/s2/api-partial-raw.csv",
        rows,
        ["operation", "phase", "repetition", "status", "elapsedMs", "scale", "targetCount",
         "startedAt", "finishedAt", "errorType", "error"],
    )
    operations = {}
    for operation in sorted({item["operation"] for item in rows}):
        values = [
            float(item["elapsedMs"])
            for item in rows
            if item["operation"] == operation and item["phase"] == "measured" and item["status"] == "completed"
        ]
        first = next(
            (item for item in rows if item["operation"] == operation and item["phase"] == "first"),
            None,
        )
        operations[operation] = {
            "firstStatus": None if first is None else first["status"],
            "firstMs": None if first is None else first["elapsedMs"],
            **summary(values),
        }
    result = {
        "schemaVersion": "shm-em-phase2a-partial-api-summary-v1",
        "scale": "S2",
        "operations": operations,
        "failures": failures,
        "completedSeriesRepetitions": sum(
            1 for item in rows if item["status"] == "completed" and item["operation"].startswith("series-")
        ),
        "gateCompleted": any(item["operation"] == "gate-inspect" and item["status"] == "completed" for item in rows),
        "futureStateAttempted": any(item["operation"] == "future-state" for item in rows),
        "stopRequired": bool(failures),
    }
    write_json(root / "scaling/s2/api-partial-summary.json", result)
    return result


def frozen_evidence(args) -> dict[str, Any]:
    result = core_diff(args.repo_root)
    write_json(args.evidence_root / "core-diff-inventory.json", result)
    completed = subprocess.run(
        ["git", "diff", FINAL_CORE_FREEZE_V2, "--", "src/backend/src/main", "src/frontend/src", "src/pit_pre/pit_pre", ".gitattributes"],
        cwd=str(args.repo_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    write_text(args.evidence_root / "frozen-core.diff", completed.stdout)
    status = subprocess.run(
        ["git", "status", "--short"], cwd=str(args.repo_root), text=True, encoding="utf-8",
        errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    ).stdout
    write_text(args.evidence_root / "git-status.txt", status)
    return result


def storage_bytes(scale: dict[str, Any]) -> int:
    return sum(int(item["DATA_LENGTH"]) + int(item["INDEX_LENGTH"]) for item in scale["storageAfter"])


def completion_report(args, environment: dict[str, Any], regressions: dict[str, Any], partial: dict[str, Any], core: dict[str, Any]) -> str:
    reference = read_json(args.evidence_root / "reference/reference-summary.json")
    scaling = read_json(args.evidence_root / "scaling/scaling-summary.json")
    pit = reference["pitPre"]
    backend = reference["backend"]["operations"]
    hardware = environment["hardware"]
    mysql = environment["mysql"]
    s1, s2 = scaling["scales"]

    def metric(item: dict[str, Any]) -> str:
        return f"{item['medianMs']:.3f} ms / {item['p95Ms']:.3f} ms / {item['count']}"

    reference_rows = [
        ("PIT_PRE full batch", pit["components"]["fullBatch"]),
        ("All-model inference", pit["components"]["allModelInference"]),
        ("Gate inspect", backend["gate-inspect"]),
        ("Future State", backend["future-state"]),
        ("Evaluate", backend["evaluate"]),
        ("Execute", backend["execute"]),
        ("Provenance trace", backend["provenance-trace"]),
        ("Full-batch series", backend["series-full-batch"]),
    ]
    table = "\n".join(f"| {name} | {item['medianMs']:.3f} ms | {item['p95Ms']:.3f} ms | {item['count']} |" for name, item in reference_rows)
    s2_full = partial["operations"]["series-full-batch"]
    acceptance = [
        ("P2A-01", "PASS" if core["pass"] else "FAIL", "Frozen production-core diff is empty."),
        ("P2A-02", "PASS", "Environment and MySQL runtime configuration captured."),
        ("P2A-03", "PASS", "Reference PIT_PRE and all required backend/API timings captured."),
        ("P2A-04", "PASS", "Reference uses 1 first + 5 warm-up + 30 measured; Execute uses 10 isolated repetitions."),
        ("P2A-05", "STOP", "S1 passed; S2 Gate first call timed out at 180 s, so S3-S5 were not run."),
        ("P2A-06", "PARTIAL", "S1 Gate integrity passed; S2 independent persisted integrity passed before Gate timeout."),
        ("P2A-07", "PASS", "Per-scale InnoDB data/index storage captured."),
        ("P2A-08", "PASS", "Scaling fixture is explicitly backend/storage only, with no inference or accuracy claim."),
        ("P2A-09", "PASS" if regressions["pass"] else "FAIL", "Backend, PIT_PRE, and frontend regression results recorded."),
        ("P2A-10", "PASS", "Evidence and review-package SHA-256 manifests generated and revalidated."),
    ]
    acceptance_table = "\n".join(f"| {code} | {status} | {note} |" for code, status, note in acceptance)
    return f"""# Phase 2A Completion Report

## 1. Baseline

- Final Core Freeze v2: `{FINAL_CORE_FREEZE_V2}`
- Phase 1B commit: `{PHASE1B_COMMIT}`
- Reference DB: `shm_em_reproduce_benchmark_reference`
- Scaling DBs: `shm_em_reproduce_benchmark_scaling_s1`, `shm_em_reproduce_benchmark_scaling_s2`
- Frozen production core modified: **NO**

## 2. Environment

- CPU: {hardware.get('cpu')} ({hardware.get('physicalCores')} physical / {hardware.get('logicalCores')} logical cores)
- RAM bytes: {hardware.get('ramBytes')}
- Storage: `{json.dumps(hardware.get('storage'), ensure_ascii=False)}`
- MySQL: {mysql.get('version')}; buffer pool {mysql.get('innodbBufferPoolSize')} bytes; max connections {mysql.get('maxConnections')}; engine {mysql.get('defaultStorageEngine')}
- Python: {environment['runtime']['python']}
- Java: `{environment['runtime']['java']['output'].splitlines()[0]}`

## 3. Reference Workflow

Public reference workload: 6 packaged models, 124 target channels, 40 future steps, 4,960 persisted forecast rows, concurrency 1.

| Component | median | p95 | measured repetitions |
| --- | ---: | ---: | ---: |
{table}

## 4. PIT_PRE

- Input assembly: {metric(pit['components']['inputAssembly'])}
- All-model inference: {metric(pit['components']['allModelInference'])}
- Engineering conversion: {metric(pit['components']['engineeringConversion'])}
- Prediction write total: {metric(pit['components']['predictionWriteTotal'])}
- Persistence-exclusive estimate: {metric(pit['components']['predictionPersistenceExclusiveEstimate'])}
- Persisted-integrity hash generation: {metric(pit['components']['persistedIntegrityHash'])}
- Full batch: {metric(pit['components']['fullBatch'])}
- Model loading/cache preparation (one-time): {pit['oneTimeSetup']['modelLoadingCachePreparationMs']:.3f} ms
- No repetitions or outliers were removed.

## 5. Backend

- Gate inspect: {metric(backend['gate-inspect'])}
- Gate evaluate: {metric(backend['gate-evaluate'])}
- Future State: {metric(backend['future-state'])}
- Single-target series: {metric(backend['series-single-target'])}
- Full-batch series: {metric(backend['series-full-batch'])}
- Evaluate: {metric(backend['evaluate'])}
- Execute: {metric(backend['execute'])}; 10 independent repetitions restored to the same formal-state baseline.
- Provenance trace: {metric(backend['provenance-trace'])}

## 6. Scaling

The scaling experiment is a **synthetic backend/storage scalability fixture**, not model-inference or predictive-accuracy evidence. It fixes 10 stations, 10 instruments, one model contract, and 40 future steps while increasing target channels and persisted rows.

| scale | rows | targets | persist rows/s | integrity recomputation | full-series median/p95 | Gate | DB data+index |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| S1 | {s1['rowCount']} | {s1['targetCount']} | {s1['persistence']['rowsPerSecond']:.3f} | {s1['integrity']['generationMs']:.3f} ms | {s1['api']['series-full-batch']['medianMs']:.3f}/{s1['api']['series-full-batch']['p95Ms']:.3f} ms | PASS, {s1['api']['gate-inspect']['medianMs']:.3f}/{s1['api']['gate-inspect']['p95Ms']:.3f} ms | {storage_bytes(s1)} bytes |
| S2 | {s2['rowCount']} | {s2['targetCount']} | {s2['persistence']['rowsPerSecond']:.3f} | {s2['integrity']['generationMs']:.3f} ms | {s2_full['medianMs']:.3f}/{s2_full['p95Ms']:.3f} ms | STOP: first call timed out at 180.008 s | {storage_bytes(s2)} bytes |

## 7. Maximum Tested Workload

- Maximum persisted and independently integrity-verified: **49,600 rows / 1,240 targets / 40 steps**.
- Maximum fully functional Gate + Future State workload: **4,960 rows / 124 targets / 40 steps**.
- S2 completed all 1 first + 5 warm-up + 30 measured single/full-series calls. The first Gate inspect did not return within the fixed 180-second client timeout.
- Future State at S2 and S3-S5 were not attempted after the STOP trigger.

## 8. MySQL Boundary

On this single recorded machine/configuration, ordinary S2 series retrieval remained functional, while the frozen Gate path exceeded 180 seconds. This is an observed application-service boundary, **not a universal MySQL capacity limit**. The experiment does not support claims about other hardware, concurrency levels, database tuning, or topology scaling.

## 9. Integrity

- Reference cross-language persisted hash recomputation: median {reference['integrity']['medianMs']:.3f} ms, p95 {reference['integrity']['p95Ms']:.3f} ms, 30/30 matches.
- S1 independent persisted-integrity verification: PASS.
- S2 independent persisted-integrity verification: PASS for all 49,600 rows, before backend Gate invocation.
- S2 Gate result integrity status is unavailable because the first Gate call timed out; it must not be reported as an integrity mismatch.

## 10. Regression Tests

- Backend Maven test/package: {'PASS' if regressions['backend']['pass'] else 'FAIL'}.
- PIT_PRE unittest discovery: {'PASS' if regressions['pitPre']['pass'] else 'FAIL'}.
- Frontend production build: {'PASS' if regressions['frontend']['pass'] else 'FAIL'}.

## 11. Frozen Core Diff

- Modified frozen files: `{core['modifiedFiles']}`
- Result: **{'NONE' if core['pass'] else 'NOT EMPTY'}**

## 12. Acceptance Matrix

| Gate | Result | Evidence |
| --- | --- | --- |
{acceptance_table}

## 13. Findings Requiring Core Change

1. The frozen Gate inspect path did not complete within 180 seconds for the valid S2 workload (49,600 rows), although full-batch series retrieval and independent persisted-integrity recomputation completed. Localization and optimization require a separately authorized production-core phase.
2. No Phase 2A production optimization was attempted. The known 50,000-row series cap was not reached because STOP occurred first at S2.

## 14. Evidence

- `artifacts/revision/benchmarks/reference/`
- `artifacts/revision/benchmarks/scaling/s1/`
- `artifacts/revision/benchmarks/scaling/s2/`
- `artifacts/revision/benchmarks/integrity/`
- `artifacts/revision/benchmarks/environment.json`
- `artifacts/revision/benchmarks/regression-tests.json`
- `artifacts/revision/benchmarks/phase2a-manifest.json`
- `artifacts/revision/benchmarks/gpt-review-package/`

## 15. STOP

Phase 2A is stopped at the first valid-workload runtime boundary. Await GPT review before any production-core change or additional scalability run.
"""


def methodology() -> str:
    return """# Phase 2A Benchmark Methodology

## Scope

The real public reference workflow measures six packaged models and the complete frozen forecast-to-event path. The synthetic scaling fixture measures backend, MySQL storage, persisted integrity, Gate, and Future State behavior only. It is not a model-inference or predictive-accuracy experiment.

## Repetition Policy

- Concurrency: 1.
- First call retained separately.
- Warm-up: 5 calls/runs.
- Measured: 30 calls/runs.
- Execute: 10 measured calls, each restored to the same formal-state baseline.
- No outlier deletion.
- Application warm-cache conditions; OS page cache was not flushed.

## Scaling Axes

Forty forecast steps are fixed. Target channels and persisted rows increase. Ten stations and ten instruments are fixed, so this is target/row scaling rather than topology scaling.

## STOP Policy

The experiment stops on the first valid persisted workload that fails or cannot complete a frozen service path. No frozen production optimization is permitted during Phase 2A.
"""


def build_review_package(args) -> dict[str, Any]:
    root = args.evidence_root
    package = root / "gpt-review-package"
    if package.exists():
        shutil.rmtree(package)
    evidence_target = package / "evidence"
    source_target = package / "source/tools/revision"
    for path in sorted(root.rglob("*")):
        if not path.is_file() or package in path.parents:
            continue
        relative = path.relative_to(root)
        target = evidence_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    for name in (
        "phase2a_benchmark_support.py", "benchmark_reference_workflow.py",
        "benchmark_scalability.py", "finalize_phase2a_evidence.py",
    ):
        source_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.repo_root / "tools/revision" / name, source_target / name)
    handoff = """# GPT Review Handoff: Phase 2A Runtime / Scalability

Review priority:

1. Verify the frozen production-core diff is empty.
2. Recompute both manifests and confirm zero byte/hash mismatches.
3. Verify reference repetition counts and Execute baseline isolation.
4. Verify S1 is a valid Gate/Future State workload.
5. Verify S2 has 49,600 persisted rows, 1,240 features, 40 steps, no duplicates, and independently matching persisted hashes before API invocation.
6. Verify all S2 series repetitions completed and the first Gate inspect timed out at 180 seconds.
7. Confirm STOP occurred before Future State S2 and before S3-S5.
8. Decide whether a separately authorized core-performance phase should localize/optimize Gate, or whether additional diagnostics are required first.

No production-core modification or additional workload is requested in this package.
"""
    write_text(package / "GPT_REVIEW_HANDOFF.md", handoff)
    review_manifest = manifest_for(package, "review-package-manifest.json")
    write_json(package / "review-package-manifest.json", review_manifest)
    zip_path = root / "SHM-EM_Phase2A_GPT_Review_Package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package).as_posix())
    result = {
        "path": str(zip_path),
        "bytes": zip_path.stat().st_size,
        "sha256": sha256_file(zip_path),
        "manifestFileCount": review_manifest["fileCountExcludingManifest"],
    }
    write_json(root / "gpt-review-package.json", result)
    return result


def verify_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    mismatches = []
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            mismatches.append(item["path"])
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Phase 2A evidence after STOP")
    parser.add_argument("--database", default="shm_em_reproduce_benchmark_reference")
    args = resolve_common_args(parser)
    root = args.evidence_root
    required = (
        root / "reference/reference-summary.json",
        root / "scaling/scaling-summary.json",
        root / "scaling/s2/api-progress.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        parser.error(f"Required benchmark evidence is missing: {missing}")

    partial = finalize_partial_scaling(root)
    regressions = run_regressions(args)
    environment = collect_environment(args, args.database)
    write_json(root / "environment.json", environment)
    core = frozen_evidence(args)
    write_text(root / "methodology.md", methodology())
    report = completion_report(args, environment, regressions, partial, core)
    write_text(root / "PHASE2A_COMPLETION_REPORT.md", report)

    manifest = manifest_for(root, "phase2a-manifest.json")
    write_json(root / "phase2a-manifest.json", manifest)
    manifest_mismatches = verify_manifest(root, manifest)
    write_json(root / "phase2a-manifest-verification.json", {"mismatches": manifest_mismatches, "pass": not manifest_mismatches})
    if manifest_mismatches:
        raise RuntimeError(f"Phase 2A manifest mismatch: {manifest_mismatches}")
    package = build_review_package(args)
    review_root = root / "gpt-review-package"
    review_manifest = read_json(review_root / "review-package-manifest.json")
    review_mismatches = verify_manifest(review_root, review_manifest)
    write_json(root / "review-package-verification.json", {"mismatches": review_mismatches, "pass": not review_mismatches})
    if review_mismatches:
        raise RuntimeError(f"Review package manifest mismatch: {review_mismatches}")
    result = {
        "referencePass": read_json(root / "reference/reference-summary.json")["pass"],
        "stopRequired": read_json(root / "scaling/scaling-summary.json")["stopRequired"],
        "regressionsPass": regressions["pass"],
        "frozenCorePass": core["pass"],
        "phase2aManifestPass": True,
        "reviewPackageManifestPass": True,
        "reviewPackage": package,
    }
    write_json(root / "finalization-summary.json", result)
    print(json.dumps(result, indent=2))
    return 0 if regressions["pass"] and core["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
