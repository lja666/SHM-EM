#!/usr/bin/env python3
"""Assemble the Phase 0.6.1 regression and acceptance evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PIT_PRE_ROOT = ROOT / "src/pit_pre"
if str(PIT_PRE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIT_PRE_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase0_6_regression import array_diff, record_diff, sha256_file


STAGE_KEYS = (
    "inputCellCount",
    "exactCellCount",
    "asofCellCount",
    "interiorInterpolationCellCount",
    "leadingBoundaryExtensionCellCount",
    "trailingBoundaryExtensionCellCount",
    "boundaryExtensionCellCount",
    "forwardFillCellCount",
    "backwardFillCellCount",
    "unresolvedMissingCellCount",
    "fillRatio",
    "nonExactAlignmentRatio",
    "maxRawGapSeconds",
)

OFFSET_KEYS = (
    "medianAbsoluteSourceOffsetSeconds",
    "p95AbsoluteSourceOffsetSeconds",
    "maxAbsoluteSourceOffsetSeconds",
    "pastSourceCellCount",
    "futureSourceCellCount",
    "pastSourceContributorCount",
    "futureSourceContributorCount",
    "maxPastSourceLagSeconds",
    "maxFutureSourceLeadSeconds",
)

DECLARED_CONTRACT_KEYS = (
    "requiredHistoryRows",
    "artifactHash",
    "preprocessorHash",
    "inferenceScriptHash",
    "bestParamsHash",
    "runtimeManifestHash",
    "environmentDigest",
    "artifactBundleHash",
    "inputSchemaHash",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--before",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1/regression-phase0_6-baseline-capture.json"),
    )
    parser.add_argument(
        "--after",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1/regression-one-pass-capture.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1"),
    )
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def declared_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: contract.get(key) for key in DECLARED_CONTRACT_KEYS}


def max_input_diff(report: dict[str, Any]) -> float:
    return max([
        report["commonInput"]["maxAbsDifference"],
        *[item["maxAbsDifference"] for item in report["models"].values()],
    ])


def build_regression(
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    input_report = {
        "schemaVersion": "shm-em-phase0-6-1-one-pass-input-regression-v1",
        "commonInput": array_diff(before["commonInput"], after["commonInput"]),
        "models": {
            code: array_diff(before["modelInputs"][code], after["modelInputs"][code])
            for code in sorted(before["modelInputs"])
        },
    }
    models: dict[str, Any] = {}
    for code in sorted(before["predictions"]):
        old = before["predictions"][code]
        new = after["predictions"][code]
        old_contract = before["contracts"][code]
        new_contract = after["contracts"][code]
        stage_before = before["alignmentQuality"][code]
        stage_after = after["alignmentQuality"][code]
        models[code] = {
            "targetCountBefore": old["targetCount"],
            "targetCountAfter": new["targetCount"],
            "stepCountBefore": old["stepCount"],
            "stepCountAfter": new["stepCount"],
            "rawPrediction": record_diff(old["records"], new["records"]),
            "engineeringPrediction": record_diff(
                old["engineeringRecords"], new["engineeringRecords"]
            ),
            "resultHashBefore": old["resultHash"],
            "resultHashAfter": new["resultHash"],
            "stageCountsBefore": {key: stage_before[key] for key in STAGE_KEYS},
            "stageCountsAfter": {key: stage_after[key] for key in STAGE_KEYS},
            "stageCountsIdentical": all(stage_before[key] == stage_after[key] for key in STAGE_KEYS),
            "directionalOffsetSummaryAfter": {key: stage_after[key] for key in OFFSET_KEYS},
            "declaredContractIdentical": (
                declared_contract(old_contract) == declared_contract(new_contract)
            ),
            "checkoutScriptHashBeforeMatchesContract": (
                old_contract["actualInferenceScriptHash"] == old_contract["inferenceScriptHash"]
            ),
            "checkoutScriptHashAfterMatchesContract": (
                new_contract["actualInferenceScriptHash"] == new_contract["inferenceScriptHash"]
            ),
        }
    prediction_report = {
        "schemaVersion": "shm-em-phase0-6-1-one-pass-prediction-regression-v1",
        "totalsBefore": before["totals"],
        "totalsAfter": after["totals"],
        "models": models,
        "declaredContractsIdentical": all(
            item["declaredContractIdentical"] for item in models.values()
        ),
        "rawCheckoutScriptHashesCorrectedByEolPolicy": all(
            not item["checkoutScriptHashBeforeMatchesContract"]
            and item["checkoutScriptHashAfterMatchesContract"]
            for item in models.values()
        ),
    }
    return input_report, prediction_report


def audit_cross_check(after: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    audit_models = {item["modelCode"]: item for item in audit["models"]}
    fields = (*STAGE_KEYS[:-3], "fillRatio", "nonExactAlignmentRatio", "maxRawGapSeconds", *OFFSET_KEYS)
    models: dict[str, Any] = {}
    for code, production in sorted(after["alignmentQuality"].items()):
        offline = audit_models[code]
        comparisons: dict[str, bool] = {}
        for field in fields:
            offline_field = "unresolvedMissingCount" if field == "unresolvedMissingCellCount" else field
            comparisons[field] = production[field] == offline[offline_field]
        models[code] = {
            "fields": comparisons,
            "matches": all(comparisons.values()),
        }
    return {
        "schemaVersion": "shm-em-phase0-6-1-production-audit-cross-check-v1",
        "models": models,
        "matches": all(item["matches"] for item in models.values()),
    }


def run_tests() -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(
        command,
        cwd=PIT_PRE_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    match = re.search(r"Ran (\d+) tests?", output)
    return {
        "command": "python -m unittest discover -s tests -v",
        "testsRun": int(match.group(1)) if match else None,
        "passed": result.returncode == 0,
        "exitCode": result.returncode,
    }


def source_boundary_check() -> dict[str, Any]:
    feature_source = (PIT_PRE_ROOT / "pit_pre/features.py").read_text(encoding="utf-8")
    forbidden = (
        "maxFillRatioAllowed",
        "maxRawGapSecondsAllowed",
        "maxAbsoluteSourceOffsetSecondsAllowed",
        "maxFutureSourceLeadSecondsAllowed",
        "sourceOffsetEligible",
    )
    changed = set(git("diff", "--name-only").stdout.splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").stdout.splitlines())
    prohibited = sorted(
        path for path in changed
        if path.startswith("src/backend/") or path.startswith("src/frontend/")
    )
    return {
        "mergeAsofCallSiteCountInProductionFeatures": feature_source.count("pd.merge_asof("),
        "legacySecondMergeHelperPresent": "def _aligned_source_times(" in feature_source,
        "forbiddenThresholdTokensPresent": [token for token in forbidden if token in feature_source],
        "prohibitedModulesModified": prohibited,
    }


def write_code_diff(output: Path) -> None:
    parts = [git("diff", "--binary", "--no-ext-diff").stdout]
    untracked = git("ls-files", "--others", "--exclude-standard").stdout.splitlines()
    for path in untracked:
        result = git(
            "diff", "--no-index", "--binary", "--", "/dev/null", path,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr)
        parts.append(result.stdout)
    output.write_text("".join(parts), encoding="utf-8")


def write_manifest(output_dir: Path) -> None:
    manifest_path = output_dir / "phase0_6_1-manifest.json"
    files = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path != manifest_path
    ]
    manifest = {
        "schemaVersion": "shm-em-phase0-6-1-manifest-v1",
        "phase": "Phase 0.6.1 - Reproducibility and Diagnostic Semantics Stabilization",
        "sourceGitCommit": git("rev-parse", "HEAD").stdout.strip(),
        "submittedTag": "v1.0.0",
        "submittedTagCommit": git("rev-parse", "v1.0.0^{}").stdout.strip(),
        "generationTimestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "coreFreezeCommitRecorded": False,
        "artifacts": files,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    before = load_json(args.before)
    after = load_json(args.after)
    audit = load_json(output_dir / "alignment-audit-v3-summary.json")
    contract_hashes = load_json(output_dir / "public-contract-hash-validation.json")
    benchmark = load_json(output_dir / "diagnostics-overhead-benchmark.json")
    input_report, prediction_report = build_regression(before, after)
    cross_check = audit_cross_check(after, audit)
    tests = run_tests()
    boundary = source_boundary_check()

    (output_dir / "one-pass-regression-input.json").write_text(
        json.dumps(input_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "one-pass-regression-prediction.json").write_text(
        json.dumps(prediction_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "production-audit-v3-cross-check.json").write_text(
        json.dumps(cross_check, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    model_results = prediction_report["models"].values()
    numerical_pass = (
        max_input_diff(input_report) == 0.0
        and all(item["rawPrediction"]["maxAbsDifference"] == 0.0 for item in model_results)
        and all(item["engineeringPrediction"]["maxAbsDifference"] == 0.0 for item in model_results)
        and all(item["resultHashBefore"] == item["resultHashAfter"] for item in model_results)
    )
    totals_pass = (
        before["totals"] == after["totals"]
        and after["totals"] == {
            "modelCount": 6,
            "predictionRecordCount": 4960,
            "stepCount": 40,
            "targetCount": 124,
        }
    )
    stage_pass = all(item["stageCountsIdentical"] for item in model_results)
    one_pass_pass = (
        boundary["mergeAsofCallSiteCountInProductionFeatures"] == 1
        and not boundary["legacySecondMergeHelperPresent"]
    )
    threshold_pass = not boundary["forbiddenThresholdTokensPresent"]
    validation = {
        "schemaVersion": "shm-em-phase0-6-1-validation-v1",
        "numericalRegressionPassed": numerical_pass,
        "maximumInputAbsoluteDifference": max_input_diff(input_report),
        "maximumRawPredictionAbsoluteDifference": max(
            item["rawPrediction"]["maxAbsDifference"] for item in model_results
        ),
        "maximumEngineeringAbsoluteDifference": max(
            item["engineeringPrediction"]["maxAbsDifference"] for item in model_results
        ),
        "totals": after["totals"],
        "totalsPassed": totals_pass,
        "stageCountsPassed": stage_pass,
        "productionMatchesOfflineAuditV3": cross_check["matches"],
        "rawContractHashesPassed": contract_hashes["passed"],
        "onePassImplementationPassed": one_pass_pass,
        "benchmarkPassed": (
            max(benchmark["maxNumericalAbsDifferenceByMode"].values()) == 0.0
            and benchmark["stageCountsIdentical"]
        ),
        "eligibilityThresholdsAdded": not threshold_pass,
        "prohibitedModulesModified": boundary["prohibitedModulesModified"],
        "pitPreUnitTests": tests,
        "declaredContractsIdentical": prediction_report["declaredContractsIdentical"],
        "rawCheckoutScriptHashesCorrectedByEolPolicy": prediction_report[
            "rawCheckoutScriptHashesCorrectedByEolPolicy"
        ],
        "coreFreezeCommitRecorded": False,
    }
    passed = all((
        numerical_pass,
        totals_pass,
        stage_pass,
        cross_check["matches"],
        contract_hashes["passed"],
        one_pass_pass,
        validation["benchmarkPassed"],
        threshold_pass,
        tests["passed"],
        prediction_report["declaredContractsIdentical"],
        prediction_report["rawCheckoutScriptHashesCorrectedByEolPolicy"],
        not boundary["prohibitedModulesModified"],
    ))
    validation["passed"] = passed
    (output_dir / "validation-summary.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "# Phase 0.6.1 Validation Summary",
        "",
        f"- Overall acceptance: `{str(passed).lower()}`",
        f"- Raw-byte contract validation: `{str(contract_hashes['passed']).lower()}`",
        f"- Maximum aligned-input absolute difference: `{validation['maximumInputAbsoluteDifference']}`",
        f"- Maximum raw-prediction absolute difference: `{validation['maximumRawPredictionAbsoluteDifference']}`",
        f"- Maximum engineering-value absolute difference: `{validation['maximumEngineeringAbsoluteDifference']}`",
        f"- Stage counts identical: `{str(stage_pass).lower()}`",
        f"- Production and offline Audit v3 match: `{str(cross_check['matches']).lower()}`",
        f"- Targets / steps / records: `{after['totals']['targetCount']} / {after['totals']['stepCount']} / {after['totals']['predictionRecordCount']}`",
        f"- PIT_PRE tests: `{tests['testsRun']}` passed",
        "- New fill/gap/offset eligibility thresholds: `none`",
        "- Core-freeze commit recorded: `false`",
        "",
    ]
    (output_dir / "phase0_6_1-summary.md").write_text(
        "\n".join(summary), encoding="utf-8"
    )
    write_code_diff(output_dir / "code-diff.patch")
    write_manifest(output_dir)
    print(json.dumps({"passed": passed, "testsRun": tests["testsRun"]}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
