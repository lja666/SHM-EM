from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from pit_pre.config import AppConfig, BootstrapConfig, ModelConfig, RuntimeConfig
from pit_pre.db import Database


RESULT_TABLE = "em_prediction_result"


class ModelContractRepository:
    def __init__(self, bootstrap: BootstrapConfig, db: Database | None = None):
        self.bootstrap = bootstrap
        self.db = db or Database(bootstrap.database)

    def load(self, project_code: str) -> AppConfig:
        project = self._project(project_code)
        rows = self.db.read_frame(
            """
            SELECT id, model_code, target_type, artifact_uri, artifact_hash,
                   preprocessor_uri, preprocessor_hash, environment_digest,
                   inference_script_hash, best_params_hash, runtime_manifest_hash,
                   artifact_bundle_hash,
                   model_version, runtime_config_json, required_history_rows,
                   input_schema_hash, contract_version, expected_steps,
                   time_step_minutes, max_operational_age_minutes
            FROM em_prediction_model
            WHERE project_id = %s AND status = 'active'
            ORDER BY model_code ASC, id ASC
            """,
            [project["id"]],
        )
        if rows.empty:
            raise ValueError(f"No active prediction model contract for project_code={project_code}")

        runtime_rows: list[dict[str, Any]] = []
        models: dict[str, ModelConfig] = {}
        for row in rows.to_dict("records"):
            runtime = _json_object(row.get("runtime_config_json"), f"model {row.get('model_code')} runtime_config_json")
            runtime_rows.append(runtime)
            model = self._model(row, runtime)
            if model.code in models:
                raise ValueError(f"Duplicate active model_code in database contract: {model.code}")
            models[model.code] = model

        contract_version = _single_value(
            [model.contract_version for model in models.values()], "contract_version"
        )
        expected_steps = int(_single_value(
            [model.expected_steps for model in models.values()], "expected_steps"
        ))
        time_step_minutes = int(_single_value(
            [model.time_step_minutes for model in models.values()], "time_step_minutes"
        ))
        prediction_mode = str(_single_value(
            [_required_text(item, "predictionMode") for item in runtime_rows], "predictionMode"
        )).lower()
        if prediction_mode != "rolling":
            raise ValueError(
                f"Unsupported database prediction mode {prediction_mode!r}; SHM-EM requires rolling mode"
            )
        schema_version = str(_single_value(
            [_required_text(item, "schemaVersion") for item in runtime_rows], "schemaVersion"
        ))
        horizon_minutes = int(_single_value(
            [_required_int(item, "predictionHorizonMinutes") for item in runtime_rows],
            "predictionHorizonMinutes",
        ))
        max_prediction_seconds = int(_single_value(
            [_required_int(item, "maxPredictionSeconds") for item in runtime_rows],
            "maxPredictionSeconds",
        ))
        if horizon_minutes != expected_steps * time_step_minutes:
            raise ValueError(
                "Database prediction contract is inconsistent: "
                f"horizon={horizon_minutes}, steps={expected_steps}, stepMinutes={time_step_minutes}"
            )

        feature_rows = self._features(int(project["id"]), schema_version)
        schema_hash = _feature_schema_hash(feature_rows)
        prediction_target_counts: dict[str, int] = {}
        for model in models.values():
            if model.input_schema_hash.lower() != schema_hash:
                raise ValueError(
                    f"Input schema hash mismatch for {model.code}: "
                    f"contract={model.input_schema_hash}, currentMapping={schema_hash}"
                )
            produced = feature_rows[
                (feature_rows["model_id"] == model.id)
                & (feature_rows["prediction_target"].astype(int) == 1)
            ]
            if produced.empty:
                raise ValueError(f"No prediction target contract is bound to model {model.code}")
            prediction_target_counts[model.code] = len(produced)

        fingerprint = _sha256(
            json.dumps(
                {
                    "projectId": int(project["id"]),
                    "contractVersion": contract_version,
                    "models": [
                        {
                            "id": model.id,
                            "code": model.code,
                            "version": model.model_version,
                            "artifactHash": model.artifact_hash,
                            "preprocessorHash": model.preprocessor_hash,
                            "inferenceScriptHash": model.inference_script_hash,
                            "bestParamsHash": model.best_params_hash,
                            "runtimeManifestHash": model.runtime_manifest_hash,
                            "environmentDigest": model.environment_digest,
                            "artifactBundleHash": model.artifact_bundle_hash,
                            "inputSchemaHash": model.input_schema_hash,
                        }
                        for model in models.values()
                    ],
                    "features": feature_rows[[
                        "model_id", "feature_code", "training_feature_code", "feature_order",
                        "prediction_target",
                    ]].to_dict("records"),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        runtime = RuntimeConfig(
            time_step_minutes=time_step_minutes,
            project_code=str(project["project_code"]),
            result_table=RESULT_TABLE,
            prediction_mode=prediction_mode,
            prediction_horizon_minutes=horizon_minutes,
            max_prediction_seconds=max_prediction_seconds,
            pipeline_version=contract_version,
            feature_mapping_version=schema_version,
            expected_steps=expected_steps,
        )
        return AppConfig(
            database=self.bootstrap.database,
            runtime=runtime,
            models=models,
            prediction_target_counts=prediction_target_counts,
            contract_fingerprint=fingerprint,
        )

    def _project(self, project_code: str) -> dict[str, Any]:
        rows = self.db.read_frame(
            "SELECT id, project_code FROM em_project WHERE project_code = %s LIMIT 1",
            [project_code],
        )
        if rows.empty:
            raise ValueError(f"Cannot find SHM-EM project_code={project_code}")
        return rows.iloc[0].to_dict()

    def _model(self, row: dict[str, Any], runtime: dict[str, Any]) -> ModelConfig:
        code = str(row.get("model_code") or "").strip()
        if not code:
            raise ValueError("Active model contract has an empty model_code")
        model_path = self._contract_path(row.get("artifact_uri"), f"{code} artifact_uri")
        preprocessor_path = self._contract_path(
            row.get("preprocessor_uri"), f"{code} preprocessor_uri"
        )
        script_path = self._contract_path(runtime.get("scriptPath"), f"{code} scriptPath")
        best_params = runtime.get("bestParamsPath")
        best_params_path = self._contract_path(best_params, f"{code} bestParamsPath") if best_params else None
        runtime_manifest_path = self._contract_path(
            runtime.get("runtimeManifestPath"), f"{code} runtimeManifestPath"
        )
        artifact_hash = str(row.get("artifact_hash") or "").strip().lower()
        if not artifact_hash:
            raise ValueError(f"Model {code} has no artifact_hash")
        actual_hash = _sha256_file(model_path)
        if actual_hash != artifact_hash:
            raise ValueError(f"Artifact hash mismatch for {code}: contract={artifact_hash}, file={actual_hash}")
        preprocessor_hash = str(row.get("preprocessor_hash") or "").strip().lower()
        if not preprocessor_hash:
            raise ValueError(f"Model {code} has no preprocessor_hash")
        actual_preprocessor_hash = _sha256_file(preprocessor_path)
        if actual_preprocessor_hash != preprocessor_hash:
            raise ValueError(
                f"Preprocessor hash mismatch for {code}: "
                f"contract={preprocessor_hash}, file={actual_preprocessor_hash}"
            )
        inference_script_hash = _required_hash(row.get("inference_script_hash"), f"{code} inference_script_hash")
        actual_script_hash = _sha256_file(script_path)
        if actual_script_hash != inference_script_hash:
            raise ValueError(
                f"Inference script hash mismatch for {code}: "
                f"contract={inference_script_hash}, file={actual_script_hash}"
            )
        best_params_hash = str(row.get("best_params_hash") or "").strip().lower() or None
        if best_params_path is None and best_params_hash is not None:
            raise ValueError(f"Model {code} declares best_params_hash without bestParamsPath")
        if best_params_path is not None:
            if best_params_hash is None:
                raise ValueError(f"Model {code} has bestParamsPath but no best_params_hash")
            actual_best_params_hash = _sha256_file(best_params_path)
            if actual_best_params_hash != best_params_hash:
                raise ValueError(
                    f"Best-parameter hash mismatch for {code}: "
                    f"contract={best_params_hash}, file={actual_best_params_hash}"
                )
        runtime_manifest_hash = _required_hash(
            row.get("runtime_manifest_hash"), f"{code} runtime_manifest_hash"
        )
        actual_runtime_manifest_hash = _sha256_file(runtime_manifest_path)
        if actual_runtime_manifest_hash != runtime_manifest_hash:
            raise ValueError(
                f"Runtime manifest hash mismatch for {code}: "
                f"contract={runtime_manifest_hash}, file={actual_runtime_manifest_hash}"
            )
        runtime_manifest = _json_object(
            runtime_manifest_path.read_text(encoding="utf-8"), f"{code} runtime manifest"
        )
        dependency_lock_path = self._contract_path(
            runtime_manifest.get("dependencyLock"), f"{code} dependencyLock"
        )
        expected_environment_digest = _sha256(
            f"{_sha256_file(dependency_lock_path)}|{runtime_manifest_hash}"
        )
        environment_digest = str(row.get("environment_digest") or "").strip().lower()
        artifact_bundle_hash = str(row.get("artifact_bundle_hash") or "").strip().lower()
        if not environment_digest or not artifact_bundle_hash:
            raise ValueError(f"Model {code} has an incomplete portable artifact contract")
        if environment_digest != expected_environment_digest:
            raise ValueError(
                f"Environment digest mismatch for {code}: "
                f"contract={environment_digest}, calculated={expected_environment_digest}"
            )
        input_schema_hash = str(row.get("input_schema_hash") or "").strip().lower()
        if not input_schema_hash:
            raise ValueError(f"Model {code} has no input_schema_hash")
        expected_bundle_hash = _sha256("|".join([
            artifact_hash,
            preprocessor_hash,
            inference_script_hash,
            best_params_hash or "",
            input_schema_hash,
            str(row.get("contract_version") or "").strip(),
            runtime_manifest_hash,
            environment_digest,
        ]))
        if artifact_bundle_hash != expected_bundle_hash:
            raise ValueError(
                f"Artifact bundle hash mismatch for {code}: "
                f"contract={artifact_bundle_hash}, calculated={expected_bundle_hash}"
            )
        return ModelConfig(
            id=int(row["id"]),
            code=code,
            target_type=str(row.get("target_type") or "").strip(),
            script_path=script_path,
            model_path=model_path,
            preprocessor_path=preprocessor_path,
            runtime_manifest_path=runtime_manifest_path,
            best_params_path=best_params_path,
            required_history_rows=_positive_int(row.get("required_history_rows"), f"{code} required_history_rows"),
            model_version=str(row.get("model_version") or "").strip(),
            artifact_hash=artifact_hash,
            preprocessor_hash=preprocessor_hash,
            inference_script_hash=inference_script_hash,
            best_params_hash=best_params_hash,
            runtime_manifest_hash=runtime_manifest_hash,
            environment_digest=environment_digest,
            artifact_bundle_hash=artifact_bundle_hash,
            input_schema_hash=input_schema_hash,
            contract_version=str(row.get("contract_version") or "").strip(),
            expected_steps=_positive_int(row.get("expected_steps"), f"{code} expected_steps"),
            time_step_minutes=_positive_int(row.get("time_step_minutes"), f"{code} time_step_minutes"),
            max_operational_age_minutes=_positive_int(
                row.get("max_operational_age_minutes"), f"{code} max_operational_age_minutes"
            ),
        )

    def _features(self, project_id: int, schema_version: str) -> pd.DataFrame:
        rows = self.db.read_frame(
            """
            SELECT model_id, feature_code, training_feature_code, feature_order, prediction_target
            FROM em_prediction_feature_mapping
            WHERE project_id = %s
              AND schema_version = %s
              AND enabled = 1
              AND required = 1
              AND LOWER(COALESCE(feature_role, 'model_input')) = 'model_input'
            ORDER BY feature_order ASC, id ASC
            """,
            [project_id, schema_version],
        )
        if rows.empty:
            raise ValueError(f"No required feature mapping contract for schema_version={schema_version}")
        if rows["model_id"].isna().any():
            raise ValueError("Every required prediction feature must be bound to an active model_id")
        codes = rows["training_feature_code"].fillna("").astype(str).str.strip()
        if (codes == "").any():
            raise ValueError("Every required prediction feature must define training_feature_code")
        duplicates = codes[codes.duplicated()].unique().tolist()
        if duplicates:
            raise ValueError(f"Duplicate training feature codes in database contract: {duplicates[:5]}")
        orders = rows["feature_order"].astype(int).tolist()
        if orders != list(range(1, len(rows) + 1)):
            raise ValueError("Prediction feature_order must be contiguous and start at 1")
        return rows

    def _contract_path(self, value: Any, field: str) -> Path:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"Database model contract is missing {field}")
        path = Path(text)
        if not path.is_absolute():
            path = (self.bootstrap.working_directory / path).resolve()
        if not path.is_file():
            raise ValueError(f"Database model contract path does not exist for {field}: {path}")
        return path


def load_app_config(
    bootstrap: BootstrapConfig,
    project_code: str,
    db: Database | None = None,
) -> AppConfig:
    return ModelContractRepository(bootstrap, db=db).load(project_code)


def _json_object(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        result = json.loads(str(value or ""))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {field}") from exc
    if not isinstance(result, dict):
        raise ValueError(f"{field} must be a JSON object")
    return result


def _required_text(source: dict[str, Any], key: str) -> str:
    value = str(source.get(key) or "").strip()
    if not value:
        raise ValueError(f"Database runtime contract is missing {key}")
    return value


def _required_int(source: dict[str, Any], key: str) -> int:
    return _positive_int(source.get(key), f"runtime {key}")


def _positive_int(value: Any, field: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return result


def _required_hash(value: Any, field: str) -> str:
    result = str(value or "").strip().lower()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError(f"{field} must be a SHA-256 hexadecimal digest")
    return result


def _single_value(values: list[Any], field: str) -> Any:
    unique = {str(value) for value in values}
    if len(unique) != 1:
        raise ValueError(f"Active model contracts disagree on {field}: {sorted(unique)}")
    return values[0]


def _feature_schema_hash(rows: pd.DataFrame) -> str:
    columns = ["time", "time1", *rows["training_feature_code"].astype(str).tolist()]
    return _sha256("|".join(columns))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
