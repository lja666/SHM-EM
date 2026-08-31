#!/usr/bin/env python3
"""Export the authoritative SHM-EM prediction contract from the reproduced database."""

from __future__ import annotations

import argparse
import datetime as dt
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import pymysql


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-host", default="127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default=os.environ.get("SHM_EM_DB_PASSWORD"))
    parser.add_argument("--database", default="shm_em_reproduce_benchmark_reference")
    parser.add_argument("--project-code", default="SHM_EM_PUBLIC_SAMPLE")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/revision/manuscript/data-model-contract-export.json"),
    )
    parser.add_argument(
        "--example",
        type=Path,
        default=Path("docs/revision/examples/data-model-contract.example.json"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("docs/revision/examples/data-model-contract.schema.json"),
    )
    args = parser.parse_args()
    if not args.db_password:
        parser.error("--db-password or SHM_EM_DB_PASSWORD is required")
    return args


def json_value(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def json_object(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list, int, float, bool)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=json_value) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    return completed.stdout.strip()


def rows(cursor, sql: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
    cursor.execute(sql, parameters)
    return list(cursor.fetchall())


def contract_schema() -> dict[str, Any]:
    hash_schema = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/lja666/SHM-EM/blob/main/docs/revision/examples/data-model-contract.schema.json",
        "title": "SHM-EM persisted prediction contract export",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schemaVersion", "contractVersion", "project", "timeline", "models",
            "features", "targets", "runtime", "validation",
        ],
        "properties": {
            "schemaVersion": {"const": "shm-em-data-model-contract-export-v1"},
            "contractVersion": {"type": "string", "minLength": 1},
            "featureMappingVersion": {"type": "string", "minLength": 1},
            "project": {
                "type": "object",
                "required": ["id", "code"],
                "properties": {"id": {"type": "integer"}, "code": {"type": "string"}},
                "additionalProperties": True,
            },
            "timeline": {
                "type": "object",
                "required": ["predictionMode", "expectedSteps", "timeStepMinutes", "horizonMinutes"],
                "properties": {
                    "predictionMode": {"const": "rolling"},
                    "expectedSteps": {"type": "integer", "minimum": 1},
                    "timeStepMinutes": {"type": "integer", "minimum": 1},
                    "horizonMinutes": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": True,
            },
            "models": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "id", "code", "version", "targetType", "requiredHistoryRows",
                        "expectedSteps", "timeStepMinutes", "artifactHash", "preprocessorHash",
                        "inferenceScriptHash", "runtimeManifestHash", "inputSchemaHash", "bundleHash",
                    ],
                    "properties": {
                        "id": {"type": "integer"}, "code": {"type": "string"},
                        "version": {"type": "string"}, "targetType": {"type": "string"},
                        "requiredHistoryRows": {"type": "integer", "minimum": 1},
                        "expectedSteps": {"type": "integer", "minimum": 1},
                        "timeStepMinutes": {"type": "integer", "minimum": 1},
                        "artifactHash": hash_schema, "preprocessorHash": hash_schema,
                        "inferenceScriptHash": hash_schema, "runtimeManifestHash": hash_schema,
                        "inputSchemaHash": hash_schema, "bundleHash": hash_schema,
                    },
                    "additionalProperties": True,
                },
            },
            "features": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "modelId", "modelCode", "order", "featureCode", "trainingFeatureCode",
                        "sourceRegistryCode", "sourceMetricCode", "sourceValueColumn", "inputValueMode",
                        "required", "predictionTarget",
                    ],
                    "properties": {
                        "modelId": {"type": "integer"}, "modelCode": {"type": "string"},
                        "order": {"type": "integer", "minimum": 1},
                        "featureCode": {"type": "string", "minLength": 1},
                        "trainingFeatureCode": {"type": "string", "minLength": 1},
                        "sourceRegistryCode": {"type": "string", "minLength": 1},
                        "sourceMetricCode": {"type": "string", "minLength": 1},
                        "sourceValueColumn": {"type": "string", "minLength": 1},
                        "inputValueMode": {"enum": ["RAW", "ENGINEERING"]},
                        "required": {"type": "boolean"},
                        "predictionTarget": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
            },
            "targets": {"type": "array", "items": {"type": "object"}},
            "runtime": {"type": "object"},
            "validation": {"type": "object"},
            "sourceOfTruth": {"type": "object"},
            "generatedAt": {"type": "string", "format": "date-time"},
            "finalCoreFreezeV3": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "compactExample": {"type": "object"},
        },
    }


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    connection = pymysql.connect(
        host=args.db_host, port=args.db_port, user=args.db_user, password=args.db_password,
        database=args.database, charset="utf8mb4", autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            projects = rows(cursor, "SELECT id, project_code, project_name FROM em_project WHERE project_code=%s", (args.project_code,))
            if len(projects) != 1:
                raise RuntimeError(f"Expected one project {args.project_code}, found {len(projects)}")
            project = projects[0]
            model_rows = rows(
                cursor,
                """
                SELECT id, project_id, model_code, model_name, model_type, target_type,
                       target_metric_code, artifact_uri, artifact_hash, preprocessor_uri,
                       preprocessor_hash, inference_script_hash, best_params_hash,
                       runtime_manifest_hash, environment_digest, artifact_bundle_hash,
                       model_version, runtime_config_json, required_history_rows,
                       input_schema_hash, contract_version, expected_steps, time_step_minutes,
                       max_operational_age_minutes, status
                FROM em_prediction_model
                WHERE project_id=%s AND status='active'
                ORDER BY model_code, id
                """,
                (project["id"],),
            )
            feature_rows = rows(
                cursor,
                """
                SELECT f.id, f.project_id, f.model_id, m.model_code, m.model_version,
                       f.feature_order, f.feature_code, f.feature_name, f.feature_label,
                       f.training_feature_code, f.feature_group, f.target_type, f.feature_role,
                       f.station_id, f.instrument_id, f.source_registry_code, f.source_metric_code,
                       f.source_field, f.source_value_column, f.input_value_mode, f.schema_version,
                       f.feature_operator_code, f.output_conversion_operator_code,
                       f.output_conversion_version, f.window_type, f.window_size_seconds,
                       f.required, f.prediction_target, f.transform_json, f.metadata_json,
                       sm.raw_unit, sm.metric_unit AS engineering_unit,
                       sm.conversion_operator_code AS station_conversion_operator,
                       metric.default_unit AS catalogue_unit
                FROM em_prediction_feature_mapping f
                JOIN em_prediction_model m ON m.id=f.model_id
                LEFT JOIN em_station_metric sm
                  ON sm.project_id=f.project_id AND sm.station_id=f.station_id
                 AND sm.instrument_id <=> f.instrument_id AND sm.metric_code=f.source_metric_code
                LEFT JOIN em_metric metric ON metric.metric_code=f.source_metric_code
                WHERE f.project_id=%s AND f.enabled=1
                  AND f.required=1 AND LOWER(COALESCE(f.feature_role,'model_input'))='model_input'
                ORDER BY f.feature_order, f.id
                """,
                (project["id"],),
            )
    finally:
        connection.close()

    if not model_rows or not feature_rows:
        raise RuntimeError("The database contract is incomplete")
    versions = {str(item["contract_version"]) for item in model_rows}
    schema_versions = {str(item["schema_version"]) for item in feature_rows}
    steps = {int(item["expected_steps"]) for item in model_rows}
    intervals = {int(item["time_step_minutes"]) for item in model_rows}
    if len(versions) != 1 or len(schema_versions) != 1 or len(steps) != 1 or len(intervals) != 1:
        raise RuntimeError("Active model contracts disagree on version or timeline")
    orders = [int(item["feature_order"]) for item in feature_rows]
    if orders != list(range(1, len(feature_rows) + 1)):
        raise RuntimeError("Feature order is not contiguous from 1")
    training_codes = [str(item["training_feature_code"] or "").strip() for item in feature_rows]
    if not all(training_codes) or len(set(training_codes)) != len(training_codes):
        raise RuntimeError("Training feature codes are empty or duplicated")
    input_schema_hash = hashlib.sha256("|".join(["time", "time1", *training_codes]).encode("utf-8")).hexdigest()
    if any(str(item["input_schema_hash"]).lower() != input_schema_hash for item in model_rows):
        raise RuntimeError("Database input_schema_hash does not match the enabled ordered feature contract")

    runtime_path = repo / "src/pit_pre/runtime-manifest.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime_hash = sha256_file(runtime_path)
    if any(str(item["runtime_manifest_hash"]).lower() != runtime_hash for item in model_rows):
        raise RuntimeError("Runtime manifest hash differs from the database model contract")

    features = []
    for item in feature_rows:
        features.append(
            {
                "id": int(item["id"]),
                "modelId": int(item["model_id"]),
                "modelCode": item["model_code"],
                "modelVersion": item["model_version"],
                "order": int(item["feature_order"]),
                "featureCode": item["feature_code"],
                "featureName": item["feature_name"],
                "featureLabel": item["feature_label"],
                "trainingFeatureCode": item["training_feature_code"],
                "featureGroup": item["feature_group"],
                "targetType": item["target_type"],
                "stationId": item["station_id"],
                "instrumentId": item["instrument_id"],
                "sourceRegistryCode": item["source_registry_code"],
                "sourceMetricCode": item["source_metric_code"],
                "sourceField": item["source_field"],
                "sourceValueColumn": item["source_value_column"],
                "inputValueMode": item["input_value_mode"],
                "rawUnit": item["raw_unit"] or item["catalogue_unit"],
                "engineeringUnit": item["engineering_unit"] or item["catalogue_unit"],
                "required": bool(item["required"]),
                "predictionTarget": bool(item["prediction_target"]),
                "transformation": {
                    "featureOperatorCode": item["feature_operator_code"],
                    "stationConversionOperatorCode": item["station_conversion_operator"],
                    "outputConversionOperatorCode": item["output_conversion_operator_code"],
                    "outputConversionVersion": item["output_conversion_version"],
                    "transform": json_object(item["transform_json"]),
                },
                "window": {"type": item["window_type"], "sizeSeconds": item["window_size_seconds"]},
                "metadata": json_object(item["metadata_json"]),
            }
        )

    models = []
    for item in model_rows:
        runtime_config = json_object(item["runtime_config_json"])
        model_features = [feature for feature in features if feature["modelId"] == int(item["id"])]
        models.append(
            {
                "id": int(item["id"]), "code": item["model_code"], "name": item["model_name"],
                "type": item["model_type"], "version": item["model_version"],
                "targetType": item["target_type"], "targetMetricCode": item["target_metric_code"],
                "requiredHistoryRows": int(item["required_history_rows"]),
                "expectedSteps": int(item["expected_steps"]),
                "timeStepMinutes": int(item["time_step_minutes"]),
                "maxOperationalAgeMinutes": int(item["max_operational_age_minutes"]),
                "inputFeatureCount": len(model_features),
                "outputTargetCount": sum(1 for feature in model_features if feature["predictionTarget"]),
                "artifactUri": item["artifact_uri"], "artifactHash": item["artifact_hash"],
                "preprocessorUri": item["preprocessor_uri"], "preprocessorHash": item["preprocessor_hash"],
                "inferenceScriptHash": item["inference_script_hash"],
                "bestParamsHash": item["best_params_hash"],
                "runtimeManifestHash": item["runtime_manifest_hash"],
                "environmentDigest": item["environment_digest"],
                "inputSchemaHash": item["input_schema_hash"],
                "bundleHash": item["artifact_bundle_hash"],
                "runtimeConfig": runtime_config,
            }
        )

    targets = [
        {
            "modelId": feature["modelId"], "modelCode": feature["modelCode"],
            "targetType": feature["targetType"], "featureCode": feature["featureCode"],
            "trainingFeatureCode": feature["trainingFeatureCode"], "stationId": feature["stationId"],
            "instrumentId": feature["instrumentId"], "engineeringUnit": feature["engineeringUnit"],
            "outputConversionOperatorCode": feature["transformation"]["outputConversionOperatorCode"],
            "outputConversionVersion": feature["transformation"]["outputConversionVersion"],
        }
        for feature in features if feature["predictionTarget"]
    ]
    expected_steps = next(iter(steps))
    time_step = next(iter(intervals))
    value = {
        "schemaVersion": "shm-em-data-model-contract-export-v1",
        "contractVersion": next(iter(versions)),
        "featureMappingVersion": next(iter(schema_versions)),
        "project": {"id": int(project["id"]), "code": project["project_code"], "name": project["project_name"]},
        "timeline": {
            "predictionMode": "rolling", "expectedSteps": expected_steps,
            "timeStepMinutes": time_step, "horizonMinutes": expected_steps * time_step,
            "sharedBaseTimeRequired": True,
        },
        "models": models,
        "features": features,
        "targets": targets,
        "runtime": {**runtime, "manifestHash": runtime_hash},
        "validation": {
            "featureOrder": "globally contiguous from 1 across enabled required model-input mappings",
            "inputSchemaHash": input_schema_hash,
            "missingRequiredFeature": "REJECT_BEFORE_INFERENCE",
            "duplicateTrainingFeatureCode": "REJECT_CONTRACT_LOAD",
            "artifactOrPreprocessorHashMismatch": "REJECT_CONTRACT_LOAD",
            "runtimeManifestOrBundleHashMismatch": "REJECT_CONTRACT_LOAD",
            "unsupportedPredictionMode": "REJECT_CONTRACT_LOAD",
            "incompleteOrMisalignedTimeline": "REJECT_EXECUTION_GATE",
            "unitOrEngineeringConversionFailure": "REJECT_RULE_EVALUATION_OR_EXECUTION",
            "executePolicy": "RECHECK_LATEST_PERSISTED_GATE_BEFORE_FORMAL_SIDE_EFFECTS",
        },
        "sourceOfTruth": {
            "database": args.database,
            "tables": ["em_prediction_model", "em_prediction_feature_mapping", "em_station_metric", "em_metric"],
            "runtimeManifest": "src/pit_pre/runtime-manifest.json",
            "contractLoader": "src/pit_pre/pit_pre/contract.py",
        },
        "finalCoreFreezeV3": git(repo, "rev-parse", "eaa7d85^{commit}"),
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    write_json(repo / args.output, value)
    write_json(repo / args.schema, contract_schema())

    selected_model = next(model for model in models if model["code"] == "settlement")
    selected_features = [feature for feature in features if feature["modelCode"] == "settlement"]
    example = {
        "schemaVersion": value["schemaVersion"],
        "contractVersion": value["contractVersion"],
        "featureMappingVersion": value["featureMappingVersion"],
        "project": value["project"],
        "timeline": value["timeline"],
        "models": [selected_model],
        "features": selected_features[:4],
        "targets": [feature for feature in targets if feature["modelCode"] == "settlement"][:2],
        "runtime": value["runtime"],
        "validation": value["validation"],
        "sourceOfTruth": value["sourceOfTruth"],
        "finalCoreFreezeV3": value["finalCoreFreezeV3"],
        "generatedAt": value["generatedAt"],
        "compactExample": {
            "modelCountShown": 1, "modelCountInFullContract": len(models),
            "featuresShown": 4, "featuresInFullContract": len(features),
            "targetsShown": 2, "targetsInFullContract": len(targets),
        },
    }
    write_json(repo / args.example, example)
    print(json.dumps({"models": len(models), "features": len(features), "targets": len(targets), "inputSchemaHash": input_schema_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
