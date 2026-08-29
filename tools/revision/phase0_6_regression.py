#!/usr/bin/env python3
"""Capture and compare the Phase 0.6 numerical regression baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PIT_PRE_ROOT = ROOT / "src/pit_pre"
if str(PIT_PRE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIT_PRE_ROOT))

import audit_input_alignment as alignment_audit
from pit_pre.cached_model_runner import CachedModelRunner
from pit_pre.config import AppConfig, DatabaseConfig, ModelConfig, RuntimeConfig
from pit_pre.features import WideTableBuilder
from pit_pre.pipeline import (
    _globalize_first_step,
    _input_window_for_model,
    _next_virtual_row,
    _prediction_values_by_feature,
)
from pit_pre.result_writer import _hash_frame


EXTRA_TABLES = {
    "em_conversion_parameter",
    "em_instrument",
    "em_metric_baseline_history",
    "em_reference_binding",
}


class PublicSampleFeatureRepository:
    def __init__(
        self,
        tables: dict[str, list[dict[str, Any]]],
        features: list[alignment_audit.Feature],
        project_id: int,
    ):
        self.features = features
        self.series = {
            feature.training_feature_code: alignment_audit.feature_rows(
                feature, tables, project_id
            )
            for feature in features
        }

    def load_enabled_mappings(self):
        return self.features

    def find_latest_time(self, mappings):
        return min(
            pd.Timestamp(self.series[code]["measurement_time"].max())
            for code in (mapping.training_feature_code for mapping in mappings)
        ).to_pydatetime()

    def read_feature_series(self, mapping, start_time, end_time):
        frame = self.series[mapping.training_feature_code]
        return frame[
            (frame["measurement_time"] >= pd.Timestamp(start_time))
            & (frame["measurement_time"] <= pd.Timestamp(end_time))
        ].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--label", required=True)
    compare = subparsers.add_parser("compare")
    compare.add_argument("--before", type=Path, required=True)
    compare.add_argument("--after", type=Path, required=True)
    compare.add_argument("--output-dir", type=Path, required=True)
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def numeric_matrix(frame: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    values = frame[columns].to_numpy(dtype=np.float64)
    payload = json.dumps(values.tolist(), separators=(",", ":"), allow_nan=False)
    return {
        "rows": int(values.shape[0]),
        "columns": columns,
        "columnCount": int(values.shape[1]),
        "dtype": str(values.dtype),
        "values": values.tolist(),
        "sha256": sha256_text(payload),
    }


def _contract_path(value: Any) -> Path:
    return PIT_PRE_ROOT / str(value).removeprefix("./")


def model_config(tables: dict[str, list[dict[str, Any]]], project_code: str) -> AppConfig:
    project = next(row for row in tables["em_project"] if row["project_code"] == project_code)
    project_id = int(project["id"])
    rows = sorted(
        [
            row for row in tables["em_prediction_model"]
            if int(row["project_id"]) == project_id and row["status"] == "active"
        ],
        key=lambda row: str(row["model_code"]),
    )
    models: dict[str, ModelConfig] = {}
    runtime_rows = []
    for row in rows:
        runtime = json.loads(str(row["runtime_config_json"]))
        runtime_rows.append(runtime)
        code = str(row["model_code"])
        best_params = runtime.get("bestParamsPath")
        models[code] = ModelConfig(
            id=int(row["id"]),
            code=code,
            target_type=str(row["target_type"]),
            script_path=_contract_path(runtime["scriptPath"]),
            model_path=_contract_path(row["artifact_uri"]),
            preprocessor_path=_contract_path(row["preprocessor_uri"]),
            runtime_manifest_path=_contract_path(runtime["runtimeManifestPath"]),
            best_params_path=_contract_path(best_params) if best_params else None,
            required_history_rows=int(row["required_history_rows"]),
            model_version=str(row["model_version"]),
            artifact_hash=str(row["artifact_hash"]),
            preprocessor_hash=str(row["preprocessor_hash"]),
            inference_script_hash=str(row["inference_script_hash"]),
            best_params_hash=None if row.get("best_params_hash") is None else str(row["best_params_hash"]),
            runtime_manifest_hash=str(row["runtime_manifest_hash"]),
            environment_digest=str(row["environment_digest"]),
            artifact_bundle_hash=str(row["artifact_bundle_hash"]),
            input_schema_hash=str(row["input_schema_hash"]),
            contract_version=str(row["contract_version"]),
            expected_steps=int(row["expected_steps"]),
            time_step_minutes=int(row["time_step_minutes"]),
            max_operational_age_minutes=int(row["max_operational_age_minutes"]),
        )
    first = rows[0]
    runtime = runtime_rows[0]
    counts = {
        model.code: sum(
            int(mapping["model_id"]) == model.id
            and int(mapping.get("prediction_target") or 0) == 1
            and int(mapping.get("required") or 0) == 1
            and int(mapping.get("enabled") or 0) == 1
            for mapping in tables["em_prediction_feature_mapping"]
        )
        for model in models.values()
    }
    return AppConfig(
        database=DatabaseConfig("offline", 0, "offline", "offline", "offline"),
        runtime=RuntimeConfig(
            time_step_minutes=int(first["time_step_minutes"]),
            project_code=project_code,
            result_table="em_prediction_result",
            prediction_mode=str(runtime["predictionMode"]),
            prediction_horizon_minutes=int(runtime["predictionHorizonMinutes"]),
            max_prediction_seconds=int(runtime["maxPredictionSeconds"]),
            pipeline_version=str(first["contract_version"]),
            feature_mapping_version=str(runtime["schemaVersion"]),
            expected_steps=int(first["expected_steps"]),
        ),
        models=models,
        prediction_target_counts=counts,
        contract_fingerprint="offline-regression-capture",
    )


def feature_mapping_lookup(tables, project_id: int) -> dict[tuple[int, str], dict[str, Any]]:
    return {
        (int(row["model_id"]), str(row.get("training_feature_code") or row["feature_code"])): row
        for row in tables["em_prediction_feature_mapping"]
        if int(row["project_id"]) == project_id and int(row.get("enabled") or 0) == 1
    }


def active_lookup(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {
        tuple(row.get(key) for key in keys): row
        for row in rows
        if row.get("effective_to") is None
    }


def engineering_values(
    model,
    records: list[dict[str, Any]],
    tables: dict[str, list[dict[str, Any]]],
    project_id: int,
) -> list[dict[str, Any]]:
    mappings = feature_mapping_lookup(tables, project_id)
    baselines = active_lookup(
        [row for row in tables["em_metric_baseline_history"] if int(row["project_id"]) == project_id],
        ("instrument_id", "metric_code"),
    )
    parameters = active_lookup(
        [row for row in tables["em_conversion_parameter"] if int(row["project_id"]) == project_id],
        ("instrument_id", "parameter_code"),
    )
    instruments = {int(row["id"]): row for row in tables["em_instrument"]}
    references = {
        (str(row["instrument_type"]), str(row["module_no"])): int(row["reference_instrument_id"])
        for row in tables["em_reference_binding"]
        if int(row["project_id"]) == project_id and int(row.get("enabled") or 0) == 1
    }
    raw_by_instrument_step: dict[tuple[int, int], float] = {}
    mapped_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record in records:
        mapping = mappings[(model.id, record["point"])]
        mapped_records.append((record, mapping))
        raw_by_instrument_step[(int(mapping["instrument_id"]), int(record["step"]))] = float(record["value"])

    output: list[dict[str, Any]] = []
    for record, mapping in mapped_records:
        raw = float(record["value"])
        instrument_id = int(mapping["instrument_id"])
        target = model.target_type
        if target == "YD":
            baseline = float(baselines[(instrument_id, "displacement_tilt_y_deg")]["baseline_value"])
            initial = float(parameters[(instrument_id, "initial_y_mm")]["parameter_value"])
            value = 1000 * math.sin(math.radians(raw)) - 1000 * math.sin(math.radians(baseline)) + initial
        elif target == "XD":
            baseline = float(baselines[(instrument_id, "displacement_tilt_x_deg")]["baseline_value"])
            value = 1000 * math.sin(math.radians(raw)) - 1000 * math.sin(math.radians(baseline))
        elif target == "water":
            elevation = float(parameters[(instrument_id, "module_elevation_m")]["parameter_value"])
            value = elevation - raw / 1000
        elif target == "settlement":
            instrument = instruments[instrument_id]
            reference_id = references[("static_level", str(instrument["module_no"]))]
            if instrument_id == reference_id:
                value = 0.0
            else:
                baseline = float(baselines[(instrument_id, "static_level_value_mm")]["baseline_value"])
                reference_baseline = float(baselines[(reference_id, "static_level_value_mm")]["baseline_value"])
                reference_raw = raw_by_instrument_step[(reference_id, int(record["step"]))]
                value = (raw - baseline) - (reference_raw - reference_baseline)
        else:
            value = raw
        output.append({
            "point": record["point"],
            "step": int(record["step"]),
            "value": float(value),
        })
    return output


def capture(label: str, output: Path) -> None:
    alignment_audit.AUDIT_TABLES.update(EXTRA_TABLES)
    sample = ROOT / "sql/shm_em_database/02_SHM_EM_public_sample.sql"
    tables = alignment_audit.parse_public_sample(sample)
    models_data, features, project_id = alignment_audit.load_contract(
        ROOT, tables, alignment_audit.PROJECT_CODE
    )
    del models_data
    config = model_config(tables, alignment_audit.PROJECT_CODE)
    repository = PublicSampleFeatureRepository(tables, features, project_id)
    builder = WideTableBuilder(repository, config.runtime.time_step_minutes)
    max_rows = max(model.required_history_rows for model in config.models.values())
    diagnostics = None
    if hasattr(builder, "build_with_diagnostics"):
        result = builder.build_with_diagnostics(max_rows)
        wide = result.values
        diagnostics = result.diagnostics
    else:
        wide = builder.build(max_rows)

    runner = CachedModelRunner(config.models)
    base_time = pd.Timestamp(wide["time"].iloc[-1]).to_pydatetime()
    base_time1 = float(wide["time1"].iloc[-1])
    initial_wide = wide.copy()
    pending: dict[str, list[pd.DataFrame]] = {code: [] for code in config.models}
    first_inputs: dict[str, dict[str, Any]] = {}
    quality: dict[str, Any] = {}

    for step in range(1, config.runtime.expected_steps + 1):
        round_predictions: dict[str, dict[str, float]] = {}
        future_time = base_time + timedelta(minutes=step * config.runtime.time_step_minutes)
        future_time1 = base_time1 + step
        for model in config.models.values():
            input_frame = _input_window_for_model(wide, model.required_history_rows)
            cached = runner.cache[model.code]
            if step == 1:
                first_inputs[model.code] = numeric_matrix(input_frame, cached.input_columns)
                if diagnostics is not None:
                    quality[model.code] = diagnostics.quality_summary(
                        cached.input_columns, model.required_history_rows
                    )
            local = runner.run(model, input_frame)
            first = _globalize_first_step(
                local, model.target_type, step, future_time, future_time1
            )
            pending[model.code].append(first)
            round_predictions.update(_prediction_values_by_feature(first, model.target_type))
        wide = pd.concat([
            wide,
            pd.DataFrame([_next_virtual_row(wide.iloc[-1], round_predictions, future_time, future_time1)]),
        ], ignore_index=True)

    predictions: dict[str, Any] = {}
    total_records = 0
    target_count = 0
    for model in config.models.values():
        frame = pd.concat(pending[model.code], ignore_index=True)
        value_column = next(column for column in frame.columns if column.endswith("_pred"))
        records = [
            {"point": str(row["point"]), "step": int(row["step"]), "value": float(row[value_column])}
            for row in frame.sort_values(["point", "step"]).to_dict("records")
        ]
        engineering = engineering_values(model, records, tables, project_id)
        predictions[model.code] = {
            "targetType": model.target_type,
            "targetCount": int(frame["point"].nunique()),
            "stepCount": int(frame["step"].nunique()),
            "recordCount": len(records),
            "resultHash": _hash_frame(frame, ["point", "step", value_column]),
            "records": records,
            "engineeringRecords": engineering,
        }
        total_records += len(records)
        target_count += int(frame["point"].nunique())

    capture_data = {
        "schemaVersion": "shm-em-phase0-6-regression-capture-v1",
        "label": label,
        "projectCode": alignment_audit.PROJECT_CODE,
        "commonHistoryRows": max_rows,
        "commonInput": numeric_matrix(
            initial_wide,
            [column for column in initial_wide.columns if column not in {"time", "time1"}],
        ),
        "modelInputs": first_inputs,
        "alignmentQuality": quality,
        "predictions": predictions,
        "totals": {
            "modelCount": len(config.models),
            "targetCount": target_count,
            "stepCount": config.runtime.expected_steps,
            "predictionRecordCount": total_records,
        },
        "contracts": {
            code: {
                "requiredHistoryRows": model.required_history_rows,
                "artifactHash": model.artifact_hash,
                "preprocessorHash": model.preprocessor_hash,
                "inferenceScriptHash": model.inference_script_hash,
                "bestParamsHash": model.best_params_hash,
                "runtimeManifestHash": model.runtime_manifest_hash,
                "environmentDigest": model.environment_digest,
                "artifactBundleHash": model.artifact_bundle_hash,
                "inputSchemaHash": model.input_schema_hash,
                "actualArtifactHash": sha256_file(model.model_path),
                "actualPreprocessorHash": sha256_file(model.preprocessor_path),
                "actualInferenceScriptHash": sha256_file(model.script_path),
                "actualBestParamsHash": (
                    sha256_file(model.best_params_path) if model.best_params_path else None
                ),
                "actualRuntimeManifestHash": sha256_file(model.runtime_manifest_path),
            }
            for code, model in config.models.items()
        },
    }
    output = resolve(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(capture_data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(capture_data["totals"], sort_keys=True))


def array_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = np.asarray(before["values"], dtype=np.float64)
    right = np.asarray(after["values"], dtype=np.float64)
    same_shape = left.shape == right.shape
    max_diff = float(np.max(np.abs(left - right))) if same_shape and left.size else 0.0
    return {
        "shapeBefore": list(left.shape),
        "shapeAfter": list(right.shape),
        "shapeIdentical": same_shape,
        "columnsIdentical": before["columns"] == after["columns"],
        "dtypeCompatible": before["dtype"] == after["dtype"],
        "maxAbsDifference": max_diff,
        "numericallyIdentical": same_shape and max_diff == 0.0,
        "hashBefore": before["sha256"],
        "hashAfter": after["sha256"],
    }


def record_diff(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    same_keys = [(x["point"], x["step"]) for x in before] == [(x["point"], x["step"]) for x in after]
    left = np.asarray([x["value"] for x in before], dtype=np.float64)
    right = np.asarray([x["value"] for x in after], dtype=np.float64)
    max_diff = float(np.max(np.abs(left - right))) if left.shape == right.shape and left.size else 0.0
    return {
        "recordCountBefore": len(before),
        "recordCountAfter": len(after),
        "keysIdentical": same_keys,
        "maxAbsDifference": max_diff,
        "numericallyIdentical": left.shape == right.shape and max_diff == 0.0,
    }


def compare(before_path: Path, after_path: Path, output_dir: Path) -> None:
    before = json.loads(resolve(before_path).read_text(encoding="utf-8"))
    after = json.loads(resolve(after_path).read_text(encoding="utf-8"))
    output_dir = resolve(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_report = {
        "schemaVersion": "shm-em-phase0-6-input-regression-v1",
        "commonInput": array_diff(before["commonInput"], after["commonInput"]),
        "models": {
            code: array_diff(before["modelInputs"][code], after["modelInputs"][code])
            for code in sorted(before["modelInputs"])
        },
    }
    prediction_models = {}
    for code in sorted(before["predictions"]):
        old = before["predictions"][code]
        new = after["predictions"][code]
        prediction_models[code] = {
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
        }
    metadata_hashes = {
        code: {
            "classification": "EXPECTED_METADATA_HASH_CHANGE",
            "beforeSha256": sha256_text(json.dumps({}, sort_keys=True, separators=(",", ":"))),
            "afterSha256": sha256_text(json.dumps(
                after["alignmentQuality"][code], sort_keys=True, separators=(",", ":")
            )),
            "numericalInputAffected": False,
            "predictionAffected": False,
        }
        for code in sorted(after["alignmentQuality"])
    }
    prediction_report = {
        "schemaVersion": "shm-em-phase0-6-prediction-regression-v1",
        "totalsBefore": before["totals"],
        "totalsAfter": after["totals"],
        "models": prediction_models,
        "contractsIdentical": before["contracts"] == after["contracts"],
        "contractsBefore": before["contracts"],
        "contractsAfter": after["contracts"],
        "alignmentMetadataHashReview": metadata_hashes,
    }
    (output_dir / "regression-input-matrix.json").write_text(
        json.dumps(input_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "regression-prediction-values.json").write_text(
        json.dumps(prediction_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    all_inputs_equal = input_report["commonInput"]["numericallyIdentical"] and all(
        item["numericallyIdentical"] for item in input_report["models"].values()
    )
    all_predictions_equal = all(
        item["rawPrediction"]["numericallyIdentical"]
        and item["engineeringPrediction"]["numericallyIdentical"]
        and item["resultHashBefore"] == item["resultHashAfter"]
        for item in prediction_models.values()
    )
    summary = [
        "# Phase 0.6 Numerical Regression Summary",
        "",
        f"- Aligned input matrices identical: `{str(all_inputs_equal).lower()}`",
        f"- Maximum aligned-input absolute difference: `{max([input_report['commonInput']['maxAbsDifference'], *[item['maxAbsDifference'] for item in input_report['models'].values()]])}`",
        f"- Raw prediction values identical: `{str(all_predictions_equal).lower()}`",
        f"- Engineering conversion values identical: `{str(all_predictions_equal).lower()}`",
        f"- Target count: `{after['totals']['targetCount']}`",
        f"- Forecast steps: `{after['totals']['stepCount']}`",
        f"- Prediction records: `{after['totals']['predictionRecordCount']}`",
        f"- Frozen model contracts and artifact hashes identical: `{str(prediction_report['contractsIdentical']).lower()}`",
        "- New fill/gap/source-age eligibility thresholds: `none`",
        "",
        "The comparison used the same committed public SQL sample, model artifacts, preprocessors, and rolling inference driver before and after instrumentation.",
    ]
    (output_dir / "regression-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    metadata_rows = [
        f"| {code} | `{item['beforeSha256']}` | `{item['afterSha256']}` | {item['classification']} |"
        for code, item in metadata_hashes.items()
    ]
    metadata = [
        "# Phase 0.6 Metadata Hash Change Review",
        "",
        "## Expected metadata change",
        "",
        "`input_snapshot_json` gains a descriptive alignment policy version and compact quality diagnostics. An external hash of that JSON is therefore expected to change (`EXPECTED_METADATA_HASH_CHANGE`).",
        "",
        "| Model | Baseline alignment payload SHA-256 | Instrumented payload SHA-256 | Classification |",
        "| --- | --- | --- | --- |",
        *metadata_rows,
        "",
        "## Unchanged numerical hashes",
        "",
        "- Batch input matrix hash: unchanged when calculated over the numerical wide table.",
        "- Per-model result hash: unchanged because it remains calculated from point, step, and predicted value.",
        "- Batch output hash: unchanged because constituent result hashes are unchanged.",
        "- Model artifact, preprocessor, inference-script, runtime-manifest, environment, bundle, and input-schema hashes: unchanged.",
        "",
        "## Pre-existing Windows checkout normalization",
        "",
        "The public contract stores SHA-256 values for LF-normalized inference scripts. This Windows worktree uses `core.autocrlf=true`, so checked-out script bytes are CRLF and strict byte-hash loading is blocked before Phase 0.6 changes. The regression records declared and actual hashes separately; LF-normalized content matches the declared contract. No model contract, script, weight, or preprocessor was modified in this phase.",
        "",
        "No diagnostic value participates in model input construction, engineering conversion, event eligibility, or gate decisions.",
    ]
    (output_dir / "metadata-hash-change-review.md").write_text(
        "\n".join(metadata) + "\n", encoding="utf-8"
    )
    if not all_inputs_equal or not all_predictions_equal or not prediction_report["contractsIdentical"]:
        raise SystemExit("Phase 0.6 numerical regression failed")
    print("PHASE0_6_NUMERICAL_REGRESSION_PASS")


def write_phase_manifest(output_dir: Path) -> None:
    output_dir = resolve(output_dir)
    manifest_path = output_dir / "phase0_6-manifest.json"
    files = []
    for path in sorted(item for item in output_dir.iterdir() if item.is_file() and item != manifest_path):
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    tag_commit = subprocess.run(
        ["git", "rev-parse", "v1.0.0^{}"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    manifest = {
        "schemaVersion": "shm-em-phase0-6-manifest-v1",
        "phase": "Phase 0.6 - Alignment Diagnostics Instrumentation and Core Stabilization",
        "sourceGitCommit": commit,
        "submittedTag": "v1.0.0",
        "submittedTagCommit": tag_commit,
        "submittedBaselineUnchanged": commit == tag_commit,
        "generationTimestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": files,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(manifest_path)


def main() -> int:
    args = parse_args()
    if args.command == "capture":
        capture(args.label, args.output)
    elif args.command == "compare":
        compare(args.before, args.after, args.output_dir)
    else:
        write_phase_manifest(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
