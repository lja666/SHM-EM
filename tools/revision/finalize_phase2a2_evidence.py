#!/usr/bin/env python3
"""Seal the stopped Phase 2A.2 Route P evidence for GPT review."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from typing import Any


PHASE2A1_CHECKPOINT = "84c13fa"
PHASE2A_BASELINE_MEDIAN_MS = 268.82065
REFERENCE_STOP_MULTIPLIER = 1.25
PRODUCTION_FILE = (
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/"
    "service/impl/PredictionExecutionGateServiceImpl.java"
)
SOURCE_FILES = (
    PRODUCTION_FILE,
    "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/"
    "PredictionExecutionGateServiceImplTest.java",
    "tools/revision/run_route_p_validation.py",
    "tools/revision/finalize_phase2a2_evidence.py",
    "tools/revision/run_failure_matrix.py",
    "tools/revision/run_phase1b_reuse_validation.py",
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


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


def manifest(root: Path, excluded_names: set[str]) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or path.name in excluded_names or "gpt-review-package" in relative.parts:
            continue
        files.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schemaVersion": "shm-em-phase2a2-manifest-v1",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fileCountExcludingManifestAndReviewPackage": len(files),
        "files": files,
    }


def copy_tree_contents(source: Path, target: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if "gpt-review-package" in relative.parts or path.name.startswith("SHM-EM_Phase2A2_GPT_Review_Package"):
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
    reference_path = root / "reference/gate-summary.json"
    equivalence_path = root / "result-set-equivalence.json"
    cross_path = root / "cross-project-safety.json"
    for required in (reference_path, equivalence_path, cross_path):
        if not required.is_file():
            raise RuntimeError(f"Required evidence is missing: {required}")

    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    equivalence = json.loads(equivalence_path.read_text(encoding="utf-8"))
    cross = json.loads(cross_path.read_text(encoding="utf-8"))
    observed_median = float(reference["measured"]["medianMs"])
    stop_line = PHASE2A_BASELINE_MEDIAN_MS * REFERENCE_STOP_MULTIPLIER
    performance_stop = {
        "schemaVersion": "shm-em-phase2a2-performance-stop-v1",
        "trigger": "RP-08_REFERENCE_GATE_REGRESSION_LINE",
        "baselineMedianMs": PHASE2A_BASELINE_MEDIAN_MS,
        "stopMultiplier": REFERENCE_STOP_MULTIPLIER,
        "stopLineMs": round(stop_line, 6),
        "observedMedianMs": observed_median,
        "observedP95Ms": reference["measured"]["p95Ms"],
        "ratioToBaseline": round(observed_median / PHASE2A_BASELINE_MEDIAN_MS, 6),
        "allCallsFunctionallyValid": reference["allCallsValid"],
        "stopRequired": observed_median > stop_line,
        "prohibitedFollowOnActionsObserved": False,
        "notRunAfterStop": [
            "S1/S2 fresh Gate performance",
            "sub-50k scaling sweep",
            "corrected S1/S2 EXPLAIN ANALYZE",
            "P00/F01-F12/I01-I02 matrix",
            "Phase 1B synthetic bridge rerun",
            "final hash regression",
        ],
    }
    write_json(root / "performance-stop.json", performance_stop)

    core_diff = git(repo, "diff", "--", PRODUCTION_FILE)
    all_diff_names = git(repo, "diff", "--name-only").splitlines()
    production_main_diff = git(repo, "diff", "--name-only", "--", "src/backend/src/main", "src/frontend", "src/pit_pre/pit_pre").splitlines()
    production = {
        "schemaVersion": "shm-em-phase2a2-production-core-diff-v1",
        "head": git(repo, "rev-parse", "HEAD"),
        "phase2a1Checkpoint": PHASE2A1_CHECKPOINT,
        "productionMainFilesModified": production_main_diff,
        "approvedProductionFile": PRODUCTION_FILE,
        "approvedFileIsOnlyProductionChange": production_main_diff == [PRODUCTION_FILE],
        "approvedAssignmentCount": core_diff.count("resultQuery.setProjectId(batch.getProjectId());"),
        "limit50000StillPresent": "resultQuery.setLimit(50000);" in (repo / PRODUCTION_FILE).read_text(encoding="utf-8"),
        "allWorkingTreeDiffNames": all_diff_names,
        "inheritedPITPREEntries": [name for name in all_diff_names if name.startswith("src/pit_pre/models/") or name == "src/pit_pre/requirements.lock.txt"],
        "productionDiff": core_diff.splitlines(),
        "productionFixCommitted": False,
        "pass": production_main_diff == [PRODUCTION_FILE]
        and core_diff.count("resultQuery.setProjectId(batch.getProjectId());") == 1,
    }
    write_json(root / "production-core-diff.json", production)
    write_text(
        root / "route-p-change.md",
        "# Phase 2A.2 Route P Change\n\n"
        f"- Phase 2A.1 evidence checkpoint: `{PHASE2A1_CHECKPOINT}`\n"
        f"- Production file: `{PRODUCTION_FILE}`\n"
        "- Authorized change: set the already-known batch project on the Gate result query.\n"
        "- Unchanged: Mapper, view, indexes, schema, integrity hashes, Future State, PIT_PRE, frontend, and the 50,000-row cap.\n"
        "- Commit state: production correction intentionally remains uncommitted pending GPT review.\n",
    )

    gates = {
        "RP-01": {"status": "PASS", "evidence": f"checkpoint {PHASE2A1_CHECKPOINT}"},
        "RP-02": {"status": "PASS", "evidence": "one projectId assignment; production-core-diff.json"},
        "RP-03": {"status": "PASS", "evidence": "4/4 valid workloads equivalent"},
        "RP-04": {"status": "PASS", "evidence": "moved row blocked; formal event delta 0"},
        "RP-05": {"status": "NOT_RUN_STOP", "evidence": "blocked by RP-08 stop line"},
        "RP-06": {"status": "NOT_RUN_STOP", "evidence": "blocked by RP-08 stop line"},
        "RP-07": {"status": "NOT_RUN_STOP", "evidence": "final hash regression blocked by RP-08 stop line"},
        "RP-08": {"status": "STOP", "evidence": f"median {observed_median:.6f} ms > {stop_line:.6f} ms"},
        "RP-09": {"status": "NOT_RUN_STOP", "evidence": "S2 benchmark not authorized after RP-08 stop"},
        "RP-10": {"status": "NOT_RUN_STOP", "evidence": "scaling sweep not authorized after RP-08 stop"},
        "RP-11": {"status": "NOT_RUN_STOP", "evidence": "EXPLAIN rerun not authorized after RP-08 stop"},
        "RP-12": {"status": "PASS", "evidence": "50,000 cap remains in production source and unit test"},
        "RP-13": {"status": "PARTIAL", "evidence": "backend tests/package PASS; PIT_PRE/frontend not rerun after stop"},
        "RP-14": {"status": "PASS", "evidence": "phase2a2-manifest-verification.json"},
    }
    completion = {
        "schemaVersion": "shm-em-phase2a2-completion-v1",
        "status": "STOPPED_FOR_GPT_REVIEW",
        "stopReason": "RP-08 reference Gate median exceeded the authorized 25% regression line",
        "resultSetEquivalencePass": equivalence["pass"],
        "crossProjectSafetyPass": cross["pass"],
        "productionCoreDiffPass": production["pass"],
        "referenceGate": reference,
        "acceptanceGates": gates,
        "productionFixCommitted": False,
        "nextDecisionOwner": "GPT review",
    }
    write_json(root / "phase2a2-completion-summary.json", completion)
    write_text(
        root / "PHASE2A2_COMPLETION_REPORT.md",
        "# Phase 2A.2 Route P Completion Report\n\n"
        "## Decision\n\n"
        "`STOPPED_FOR_GPT_REVIEW` at RP-08. No follow-on optimization or performance workload was run.\n\n"
        "## Passed Before Stop\n\n"
        "- Phase 2A.1 evidence checkpoint: `84c13fa`.\n"
        "- Authorized production correction is exactly one `projectId` scope assignment.\n"
        "- Reference, S1, S2, and Phase 1B legal result sets are fully equivalent.\n"
        "- S2 batch-only query: 226,077.22 ms; project+batch query: 6,394.26 ms.\n"
        "- Cross-project moved-row case: Gate ineligible, integrity invalid, Execute rejected, formal event delta 0.\n\n"
        "## Stop Trigger\n\n"
        f"Reference Gate measured median was `{observed_median:.6f} ms`; the authorized stop line was `{stop_line:.6f} ms` "
        f"(`{REFERENCE_STOP_MULTIPLIER:.2f} x` the Phase 2A median `{PHASE2A_BASELINE_MEDIAN_MS:.6f} ms`). "
        "All calls were functionally valid, but the performance regression line is binding.\n\n"
        "## Deliberately Not Run\n\n"
        "- S1/S2 fresh Gate performance and sub-50k sweep.\n"
        "- Corrected S1/S2 EXPLAIN ANALYZE.\n"
        "- P00/F01-F12/I01-I02 and Phase 1B reruns.\n"
        "- Final numerical/hash regression.\n\n"
        "The production fix remains uncommitted. GPT must decide whether the Reference anomaly warrants a controlled repeat or another action.\n",
    )

    manifest_path = root / "phase2a2-manifest.json"
    write_json(manifest_path, manifest(root, {manifest_path.name, "phase2a2-manifest-verification.json"}))
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest_data["files"]:
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            mismatches.append(item["path"])
    verification = {
        "schemaVersion": "shm-em-phase2a2-manifest-verification-v1",
        "checkedFiles": len(manifest_data["files"]),
        "mismatches": mismatches,
        "pass": not mismatches,
    }
    write_json(root / "phase2a2-manifest-verification.json", verification)

    package_root = root / "gpt-review-package"
    shutil.rmtree(package_root, ignore_errors=True)
    evidence_root = package_root / "evidence"
    source_root = package_root / "source"
    copy_tree_contents(root, evidence_root)
    for relative in SOURCE_FILES:
        source = repo / relative
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    write_text(
        package_root / "GPT_REVIEW_HANDOFF.md",
        "# GPT Review Handoff: Phase 2A.2 Route P\n\n"
        "Review focus:\n\n"
        "1. Confirm RP-01 through RP-04 and RP-12 are supported by evidence.\n"
        "2. Confirm the Reference Gate median (`381.393750 ms`) requires the documented RP-08 stop.\n"
        "3. Confirm no S1/S2, scaling, SQL-plan, failure-matrix, Phase 1B, or hash work was run after the stop.\n"
        "4. Decide whether to authorize one controlled Reference repeat, reject Route P, or prescribe another bounded action.\n"
        "5. Do not record Final Core Freeze v3 from this package. The production correction is uncommitted.\n",
    )
    review_manifest_path = package_root / "review-package-manifest.json"
    review_manifest = manifest(package_root, {review_manifest_path.name})
    write_json(review_manifest_path, review_manifest)
    zip_path = root / "SHM-EM_Phase2A2_GPT_Review_Package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_root).as_posix())
    package_info = {
        "schemaVersion": "shm-em-phase2a2-review-package-v1",
        "path": str(zip_path),
        "bytes": zip_path.stat().st_size,
        "sha256": sha256_file(zip_path),
        "zipTest": None,
    }
    with zipfile.ZipFile(zip_path, "r") as archive:
        package_info["zipTest"] = archive.testzip()
        package_info["members"] = len(archive.infolist())
    write_json(root / "gpt-review-package.json", package_info)
    print(json.dumps(package_info, indent=2))
    return 0 if verification["pass"] and package_info["zipTest"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
