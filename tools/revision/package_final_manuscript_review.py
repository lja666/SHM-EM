#!/usr/bin/env python3
"""Build the project-local GPT review package for final manuscript sources."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"
OUTPUT_REL = Path("artifacts/revision/final-manuscript-review")
SOURCE_PATHS = (
    "manuscript/SHM-EM_Revised_Manuscript_Source.md",
    "manuscript/Response_to_Reviewers_Source.md",
    "manuscript/Revision_Change_Map.md",
    "manuscript/Final_Reviewer_Evidence_Map.md",
    "manuscript/Final_Submission_Checklist.md",
)
EVIDENCE_PATHS = (
    "docs/revision/DATA_MODEL_CONTRACT_SPEC.md",
    "docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md",
    "docs/revision/MODEL_CONFIG_SUMMARY.md",
    "docs/revision/PROVENANCE_TRACE_EXAMPLE.md",
    "docs/revision/RELATED_SOFTWARE_COMPARISON.md",
    "docs/revision/SENSORTHINGS_POSITIONING.md",
    "docs/revision/STORAGE_ADAPTER_BOUNDARY.md",
    "docs/revision/figures/forecast-event-sequence.mmd",
    "SECURITY.md",
    "compose.yaml",
    "src/backend/Dockerfile",
    "src/frontend/Dockerfile",
    "src/pit_pre/Dockerfile",
    "src/pit_pre/pit_pre/features.py",
    "src/pit_pre/pit_pre/pipeline.py",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/ProjectFutureStateServiceImpl.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/MetricRuleEventEngine.java",
    "artifacts/revision/manuscript/software-test-summary.md",
    "artifacts/revision/manuscript/final-performance-table.md",
    "artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md",
    "artifacts/revision/manuscript/METADATA_C6_PROPOSED.md",
    "artifacts/revision/manuscript/related-software-comparison.md",
    "artifacts/revision/manuscript/sequence-code-crosscheck.json",
    "artifacts/revision/manuscript/model-config-summary.json",
    "artifacts/revision/manuscript/MODEL_DIMENSION_RECONCILIATION.md",
    "artifacts/revision/manuscript/model-dimension-reconciliation.json",
    "artifacts/revision/manuscript/EVALUATE_SIDE_EFFECT_RECONCILIATION.md",
    "artifacts/revision/manuscript/data-model-contract-export.json",
    "artifacts/revision/manuscript/provenance-trace-final.json",
    "artifacts/revision/benchmarks/route-p/phase1b-regression.json",
    "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md",
    "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.json",
    "artifacts/revision/portability/cross-platform-comparison.json",
    "artifacts/revision/portability/cross-platform-numeric-difference.json",
    "artifacts/revision/portability/PHASE2C_COMPLETION_REPORT.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def completion_report(head: str, validation: dict[str, object]) -> str:
    return f"""# Final Manuscript Source Completion Report

## Authorized boundary

- Editorial authority: submitted manuscript `SOFTX-D-26-00931.pdf`.
- Final Core Freeze v3: `{FREEZE}`.
- Manuscript source preparation HEAD: `{head}`.
- Production-core diff: **NONE**.
- Production code, models, experiments, performance logic, tolerance rules, SensorThings, authentication, and third-configuration work: **NOT CHANGED**.

## Source deliverables

1. `manuscript/SHM-EM_Revised_Manuscript_Source.md`
2. `manuscript/Response_to_Reviewers_Source.md`
3. `manuscript/Revision_Change_Map.md`
4. `manuscript/Final_Reviewer_Evidence_Map.md`
5. `manuscript/Final_Submission_Checklist.md`

## Automated preflight

- Checks: `{len(validation['checks'])}/{len(validation['checks'])}` PASS.
- Reviewer items: `{validation['reviewerItemCount']}/27`.
- References: `{validation['referenceCount']}/30`.
- M1: Predictive-SHM shared multi-model origin/timeline = `Not reported`.
- M2: validation matrix = one positive control + 12 failure paths + two input controls.
- M3: second-configuration model bundles = software-workflow fixtures only.
- M4: normalized output hash differs; `exactPredictionReproduction=false`; `toleranceApplied=false`; full row-wise comparison retained.

## Required stop

`STOP_FOR_GPT_FINAL_SCIENTIFIC_CONSISTENCY_REVIEW`

No clean/marked DOCX or final formatted response letter has been generated. GPT must first verify scientific consistency, reviewer coverage, evidence correspondence, and non-claims.
"""


def handoff(head: str, zip_sha: str | None = None) -> str:
    hash_line = zip_sha or "generated after the non-self-referential package is assembled"
    return f"""# GPT Review Handoff: Final Manuscript Sources

Please review the final Markdown sources prepared at commit `{head}` against Final Core Freeze v3 `{FREEZE}` and the submitted Editorial Manager PDF.

## Decision requested

Determine whether the five Markdown sources are scientifically consistent and may proceed to clean/marked DOCX generation.

## Priority checks

1. The manuscript retains exactly three contributions and does not repurpose persisted-result integrity as a fourth contribution.
2. Predictive-SHM, OGC SensorThings, and generic CEP are described fairly and from documented responsibilities.
3. The common `16 x 164` aligned pool is distinguished from the model input matrices (five `x 114`, settlement `x 164`), model-owned mapping counts (42/42/14/14/2/50), target counts (42/42/14/14/2/10), and 12-16 model histories.
4. The missing/asynchronous policy matches frozen code: backward-asof, declared interpolation/boundary fill, signed diagnostics, unresolved required input rejection, and separate freshness.
5. The second configuration is software-workflow evidence only; its two bundles and 1,120 outputs are not treated as bridge prediction validation.
6. The validation matrix is counted as P00 + F01-F12 + I01-I02; Evaluate is described as writing one audit run while creating no formal event, link, workflow, notification, report, or evidence record.
7. Runtime claims use the final table and do not imply linear scaling or a MySQL 50k limit.
8. Portability retains normalized-output non-identity, no tolerance, full row-wise evidence, and Windows as exact-output reference.
9. All 27 reviewer comments are answered with manuscript changes, evidence, and non-claim boundaries.
10. No final release/tag/checksum is implied complete before the checklist synchronization step.

## Stable project-local paths

- Canonical ZIP: `artifacts/revision/final-manuscript-review/SHM-EM_Final_Manuscript_GPT_Review_Package.zip`
- Direct ordinary files: `artifacts/revision/final-manuscript-review/gpt-direct-upload-final-manuscript/`
- Package SHA-256: `{hash_line}`

The direct ordinary files are the preferred upload route if a ZIP is not mounted by the review environment.

## Required stop

`STOP_FOR_GPT_FINAL_SCIENTIFIC_CONSISTENCY_REVIEW`
"""


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    output = repo / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    validation_path = output / "final-manuscript-source-validation.json"

    subprocess.run(
        [sys.executable, str(repo / "tools/revision/validate_final_manuscript_sources.py"), "--output", str(validation_path.relative_to(repo))],
        cwd=repo,
        check=True,
    )
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not validation["pass"]:
        raise RuntimeError("Final manuscript source validation did not pass")

    head = git(repo, "rev-parse", "HEAD")
    for relative in (*SOURCE_PATHS, *EVIDENCE_PATHS):
        if not (repo / relative).is_file():
            raise RuntimeError(f"Review-package source missing: {relative}")

    report_path = output / "FINAL_MANUSCRIPT_COMPLETION_REPORT.md"
    manifest_path = output / "final-manuscript-review-manifest.json"
    handoff_path = output / "GPT_REVIEW_HANDOFF_FINAL_MANUSCRIPT.md"
    write_text(report_path, completion_report(head, validation))
    write_text(handoff_path, handoff(head))

    package_sources = [*SOURCE_PATHS, *EVIDENCE_PATHS]
    files = [
        {
            "path": relative,
            "bytes": (repo / relative).stat().st_size,
            "sha256": sha256(repo / relative),
        }
        for relative in package_sources
    ]
    manifest = {
        "schemaVersion": "shm-em-final-manuscript-review-manifest-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "submittedManuscriptAuthority": "SOFTX-D-26-00931.pdf",
        "finalCoreFreezeV3": FREEZE,
        "sourcePreparationHead": head,
        "sourceFiles": list(SOURCE_PATHS),
        "validation": {
            "pass": validation["pass"],
            "checkCount": len(validation["checks"]),
            "reviewerItemCount": validation["reviewerItemCount"],
            "referenceCount": validation["referenceCount"],
        },
        "productionCoreDiff": "NONE",
        "files": files,
        "stopRequired": True,
        "nextDecisionOwner": "GPT scientific-consistency review",
    }
    write_json(manifest_path, manifest)

    zip_path = output / "SHM-EM_Final_Manuscript_GPT_Review_Package.zip"
    generated = (validation_path, report_path, manifest_path, handoff_path)
    with tempfile.TemporaryDirectory(prefix="shm-em-final-manuscript-") as temp_name:
        root = Path(temp_name) / "SHM-EM_Final_Manuscript_GPT_Review_Package"
        for relative in package_sources:
            source = repo / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for source in generated:
            target = root / OUTPUT_REL / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in sorted(root.rglob("*")):
                if source.is_file():
                    archive.write(source, source.relative_to(root).as_posix())

    zip_sha = sha256(zip_path)
    write_text(handoff_path, handoff(head, zip_sha))

    direct = output / "gpt-direct-upload-final-manuscript"
    if direct.exists():
        shutil.rmtree(direct)
    direct.mkdir(parents=True)
    direct_map = {
        handoff_path: "GPT_REVIEW_HANDOFF.md",
        report_path: report_path.name,
        manifest_path: manifest_path.name,
        validation_path: validation_path.name,
    }
    for relative in SOURCE_PATHS:
        direct_map[repo / relative] = Path(relative).name
    for source, name in direct_map.items():
        shutil.copy2(source, direct / name)

    verification = {
        "schemaVersion": "shm-em-final-manuscript-review-package-verification-v1",
        "sourcePreparationHead": head,
        "canonicalZip": {
            "path": str(zip_path.relative_to(repo)).replace("\\", "/"),
            "bytes": zip_path.stat().st_size,
            "sha256": zip_sha,
        },
        "directUploadDirectory": str(direct.relative_to(repo)).replace("\\", "/"),
        "directUploadFiles": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(direct.iterdir()) if path.is_file()
        ],
        "handoffHashNote": "The ZIP-internal handoff uses a non-self-referential placeholder; the project-local and direct-upload handoffs report the ZIP hash.",
        "pass": True,
    }
    write_json(output / "final-manuscript-review-package-verification.json", verification)
    print(json.dumps({
        "pass": True,
        "sourcePreparationHead": head,
        "zip": verification["canonicalZip"],
        "directUploadFiles": len(verification["directUploadFiles"]),
        "stop": "STOP_FOR_GPT_FINAL_SCIENTIFIC_CONSISTENCY_REVIEW",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
