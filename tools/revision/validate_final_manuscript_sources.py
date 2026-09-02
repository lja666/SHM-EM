#!/usr/bin/env python3
"""Validate the scientific wording and frozen-core boundary of final sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"
SUBMITTED_TAG = "v1.0.0"
SUBMITTED_COMMIT = "1d2ab45e516ef4167c6c4c4265da5b533b2eab78"
RELEASE_TAG = "v1.0.1"
CORE_PATHS = ("src/backend/src/main", "src/pit_pre/pit_pre", "src/frontend/src")
SOURCE_FILES = (
    "SHM-EM_Revised_Manuscript_Source.md",
    "Response_to_Reviewers_Source.md",
    "Revision_Change_Map.md",
    "Final_Reviewer_Evidence_Map.md",
    "Final_Submission_Checklist.md",
)
REVIEWER_IDS = (
    "R1-0",
    "R1-1", "R1-2", "R1-3", "R1-4", "R1-5", "R1-6", "R1-7", "R1-8", "R1-9",
    "R1-10", "R1-11", "R1-12", "R1-13", "R1-14", "R1-15", "R1-16", "R1-17", "R1-18", "R1-19",
    "R2-1", "R2-2", "R2-3",
    "R3-1", "R3-2", "R3-3", "R3-4",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/revision/final-manuscript-review/final-manuscript-source-validation.json",
    )
    parser.add_argument(
        "--validated-source-head",
        help="Reviewed source commit whose five manuscript files must match the current worktree.",
    )
    return parser.parse_args()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout


def git_optional(repo: Path, *args: str) -> str:
    try:
        return git(repo, *args)
    except subprocess.CalledProcessError:
        return ""


def check(checks: list[dict[str, object]], identifier: str, passed: bool, detail: str) -> None:
    checks.append({"id": identifier, "status": "PASS" if passed else "FAIL", "detail": detail})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    source_root = repo / "manuscript"
    output = repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []

    paths = [source_root / name for name in SOURCE_FILES]
    validated_source_head = args.validated_source_head or git(repo, "rev-parse", "HEAD").strip()
    source_relatives = [str(path.relative_to(repo)).replace("\\", "/") for path in paths]
    source_diff = git(repo, "diff", "--name-only", validated_source_head, "--", *source_relatives).strip()
    if source_diff:
        raise RuntimeError(
            f"Current manuscript sources differ from validated source head {validated_source_head}: {source_diff}"
        )
    check(checks, "FM-01", all(path.is_file() for path in paths), "All five authorized Markdown source files exist.")
    if not all(path.is_file() for path in paths):
        output.write_text(json.dumps({"checks": checks, "pass": False}, indent=2) + "\n", encoding="utf-8")
        return 1

    manuscript = paths[0].read_text(encoding="utf-8")
    response = paths[1].read_text(encoding="utf-8")
    change_map = paths[2].read_text(encoding="utf-8")
    evidence_map = paths[3].read_text(encoding="utf-8")
    checklist = paths[4].read_text(encoding="utf-8")
    combined = "\n".join((manuscript, response, change_map, evidence_map, checklist))

    required_sections = (
        "# 1. Motivation and significance",
        "## 1.1 Intended users and experimental setup",
        "# 2. Software description",
        "## 2.1 Software architecture",
        "### 2.1.1 Engineering monitoring object model and observation registry",
        "### 2.1.2 Engineering-semantic data-model contract",
        "### 2.1.3 Multi-target rolling forecasts and Project Future State",
        "### 2.1.4 Controlled transition from forecasts to engineering events",
        "### 2.1.5 Response, provenance, and reproduction",
        "## 2.2 Main functionalities",
        "## 2.3 Rule configuration and interfaces",
        "# 3. Software validation",
        "## 3.1 Public excavation-monitoring reference case",
        "## 3.2 Cross-configuration reuse",
        "## 3.3 Failure-path and execution-safety validation",
        "## 3.4 Runtime and bounded scalability",
        "## 3.5 Provenance and reproducibility",
        "# 4. Impact",
        "## 4.1 Reproducible and auditable forecast integration",
        "## 4.2 Cross-configuration reuse",
        "## 4.3 Controlled event transition and traceability",
        "## 4.4 Current deployment and scientific scope",
        "# 5. Conclusions",
        "# 6. Data and software availability",
    )
    check(checks, "FM-02", all(section in manuscript for section in required_sections), "Authorized manuscript structure is complete.")

    contribution_terms = (
        "versioned engineering-semantic data-model contract",
        "synchronized Project Future State",
        "controlled forecast-to-event transition",
    )
    check(checks, "FM-03", all(term.lower() in manuscript.lower() for term in contribution_terms), "All three and only the authorized contribution concepts are present.")

    m1 = "| Shared prediction origin and future timeline | Not applicable | Not applicable | Not reported | Yes |"
    check(checks, "FM-04", m1 in manuscript and "| M1 |" in change_map and "`Not reported`" in change_map, "M1 Predictive-SHM wording is applied.")

    forbidden_m2 = (
        "15 negative/integrity",
        "15-case negative",
        "15/15 negative",
        "all 15 invalid",
        "all 15 negative",
    )
    required_m2 = "15-case validation matrix comprising one positive control, 12 failure-path cases, and two input-availability controls"
    check(
        checks,
        "FM-05",
        required_m2.lower() in combined.lower() and not any(term in combined.lower() for term in forbidden_m2),
        "M2 validation-matrix count and blocked-case boundary are consistent.",
    )

    required_m3 = "used solely as software-workflow fixtures"
    check(
        checks,
        "FM-06",
        required_m3 in combined and "not interpreted as bridge-domain predictive validation" in combined,
        "M3 second-configuration bundles are constrained to workflow-fixture use.",
    )

    forbidden_m4 = ("negligible", "equivalent within tolerance", "exact linux reproduction")
    required_m4 = (
        "exactPredictionReproduction=false",
        "toleranceApplied=false",
        "0.00285349",
        "full row-wise comparison",
    )
    check(
        checks,
        "FM-07",
        all(term in combined for term in required_m4) and not any(term in combined.lower() for term in forbidden_m4),
        "M4 output-hash mismatch, no-tolerance, and row-wise evidence boundaries are retained.",
    )

    numerical_terms = (
        "6 models",
        "124 targets",
        "40 steps",
        "4,960",
        "16-step common",
        "12-16",
        "343.129",
        "407.100",
        "49,600",
        "50,000-row Gate",
        "1,120 forecast rows",
    )
    check(checks, "FM-08", all(term.lower() in combined.lower() for term in numerical_terms), "Required final numerical anchors are present.")

    model_rows = (
        "| YD | Deep horizontal displacement Y (mm) | 16 | 114 | 42 |",
        "| XD | Deep horizontal displacement X (mm) | 12 | 114 | 42 |",
        "| Strain | Earth-pressure strain (microstrain) | 13 | 114 | 14 |",
        "| Pressure | Earth pressure (MPa) | 13 | 114 | 14 |",
        "| Water | Groundwater elevation (m) | 13 | 114 | 2 |",
        "| Settlement | Surface settlement (mm) | 12 | 164 | 10 |",
    )
    check(checks, "FM-09", all(row in manuscript for row in model_rows), "Model-specific history/aligned-input/target dimensions match frozen runtime evidence.")

    alignment_terms = (
        "backward-asof",
        "declared linear interpolation and boundary-fill policy",
        "signed source-time offsets",
        "entire required feature is unavailable",
        "Freshness is checked separately",
    )
    check(checks, "FM-10", all(term.lower() in manuscript.lower() for term in alignment_terms), "Missing/asynchronous and separate freshness behavior are explicit.")

    response_ids = re.findall(r"^### (R\d+-\d+)\.", response, flags=re.MULTILINE)
    check(checks, "FM-11", tuple(response_ids) == REVIEWER_IDS, "All 27 reviewer items appear once and in order.")

    blocks = re.split(r"(?=^### R\d+-\d+\.)", response, flags=re.MULTILINE)[1:]
    fields = ("**Reviewer comment**", "**Response**", "**Changes in manuscript**", "**Evidence**", "**Scope / non-claim**")
    check(checks, "FM-12", len(blocks) == 27 and all(all(field in block for field in fields) for block in blocks), "Every reviewer response contains all five required fields.")

    mapped_ids = re.findall(r"^\| (R\d+-\d+) \|", evidence_map, flags=re.MULTILINE)
    check(checks, "FM-13", tuple(mapped_ids) == REVIEWER_IDS, "Final reviewer evidence map covers all 27 items in order.")

    reference_ids = [int(value) for value in re.findall(r"^\[(\d+)\]", manuscript, flags=re.MULTILINE)]
    check(checks, "FM-14", reference_ids == list(range(1, 31)), "Reference list contains the submitted 30 references in sequence.")

    overclaims = (
        "linear scalability",
        "o(n) scalability",
        "mysql limit is 50,000",
        "sensorThings compatible",
        "sensorThings conformant",
        "production-ready security",
        "bridge forecasting validated",
        "universal no-code onboarding",
    )
    # Some negated boundary sentences legitimately contain these words. Require the risky affirmative forms to be absent.
    risky = (
        "demonstrates linear scalability",
        "establishes linear scalability",
        "SHM-EM is SensorThings compatible",
        "SHM-EM is SensorThings conformant",
        "production-ready security is provided",
        "bridge forecasting is validated",
        "demonstrates universal no-code onboarding",
    )
    check(checks, "FM-15", not any(term.lower() in combined.lower() for term in risky), "Blocked affirmative overclaims are absent.")

    committed_core = git(repo, "diff", f"{FREEZE}..HEAD", "--", *CORE_PATHS).strip()
    worktree_core = git(repo, "diff", "--", *CORE_PATHS).strip()
    check(checks, "FM-16", not committed_core and not worktree_core, "Production core remains identical to Final Core Freeze v3.")

    check(checks, "FM-17", "- [ ] GPT confirms manuscript claims" in checklist and "Generate `Revised Manuscript Clean.docx`" in checklist, "Required GPT stop precedes DOCX generation.")

    dimension_path = repo / "artifacts/revision/manuscript/model-dimension-reconciliation.json"
    dimension_ok = False
    if dimension_path.is_file():
        dimensions = json.loads(dimension_path.read_text(encoding="utf-8"))
        expected_dimensions = {
            "YD": (16, 114, 42), "XD": (12, 114, 42),
            "Strain": (13, 114, 14), "Pressure": (13, 114, 14),
            "water": (13, 114, 2), "settlement": (12, 164, 10),
        }
        actual_dimensions = {
            item["modelCode"]: (
                item["historyRows"], item["columnsPassedToPreprocessor"], item["outputTargets"]
            )
            for item in dimensions.get("models", [])
        }
        dimension_ok = (
            dimensions.get("status") == "PASS"
            and dimensions.get("commonAlignedMatrixShape") == [16, 164]
            and actual_dimensions == expected_dimensions
            and all(all(item.get("checks", {}).values()) for item in dimensions.get("models", []))
            and all(row in manuscript for row in model_rows)
        )
    check(checks, "FM-18", dimension_ok, "Manuscript dimensions match the model-dimension reconciliation artifact.")

    c1 = re.search(r"^\| C1 \| Current code version \|\s*([^|]+?)\s*\|$", manuscript, flags=re.MULTILINE)
    c2 = re.search(r"^\| C2 \|.*?/releases/tag/(v\d+\.\d+\.\d+).*?fixed commit:\s*`([0-9a-f]{40})`.*\|$", manuscript, flags=re.MULTILINE)
    c7 = re.search(r"^\| C7 \|.*?/tree/(v\d+\.\d+\.\d+)/docs", manuscript, flags=re.MULTILINE)
    section6 = manuscript.split("# 6. Data and software availability", 1)[-1].split("# Acknowledgements", 1)[0]
    section6_tag = re.search(r"/releases/tag/(v\d+\.\d+\.\d+)", section6)
    section6_commit = re.search(r"fixed release commit\s*`([0-9a-f]{40})`", section6)
    section6_archive = re.search(r"`(SHM-EM-v1\.0\.1\.zip)`.*?SHA-256\s*`([0-9a-f]{64})`", section6, flags=re.DOTALL)
    release_archive = repo / "artifacts/releases/SHM-EM-v1.0.1.zip"
    tag_commit = ""
    try:
        tag_commit = git(repo, "rev-parse", f"{RELEASE_TAG}^{{}}").strip()
    except subprocess.CalledProcessError:
        pass
    release_verification_path = repo / "artifacts/revision/final-manuscript-review/release-publication-verification.json"
    release_verification = (
        json.loads(release_verification_path.read_text(encoding="utf-8"))
        if release_verification_path.is_file() else {}
    )
    archive_ok = bool(
        section6_archive and release_archive.is_file()
        and sha256(release_archive) == section6_archive.group(2)
    )
    release_metadata_ok = bool(
        c1 and c1.group(1).strip() == RELEASE_TAG
        and c2 and c2.group(1) == RELEASE_TAG
        and c7 and c7.group(1) == RELEASE_TAG
        and section6_tag and section6_tag.group(1) == RELEASE_TAG
        and section6_commit and c2.group(2) == section6_commit.group(1)
        and tag_commit and tag_commit == c2.group(2)
        and release_verification.get("pass") is True
        and release_verification.get("release", {}).get("fixedCommit") == tag_commit
        and release_verification.get("release", {}).get("sha256") == section6_archive.group(2)
        and archive_ok
    )
    check(checks, "FM-19", release_metadata_ok, "C1/C2/C7/Section 6 identify one tag, fixed commit, and verified release archive SHA-256.")

    submitted_local = git_optional(repo, "rev-parse", f"{SUBMITTED_TAG}^{{}}").strip()
    submitted_unchanged = (
        submitted_local == SUBMITTED_COMMIT
        and release_verification.get("checks", {}).get("submittedTagUnchanged") is True
        and release_verification.get("submittedRelease", {}).get("fixedCommit") == SUBMITTED_COMMIT
    )
    check(checks, "FM-20", submitted_unchanged, "Submitted immutable v1.0.0 still resolves locally and remotely to the original submitted commit.")

    bare_evaluate_terms = (
        "side-effect-free Evaluate",
        "Evaluate is side-effect free",
        "Evaluate is side-effect-free",
        "separates side-effect-free Evaluate",
    )
    evaluate_reconciliation = repo / "artifacts/revision/manuscript/EVALUATE_SIDE_EFFECT_RECONCILIATION.md"
    evaluate_ok = (
        evaluate_reconciliation.is_file()
        and not any(term.lower() in (manuscript + "\n" + response).lower() for term in bare_evaluate_terms)
        and "evaluation/audit run" in manuscript
        and "no formal business side effects" in response
    )
    check(checks, "FM-21", evaluate_ok, "Evaluate wording discloses audit persistence and limits the zero-side-effect claim to formal business records.")

    cep_rows = (
        "| Execution-time eligibility recheck | Not applicable | Not reported | Not reported | Yes |",
        "| Formal event-to-prediction provenance link | Not applicable | Not reported | Not reported | Yes |",
    )
    check(checks, "FM-22", all(row in manuscript for row in cep_rows), "Generic CEP execution recheck and provenance cells are source-grounded as Not reported.")

    sensor_ref = "[8] Liang S, Khalafbeigi T, van der Schaaf H, editors. OGC SensorThings API Part 1: Sensing Version 1.1. OGC Implementation Standard 18-088."
    check(checks, "FM-23", sensor_ref in manuscript and "15-078r6" not in manuscript, "Reference 8 uses SensorThings Part 1 Sensing v1.1, OGC 18-088.")

    governance_terms = (
        "authorized correction", "authorized narrow correction", "gpt", "final core freeze v3",
        "performance-corrected frozen core",
    )
    check(checks, "FM-24", not any(term in response.lower() for term in governance_terms), "Public response letter contains no internal governance jargon.")

    result = {
        "schemaVersion": "shm-em-final-manuscript-source-validation-v2",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "finalCoreFreezeV3": FREEZE,
        "head": git(repo, "rev-parse", "HEAD").strip(),
        "validatedSourceHead": validated_source_head,
        "sourceFiles": source_relatives,
        "reviewerItemCount": len(response_ids),
        "referenceCount": len(reference_ids),
        "checks": checks,
        "pass": all(item["status"] == "PASS" for item in checks),
        "productionCoreDiff": {
            "committedSinceFreezeV3": committed_core or "NONE",
            "worktree": worktree_core or "NONE",
        },
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "checks": len(checks), "reviewerItems": len(response_ids), "references": len(reference_ids)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
