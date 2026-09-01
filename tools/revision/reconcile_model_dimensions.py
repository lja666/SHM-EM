#!/usr/bin/env python3
"""Reconcile public model dimensions against frozen runtime artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib


ORDER = ("YD", "XD", "Strain", "Pressure", "water", "settlement")
DISPLAY = {"water": "Water", "settlement": "Settlement"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_line(path: Path, needle: str) -> int:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return number
    raise RuntimeError(f"Cannot find source anchor in {path}: {needle}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    artifacts = repo / "artifacts/revision/manuscript"
    regression_path = repo / "artifacts/revision/phase0_6/regression-input-matrix.json"
    config_path = artifacts / "model-config-summary.json"
    contract_path = artifacts / "data-model-contract-export.json"
    runner_path = repo / "src/pit_pre/pit_pre/cached_model_runner.py"

    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    model_configs = {item["modelCode"]: item for item in config["models"]}
    contract_models = {item["code"]: item for item in contract["models"]}

    common_shape = regression["commonInput"]["shapeBefore"]
    if common_shape != [16, 164]:
        raise RuntimeError(f"Unexpected common aligned matrix shape: {common_shape}")

    models: list[dict[str, Any]] = []
    for code in ORDER:
        summary = model_configs[code]
        contract_model = contract_models[code]
        preprocessor_path = repo / summary["preprocessor"]["path"]
        script_path = repo / summary["inferenceScript"]["path"]
        preprocessor = joblib.load(preprocessor_path)
        input_columns = list(preprocessor["input_columns"])
        target_columns = list(preprocessor["target_columns"])
        input_width = len(input_columns)
        output_targets = len(target_columns)
        environment_width = sum(column.endswith("water_value") for column in input_columns)
        contextual_width = input_width - environment_width
        architecture = summary["architecture"]
        history = int(summary["requiredHistoryRows"])
        m = int(architecture["historyWindowM"])
        lag = int(architecture["lag"])
        regression_shape = regression["models"][code]["shapeBefore"]

        checks = {
            "declaredHistoryCoversModelInput": history >= m + lag,
            "phase06RunnerFrameMatchesDeclaredHistoryAndPreprocessorWidth": regression_shape == [history, input_width],
            "preprocessorInputHashMatchesSummary": sha256(preprocessor_path) == summary["preprocessor"]["sha256"],
            "scriptHashMatchesSummary": sha256(script_path) == summary["inferenceScript"]["sha256"],
            "responseWidthMatchesTargets": architecture["responseDimension"] == output_targets,
            "environmentWidthMatchesArtifact": architecture["environmentDimension"] == environment_width,
            "contextWidthMatchesArtifact": architecture["contextualInputDimension"] == contextual_width,
        }
        if not all(checks.values()):
            raise RuntimeError(f"Dimension reconciliation failed for {code}: {checks}")

        model_mapping_count = contract_model.get(
            "modelFeatureMappingCount", contract_model.get("inputFeatureCount")
        )
        models.append(
            {
                "model": DISPLAY.get(code, code),
                "modelCode": code,
                "historyRows": history,
                "commonWideFeatureColumns": common_shape[1],
                "databaseModelFeatureMappingCount": model_mapping_count,
                "columnsPassedToPreprocessor": input_width,
                "runnerFrameShape": [history, input_width],
                "scaledModelMatrixShape": [m + lag, input_width],
                "tensorShapesEnteringModel": {
                    "response": [1, m, output_targets],
                    "environment": [1, lag, environment_width],
                    "contextual": [1, m, contextual_width],
                },
                "internalBranchWidths": {
                    "response": output_targets,
                    "environment": environment_width,
                    "transformedFeatures": contextual_width,
                },
                "outputTargets": output_targets,
                "interpretation": (
                    "The database model-feature mapping count identifies model-owned mappings/targets; "
                    "it is not the frozen preprocessor input width."
                ),
                "evidence": {
                    "phase06Matrix": {
                        "path": regression_path.relative_to(repo).as_posix(),
                        "shape": regression_shape,
                    },
                    "preprocessor": {
                        "path": preprocessor_path.relative_to(repo).as_posix(),
                        "sha256": sha256(preprocessor_path),
                        "inputColumnCount": input_width,
                        "targetColumnCount": output_targets,
                    },
                    "inferenceScript": {
                        "path": script_path.relative_to(repo).as_posix(),
                        "sha256": sha256(script_path),
                        "scaleLine": find_line(script_path, "values = scaler_all.transform(model_df)"),
                        "responseSliceLine": find_line(script_path, "x_response_np = values["),
                        "contextSliceLine": find_line(script_path, "x_cat_np = values["),
                        "environmentSliceLine": find_line(script_path, "x_env_np = values["),
                    },
                    "cachedRunner": {
                        "path": runner_path.relative_to(repo).as_posix(),
                        "preprocessorValidationLine": find_line(
                            runner_path, "_validate_preprocessor_columns(cached, input_cols"
                        ),
                        "modelInvocationLine": find_line(runner_path, "pred_scaled = cached.model("),
                    },
                    "weightDerivedArchitecture": architecture,
                },
                "checks": checks,
            }
        )

    result = {
        "schemaVersion": "shm-em-model-dimension-reconciliation-v1",
        "status": "PASS",
        "decision": "CASE_A_ACTUAL_ALIGNED_INPUT_IS_114_OR_164",
        "commonAlignedMatrixShape": common_shape,
        "commonWideFeatureColumns": common_shape[1],
        "models": models,
        "sourceBoundary": {
            "productionCoreModified": False,
            "newInferenceExecuted": False,
            "source": "Frozen preprocessors, model-weight-derived configuration, inference scripts, and Phase 0.6 matrices.",
        },
    }
    json_path = artifacts / "model-dimension-reconciliation.json"
    write_json(json_path, result)

    rows = []
    for item in models:
        tensors = item["tensorShapesEnteringModel"]
        branches = item["internalBranchWidths"]
        evidence = item["evidence"]
        rows.append(
            "| {model} | {history} | {common} | {pre} | response `{response}`; environment `{env}`; contextual `{context}` | "
            "{rw}/{ew}/{cw} | {targets} | Phase 0.6 `{phase}`; `{pp}`; `{script}` |".format(
                model=item["model"],
                history=item["historyRows"],
                common=item["commonWideFeatureColumns"],
                pre=item["columnsPassedToPreprocessor"],
                response="x".join(map(str, tensors["response"])),
                env="x".join(map(str, tensors["environment"])),
                context="x".join(map(str, tensors["contextual"])),
                rw=branches["response"], ew=branches["environment"], cw=branches["transformedFeatures"],
                targets=item["outputTargets"],
                phase="x".join(map(str, evidence["phase06Matrix"]["shape"])),
                pp=evidence["preprocessor"]["path"],
                script=evidence["inferenceScript"]["path"],
            )
        )

    markdown = "\n".join(
        [
            "# Model Dimension Reconciliation",
            "",
            "## Decision",
            "",
            "**PASS - Case A.** The frozen preprocessors receive 114 aligned feature columns for YD, XD, Strain, Pressure, and Water, and 164 for Settlement. The previously reported values 42/42/14/14/2/50 were database model-feature mapping counts; 42/42/14/14/2 are also output widths, while 50 is the Settlement-owned mapping count. They are not complete model input widths.",
            "",
            "The common aligned input is a `16 x 164` numerical feature matrix; `time` and `time1` are excluded from that count. Each model selects the ordered columns declared by its frozen preprocessor before scaling. The Transformer-CNN receives three tensors rather than one unsplit tensor: a response branch, a two-channel water/environment branch, and a contextual transformed-feature branch.",
            "",
            "No model inference, training, or production-core change was performed for this reconciliation.",
            "",
            "## Reconciled dimensions",
            "",
            "| Model | History rows | Common/wide columns | Columns passed to preprocessor | Tensor feature width entering model | Internal branch width (response/environment/context) | Output targets | Evidence |",
            "|---|---:|---:|---:|---|---|---:|---|",
            *rows,
            "",
            "## Evidence chain",
            "",
            "1. `WideTableBuilder` creates the common 164-feature aligned table; the Phase 0.6 capture removes `time` and `time1` before recording its `16 x 164` matrix.",
            "2. `CachedModelRunner` reconstructs ordered feature groups, requires exact equality with each frozen preprocessor's `input_columns`, and invokes the model with `x_response`, `x_env`, and `x_cat`. The inference scripts select their final `m + lag` rows before scaling. Pressure declares a conservative 13-row runner window but consumes its final 12 rows (`m=10`, `lag=2`); the other five declared windows equal `m + lag`.",
            "3. Each frozen inference script slices those three tensors from the scaled 114- or 164-column matrix. Weight-derived `responseDimension`, `environmentDimension`, and `contextualInputDimension` agree with the slice widths.",
            "4. The Phase 0.6 per-model matrices are exactly `history rows x preprocessor input columns`: Pressure `13 x 114`, Strain `13 x 114`, XD `12 x 114`, YD `16 x 114`, Settlement `12 x 164`, and Water `13 x 114`.",
            "5. The machine-readable companion records source paths, SHA-256 values, source anchors, tensor shapes, and all equality checks.",
            "",
            "## Contract terminology correction",
            "",
            "Public contract exports now distinguish `modelFeatureMappingCount` from `alignedInputFeatureCount` and `outputTargetCount`. The model-feature mapping count is retained because it describes database ownership and target binding, but it must not be labelled as the complete inference input width.",
        ]
    )
    (artifacts / "MODEL_DIMENSION_RECONCILIATION.md").write_text(
        markdown + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"status": "PASS", "models": len(models), "commonShape": common_shape}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
