#!/usr/bin/env python3
"""Compare the Docker/Linux reference result with the frozen Windows baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux", type=Path, default=Path("artifacts/revision/portability/linux-reference-reproduction.json"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/revision/portability"))
    return parser.parse_args()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = arguments()
    repo = Path(__file__).resolve().parents[2]
    linux = load(repo / args.linux)
    model_summary = load(repo / "artifacts/revision/manuscript/model-config-summary.json")
    expected_models = {
        item["modelCode"]: {
            "artifactHash": item["artifact"]["sha256"],
            "preprocessorHash": item["preprocessor"]["sha256"],
            "inferenceScriptHash": item["inferenceScript"]["sha256"],
            "inputSchemaHash": item["inputSchemaHash"],
            "runtimeManifestHash": item["runtimeManifestHash"],
            "requiredHistoryRows": item["requiredHistoryRows"],
        }
        for item in model_summary["models"]
    }
    linux_models = {item["modelCode"]: {key: item[key] for key in expected_models[item["modelCode"]]} for item in linux["models"]}
    checks = {
        "modelContractHashes": linux_models == expected_models,
        "modelCount": linux["modelCount"] == 6,
        "targetCount": linux["targetCount"] == 124,
        "predictionSteps": linux["predictionSteps"] == 40,
        "resultCount": linux["resultCount"] == 4960,
        "inputHashExact": linux["predictionInputHash"] == linux["expectedPredictionInputHash"],
        "normalizedOutputHashExact": linux["predictionOutputHash"] == linux["expectedPredictionOutputHash"],
        "gateLogicalState": linux["gate"]["resultIntegrityValid"] and linux["gate"]["executionEligible"],
        "futureStateLogicalState": linux["checks"]["futureState"],
        "evaluateSemantics": linux["checks"]["evaluateFormalSideEffectFree"] and linux["evaluate"]["eventCount"] >= 1,
        "executeProvenanceSemantics": linux["checks"]["executeFormalEvent"] and linux["checks"]["eventTrace"],
    }
    result = {
        "schemaVersion": "shm-em-phase2c-cross-platform-comparison-v1",
        "windowsBaseline": {"finalCoreFreezeV3": "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f", "source": "public dataset manifest and Phase 2B model-config summary"},
        "linuxDocker": {"source": args.linux.as_posix(), "executionEnvironment": linux["executionEnvironment"]},
        "hashes": {"input": {"windowsExpected": linux["expectedPredictionInputHash"], "linuxActual": linux["predictionInputHash"]}, "normalizedOutput": {"windowsExpected": linux["expectedPredictionOutputHash"], "linuxActual": linux["predictionOutputHash"]}},
        "stateHashComparison": {"status": "NOT_COMPARABLE_BY_DESIGN", "reason": "Project Future State stateHash includes batch identity; cross-environment batch identifiers differ. Logical risks and eligibility are compared instead."},
        "checks": checks,
        "exactPredictionReproduction": checks["inputHashExact"] and checks["normalizedOutputHashExact"],
        "pass": all(checks.values()),
        "toleranceApplied": False,
    }
    output = repo / args.output_root
    output.mkdir(parents=True, exist_ok=True)
    (output / "cross-platform-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# Cross-Platform Comparison",
        "",
        "The frozen public Windows baseline is compared with the Docker/Linux execution without changing the model contract or applying a numerical tolerance.",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines.extend(f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in checks.items())
    lines.extend(["", f"- Linux input hash: `{result['hashes']['input']['linuxActual']}`", f"- Linux normalized output hash: `{result['hashes']['normalizedOutput']['linuxActual']}`", "- Future State `stateHash` is not compared bitwise because it includes environment-specific batch identity; logical eligibility and risk semantics are compared.", "- No tolerance or relaxed hash contract was applied."])
    (output / "cross-platform-comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"exactPredictionReproduction": result["exactPredictionReproduction"], "checks": checks, "pass": result["pass"]}, indent=2))
    if not checks["normalizedOutputHashExact"]:
        print("STOP: Docker/Linux normalized output hash differs from the frozen Windows baseline.")
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
