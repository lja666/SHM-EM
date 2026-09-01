#!/usr/bin/env python3
"""Validate Phase 2D and create a stable project-local GPT review package."""

from __future__ import annotations

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any
import zipfile


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"


def text(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Required Phase 2D file is missing: {path}")
    return path.read_text(encoding="utf-8")


def load(path: Path) -> Any:
    return json.loads(text(path))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    ).stdout


def gate(identifier: str, passed: bool, evidence: list[str], detail: str) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "evidence": evidence, "detail": detail}


def required_paths() -> list[str]:
    return [
        "tools/revision/build_phase2d_manuscript_evidence.py",
        "tools/revision/finalize_phase2d_evidence.py",
        "docs/revision/RELATED_SOFTWARE_COMPARISON.md",
        "docs/revision/SENSORTHINGS_POSITIONING.md",
        "docs/revision/figures/forecast-event-sequence.mmd",
        "artifacts/revision/manuscript/related-software-sources.json",
        "artifacts/revision/manuscript/related-software-comparison.csv",
        "artifacts/revision/manuscript/related-software-comparison.md",
        "artifacts/revision/manuscript/sequence-code-crosscheck.json",
        "artifacts/revision/manuscript/FIGURE4_REDUCTION_PLAN.md",
        "artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md",
        "artifacts/revision/manuscript/REPETITION_REDUCTION_MAP.md",
        "artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md",
        "artifacts/revision/manuscript/REVIEWER_RESPONSE_FACTS.md",
        "artifacts/revision/manuscript/METADATA_C6_PROPOSED.md",
        "artifacts/revision/manuscript/reviewer-evidence-map-final.json",
        "artifacts/revision/manuscript/reviewer-evidence-map-final.md",
    ]


def build_gates(repo: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    output = repo / "artifacts/revision/manuscript"
    sources = load(output / "related-software-sources.json")
    with (output / "related-software-comparison.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        comparison = list(csv.DictReader(handle))
    related = text(repo / "docs/revision/RELATED_SOFTWARE_COMPARISON.md")
    sensor = text(repo / "docs/revision/SENSORTHINGS_POSITIONING.md")
    sequence = text(repo / "docs/revision/figures/forecast-event-sequence.mmd")
    crosscheck = load(output / "sequence-code-crosscheck.json")
    figure = text(output / "FIGURE4_REDUCTION_PLAN.md")
    impact = text(output / "IMPACT_RESTRUCTURING_PLAN.md")
    repetition = text(output / "REPETITION_REDUCTION_MAP.md")
    limitations = text(output / "FINAL_LIMITATION_MATRIX.md")
    response = text(output / "REVIEWER_RESPONSE_FACTS.md")
    metadata = text(output / "METADATA_C6_PROPOSED.md")
    reviewer = load(output / "reviewer-evidence-map-final.json")

    allowed = {"Yes", "Partial", "Not reported", "Not applicable"}
    third_party = [
        row[column]
        for row in comparison
        for column in ("OGC SensorThings", "generic CEP", "Predictive-SHM")
    ]
    source_ids = {item["id"] for item in sources["sources"]}
    code_hashes_match = all(
        sha256(repo / path) == expected
        for path, expected in crosscheck["sourceHashes"].items()
    )
    response_items = [line.split(" - ", 1)[0].replace("## ", "") for line in response.splitlines() if line.startswith("## R")]
    mapped_items = [entry["reviewerItem"] for entry in reviewer["entries"]]
    core_paths = ["src/backend/src/main", "src/pit_pre/pit_pre", "src/frontend/src"]
    committed_core_diff = git(repo, "diff", f"{FREEZE}..HEAD", "--", *core_paths)
    worktree_core_diff = git(repo, "diff", "--", *core_paths)
    core_diffs = {
        "committedSinceFreezeV3": committed_core_diff,
        "uncommittedProductionCore": worktree_core_diff,
    }

    gates = [
        gate(
            "P2D-01",
            len(comparison) == 12 and {"predictive-shm", "ogc-sensorthings-1.1", "generic-cep"} <= source_ids
            and "publisher abstract" in related and "10.1016/j.softx.2026.102732" in related
            and next(row for row in comparison if row["capability"] == "Shared prediction origin and future timeline")["Predictive-SHM"] == "Not reported",
            ["docs/revision/RELATED_SOFTWARE_COMPARISON.md", "artifacts/revision/manuscript/related-software-sources.json"],
            "Predictive-SHM differentiation is limited to source-grounded published capabilities.",
        ),
        gate(
            "P2D-02",
            all(value in allowed for value in third_party) and "No" not in third_party,
            ["artifacts/revision/manuscript/related-software-comparison.csv"],
            "All third-party cells use the controlled vocabulary; no unsupported `No` appears.",
        ),
        gate(
            "P2D-03",
            "does **not** implement" in sensor and "no claim of SensorThings API conformance or compatibility" in sensor
            and "prospective adapter boundary, not an implemented feature" in sensor,
            ["docs/revision/SENSORTHINGS_POSITIONING.md"],
            "The SensorThings adapter and conformance boundary is explicit.",
        ),
        gate(
            "P2D-04",
            "not a claim that CEP is incapable" in related and "Generic CEP supplies established" in related,
            ["docs/revision/RELATED_SOFTWARE_COMPARISON.md"],
            "The CEP comparison recognizes generic stream/rule/event capabilities and makes no incapability claim.",
        ),
        gate(
            "P2D-05",
            sequence.startswith("sequenceDiagram") and code_hashes_match and len(crosscheck["anchors"]) == 10
            and crosscheck["futureStateIsIndependentReadPath"] is True
            and "Evaluate(rule, batch)" in sequence and "Execute(rule, batch, executionMode)" in sequence,
            ["docs/revision/figures/forecast-event-sequence.mmd", "artifacts/revision/manuscript/sequence-code-crosscheck.json"],
            "The sequence is anchored to the frozen source and does not make Future State an Execute precondition.",
        ),
        gate(
            "P2D-06",
            "175 mm" in figure and "2-by-2 asymmetric layout" in figure and "does not constitute scientific validation" in figure
            and all(name in figure for name in ("Project Workspace", "Observation and Prediction", "Prediction Runs")),
            ["artifacts/revision/manuscript/FIGURE4_REDUCTION_PLAN.md"],
            "Figure 4 has a concrete one-composite crop, layout, resolution, and caption plan.",
        ),
        gate(
            "P2D-07",
            impact.count("Evidence: `") >= 4 and "do not establish production throughput or linear scalability" in impact
            and "not interpreted as bridge-domain predictive validation" in impact
            and "15-case validation matrix comprising one positive control" in impact,
            ["artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md"],
            "Every Impact subsection is evidence-linked and bounded.",
        ),
        gate(
            "P2D-08",
            "used solely as software-workflow fixtures" in impact
            and "not interpreted as bridge-domain predictive validation or cross-domain forecasting accuracy" in impact
            and "one independently registered synthetic" in impact,
            ["artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md"],
            "The second configuration is software-reuse evidence only.",
        ),
        gate(
            "P2D-09",
            "did not produce a bitwise-identical" in metadata and "0.00285349" in metadata
            and "exactPredictionReproduction=false" in metadata and "toleranceApplied=false" in metadata
            and "full row-wise comparison artifact" in metadata
            and "no tolerance was applied" in metadata and "native ubuntu-host validation was not separately captured" in metadata.lower(),
            ["artifacts/revision/manuscript/METADATA_C6_PROPOSED.md", "artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md"],
            "The Phase 2C portability limitation is preserved without tolerance reinterpretation.",
        ),
        gate(
            "P2D-10",
            "Point forecasts only" in limitations and "not quantified predictive uncertainty" in limitations
            and "probabilistic" in limitations,
            ["artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md"],
            "Point forecasts and the distinction between Gate eligibility and uncertainty are explicit.",
        ),
        gate(
            "P2D-11",
            "50,000-row Gate inspection cap" in limitations and "application safeguard" in limitations
            and "not a MySQL capacity" in limitations,
            ["artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md"],
            "The 50,000-row cap is classified as an application-level bounded-query safeguard.",
        ),
        gate(
            "P2D-12",
            all(section in repetition for section in ("Introduction", "Section 2.1", "Section 2.2", "Section 3", "Section 4", "Conclusion"))
            and all(contribution in repetition for contribution in ("Versioned data-model contract", "Project Future State", "Controlled transition")),
            ["artifacts/revision/manuscript/REPETITION_REDUCTION_MAP.md"],
            "The repetition map covers all requested sections and all three recurring contributions.",
        ),
        gate(
            "P2D-13",
            len(response_items) == 27 and response_items == mapped_items and reviewer["reviewerItems"] == 27
            and response.count("**Deliberately not claimed:**") == 27
            and response.count("**Key result:**") == 27,
            ["artifacts/revision/manuscript/REVIEWER_RESPONSE_FACTS.md", "artifacts/revision/manuscript/reviewer-evidence-map-final.md"],
            "The fact sheet covers all 27 reviewer headings with explicit non-claims and results.",
        ),
        gate(
            "P2D-14",
            not committed_core_diff.strip() and not worktree_core_diff.strip(),
            ["artifacts/revision/manuscript/phase2d-production-core-diff.txt", "artifacts/revision/manuscript/phase2d-production-core-worktree-diff.txt"],
            "Production core remains identical to Final Core Freeze v3.",
        ),
    ]
    return gates, core_diffs


def completion_report(gates: list[dict[str, Any]], head: str) -> str:
    lines = [
        "# Phase 2D Completion Report",
        "",
        "## Boundary",
        "",
        f"- Final Core Freeze v3: `{FREEZE}`",
        f"- Phase 2D evidence-preparation HEAD: `{head}`",
        "- Production business-core diff: **NONE**",
        "- Work performed: related-software positioning, figure sources/plans, evidence-driven Impact planning, limitations, reviewer facts, and final evidence mapping.",
        "- Work deliberately excluded: production algorithms, database changes, authentication, SensorThings implementation, models, tolerance rules, and further performance engineering.",
        "",
        "## Acceptance Gates",
        "",
        "| Gate | Status | Result |",
        "|---|---|---|",
    ]
    for item in gates:
        lines.append(f"| {item['id']} | {item['status']} | {item['detail']} |")
    lines.extend([
        "",
        "## Key scientific boundaries retained",
        "",
        "- Predictive-SHM is treated as complementary upstream forecasting software; no cross-system superiority is claimed.",
        "- Generic CEP is credited with stream/window/rule/event capabilities; SHM-EM is positioned by its forecast-specific persisted controls.",
        "- SHM-EM does not claim OGC SensorThings conformance or compatibility.",
        "- The synthetic bridge configuration is software-reuse evidence, not predictive generalization.",
        "- The current six models produce point forecasts; Gate eligibility is not uncertainty quantification.",
        "- The 50,000-row Gate cap is an application-level bounded-query safeguard, not a MySQL limit.",
        "- Docker Linux reproduced the logical workflow but not a bitwise-identical normalized output hash; no tolerance was introduced.",
        "",
        "## STOP",
        "",
        "`STOP_FOR_GPT_PHASE2D_REVIEW`",
        "",
        "Final Manuscript Revision + Response to Reviewers is not authorized by this package and must wait for GPT review.",
    ])
    return "\n".join(lines)


def handoff_text(head: str, package_sha: str | None = None) -> str:
    package_line = "generated after this handoff" if package_sha is None else package_sha
    return f"""# GPT Review Handoff: Phase 2D

Please review Phase 2D at evidence-preparation commit `{head}` against Final Core Freeze v3 `{FREEZE}`.

## Decision requested

Verify P2D-01 through P2D-14 and decide whether SHM-EM may enter **Final Manuscript Revision + Response to Reviewers**.

## Priority checks

1. Predictive-SHM claims are limited to primary-source documented capabilities and no unsupported third-party `No` is used.
2. Generic CEP is compared fairly and SensorThings conformance is explicitly not claimed.
3. `forecast-event-sequence.mmd` matches the frozen code order: Evaluate performs non-persisted REPLAY inspection; Execute recomputes/persists Gate eligibility before formal rule/event side effects; Future State is an independent read path.
4. Figure 4 is reduced from three pages to one compact illustrative composite, while scientific evidence moves to tables, algorithm, failure matrix, runtime, reuse, and provenance.
5. Impact wording uses measured evidence and does not generalize the synthetic bridge fixture.
6. Point-forecast, 50k application cap, MySQL-only, security, SensorThings, and cross-platform numerical limitations remain explicit.
7. `REVIEWER_RESPONSE_FACTS.md` covers all 27 reviewer headings.
8. Production core diff relative to Final Core Freeze v3 is NONE.

## Stable project-local paths

- Canonical ZIP: `artifacts/revision/manuscript/SHM-EM_Phase2D_GPT_Review_Package.zip`
- Direct-upload ordinary files: `artifacts/revision/manuscript/gpt-direct-upload-phase2d/`
- Package SHA-256: `{package_line}`

## Required stop

Codex has stopped after Phase 2D. Do not infer that the manuscript or final response has already been edited.
"""


def package(repo: Path, output: Path, head: str, manifest: dict[str, Any]) -> dict[str, Any]:
    direct = output / "gpt-direct-upload-phase2d"
    direct_resolved = direct.resolve()
    if repo.resolve() not in direct_resolved.parents:
        raise RuntimeError(f"Unsafe direct-upload path: {direct_resolved}")
    if direct.exists():
        shutil.rmtree(direct)
    direct.mkdir(parents=True)

    direct_sources = {
        "GPT_REVIEW_HANDOFF.md": output / "GPT_REVIEW_HANDOFF_PHASE2D.md",
        "PHASE2D_COMPLETION_REPORT.md": output / "PHASE2D_COMPLETION_REPORT.md",
        "phase2d-manifest.json": output / "phase2d-manifest.json",
        "related-software-comparison.md": output / "related-software-comparison.md",
        "forecast-event-sequence.mmd": repo / "docs/revision/figures/forecast-event-sequence.mmd",
        "FIGURE4_REDUCTION_PLAN.md": output / "FIGURE4_REDUCTION_PLAN.md",
        "IMPACT_RESTRUCTURING_PLAN.md": output / "IMPACT_RESTRUCTURING_PLAN.md",
        "FINAL_LIMITATION_MATRIX.md": output / "FINAL_LIMITATION_MATRIX.md",
        "REVIEWER_RESPONSE_FACTS.md": output / "REVIEWER_RESPONSE_FACTS.md",
        "reviewer-evidence-map-final.md": output / "reviewer-evidence-map-final.md",
        "METADATA_C6_PROPOSED.md": output / "METADATA_C6_PROPOSED.md",
    }
    for name, source in direct_sources.items():
        shutil.copy2(source, direct / name)

    package_paths = required_paths() + [
        "artifacts/revision/manuscript/PHASE2D_COMPLETION_REPORT.md",
        "artifacts/revision/manuscript/GPT_REVIEW_HANDOFF_PHASE2D.md",
        "artifacts/revision/manuscript/phase2d-manifest.json",
        "artifacts/revision/manuscript/phase2d-production-core-diff.txt",
        "artifacts/revision/manuscript/phase2d-production-core-worktree-diff.txt",
        "artifacts/revision/manuscript/final-performance-table.md",
        "artifacts/revision/manuscript/software-test-summary.md",
        "artifacts/revision/manuscript/claim-gap-matrix-final.md",
        "artifacts/revision/benchmarks/route-p/phase1b-regression.json",
        "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md",
        "docs/revision/DATA_MODEL_CONTRACT_SPEC.md",
        "docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md",
        "docs/revision/PROVENANCE_TRACE_EXAMPLE.md",
        "docs/revision/STORAGE_ADAPTER_BOUNDARY.md",
        "SECURITY.md",
        "artifacts/revision/portability/cross-platform-comparison.md",
        "artifacts/revision/portability/portability-limitations.md",
    ]
    zip_path = output / "SHM-EM_Phase2D_GPT_Review_Package.zip"
    with tempfile.TemporaryDirectory(prefix="shm-em-phase2d-") as temp_name:
        root = Path(temp_name) / "SHM-EM_Phase2D_GPT_Review_Package"
        for relative in package_paths:
            source = repo / relative
            if not source.is_file():
                raise RuntimeError(f"Package source missing: {relative}")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in sorted(root.rglob("*")):
                if source.is_file():
                    archive.write(source, source.relative_to(root).as_posix())

    verification = {
        "schemaVersion": "shm-em-phase2d-review-package-verification-v1",
        "finalCoreFreezeV3": FREEZE,
        "evidencePreparationHead": head,
        "canonicalZip": {
            "path": str(zip_path.relative_to(repo)).replace("\\", "/"),
            "bytes": zip_path.stat().st_size,
            "sha256": sha256(zip_path),
            "entries": len(package_paths),
        },
        "directUploadDirectory": str(direct.relative_to(repo)).replace("\\", "/"),
        "directUploadFiles": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(direct.iterdir()) if path.is_file()
        ],
        "manifestGateCount": len(manifest["gates"]),
        "allGatesPass": manifest["allGatesPass"],
    }
    write(output / "phase2d-review-package-verification.json", verification)
    return verification


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    output = repo / "artifacts/revision/manuscript"
    for relative in required_paths():
        if not (repo / relative).is_file():
            raise RuntimeError(f"Required Phase 2D file is missing: {relative}")

    gates, core_diffs = build_gates(repo)
    head = git(repo, "rev-parse", "HEAD").strip()
    write_text(output / "phase2d-production-core-diff.txt", core_diffs["committedSinceFreezeV3"] or "NONE\n")
    write_text(output / "phase2d-production-core-worktree-diff.txt", core_diffs["uncommittedProductionCore"] or "NONE\n")
    write_text(output / "PHASE2D_COMPLETION_REPORT.md", completion_report(gates, head))
    write_text(output / "GPT_REVIEW_HANDOFF_PHASE2D.md", handoff_text(head))

    files = [
        {
            "path": relative,
            "bytes": (repo / relative).stat().st_size,
            "sha256": sha256(repo / relative),
        }
        for relative in required_paths()
    ]
    manifest = {
        "schemaVersion": "shm-em-phase2d-manifest-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "finalCoreFreezeV3": FREEZE,
        "evidencePreparationHead": head,
        "phase": "Related Software Positioning, Figures, and Impact Restructuring",
        "gates": gates,
        "allGatesPass": all(item["status"] == "PASS" for item in gates),
        "files": files,
        "productionCoreDiff": "NONE" if not any(value.strip() for value in core_diffs.values()) else "NONEMPTY",
        "stopRequired": True,
        "nextDecisionOwner": "GPT review",
    }
    write(output / "phase2d-manifest.json", manifest)
    if not manifest["allGatesPass"]:
        failed = [item["id"] for item in gates if item["status"] != "PASS"]
        raise RuntimeError(f"Phase 2D gates failed: {', '.join(failed)}")

    verification = package(repo, output, head, manifest)
    # Add the immutable ZIP hash to both project-local handoff copies, then refresh the ZIP once.
    package_hash = verification["canonicalZip"]["sha256"]
    write_text(output / "GPT_REVIEW_HANDOFF_PHASE2D.md", handoff_text(head, package_hash))
    shutil.copy2(output / "GPT_REVIEW_HANDOFF_PHASE2D.md", output / "gpt-direct-upload-phase2d/GPT_REVIEW_HANDOFF.md")
    # The package deliberately contains the pre-hash handoff to avoid a self-referential ZIP hash.
    verification["handoffHashNote"] = (
        "The external/project-local handoff reports the ZIP hash. The ZIP-internal handoff uses a non-self-referential placeholder."
    )
    verification["externalHandoffSha256"] = sha256(output / "GPT_REVIEW_HANDOFF_PHASE2D.md")
    verification["directUploadFiles"] = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted((output / "gpt-direct-upload-phase2d").iterdir()) if path.is_file()
    ]
    write(output / "phase2d-review-package-verification.json", verification)
    print(json.dumps({
        "allGatesPass": manifest["allGatesPass"],
        "gateCount": len(gates),
        "zip": verification["canonicalZip"],
        "directUploadFiles": len(verification["directUploadFiles"]),
        "stop": "STOP_FOR_GPT_PHASE2D_REVIEW",
    }, indent=2))


if __name__ == "__main__":
    main()
