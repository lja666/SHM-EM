#!/usr/bin/env python3
"""Collect manuscript-facing test families without double-counting overlapping scopes."""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=Path("artifacts/revision/manuscript")
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"Required evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def surefire(repo: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_root = repo / "src/backend/target/surefire-reports"
    files = sorted(report_root.glob("TEST-*.xml"))
    if not files:
        raise RuntimeError("No Maven Surefire XML reports were found")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    cases = []
    for path in files:
        root = ET.parse(path).getroot()
        for key in totals:
            totals[key] += int(root.attrib.get(key, "0"))
        for case in root.findall(".//testcase"):
            status = "PASS"
            if case.find("failure") is not None:
                status = "FAIL"
            elif case.find("error") is not None:
                status = "ERROR"
            elif case.find("skipped") is not None:
                status = "SKIPPED"
            cases.append(
                {
                    "suite": case.attrib.get("classname") or root.attrib.get("name"),
                    "name": case.attrib.get("name"),
                    "status": status,
                    "seconds": float(case.attrib.get("time", "0") or 0),
                    "report": path.relative_to(repo).as_posix(),
                }
            )
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["suiteFiles"] = len(files)
    totals["pass"] = totals["failures"] == 0 and totals["errors"] == 0
    return totals, cases


def pit_pre_inventory(repo: Path) -> dict[str, Any]:
    test_files = sorted((repo / "src/pit_pre/tests").glob("test_*.py"))
    methods = []
    for path in test_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                methods.append(f"{path.name}::{node.name}")
    return {"files": len(test_files), "cases": len(methods), "caseIds": sorted(methods)}


def future_state_boundary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    selected = {
        item["name"]: item for item in cases
        if item["suite"] and item["suite"].endswith("ProjectFutureStateServiceImplTest")
    }
    coverage = {
        "aggregatesConsecutiveForecastRiskAndKeepsObservedRiskSeparate": [
            "one-step does not satisfy a two-step threshold",
            "consecutive-step exceedance", "observed/forecast separation", "earliest exceedance",
        ],
        "rejectsPolicyHashDriftBeforeAggregation": ["policy version/hash integrity"],
        "leavesFeatureUnassessedWhenNoApplicableRuleExists": ["no applicable rule", "unassessed target"],
        "distinguishesStrictAndInclusiveExactThresholds": ["exact threshold", "operator boundary"],
        "aggregatesMultipleTargetsAndStationsByHighestSeverityAndEarliestTime": [
            "multi-target station", "multi-station project", "severity ordering", "earliest exceedance tie",
        ],
        "producesDeterministicStateHashForEquivalentInput": ["deterministic state hash"],
    }
    results = []
    for name, boundaries in coverage.items():
        case = selected.get(name)
        results.append(
            {
                "test": name, "boundaries": boundaries,
                "status": None if case is None else case["status"],
                "seconds": None if case is None else case["seconds"],
            }
        )
    return {
        "schemaVersion": "shm-em-future-state-boundary-tests-v1",
        "source": "Maven Surefire XML for ProjectFutureStateServiceImplTest",
        "productionAlgorithmModified": False,
        "cases": results,
        "pass": all(item["status"] == "PASS" for item in results),
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# SHM-EM Software Testing Summary",
        "",
        "Test families are reported as independent evidence scopes. The overall total is intentionally not computed because backend cases, failure injections, end-to-end checks, and reproduction benchmarks overlap in behavior and would otherwise be double-counted.",
        "",
        "| Test family | Cases/checks | Passed | Status | Evidence |",
        "|---|---:|---:|---|---|",
    ]
    for family in summary["families"]:
        lines.append(
            f"| {family['name']} | {family['cases']} | {family['passed']} | {family['status']} | `{family['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Counting policy",
            "",
            "- Maven Surefire is the primary count for backend test methods at this checkout.",
            "- PIT_PRE test methods are counted from source and their status is taken from the final recorded unittest run.",
            "- P00/F01-F12/I01-I02 are reported as a 15-case validation matrix comprising one positive control, 12 failure-path cases, and two input-availability controls, even when a case is also represented by a unit test.",
            "- Phase 1B B9-B15 are seven acceptance checks for one end-to-end second-configuration workflow, not seven independent unit tests.",
            "- Frontend type checking and production build are two checks from one build pipeline.",
            "- No statement about code-coverage percentage is made because no stable coverage instrument is part of the submitted release.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    root = repo / args.output_root
    backend, backend_cases = surefire(repo)
    pit_inventory = pit_pre_inventory(repo)
    route_root = repo / "artifacts/revision/benchmarks/route-p"
    final_regression = load_json(root / "phase2b-final-regression.json")
    final_checks = {item["id"]: item for item in final_regression["checks"]}
    matrix = load_json(route_root / "failure-regression/failure-matrix-v2.json")
    phase1b = load_json(route_root / "phase1b-regression.json")
    reference = load_json(repo / "artifacts/revision/benchmarks/reference/reference-summary.json")
    matrix_passed = sum(1 for item in matrix if item.get("pass"))
    functional_checks = phase1b["functionalChecks"]
    phase1b_passed = sum(1 for item in functional_checks.values() if item.get("pass"))
    backend_command_pass = final_checks["BACKEND_MAVEN_TEST_PACKAGE"]["pass"]
    pit_pre_pass = final_checks["PIT_PRE_UNITTEST"]["pass"]
    frontend_pass = final_checks["FRONTEND_PRODUCTION_BUILD"]["pass"]
    families = [
        {
            "id": "BACKEND_SUREFIRE", "name": "Backend unit/service/API tests",
            "cases": backend["tests"], "passed": backend["passed"],
            "status": "PASS" if backend["pass"] and backend_command_pass else "FAIL",
            "evidence": "src/backend/target/surefire-reports/TEST-*.xml",
            "countingScope": "unique Maven testcase executions in the final run",
        },
        {
            "id": "PIT_PRE_UNITTEST", "name": "PIT_PRE contract/alignment/integrity tests",
            "cases": pit_inventory["cases"], "passed": pit_inventory["cases"] if pit_pre_pass else 0,
            "status": "PASS" if pit_pre_pass else "FAIL",
            "evidence": "artifacts/revision/manuscript/phase2b-final-regression.json",
            "countingScope": "test methods in src/pit_pre/tests; status from the Phase 2B final unittest run",
        },
        {
            "id": "FAILURE_MATRIX", "name": "Negative and persisted-integrity matrix",
            "cases": len(matrix), "passed": matrix_passed,
            "status": "PASS" if matrix_passed == len(matrix) == 15 else "FAIL",
            "evidence": "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.json",
            "countingScope": "P00, F01-F12, I01-I02 once each",
        },
        {
            "id": "PHASE1B_E2E", "name": "Second-configuration end-to-end acceptance",
            "cases": len(functional_checks), "passed": phase1b_passed,
            "status": "PASS" if phase1b_passed == len(functional_checks) else "FAIL",
            "evidence": "artifacts/revision/benchmarks/route-p/phase1b-regression.json",
            "countingScope": "B9-B15 acceptance checks for one workflow",
        },
        {
            "id": "FRONTEND_VALIDATION", "name": "Frontend typecheck and production build",
            "cases": 2, "passed": 2 if frontend_pass else 0,
            "status": "PASS" if frontend_pass else "FAIL",
            "evidence": "artifacts/revision/manuscript/phase2b-final-regression.json",
            "countingScope": "vue-tsc type checking followed by the Vite production bundle in npm run build",
        },
        {
            "id": "REFERENCE_E2E", "name": "Public reference end-to-end reproduction",
            "cases": 1, "passed": 1 if reference["pass"] else 0,
            "status": "PASS" if reference["pass"] else "FAIL",
            "evidence": "artifacts/revision/benchmarks/reference/reference-summary.json",
            "countingScope": "one complete six-model reference workflow",
        },
    ]
    result = {
        "schemaVersion": "shm-em-software-test-summary-v1",
        "finalCoreFreezeV3": "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f",
        "families": families,
        "backend": {**backend, "cases": backend_cases},
        "pitPreInventory": pit_inventory,
        "doubleCountingPolicy": "No global case total; family scopes overlap and are reported independently.",
        "allFamiliesPass": all(item["status"] == "PASS" for item in families),
        "finalRegression": final_regression,
    }
    write_json(root / "software-test-summary.json", result)
    root.mkdir(parents=True, exist_ok=True)
    with (root / "software-test-summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "name", "cases", "passed", "status", "evidence", "countingScope"])
        writer.writeheader()
        writer.writerows(families)
    (root / "software-test-summary.md").write_text(markdown(result), encoding="utf-8", newline="\n")
    boundary = future_state_boundary(backend_cases)
    write_json(root / "future-state-boundary-tests.json", boundary)
    if not result["allFamiliesPass"] or not boundary["pass"]:
        raise RuntimeError("Final test summary contains a failed family or Future State boundary")
    print(json.dumps({"families": len(families), "allFamiliesPass": True, "futureStateCases": len(boundary["cases"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
