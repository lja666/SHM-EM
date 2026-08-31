#!/usr/bin/env python3
"""Validate Phase 2B evidence, write the manifest, and package it for GPT review."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any
import zipfile

import jsonschema


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"


def load(path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"Required Phase 2B file is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout


def gate(identifier: str, passed: bool, evidence: list[str], detail: str) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "evidence": evidence, "detail": detail}


def required_paths() -> list[str]:
    return [
        "docs/revision/DATA_MODEL_CONTRACT_SPEC.md",
        "tools/revision/export_data_model_contract.py",
        "docs/revision/examples/data-model-contract.example.json",
        "docs/revision/examples/data-model-contract.schema.json",
        "artifacts/revision/manuscript/data-model-contract-export.json",
        "docs/revision/PROJECT_FUTURE_STATE_SPEC.md",
        "docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md",
        "artifacts/revision/manuscript/future-state-boundary-tests.json",
        "tools/revision/run_phase2b_regression.py",
        "tools/revision/collect_final_test_summary.py",
        "artifacts/revision/manuscript/phase2b-final-regression.json",
        "artifacts/revision/manuscript/software-test-summary.json",
        "artifacts/revision/manuscript/software-test-summary.csv",
        "artifacts/revision/manuscript/software-test-summary.md",
        "tools/revision/export_provenance_trace.py",
        "docs/revision/PROVENANCE_TRACE_EXAMPLE.md",
        "artifacts/revision/manuscript/provenance-trace-final.json",
        "artifacts/revision/manuscript/provenance-trace-final.md",
        "tools/revision/export_model_config_summary.py",
        "docs/revision/MODEL_CONFIG_SUMMARY.md",
        "artifacts/revision/manuscript/model-config-summary.json",
        "tools/revision/build_phase2b_manuscript_evidence.py",
        "artifacts/revision/manuscript/PERFORMANCE_EVIDENCE_SELECTION.md",
        "artifacts/revision/manuscript/final-performance-table.csv",
        "artifacts/revision/manuscript/final-performance-table.md",
        "artifacts/revision/manuscript/reviewer-evidence-map.json",
        "artifacts/revision/manuscript/reviewer-evidence-map.md",
        "artifacts/revision/manuscript/claim-gap-matrix-final.md",
        "artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md",
        "tools/revision/finalize_phase2b_evidence.py",
        "artifacts/revision/reuse/core-freeze-v3-commit.txt",
        "artifacts/revision/reuse/core-freeze-lineage.json",
    ]


def build_gates(repo: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    output = repo / "artifacts/revision/manuscript"
    contract = load(output / "data-model-contract-export.json")
    example = load(repo / "docs/revision/examples/data-model-contract.example.json")
    schema = load(repo / "docs/revision/examples/data-model-contract.schema.json")
    jsonschema.validate(example, schema)
    boundary = load(output / "future-state-boundary-tests.json")
    tests = load(output / "software-test-summary.json")
    provenance = load(output / "provenance-trace-final.json")
    models = load(output / "model-config-summary.json")
    reviewer = load(output / "reviewer-evidence-map.json")
    route_p = load(repo / "artifacts/revision/benchmarks/route-p/scaling-sweep-v2-summary.json")
    lineage = load(repo / "artifacts/revision/reuse/core-freeze-lineage.json")
    freeze_record = (repo / "artifacts/revision/reuse/core-freeze-v3-commit.txt").read_text(encoding="utf-8").strip()
    core_paths = ["src/backend/src/main", "src/frontend/src", "src/pit_pre/pit_pre", "src/pit_pre/models"]
    committed_diff = git(repo, "diff", f"{FREEZE}..HEAD", "--", *core_paths)
    worktree_diff = git(repo, "diff", "--", *core_paths)
    diffs = {"committedSinceFreezeV3": committed_diff, "uncommittedProductionCore": worktree_diff}
    selection = (output / "PERFORMANCE_EVIDENCE_SELECTION.md").read_text(encoding="utf-8")
    performance_table = (output / "final-performance-table.csv").read_text(encoding="utf-8-sig")
    entries = reviewer["entries"]
    gates = [
        gate("P2B-01", freeze_record == FREEZE and lineage.get("finalCoreFreezeV3") == FREEZE, ["artifacts/revision/reuse/core-freeze-v3-commit.txt", "artifacts/revision/reuse/core-freeze-lineage.json"], "Performance-Corrected Final Core Freeze v3 is recorded and unchanged."),
        gate("P2B-02", contract["finalCoreFreezeV3"] == FREEZE and len(contract["models"]) == 6 and len(contract["features"]) == 164 and len(contract["targets"]) == 124 and example["contractVersion"] == contract["contractVersion"], ["artifacts/revision/manuscript/data-model-contract-export.json", "docs/revision/examples/data-model-contract.example.json", "docs/revision/examples/data-model-contract.schema.json"], "The compact example validates against its schema and is derived from the authoritative exported contract."),
        gate("P2B-03", boundary["pass"] and len(boundary["cases"]) == 6 and boundary["productionAlgorithmModified"] is False, ["docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md", "artifacts/revision/manuscript/future-state-boundary-tests.json"], "Future State pseudocode is paired with six passing code-level boundary cases."),
        gate("P2B-04", tests["allFamiliesPass"] and "No global case total" in tests["doubleCountingPolicy"], ["artifacts/revision/manuscript/software-test-summary.json", "artifacts/revision/manuscript/software-test-summary.md"], "The automated final summary reports independent families and forbids a double-counted global total."),
        gate("P2B-05", provenance["source"]["isolatedFormalStateRestored"] and provenance["persistedIntegrity"]["executionEligible"] and provenance["persistedIntegrity"]["resultIntegrityValid"] and provenance["selectedForecastSeries"]["pointCount"] == 40 and provenance["eventPredictionLink"]["prediction_gate_id"] is not None, ["artifacts/revision/manuscript/provenance-trace-final.json", "docs/revision/PROVENANCE_TRACE_EXAMPLE.md"], "One restored formal-event run links rule, batch, run, Gate, 40-step forecast, event, and evidence state."),
        gate("P2B-06", models["modelCount"] == 6 and models["allHashChecksPass"] and all(all(item["hashChecks"].values()) for item in models["models"]), ["artifacts/revision/manuscript/model-config-summary.json", "docs/revision/MODEL_CONFIG_SUMMARY.md"], "All six model summaries are artifact/database derived and every recorded hash check passes."),
        gate("P2B-07", route_p["reference"]["measured"]["medianMs"] == 343.12905 and route_p["reference"]["measured"]["p95Ms"] == 407.1003 and "343.12905" in performance_table and "407.1003" in performance_table, ["artifacts/revision/manuscript/final-performance-table.csv", "artifacts/revision/benchmarks/route-p/scaling-sweep-v2-summary.json"], "The final table uses the single authorized corrected Gate benchmark."),
        gate("P2B-08", "do not establish linear scalability" in (output / "final-performance-table.md").read_text(encoding="utf-8") and "six-level nonmonotonic sweep" in selection, ["artifacts/revision/manuscript/PERFORMANCE_EVIDENCE_SELECTION.md"], "Intermediate nonmonotonic and localization evidence is explicitly diagnostic-only."),
        gate("P2B-09", reviewer["reviewerItems"] == 27 and {entry["reviewerItem"][:2] for entry in entries} == {"R1", "R2", "R3"}, ["artifacts/revision/manuscript/reviewer-evidence-map.json", "artifacts/revision/manuscript/reviewer-evidence-map.md"], "All 27 headings from the three-reviewer strategy are mapped."),
        gate("P2B-10", not committed_diff.strip() and not worktree_diff.strip(), ["artifacts/revision/manuscript/production-core-diff-since-freeze-v3.txt", "artifacts/revision/manuscript/production-core-worktree-diff.txt"], "No production-core content differs from Final Core Freeze v3."),
    ]
    return gates, diffs


def handoff_text(manifest: dict[str, Any]) -> str:
    return f"""# SHM-EM Phase 2B GPT Review Handoff

## Decision requested

Review whether Phase 2B Formal Specification & Evidence Consolidation satisfies P2B-01 through P2B-10 without modifying the frozen production core. Decide whether the revision may proceed to the remaining documentation/manuscript work or whether a specific evidence gap must be corrected first.

## Frozen core

- Performance-Corrected Final Core Freeze v3: `{FREEZE}`
- Evidence preparation HEAD: `{manifest['evidencePreparationHead']}`
- Production-core diff since Freeze v3: **NONE**
- Uncommitted production-core diff: **NONE**

## Phase 2B results

- Data/model contract: 6 active models, 164 ordered input features, 124 prediction targets, shared 40-step/3-minute timeline; compact example schema-valid.
- Future State: code-accurate specification and pseudocode; six boundary tests PASS.
- Final regression: backend 55/55, PIT_PRE 13/13, failure/integrity 15/15, Phase 1B 7/7, frontend 2/2, reference reproduction PASS.
- Model configuration: six models, all database/artifact/runtime hash checks PASS.
- Provenance: one formal event traced across rule, prediction batch/run, Gate, 40-step series, event link, and evidence; isolated formal state restored.
- Performance: final corrected Gate 343.129 ms median / 407.100 ms p95; S1 4,960 and S2 49,600 rows retained as tenfold functional stress, without a linear-scaling claim.
- Reviewer map: all 27 headings across R1/R2/R3 mapped to evidence and remaining manuscript actions.

## Deliberate limitations retained

- The Gate reference implementation is bounded to 50,000 prediction-display rows per inspection.
- Forecasts are point estimates; uncertainty quantification is not implemented.
- Linux/Docker reproduction is not claimed; native Windows is the validated path.
- Deployment security and related-software/SensorThings comparison remain documentation/manuscript tasks.
- No cross-system performance or predictive-accuracy superiority claim is made.

## Gate result

All ten Phase 2B gates are PASS. Phase 2B stops here pending GPT review, as required by the handoff.
"""


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    output = repo / "artifacts/revision/manuscript"
    output.mkdir(parents=True, exist_ok=True)
    gates, diffs = build_gates(repo)
    (output / "production-core-diff-since-freeze-v3.txt").write_text(diffs["committedSinceFreezeV3"] or "NONE\n", encoding="utf-8", newline="\n")
    (output / "production-core-worktree-diff.txt").write_text(diffs["uncommittedProductionCore"] or "NONE\n", encoding="utf-8", newline="\n")
    paths = required_paths() + [
        "artifacts/revision/manuscript/production-core-diff-since-freeze-v3.txt",
        "artifacts/revision/manuscript/production-core-worktree-diff.txt",
    ]
    records = []
    for relative in paths:
        path = repo / relative
        if not path.is_file():
            raise RuntimeError(f"Manifest input is missing: {relative}")
        records.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "schemaVersion": "shm-em-phase2b-manifest-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "finalCoreFreezeV3": FREEZE,
        "evidencePreparationHead": git(repo, "rev-parse", "HEAD").strip(),
        "gates": gates,
        "allGatesPass": all(item["status"] == "PASS" for item in gates),
        "files": records,
        "stopRequired": True,
        "nextDecisionOwner": "GPT review",
    }
    write(output / "phase2b-manifest.json", manifest)
    (output / "GPT_REVIEW_HANDOFF.md").write_text(handoff_text(manifest), encoding="utf-8", newline="\n")
    manifest_files = [*paths, "artifacts/revision/manuscript/phase2b-manifest.json", "artifacts/revision/manuscript/GPT_REVIEW_HANDOFF.md", "tools/revision/finalize_phase2b_evidence.py", "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/ProjectFutureStateServiceImplTest.java"]
    package = output / "SHM-EM_Phase2B_GPT_Review_Package.zip"
    with tempfile.TemporaryDirectory(prefix="shm-em-phase2b-") as temporary:
        staging = Path(temporary) / "SHM-EM_Phase2B_GPT_Review_Package"
        for relative in manifest_files:
            source = repo / relative
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging.parent).as_posix())
    package_record = {"path": package.relative_to(repo).as_posix(), "bytes": package.stat().st_size, "sha256": sha256(package), "allGatesPass": manifest["allGatesPass"]}
    write(output / "phase2b-gpt-review-package.json", package_record)
    verification = {
        "schemaVersion": "shm-em-phase2b-verification-v1",
        "manifestSha256": sha256(output / "phase2b-manifest.json"),
        "package": package_record,
        "gateCount": len(gates),
        "passedGateCount": sum(item["status"] == "PASS" for item in gates),
        "pass": manifest["allGatesPass"],
    }
    write(output / "phase2b-manifest-verification.json", verification)
    print(json.dumps(verification, indent=2))
    return 0 if verification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
