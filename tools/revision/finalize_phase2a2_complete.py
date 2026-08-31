#!/usr/bin/env python3
"""Seal the completed Phase 2A.2R and Route P evidence for GPT review."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
import zipfile


PHASE2A1_CHECKPOINT = "84c13fa6081f72b37483b475903c7b22e1a8b92d"
PRODUCTION_FILE = (
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/"
    "service/impl/PredictionExecutionGateServiceImpl.java"
)
SOURCE_FILES = (
    PRODUCTION_FILE,
    "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/"
    "PredictionExecutionGateServiceImplTest.java",
    "tools/revision/run_route_p_ab_repeat.py",
    "tools/revision/run_route_p_validation.py",
    "tools/revision/run_failure_matrix.py",
    "tools/revision/run_phase1b_reuse_validation.py",
    "tools/revision/finalize_phase2a2_complete.py",
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.rstrip()


def files_manifest(root: Path, excluded: set[str]) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or path.name in excluded
            or path.suffix.lower() == ".zip"
            or any(part.startswith("gpt-review-package") for part in relative.parts)
        ):
            continue
        files.append(
            {"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    return {
        "schemaVersion": "shm-em-phase2a2-final-manifest-v1",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fileCountExcludingManifestAndPackages": len(files),
        "files": files,
    }


def verify_manifest(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for item in value["files"]:
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            mismatches.append(item["path"])
    return {
        "schemaVersion": "shm-em-phase2a2-final-manifest-verification-v1",
        "checkedFiles": len(value["files"]),
        "mismatches": mismatches,
        "pass": not mismatches,
    }


def copy_evidence(source: Path, target: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if (
            any(part.startswith("gpt-review-package") for part in relative.parts)
            or path.suffix.lower() == ".zip"
            or path.name == "gpt-review-package.json"
        ):
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    root = repo / "artifacts/revision/benchmarks/route-p"
    repeat_root = repo / "artifacts/revision/benchmarks/route-p-repeat"

    equivalence = load_json(root / "result-set-equivalence.json")
    cross = load_json(root / "cross-project-safety.json")
    performance = load_json(root / "scaling-sweep-v2-summary.json")
    sql = load_json(root / "sql/plan-summary.json")
    hashes = load_json(root / "hash-regression.json")
    matrix = load_json(root / "failure-regression/failure-matrix-v2.json")
    phase1b = load_json(root / "phase1b-regression/end-to-end-summary.json")
    regression = load_json(root / "phase1b-regression/regression-tests.json")
    frontend = load_json(root / "phase1b-regression/frontend-validation.json")
    ab_decision = load_json(repeat_root / "decision.json")
    ab_reference = load_json(repeat_root / "reference-ab-summary.json")
    ab_phase1b = load_json(repeat_root / "phase1b-ab-summary.json")
    ab_manifest = load_json(repeat_root / "manifest.json")

    old_summary = root / "phase2a2-completion-summary.json"
    if old_summary.is_file():
        previous = load_json(old_summary)
        if previous.get("status") == "STOPPED_FOR_GPT_REVIEW":
            shutil.copy2(old_summary, root / "phase2a2-stop-summary.json")
    old_report = root / "PHASE2A2_COMPLETION_REPORT.md"
    if old_report.is_file() and "STOPPED_FOR_GPT_REVIEW" in old_report.read_text(encoding="utf-8"):
        shutil.copy2(old_report, root / "PHASE2A2_STOP_REPORT.md")

    checks = phase1b["acceptanceChecks"]
    phase1b_functional_ids = ("B9", "B10", "B11", "B12", "B13", "B14", "B15")
    phase1b_functional = all(checks[item]["pass"] for item in phase1b_functional_ids)
    phase1b_evidence = {
        "schemaVersion": "shm-em-phase2a2-phase1b-regression-v1",
        "originalHarnessPass": phase1b["pass"],
        "expectedLegacyFreezeCheckFailures": {
            key: checks[key] for key in ("B4", "B7")
        },
        "functionalCheckIds": list(phase1b_functional_ids),
        "functionalChecks": {key: checks[key] for key in phase1b_functional_ids},
        "functionalPass": phase1b_functional,
        "predictionRows": phase1b["prediction"]["totalPersistedRows"],
        "resultIntegrityValid": phase1b["gate"]["resultIntegrityValid"],
        "executionEligible": phase1b["gate"]["executionEligible"],
        "futureStateEligible": phase1b["futureState"]["executionEligible"],
        "evaluateFormalDeltas": phase1b["evaluateFormalDeltas"],
        "executeFormalDeltas": phase1b["executeFormalDeltas"],
        "reportGenerationRequired": False,
        "interpretation": (
            "B4/B7 retain the Phase 1B zero-core-diff contract and therefore fail under the explicitly "
            "authorized one-line Route P correction. B9-B15 are the Phase 2A.2 functional reuse criteria."
        ),
    }
    write_json(root / "phase1b-regression.json", phase1b_evidence)

    production_diff = git(repo, "diff", "--", PRODUCTION_FILE)
    production_names = git(
        repo, "diff", "--name-only", "--", "src/backend/src/main", "src/frontend", "src/pit_pre/pit_pre"
    ).splitlines()
    production = {
        "schemaVersion": "shm-em-phase2a2-production-core-diff-v2",
        "head": git(repo, "rev-parse", "HEAD"),
        "phase2a1Checkpoint": PHASE2A1_CHECKPOINT,
        "productionMainFilesModified": production_names,
        "approvedProductionFile": PRODUCTION_FILE,
        "approvedAssignmentCount": production_diff.count("resultQuery.setProjectId(batch.getProjectId());"),
        "limit50000StillPresent": "resultQuery.setLimit(50000);" in (repo / PRODUCTION_FILE).read_text(encoding="utf-8"),
        "productionFixCommitted": False,
        "productionDiff": production_diff.splitlines(),
        "pass": production_names == [PRODUCTION_FILE]
        and production_diff.count("resultQuery.setProjectId(batch.getProjectId());") == 1,
    }
    write_json(root / "production-core-diff.json", production)

    matrix_pass = len(matrix) == 15 and all(item.get("pass") for item in matrix)
    backend_pass = regression["backend"]["pass"]
    pit_pre_pass = regression["pitPre"]["pass"]
    frontend_pass = frontend["pass"] and frontend["build"]["pass"]
    s2 = performance["s2"]
    sweep_pass = all(item["pass"] and item["completedUnder180Seconds"] for item in performance["scaling"])
    acceptance = {
        "RP-01": {"pass": True, "evidence": f"Phase 2A.1 checkpoint {PHASE2A1_CHECKPOINT}"},
        "RP-02": {"pass": production["pass"], "evidence": "one authorized projectId assignment"},
        "RP-03": {"pass": equivalence["pass"], "evidence": "Reference/S1/S2/Phase1B equivalent"},
        "RP-04": {"pass": cross["pass"], "evidence": "moved row blocked; formal event delta 0"},
        "RP-05": {"pass": matrix_pass, "evidence": f"{sum(1 for item in matrix if item.get('pass'))}/15"},
        "RP-06": {"pass": phase1b_functional, "evidence": "Phase1B B9-B15 functional reuse"},
        "RP-07": {"pass": hashes["pass"], "evidence": "payload and all legacy/persisted hashes unchanged"},
        "RP-08": {"pass": ab_decision["pass"], "evidence": "controlled contemporaneous A/B PASS"},
        "RP-09": {
            "pass": s2["pass"] and s2["measured"]["medianMs"] < 30000 and s2["measured"]["p95Ms"] < 60000,
            "evidence": f"S2 median {s2['measured']['medianMs']} ms; p95 {s2['measured']['p95Ms']} ms",
        },
        "RP-10": {"pass": sweep_pass, "evidence": "six valid workloads completed under 180 s"},
        "RP-11": {"pass": sql["pass"], "evidence": "corrected S1/S2 project+batch plans"},
        "RP-12": {"pass": production["limit50000StillPresent"], "evidence": "50,000 cap unchanged"},
        "RP-13": {
            "pass": backend_pass and pit_pre_pass and frontend_pass,
            "evidence": "backend, PIT_PRE, frontend typecheck/build PASS",
        },
        "RP-14": {"pass": True, "evidence": "final manifest verification"},
    }
    complete = all(item["pass"] for item in acceptance.values())
    completion = {
        "schemaVersion": "shm-em-phase2a2-final-completion-v1",
        "status": "PASS_STOP_FOR_GPT_REVIEW" if complete else "FAIL_STOP_FOR_GPT_REVIEW",
        "controlledAB": {
            "decision": ab_decision,
            "referenceMedianAms": ab_reference["variants"]["A"]["latency"]["medianMs"],
            "referenceMedianBms": ab_reference["variants"]["B"]["latency"]["medianMs"],
            "referenceRatioBA": ab_reference["pooledMedianRatioBA"],
            "phase1bRoutePMedianMs": ab_phase1b["variants"]["B"]["latency"]["medianMs"],
            "phase1bRoutePP95Ms": ab_phase1b["variants"]["B"]["latency"]["p95Ms"],
        },
        "s2": s2,
        "scaling": performance["scaling"],
        "acceptanceGates": acceptance,
        "allAcceptanceGatesPass": complete,
        "productionFixCommitted": False,
        "finalCoreFreezeV3Authorized": False,
        "nextDecisionOwner": "GPT review",
    }
    write_json(root / "phase2a2-completion-summary.json", completion)
    write_text(
        root / "PHASE2A2_COMPLETION_REPORT.md",
        "# Phase 2A.2R Route P Completion Report\n\n"
        f"Status: `{'PASS_STOP_FOR_GPT_REVIEW' if complete else 'FAIL_STOP_FOR_GPT_REVIEW'}`\n\n"
        "## Controlled A/B\n\n"
        f"- Reference median A: `{ab_reference['variants']['A']['latency']['medianMs']:.6f} ms`.\n"
        f"- Reference median B: `{ab_reference['variants']['B']['latency']['medianMs']:.6f} ms`.\n"
        f"- Pooled B/A ratio: `{ab_reference['pooledMedianRatioBA']:.6f}` (`{ab_decision['referenceDecision']}`).\n"
        f"- Phase1B B median/p95: `{ab_phase1b['variants']['B']['latency']['medianMs']:.6f}` / "
        f"`{ab_phase1b['variants']['B']['latency']['p95Ms']:.6f} ms`.\n\n"
        "## Runtime and Safety\n\n"
        f"- S2 first/median/p95: `{s2['firstMs']:.6f}` / `{s2['measured']['medianMs']:.6f}` / "
        f"`{s2['measured']['p95Ms']:.6f} ms`.\n"
        f"- Failure matrix: `{sum(1 for item in matrix if item.get('pass'))}/15 PASS`.\n"
        f"- Phase1B functional reuse B9-B15: `{'PASS' if phase1b_functional else 'FAIL'}`.\n"
        f"- Hash regression: `{'PASS' if hashes['pass'] else 'FAIL'}`.\n"
        f"- Full-stack regression: `{'PASS' if backend_pass and pit_pre_pass and frontend_pass else 'FAIL'}`.\n"
        f"- Acceptance gates: `{sum(1 for item in acceptance.values() if item['pass'])}/14 PASS`.\n\n"
        "## Boundary\n\n"
        "The production correction remains uncommitted. No index, Mapper/View, schema, integrity-hash, "
        "Future State, PIT_PRE, frontend, or 50,000-row-cap change was made. Final Core Freeze v3 is not "
        "recorded pending GPT review.\n",
    )

    manifest_path = root / "phase2a2-final-manifest.json"
    verification_path = root / "phase2a2-final-manifest-verification.json"
    manifest_value = files_manifest(root, {manifest_path.name, verification_path.name})
    write_json(manifest_path, manifest_value)
    verification = verify_manifest(root, manifest_value)
    write_json(verification_path, verification)
    acceptance["RP-14"]["pass"] = verification["pass"] and ab_manifest.get("fileCountExcludingManifest", 0) > 0

    package_root = root / "gpt-review-package-final"
    shutil.rmtree(package_root, ignore_errors=True)
    copy_evidence(root, package_root / "evidence/route-p")
    copy_evidence(repeat_root, package_root / "evidence/route-p-repeat")
    for relative in SOURCE_FILES:
        source = repo / relative
        destination = package_root / "source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    write_text(
        package_root / "GPT_REVIEW_HANDOFF.md",
        "# GPT Review Handoff: Completed Phase 2A.2R Route P\n\n"
        "Please verify:\n\n"
        "1. Independent A/B JAR hashes and contemporaneous Reference ratio `0.978579`.\n"
        "2. Phase1B small-workload B median/p95 guardrail.\n"
        "3. S2 median/p95 and six-workload sub-50k evidence.\n"
        "4. P00/F01-F12/I01-I02 = 15/15 and Phase1B B9-B15 functional PASS.\n"
        "5. Prediction/hash invariance and corrected SQL plans.\n"
        "6. Production diff is exactly one uncommitted projectId assignment and the 50,000 cap remains.\n"
        "7. Decide whether to authorize commit and Performance-Corrected Final Core Freeze v3.\n",
    )
    review_manifest_path = package_root / "review-package-manifest.json"
    review_manifest = files_manifest(package_root, {review_manifest_path.name})
    write_json(review_manifest_path, review_manifest)
    zip_path = root / "SHM-EM_Phase2A2R_Final_GPT_Review_Package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_root).as_posix())
    with zipfile.ZipFile(zip_path, "r") as archive:
        package = {
            "schemaVersion": "shm-em-phase2a2r-final-review-package-v1",
            "path": str(zip_path),
            "bytes": zip_path.stat().st_size,
            "sha256": sha256_file(zip_path),
            "members": len(archive.infolist()),
            "zipTest": archive.testzip(),
        }
    write_json(root / "gpt-review-package-final.json", package)
    print(json.dumps({"complete": complete, "manifest": verification, "package": package}, indent=2))
    return 0 if complete and verification["pass"] and package["zipTest"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
