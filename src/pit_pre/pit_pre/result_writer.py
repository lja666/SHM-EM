from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from pit_pre.config import ModelConfig
from pit_pre.db import Database


PREDICTION_VALUE_COLUMNS = {
    "YD": "YD_pred",
    "XD": "XD_pred",
    "Strain": "Strain_pred",
    "Pressure": "Pressure_pred",
    "water": "water_pred",
    "settlement": "settlement_pred",
}


@dataclass(frozen=True)
class PredictionWriteResult:
    run_id: int
    inserted_rows: int
    result_hash: str


class PredictionResultWriter:
    def __init__(
        self,
        db: Database,
        project_id: int,
        time_step_minutes: int,
        horizon_minutes: int,
        rolling_steps: int,
        pipeline_version: str,
        feature_mapping_version: str,
    ):
        self.db = db
        self.project_id = project_id
        self.time_step_minutes = time_step_minutes
        self.horizon_minutes = horizon_minutes
        self.rolling_steps = rolling_steps
        self.pipeline_version = pipeline_version
        self.feature_mapping_version = feature_mapping_version

    def create_batch(
        self,
        batch_code: str,
        base_time: datetime,
        model_count: int,
        feature_count: int,
        started_at: datetime,
        input_hash: str | None = None,
    ) -> int:
        sql = """
            INSERT INTO em_prediction_batch (
                batch_code, project_id, base_time, time_step_minutes, horizon_minutes,
                rolling_steps, model_count, feature_count, pipeline_version,
                feature_mapping_version, input_hash, status, started_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'running', %s)
        """
        return self.db.insert_one(
            sql,
            [
                batch_code,
                self.project_id,
                base_time,
                self.time_step_minutes,
                self.horizon_minutes,
                self.rolling_steps,
                model_count,
                feature_count,
                self.pipeline_version,
                self.feature_mapping_version,
                input_hash,
                started_at,
            ],
        )

    def finish_batch(
        self,
        batch_id: int,
        status: str,
        message: str | None = None,
        output_hash: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        self.db.execute(
            """
            UPDATE em_prediction_batch
            SET status = %s,
                message = %s,
                output_hash = %s,
                finished_at = %s
            WHERE id = %s
            """,
            [status, message, output_hash, finished_at or datetime.now(), batch_id],
        )

    def write(
        self,
        model: ModelConfig,
        long_df: pd.DataFrame,
        base_time: datetime,
        input_window_start: datetime,
        input_window_end: datetime,
        prediction_run_id: str,
        batch_id: int,
        runtime_seconds: float,
        input_schema_hash: str | None = None,
        input_alignment_metadata: dict[str, object] | None = None,
    ) -> PredictionWriteResult:
        model_id = self._model_id(model)
        target_features = self._feature_lookup(model.target_type)
        value_col = _prediction_value_column(model.target_type, long_df)
        now = datetime.now()
        result_hash = _hash_frame(long_df, ["point", "step", value_col])

        run_id = self.db.insert_one(
            """
            INSERT INTO em_prediction_run (
                project_id, batch_id, model_id, model_code, model_version, target_type,
                artifact_hash, preprocessor_hash, inference_script_hash, best_params_hash,
                runtime_manifest_hash, environment_digest, artifact_bundle_hash,
                input_schema_hash, required_history_rows, metric_code,
                input_window_start, input_window_end, horizon_seconds, horizon_minutes,
                rolling_steps, input_snapshot_json, status, message, result_hash,
                runtime_seconds, started_at, finished_at
            )
            SELECT
                %s, %s, id, model_code, model_version, target_type,
                artifact_hash, preprocessor_hash, inference_script_hash, best_params_hash,
                runtime_manifest_hash, environment_digest, artifact_bundle_hash,
                %s, %s, COALESCE(target_metric_code, target_type),
                %s, %s, %s, %s, %s, %s, 'success', NULL, %s,
                %s, %s, %s
            FROM em_prediction_model
            WHERE id = %s
            """,
            [
                self.project_id,
                batch_id,
                input_schema_hash,
                model.required_history_rows,
                input_window_start,
                input_window_end,
                self.horizon_minutes * 60,
                self.horizon_minutes,
                self.rolling_steps,
                json.dumps(
                    _input_snapshot(
                        model=model,
                        prediction_run_id=prediction_run_id,
                        feature_mapping_version=self.feature_mapping_version,
                        input_alignment_metadata=input_alignment_metadata,
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                result_hash,
                runtime_seconds,
                now,
                now,
                model_id,
            ],
        )
        rows = []
        for row in long_df.to_dict("records"):
            training_feature_code = str(row.get("point"))
            feature = target_features.get(training_feature_code, {})
            feature_code = str(feature.get("feature_code") or training_feature_code)
            feature_name = str(feature.get("feature_name") or feature_code)
            step = int(row["step"])
            horizon_minutes = step * self.time_step_minutes
            future_time = _prediction_future_time(row, base_time, step, self.time_step_minutes)
            predicted_value = _nullable_float(row.get(value_col))
            if predicted_value is None:
                continue
            source_record_key = f"{prediction_run_id}:{model.code}:{feature_code}:{step}"
            rows.append(
                (
                    run_id,
                    batch_id,
                    model_id,
                    model.target_type,
                    feature_code,
                    feature_name,
                    self.project_id,
                    feature.get("station_id"),
                    feature.get("instrument_id"),
                    feature.get("source_metric_code") or model.target_type,
                    step,
                    horizon_minutes,
                    base_time,
                    future_time,
                    base_time,
                    future_time,
                    predicted_value,
                    feature.get("predicted_unit"),
                    predicted_value,
                    feature.get("predicted_unit"),
                    "normal",
                    source_record_key,
                    now,
                )
            )

        sql = """
            INSERT INTO em_prediction_result (
                run_id, batch_id, model_id, target_type, feature_code, feature_name,
                project_id, station_id, instrument_id, metric_code,
                step, horizon_minutes, base_time, future_time,
                predicted_at, prediction_time, raw_predicted_value, raw_predicted_unit,
                predicted_value, predicted_unit,
                quality_flag, source_record_key, created_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
        """
        inserted_rows = self.db.execute_many(sql, rows)
        self._apply_engineering_conversion(run_id, model.target_type)
        return PredictionWriteResult(run_id=run_id, inserted_rows=inserted_rows, result_hash=result_hash)

    def _apply_engineering_conversion(self, run_id: int, target_type: str) -> None:
        if target_type == "YD":
            self.db.execute(
                """
                UPDATE em_prediction_result r
                JOIN em_metric_baseline_history h
                  ON h.project_id=r.project_id AND h.instrument_id=r.instrument_id
                 AND h.metric_code='displacement_tilt_y_deg' AND h.effective_to IS NULL
                JOIN em_conversion_parameter p
                  ON p.project_id=r.project_id AND p.instrument_id=r.instrument_id
                 AND p.parameter_code='initial_y_mm' AND p.effective_to IS NULL
                SET r.engineering_metric_code='deep_horizontal_displacement_y',
                    r.engineering_value=1000*SIN(RADIANS(r.raw_predicted_value))
                      -1000*SIN(RADIANS(h.baseline_value))+p.parameter_value,
                    r.engineering_unit='mm',
                    r.conversion_operator_code='displacement_y_engineering',
                    r.conversion_version='displacement-v2-20260714',
                    r.conversion_status='success',
                    r.conversion_remark='Raw predicted Y angle converted with baseline and calibrated initial Y'
                WHERE r.run_id=%s
                """,
                [run_id],
            )
        elif target_type == "XD":
            self.db.execute(
                """
                UPDATE em_prediction_result r
                JOIN em_metric_baseline_history h
                  ON h.project_id=r.project_id AND h.instrument_id=r.instrument_id
                 AND h.metric_code='displacement_tilt_x_deg' AND h.effective_to IS NULL
                SET r.engineering_metric_code='deep_horizontal_displacement_x',
                    r.engineering_value=1000*SIN(RADIANS(r.raw_predicted_value))
                      -1000*SIN(RADIANS(h.baseline_value)),
                    r.engineering_unit='mm',
                    r.conversion_operator_code='displacement_x_engineering',
                    r.conversion_version='displacement-v2-20260714',
                    r.conversion_status='success',
                    r.conversion_remark='Raw predicted X angle converted with baseline; initial X is zero'
                WHERE r.run_id=%s
                """,
                [run_id],
            )
        elif target_type == "water":
            self.db.execute(
                """
                UPDATE em_prediction_result r
                JOIN em_conversion_parameter p
                  ON p.project_id=r.project_id AND p.instrument_id=r.instrument_id
                 AND p.parameter_code='module_elevation_m' AND p.effective_to IS NULL
                SET r.engineering_metric_code='groundwater_elevation_m',
                    r.engineering_value=p.parameter_value-r.raw_predicted_value/1000,
                    r.engineering_unit='m',
                    r.conversion_operator_code='pit_water_elevation',
                    r.conversion_version='pit-water-v2-20260714',
                    r.conversion_status='success',
                    r.conversion_remark='Raw predicted pressure head converted to excavation groundwater elevation'
                WHERE r.run_id=%s
                """,
                [run_id],
            )
        elif target_type == "settlement":
            self.db.execute(
                """
                UPDATE em_prediction_result r
                JOIN em_instrument i ON i.id=r.instrument_id
                JOIN em_reference_binding b
                  ON b.project_id=r.project_id AND b.instrument_type='static_level'
                 AND b.module_no=i.module_no AND b.enabled=1
                JOIN em_metric_baseline_history h
                  ON h.project_id=r.project_id AND h.instrument_id=r.instrument_id
                 AND h.metric_code='static_level_value_mm' AND h.effective_to IS NULL
                JOIN em_metric_baseline_history rh
                  ON rh.project_id=r.project_id AND rh.instrument_id=b.reference_instrument_id
                 AND rh.metric_code='static_level_value_mm' AND rh.effective_to IS NULL
                JOIN em_prediction_result rr
                  ON rr.batch_id=r.batch_id AND rr.step=r.step AND rr.target_type='settlement'
                 AND rr.instrument_id=b.reference_instrument_id
                SET r.engineering_metric_code='ground_settlement',
                    r.engineering_value=CASE WHEN r.instrument_id=b.reference_instrument_id THEN 0
                      ELSE (r.raw_predicted_value-h.baseline_value)
                        -(rr.raw_predicted_value-rh.baseline_value) END,
                    r.engineering_unit='mm',
                    r.conversion_operator_code='static_level_reference_compensation',
                    r.conversion_version='static-level-v2-positive-20260713',
                    r.conversion_status='success',
                    r.conversion_remark='Prediction point change minus same-batch same-step reference-point change'
                WHERE r.run_id=%s
                """,
                [run_id],
            )
        else:
            self.db.execute(
                """
                UPDATE em_prediction_result
                SET engineering_metric_code=metric_code,
                    engineering_value=raw_predicted_value,
                    engineering_unit=raw_predicted_unit,
                    conversion_operator_code='identity',
                    conversion_version='v1',
                    conversion_status='success',
                    conversion_remark='Identity engineering mapping'
                WHERE run_id=%s
                """,
                [run_id],
            )
        self.db.execute(
            """
            UPDATE em_prediction_result
            SET conversion_status='missing_prerequisite',
                conversion_remark=CONCAT(
                  'Engineering conversion prerequisites are incomplete for target ',
                  COALESCE(target_type,'unknown'))
            WHERE run_id=%s AND conversion_status='pending'
            """,
            [run_id],
        )

    def _model_id(self, model: ModelConfig) -> int:
        return model.id

    def _feature_lookup(self, target_type: str) -> dict[str, dict]:
        df = self.db.read_frame(
            """
            SELECT feature_code, feature_name,
                   COALESCE(
                       NULLIF(training_feature_code, ''),
                       JSON_UNQUOTE(JSON_EXTRACT(metadata_json, '$.trainingFeatureCode')),
                       feature_code
                   ) AS training_feature_code,
                   station_id, instrument_id,
                   source_metric_code, m.default_unit AS predicted_unit
            FROM em_prediction_feature_mapping f
            LEFT JOIN em_metric m ON m.metric_code = f.source_metric_code
            WHERE f.project_id = %s
              AND f.schema_version = %s
              AND f.enabled = 1
              AND f.feature_group = %s
            """,
            [self.project_id, self.feature_mapping_version, target_type],
        )
        return {str(row["training_feature_code"]): row for row in df.to_dict("records")}


def _runtime_environment() -> dict[str, object]:
    packages = {}
    for distribution in ("joblib", "numpy", "pandas", "PyMySQL", "scikit-learn", "torch"):
        try:
            packages[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            packages[distribution] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _input_snapshot(
    model: ModelConfig,
    prediction_run_id: str,
    feature_mapping_version: str,
    input_alignment_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "predictionRunCode": prediction_run_id,
        "artifactUri": model.model_path.name,
        "preprocessorUri": model.preprocessor_path.name,
        "inferenceScriptHash": model.inference_script_hash,
        "bestParamsHash": model.best_params_hash,
        "runtimeManifestHash": model.runtime_manifest_hash,
        "environmentDigest": model.environment_digest,
        "runtimeEnvironment": _runtime_environment(),
        "featureMappingVersion": feature_mapping_version,
    }
    if input_alignment_metadata:
        snapshot.update(input_alignment_metadata)
    return snapshot


def _prediction_value_column(target_type: str, df: pd.DataFrame) -> str:
    preferred = PREDICTION_VALUE_COLUMNS.get(target_type)
    if preferred and preferred in df.columns:
        return preferred
    pred_cols = [c for c in df.columns if c.endswith("_pred")]
    if len(pred_cols) == 1:
        return pred_cols[0]
    raise ValueError(f"Cannot determine prediction value column for target_type={target_type}")


def _nullable_float(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _nullable_dt(value):
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).to_pydatetime()


def _prediction_future_time(row: dict, base_time: datetime, step: int, time_step_minutes: int) -> datetime:
    explicit = _nullable_dt(row.get("future_time"))
    if explicit is not None:
        return explicit
    return base_time + timedelta(minutes=step * time_step_minutes)


def _hash_frame(df: pd.DataFrame, columns: list[str]) -> str:
    stable = df[columns].copy()
    stable = stable.sort_values(columns[:2]).reset_index(drop=True)
    payload = stable.to_json(orient="records", date_format="iso", force_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
