#!/usr/bin/env python3
"""Build the bounded GPT review package for the Phase 1B stop point."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


FINAL_CORE_FREEZE_V2 = "b41c1894f75561c8ef682062a5e6dab35c3916a7"
FREEZE_RECORD_COMMIT = "3a1b4fc5990b28929c78f46f93a5deaae85140bf"
FROZEN_PATHS = (
    "src/backend/src/main",
    "src/frontend/src",
    "src/pit_pre/pit_pre",
    ".gitattributes",
)
SOURCE_FILES = (
    "sql/shm_em_database/revision/phase1b_synthetic_bridge.sql",
    "docs/revision/phase1b-second-configuration.md",
    "docs/revision/phase1b-model-fixture-card.md",
    "tools/revision/run_phase1b_reuse_validation.py",
    "tools/revision/build_phase1b_review_package.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {completed.stderr}")
    return completed.stdout


def handoff(summary: dict, status: str, frozen_diff: str) -> str:
    checks = summary["acceptanceChecks"]
    passed = sum(1 for item in checks.values() if item["pass"])
    config = summary["configuration"]
    prediction = summary["prediction"]
    future = summary["futureState"]
    gate = summary["gate"]
    frontend = summary["frontend"]
    response = summary["responseWorkflowOutcome"]
    step_statuses = response["stepStatuses"]
    lines = [
        "# SHM-EM Phase 1B GPT Review Handoff",
        "",
        "## Stop Point",
        "",
        f"- Final Core Freeze v2: `{FINAL_CORE_FREEZE_V2}`",
        f"- Freeze record commit: `{FREEZE_RECORD_COMMIT}`",
        "- Phase 1B changes committed: `false`",
        "- Required action: review only; do not infer approval for a subsequent phase.",
        "",
        "## Second Configuration",
        "",
        f"- Project: `{config['project']['project_code']}`",
        f"- Infrastructure type: `{config['project']['infrastructure_type']}`",
        f"- Stations: `{config['counts']['stations']}`",
        f"- Instruments: `{config['counts']['instruments']}`",
        f"- Existing observation registries reused: `{config['counts']['registries']}`",
        f"- Active model workflow fixtures: `{config['counts']['models']}`",
        f"- Feature mappings: `{config['counts']['features']}`",
        "- Scope: packaged excavation Strain/Pressure artifacts are deterministic workflow fixtures only; no bridge predictive-accuracy or transferability claim is made.",
        "",
        "## End-to-End Result",
        "",
        f"- Acceptance checks: `{passed}/{len(checks)}`",
        f"- Persisted predictions: `{prediction['totalPersistedRows']}`",
        f"- Gate execution eligible: `{str(gate['executionEligible']).lower()}`",
        f"- Persisted result integrity valid: `{str(gate['resultIntegrityValid']).lower()}`",
        f"- Future State assessed features: `{future['assessedFeatureCount']}`",
        f"- Evaluate formal side effects: `{sum(summary['evaluateFormalDeltas'].values())}`",
        f"- Execute event delta: `{summary['executeFormalDeltas']['events']}`",
        f"- Execute workflow delta: `{summary['executeFormalDeltas']['responseWorkflows']}`",
        f"- Execute prediction-link delta: `{summary['executeFormalDeltas']['predictionLinks']}`",
        f"- Response steps: RULE_TRIGGER `{step_statuses.get('RULE_TRIGGER')}`; NOTIFICATION `{step_statuses.get('NOTIFICATION')}`; REPORT_GENERATION `{step_statuses.get('REPORT_GENERATION')}`; EVIDENCE_ARCHIVE `{step_statuses.get('EVIDENCE_ARCHIVE')}`",
        f"- Report records created: `{response['reportsCreated']}`",
        "- Report-generation success is not used as a reuse acceptance criterion and is not claimed for this fixture.",
        f"- Event ID: `{summary['eventId']}`",
        f"- Workflow ID: `{summary['workflowId']}`",
        f"- Provenance link ID: `{summary['provenanceLinkId']}`",
        f"- Negative missing-mapping rejection: `{str(summary['negativeOnboarding']['pass']).lower()}`",
        f"- Frontend dependency install/build/routes: `{str(frontend['pass']).lower()}`",
        "",
        "## Frozen-Core Verification",
        "",
        f"- Frozen diff is empty: `{str(not frozen_diff.strip()).lower()}`",
        f"- Backend production files modified: `{summary['coreDiff']['coreBackendFilesModified']}`",
        f"- Frontend production files modified: `{summary['coreDiff']['coreFrontendFilesModified']}`",
        f"- PIT_PRE core files modified: `{summary['coreDiff']['pitPreCoreFilesModified']}`",
        f"- Existing `em_obs_*` schema alterations: `{summary['coreDiff']['existingSourceTableSchemaChangeCount']}`",
        "",
        "## Review Focus",
        "",
        "1. Verify the synthetic bridge is a configuration-reuse fixture, not a predictive-generalization claim.",
        "2. Recalculate `phase1b-manifest.json` and `review-package-manifest.json` hashes.",
        "3. Verify B1-B15 using `end-to-end-summary.json` and the linked machine-readable evidence.",
        "4. Verify the missing-mapping case fails before inference and creates no batch.",
        "5. Verify Evaluate has zero formal side effects and Execute creates one event, workflow, four workflow steps, and one prediction link.",
        "6. Preserve the observed REPORT_GENERATION failure and zero report records; do not infer report-generation success.",
        "7. Treat persisted-result integrity as independent Gate revalidation, not as a claim that Event Trace directly exposes every persisted-integrity field.",
        "8. Verify frozen production core remains byte-diff empty from Final Core Freeze v2.",
        "",
        "## Git Status At Packaging",
        "",
        "```text",
        status.rstrip(),
        "```",
        "",
        "## Decision Boundary",
        "",
        "`STOP_FOR_GPT_REVIEW`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    evidence = repo / "artifacts/revision/reuse-v2"
    package = evidence / "gpt-review-package"
    archive = evidence / "SHM-EM_Phase1B_GPT_Review_Package.zip"
    checksum = archive.with_suffix(archive.suffix + ".sha256")

    summary_path = evidence / "end-to-end-summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("pass") or summary.get("stop") != "STOP_FOR_GPT_REVIEW":
        raise RuntimeError("Phase 1B evidence is not at a passing review stop point")

    status = git(repo, "status", "--short", "--untracked-files=all")
    frozen_diff = git(repo, "diff", "--binary", FINAL_CORE_FREEZE_V2, "--", *FROZEN_PATHS)
    if frozen_diff.strip():
        raise RuntimeError("Frozen production core differs from Final Core Freeze v2")

    if package.exists():
        shutil.rmtree(package)
    for path in (archive, checksum):
        if path.exists():
            path.unlink()
    package.mkdir(parents=True)
    (package / "evidence").mkdir()

    handoff_text = handoff(summary, status, frozen_diff)
    (evidence / "GPT_REVIEW_HANDOFF.md").write_text(
        handoff_text, encoding="utf-8", newline="\n"
    )

    excluded = {package.resolve(), archive.resolve(), checksum.resolve()}
    for source in sorted(evidence.iterdir()):
        if source.resolve() in excluded or source.name == "gpt-review-package":
            continue
        if source.is_file():
            shutil.copy2(source, package / "evidence" / source.name)

    for relative in SOURCE_FILES:
        source = repo / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = package / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    (package / "git-status.txt").write_text(status, encoding="utf-8", newline="\n")
    (package / "frozen-core.diff").write_text(
        frozen_diff, encoding="utf-8", newline="\n"
    )
    (package / "GPT_REVIEW_HANDOFF.md").write_text(
        handoff_text, encoding="utf-8", newline="\n"
    )

    files = []
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.name != "review-package-manifest.json":
            files.append(
                {
                    "path": path.relative_to(package).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "schemaVersion": "shm-em-phase1b-gpt-review-package-v1",
        "finalCoreFreezeV2": FINAL_CORE_FREEZE_V2,
        "freezeRecordCommit": FREEZE_RECORD_COMMIT,
        "phase1bCommitted": False,
        "stop": "STOP_FOR_GPT_REVIEW",
        "sourceFileCount": len(SOURCE_FILES),
        "fileCountExcludingManifest": len(files),
        "files": files,
    }
    (package / "review-package-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    shutil.make_archive(str(archive.with_suffix("")), "zip", package)
    archive_hash = sha256(archive)
    checksum.write_text(
        f"{archive_hash}  {archive.name}\n", encoding="ascii", newline="\n"
    )
    print(
        json.dumps(
            {
                "package": str(package),
                "archive": str(archive),
                "archiveSha256": archive_hash,
                "files": len(files) + 1,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
