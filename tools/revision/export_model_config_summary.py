#!/usr/bin/env python3
"""Export verifiable six-model configuration metadata without inferred claims."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("artifacts/revision/manuscript/data-model-contract-export.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/revision/manuscript/model-config-summary.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/revision/MODEL_CONFIG_SUMMARY.md"),
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def resolve(pit_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(str(value).replace("\\", "/"))
    return path if path.is_absolute() else (pit_root / path).resolve()


def literal_assignment(script: Path, name: str) -> Any:
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    return None


def state_dict(path: Path) -> dict[str, Any]:
    loaded = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(loaded, dict) and isinstance(loaded.get("state_dict"), dict):
        loaded = loaded["state_dict"]
    if not isinstance(loaded, dict):
        raise RuntimeError(f"Unsupported model artifact structure: {path}")
    result = {}
    for key, value in loaded.items():
        normalized = key[7:] if key.startswith("module.") else key
        result[normalized] = value
    return result


def shape(state: dict[str, Any], key: str) -> list[int] | None:
    value = state.get(key)
    return None if value is None or not hasattr(value, "shape") else [int(item) for item in value.shape]


def script_default(script_text: str, field: str) -> int | None:
    match = re.search(rf'params\.get\("{re.escape(field)}",\s*(\d+)\)', script_text)
    return None if match is None else int(match.group(1))


def markdown(value: dict[str, Any]) -> str:
    lines = [
        "# SHM-EM Six-Model Configuration Summary",
        "",
        f"Final Core Freeze v3: `{value['finalCoreFreezeV3']}`.",
        "",
        "This file is generated from the database-derived contract, immutable bundle metadata, actual inference scripts, parameter files, runtime manifest, and model weight shapes. Parameters that cannot be independently recovered are not guessed.",
        "",
        "| Model | History | Inputs | Targets | d_model | Heads | FF dim | CNN channels/kernel | Dropout | Params source | Hashes |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for model in value["models"]:
        architecture = model["architecture"]
        checks = model["hashChecks"]
        lines.append(
            "| {code} | {history} | {inputs} | {targets} | {d_model} | {heads} | {ff} | {conv}/{kernel} | {dropout:.6f} | {source} | {hashes} |".format(
                code=model["modelCode"], history=model["requiredHistoryRows"],
                inputs=model["inputFeatureCount"], targets=model["outputTargetCount"],
                d_model=architecture["dModel"], heads=architecture["numHeads"],
                ff=architecture["feedForwardHiddenDimension"],
                conv=architecture["convolutionHiddenChannels"], kernel=architecture["kernelSize"],
                dropout=architecture["dropout"], source=model["parameterSource"]["type"],
                hashes="PASS" if all(checks.values()) else "FAIL",
            )
        )
    lines.extend(
        [
            "",
            "## Shared deployed architecture",
            "",
            "Every bundle uses one custom Transformer encoder layer followed by response, environment, and transformed-feature 1-D convolution branches and one final convolution. `d_model` is the attention input dimension. The deployed rolling pipeline persists 40 future steps at 3-minute intervals; the model-internal direct-output chunk is `n=3` and the historical response window is `m=10` where encoded by the script/parameter contract.",
            "",
            "The number of attention heads and dropout cannot be recovered uniquely from tensor shapes. They are therefore taken only from the checked best-parameter file, or from the inference script's explicit fallback contract for YD. YD is marked `script_fallback`; it has no separate best-parameter artifact.",
            "",
            "## Reproducibility boundary",
            "",
            "The current bundles are CPU-executed point-forecast models. They do not emit calibrated predictive intervals or probabilistic exceedance. The execution gate validates software/data integrity and eligibility; it does not convert a point forecast into a statistical confidence guarantee.",
            "",
            "The full hashes, paths, tensor-derived dimensions, and parameter provenance are in `artifacts/revision/manuscript/model-config-summary.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    contract = json.loads((repo / args.contract).read_text(encoding="utf-8"))
    pit_root = repo / "src/pit_pre"
    features = contract["features"]
    models = []
    for model in contract["models"]:
        config = model["runtimeConfig"]
        script = resolve(pit_root, config["scriptPath"])
        artifact = resolve(pit_root, model["artifactUri"])
        preprocessor = resolve(pit_root, model["preprocessorUri"])
        best_params_path = resolve(pit_root, config.get("bestParamsPath"))
        runtime_manifest = resolve(pit_root, config["runtimeManifestPath"])
        required_paths = [script, artifact, preprocessor, runtime_manifest]
        if any(path is None or not path.is_file() for path in required_paths):
            raise RuntimeError(f"Model {model['code']} has a missing runtime artifact")

        if best_params_path is not None:
            if not best_params_path.is_file():
                raise RuntimeError(f"Model {model['code']} best-parameter file is missing")
            params = json.loads(best_params_path.read_text(encoding="utf-8"))
            parameter_source = {
                "type": "best_params_file",
                "path": best_params_path.relative_to(repo).as_posix(),
                "note": "Parameters not encoded by tensor shape are read from this hash-checked file.",
            }
        else:
            params = literal_assignment(script, "FALLBACK_PARAMS")
            if not isinstance(params, dict):
                raise RuntimeError(f"Model {model['code']} has neither best params nor a script fallback")
            parameter_source = {
                "type": "script_fallback",
                "path": script.relative_to(repo).as_posix(),
                "note": "No independent best-parameter file is declared; explicit script values are reported.",
            }

        script_text = script.read_text(encoding="utf-8")
        state = state_dict(artifact)
        response_shape = shape(state, "conv_response.conv1d.weight")
        env_shape = shape(state, "conv_env.conv1d.weight")
        transformed_shape = shape(state, "conv_trans.conv1d.weight")
        ff_shape = shape(state, "transformer.self_ff.0.weight")
        if not all((response_shape, env_shape, transformed_shape, ff_shape)):
            raise RuntimeError(f"Model {model['code']} lacks expected Transformer-CNN tensor keys")
        d_model = transformed_shape[1]
        architecture = {
            "family": "TransformerCnn",
            "transformerLayers": 1 if script_text.count("self.transformer = TransformerEncoderLayer(") == 1 else None,
            "dModel": d_model,
            "numHeads": int(params["num_heads"]),
            "feedForwardHiddenDimension": ff_shape[0],
            "convolutionHiddenChannels": response_shape[0],
            "kernelSize": response_shape[2],
            "dropout": float(params["dropout"]),
            "responseDimension": response_shape[1],
            "environmentDimension": env_shape[1],
            "transformedFeatureDimension": transformed_shape[1],
            "cnnBranches": ["response", "environment", "transformed_features", "final_output"],
            "historyWindowM": int(params.get("fixed_m", params.get("m", script_default(script_text, "m") or 10))),
            "directOutputChunkN": int(params.get("fixed_n", params.get("n", literal_assignment(script, "FALLBACK_N") or script_default(script_text, "n") or 3))),
            "lag": int(params["lag"]),
        }
        model_features = [item for item in features if item["modelId"] == model["id"]]
        checks = {
            "artifactHash": sha256_file(artifact) == model["artifactHash"],
            "preprocessorHash": sha256_file(preprocessor) == model["preprocessorHash"],
            "inferenceScriptHash": sha256_file(script) == model["inferenceScriptHash"],
            "runtimeManifestHash": sha256_file(runtime_manifest) == model["runtimeManifestHash"],
            "bestParamsHash": (
                model["bestParamsHash"] is None and best_params_path is None
            ) or (
                best_params_path is not None and sha256_file(best_params_path) == model["bestParamsHash"]
            ),
        }
        if not all(checks.values()):
            raise RuntimeError(f"Model {model['code']} hash validation failed: {checks}")
        models.append(
            {
                "modelCode": model["code"], "modelVersion": model["version"],
                "targetType": model["targetType"],
                "requiredHistoryRows": model["requiredHistoryRows"],
                "inputFeatureCount": len(model_features),
                "outputTargetCount": sum(1 for item in model_features if item["predictionTarget"]),
                "futureSteps": model["expectedSteps"], "timeStepMinutes": model["timeStepMinutes"],
                "architecture": architecture, "parameterSource": parameter_source,
                "trainingParametersRecordedButNotUsedAsRuntimeClaims": {
                    key: params.get(key) for key in ("learning_rate", "batch_size") if key in params
                },
                "artifact": {
                    "path": artifact.relative_to(repo).as_posix(), "sha256": model["artifactHash"]
                },
                "preprocessor": {
                    "path": preprocessor.relative_to(repo).as_posix(), "sha256": model["preprocessorHash"]
                },
                "inferenceScript": {
                    "path": script.relative_to(repo).as_posix(), "sha256": model["inferenceScriptHash"]
                },
                "inputSchemaHash": model["inputSchemaHash"], "bundleHash": model["bundleHash"],
                "runtimeManifestHash": model["runtimeManifestHash"], "hashChecks": checks,
                "knownLimitations": [
                    "point forecasts only", "CPU runtime captured by the current manifest",
                    "architecture summary does not claim forecasting accuracy or model generalization",
                ],
            }
        )

    result = {
        "schemaVersion": "shm-em-model-config-summary-v1",
        "finalCoreFreezeV3": contract["finalCoreFreezeV3"],
        "contractVersion": contract["contractVersion"],
        "featureMappingVersion": contract["featureMappingVersion"],
        "runtime": contract["runtime"],
        "models": models,
        "modelCount": len(models),
        "allHashChecksPass": all(all(model["hashChecks"].values()) for model in models),
        "source": {
            "databaseDerivedContract": args.contract.as_posix(),
            "weights": "Tensor dimensions loaded from each declared model artifact",
            "nonTensorParameters": "Hash-checked best_params.json or explicit inference-script fallback",
        },
    }
    if len(models) != 6 or not result["allHashChecksPass"]:
        raise RuntimeError("Expected six verified model configurations")
    write_json(repo / args.output, result)
    markdown_path = repo / args.markdown
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps({"models": len(models), "allHashChecksPass": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
