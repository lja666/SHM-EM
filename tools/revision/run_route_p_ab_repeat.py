#!/usr/bin/env python3
"""Run the controlled contemporaneous Route P A/B repeat."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time
from typing import Any
import urllib.error
import urllib.request

import psutil

from phase2a_benchmark_support import (
    Backend,
    cleanup_runtime,
    collect_environment,
    resolve_common_args,
    sha256_file,
    summary,
    utc_iso,
    write_json,
    write_text,
)


BASELINE_COMMIT = "84c13fa6081f72b37483b475903c7b22e1a8b92d"
PRODUCTION_FILE = (
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/"
    "service/impl/PredictionExecutionGateServiceImpl.java"
)
REFERENCE_SCHEDULE = (("A", "B"), ("B", "A"), ("A", "B"), ("B", "A"))
SMALL_SCHEDULE = (("A", "B"), ("B", "A"))
WORKLOADS = {
    "reference": {
        "database": "shm_em_reproduce_benchmark_reference",
        "projectId": 1,
        "batchId": 40,
        "rows": 4960,
        "targets": 124,
        "warmups": 3,
        "measured": 15,
    },
    "phase1b": {
        "database": "shm_em_reproduce_phase1b_bridge",
        "projectId": 2,
        "batchId": 5,
        "rows": 1120,
        "targets": 28,
        "warmups": 3,
        "measured": 20,
    },
    "s1": {
        "database": "shm_em_reproduce_benchmark_scaling_s1",
        "projectId": 2,
        "batchId": 5,
        "rows": 4960,
        "targets": 124,
        "warmups": 3,
        "measured": 10,
    },
}


def run_command(command: list[str], cwd: Path, env: dict[str, str], log_path: Path, timeout: int = 600) -> None:
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False,
    )
    write_text(
        log_path,
        f"command: {' '.join(command)}\n"
        f"cwd: {cwd}\n"
        f"elapsedSeconds: {time.perf_counter() - started:.6f}\n"
        f"exitCode: {completed.returncode}\n\n{completed.stdout or ''}",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Build failed; see {log_path}")


def find_jar(backend_root: Path) -> Path:
    jars = sorted(
        (backend_root / "target").glob("*.jar"), key=lambda item: item.stat().st_mtime, reverse=True
    )
    jar = next((item for item in jars if not item.name.endswith(".original")), None)
    if jar is None:
        raise RuntimeError(f"No backend jar found under {backend_root / 'target'}")
    return jar


def build_variants(args, root: Path) -> dict[str, dict[str, Any]]:
    variants_root = args.runtime_root / "variants"
    variants_root.mkdir(parents=True, exist_ok=True)
    worktree = Path(tempfile.mkdtemp(prefix="shm-em-route-p-a-"))
    worktree.rmdir()
    env = os.environ.copy()
    env["JAVA_HOME"] = str(args.java.parent.parent)
    env["PATH"] = str(args.java.parent) + os.pathsep + env.get("PATH", "")
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), BASELINE_COMMIT],
            cwd=args.repo_root, text=True, capture_output=True, check=True,
        )
        backend_a = worktree / "src/backend"
        run_command(
            [str(args.maven), "-q", "-DskipTests", "clean", "package"],
            backend_a, env, root / "build-baseline-a.log",
        )
        jar_a = variants_root / "baseline-A.jar"
        shutil.copy2(find_jar(backend_a), jar_a)

        backend_b = args.repo_root / "src/backend"
        run_command(
            [str(args.maven), "-q", "-DskipTests", "clean", "package"],
            backend_b, env, root / "build-routeP-b.log",
        )
        jar_b = variants_root / "routeP-B.jar"
        shutil.copy2(find_jar(backend_b), jar_b)

        current_diff = subprocess.run(
            ["git", "diff", "--", PRODUCTION_FILE], cwd=args.repo_root,
            text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
        ).stdout
        production_names = subprocess.run(
            ["git", "diff", "--name-only", "--", "src/backend/src/main", "src/frontend", "src/pit_pre/pit_pre"],
            cwd=args.repo_root, text=True, capture_output=True, check=True,
        ).stdout.splitlines()
        if production_names != [PRODUCTION_FILE] or current_diff.count(
                "resultQuery.setProjectId(batch.getProjectId());") != 1:
            raise RuntimeError("Variant B production diff is not the authorized one-line Route P correction")
        variants = {
            "A": {
                "name": "Baseline",
                "commit": BASELINE_COMMIT,
                "routePAssignmentPresent": False,
                "jarPath": str(jar_a),
                "jarBytes": jar_a.stat().st_size,
                "jarSha256": sha256_file(jar_a),
            },
            "B": {
                "name": "Route P",
                "commit": None,
                "head": subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=args.repo_root, text=True,
                    capture_output=True, check=True,
                ).stdout.strip(),
                "routePAssignmentPresent": True,
                "productionFixCommitted": False,
                "productionDiff": current_diff.splitlines(),
                "jarPath": str(jar_b),
                "jarBytes": jar_b.stat().st_size,
                "jarSha256": sha256_file(jar_b),
            },
        }
        write_json(root / "variant-a.json", variants["A"])
        write_json(root / "variant-b.json", variants["B"])
        return variants
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=args.repo_root, text=True, capture_output=True, check=False,
        )
        shutil.rmtree(worktree, ignore_errors=True)


def raw_gate(port: int, batch_id: int) -> tuple[float, int, dict[str, Any]]:
    path = f"/api/em/predictions/batches/{batch_id}/execution-gate?mode=REPRODUCTION"
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    started = time.perf_counter_ns()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
            return (time.perf_counter_ns() - started) / 1_000_000, response.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"code": exc.code, "message": raw, "data": None}
        return (time.perf_counter_ns() - started) / 1_000_000, exc.code, body


def gate_signature(gate: dict[str, Any]) -> str:
    fields = (
        "batchId", "projectId", "expectedModelCount", "actualModelCount", "successfulModelCount",
        "expectedFeatureCount", "actualFeatureCount", "expectedPointCount", "actualPointCount",
        "missingPointCount", "invalidTimestampCount", "qualityIssueCount", "modelSetValid",
        "featureSetValid", "timelineValid", "qualityValid", "artifactHashValid",
        "resultIntegrityValid", "freshnessValid", "executionEligible", "issues",
    )
    value = {field: gate.get(field) for field in fields}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def run_process(args, root: Path, workload_name: str, workload: dict[str, Any], variant: str,
                block: int, order: int, jar: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    args.backend_jar = jar
    runtime = args.runtime_root / f"{workload_name}-block-{block}-{order}-{variant}"
    backend = Backend(args, workload["database"], args.backend_port, runtime)
    startup_started = time.perf_counter_ns()
    backend.start()
    startup_ms = (time.perf_counter_ns() - startup_started) / 1_000_000
    pid = int(backend.process.pid)
    process = psutil.Process(pid)
    rss_before = int(process.memory_info().rss)
    calls = []
    first_request_ms = None
    started_at = utc_iso()
    try:
        for phase, count in (("warmup", workload["warmups"]), ("measured", workload["measured"])):
            for repetition in range(1, count + 1):
                timestamp = utc_iso()
                elapsed_ms, http_status, body = raw_gate(args.backend_port, workload["batchId"])
                if first_request_ms is None:
                    first_request_ms = elapsed_ms
                gate = body.get("data") if isinstance(body, dict) else None
                gate = gate if isinstance(gate, dict) else {}
                functional = (
                    body.get("code") == 0
                    and gate.get("actualPointCount") == workload["rows"]
                    and gate.get("resultIntegrityValid") is True
                    and gate.get("executionEligible") is True
                )
                calls.append(
                    {
                        "workload": workload_name,
                        "variant": variant,
                        "block": block,
                        "order": order,
                        "phase": phase,
                        "repetition": repetition,
                        "elapsedMs": round(elapsed_ms, 6),
                        "httpStatus": http_status,
                        "resultIntegrityValid": gate.get("resultIntegrityValid"),
                        "executionEligible": gate.get("executionEligible"),
                        "actualPointCount": gate.get("actualPointCount"),
                        "functionalValid": functional,
                        "gateSignature": gate_signature(gate) if gate else None,
                        "jvmPid": pid,
                        "timestamp": timestamp,
                    }
                )
                if not functional:
                    raise RuntimeError(
                        f"Functional Gate failure in {workload_name} block {block} variant {variant}: {body}"
                    )
        rss_after = int(process.memory_info().rss)
        process_summary = {
            "workload": workload_name,
            "variant": variant,
            "block": block,
            "order": order,
            "jvmPid": pid,
            "startedAt": started_at,
            "startupMs": round(startup_ms, 6),
            "firstRequestMs": round(float(first_request_ms), 6),
            "rssBeforeBytes": rss_before,
            "rssAfterBytes": rss_after,
            "backendLog": str(backend.stdout_path),
        }
        return calls, process_summary
    finally:
        backend.stop()
        time.sleep(0.5)


def write_raw(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "workload", "variant", "block", "order", "phase", "repetition", "elapsedMs",
        "httpStatus", "resultIntegrityValid", "executionEligible", "actualPointCount",
        "functionalValid", "gateSignature", "jvmPid", "timestamp",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def workload_summary(workload_name: str, rows: list[dict[str, Any]], processes: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if row["phase"] == "measured"]
    variants = {}
    for variant in ("A", "B"):
        selected = [row for row in measured if row["variant"] == variant]
        variants[variant] = {
            "measuredCalls": len(selected),
            "latency": summary([float(row["elapsedMs"]) for row in selected]),
            "allFunctionalValid": all(row["functionalValid"] for row in selected),
            "gateSignatures": sorted({row["gateSignature"] for row in selected}),
        }
    blocks = []
    for block in sorted({int(row["block"]) for row in measured}):
        values = {}
        for variant in ("A", "B"):
            selected = [float(row["elapsedMs"]) for row in measured
                        if row["block"] == block and row["variant"] == variant]
            values[variant] = statistics.median(selected)
        blocks.append(
            {
                "block": block,
                "medianAms": round(values["A"], 6),
                "medianBms": round(values["B"], 6),
                "medianRatioBA": round(values["B"] / values["A"], 6),
            }
        )
    median_a = variants["A"]["latency"]["medianMs"]
    median_b = variants["B"]["latency"]["medianMs"]
    p95_a = variants["A"]["latency"]["p95Ms"]
    p95_b = variants["B"]["latency"]["p95Ms"]
    functional_equivalence = (
        variants["A"]["allFunctionalValid"]
        and variants["B"]["allFunctionalValid"]
        and variants["A"]["gateSignatures"] == variants["B"]["gateSignatures"]
    )
    return {
        "schemaVersion": "shm-em-phase2a2r-ab-summary-v1",
        "workload": workload_name,
        "variants": variants,
        "pairedBlocks": blocks,
        "pooledMedianRatioBA": round(median_b / median_a, 6),
        "pooledP95RatioBA": round(p95_b / p95_a, 6),
        "absoluteMedianDeltaMs": round(median_b - median_a, 6),
        "functionalEquivalence": functional_equivalence,
        "processes": processes,
    }


def run_workload(args, root: Path, variants: dict[str, dict[str, Any]], workload_name: str,
                 schedule: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    workload = WORKLOADS[workload_name]
    rows = []
    processes = []
    for block, order_values in enumerate(schedule, start=1):
        for order, variant in enumerate(order_values, start=1):
            print(f"[{workload_name}] block {block}/{len(schedule)} order {order}: variant {variant}", flush=True)
            calls, process_summary = run_process(
                args, root, workload_name, workload, variant, block, order,
                Path(variants[variant]["jarPath"]),
            )
            rows.extend(calls)
            processes.append(process_summary)
            write_raw(root / f"{workload_name}-ab-raw.csv", rows)
            write_json(root / f"{workload_name}-processes.json", processes)
    result = workload_summary(workload_name, rows, processes)
    write_json(root / f"{workload_name}-ab-summary.json", result)
    return result


def decide(reference: dict[str, Any], phase1b: dict[str, Any], s1: dict[str, Any]) -> dict[str, Any]:
    ratio = float(reference["pooledMedianRatioBA"])
    delta = float(reference["absoluteMedianDeltaMs"])
    blocks_under_120 = sum(1 for item in reference["pairedBlocks"] if item["medianRatioBA"] <= 1.20)
    blocks_b_slower = sum(1 for item in reference["pairedBlocks"] if item["medianRatioBA"] > 1.0)
    if ratio <= 1.15 and reference["functionalEquivalence"]:
        reference_decision = "PASS"
    elif ratio <= 1.25 and blocks_under_120 >= 3 and delta < 100 and reference["functionalEquivalence"]:
        reference_decision = "PASS_SMALL_REFERENCE_OVERHEAD"
    elif ratio > 1.25 and blocks_b_slower >= 3:
        reference_decision = "FAIL"
    else:
        reference_decision = "REVIEW_REQUIRED"
    phase1b_b = phase1b["variants"]["B"]
    phase1b_guardrail = (
        phase1b["functionalEquivalence"]
        and phase1b_b["latency"]["medianMs"] < 2000
        and phase1b_b["latency"]["p95Ms"] < 3000
    )
    overall_pass = reference_decision.startswith("PASS") and phase1b_guardrail
    return {
        "schemaVersion": "shm-em-phase2a2r-decision-v1",
        "referenceDecision": reference_decision,
        "referenceRatioBA": ratio,
        "referenceAbsoluteMedianDeltaMs": delta,
        "referenceBlocksAtOrBelow1_20": blocks_under_120,
        "referenceBlocksBSlower": blocks_b_slower,
        "phase1bGuardrailPass": phase1b_guardrail,
        "phase1bRoutePMedianMs": phase1b_b["latency"]["medianMs"],
        "phase1bRoutePP95Ms": phase1b_b["latency"]["p95Ms"],
        "phase1bRatioBA": phase1b["pooledMedianRatioBA"],
        "s1SanityRatioBA": s1["pooledMedianRatioBA"],
        "pass": overall_pass,
        "next": "CONTINUE_PHASE2A2" if overall_pass else "STOP_FOR_GPT_REVIEW",
        "productionFixCommitted": False,
    }


def build_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or path.name == "manifest.json" or "gpt-review-package" in relative.parts:
            continue
        files.append(
            {"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    return {
        "schemaVersion": "shm-em-phase2a2r-manifest-v1",
        "generatedAt": utc_iso(),
        "files": files,
        "fileCountExcludingManifest": len(files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled Route P A/B repeat")
    parser.add_argument("--backend-port", type=int, default=5199)
    args = resolve_common_args(parser)
    root = args.repo_root / "artifacts/revision/benchmarks/route-p-repeat"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    write_text(
        root / "methodology.md",
        "# Phase 2A.2R Controlled Contemporaneous A/B Repeat\n\n"
        "- Variant A: clean detached worktree at `84c13fa6081f72b37483b475903c7b22e1a8b92d`.\n"
        "- Variant B: current uncommitted Route P working tree with exactly one production assignment.\n"
        "- Reference order: A-B, B-A, A-B, B-A; each fresh process uses 3 warmups and 15 measured calls.\n"
        "- Phase 1B and S1 order: A-B, B-A; fresh process for every variant/block.\n"
        "- Same JDK, Maven, MySQL server, database snapshot, machine, JVM profile, and Gate endpoint.\n",
    )
    try:
        variants = build_variants(args, root)
        environment = collect_environment(args, WORKLOADS["reference"]["database"])
        environment["baselineCommit"] = BASELINE_COMMIT
        environment["variantJarSha256"] = {
            key: value["jarSha256"] for key, value in variants.items()
        }
        write_json(root / "environment.json", environment)

        reference = run_workload(args, root, variants, "reference", REFERENCE_SCHEDULE)
        phase1b = run_workload(args, root, variants, "phase1b", SMALL_SCHEDULE)
        s1 = run_workload(args, root, variants, "s1", SMALL_SCHEDULE)
        decision = decide(reference, phase1b, s1)
        write_json(root / "decision.json", decision)
        write_json(root / "manifest.json", build_manifest(root))
        print(json.dumps(decision, indent=2))
        return 0 if decision["pass"] else 2
    finally:
        cleanup_runtime(args)


if __name__ == "__main__":
    raise SystemExit(main())
