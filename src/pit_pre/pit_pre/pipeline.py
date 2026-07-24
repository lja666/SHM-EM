from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from time import perf_counter

import pandas as pd

from pit_pre.config import AppConfig, ModelConfig
from pit_pre.db import Database
from pit_pre.features import FeatureRepository, WideTableBuilder
from pit_pre.result_writer import PredictionResultWriter


@dataclass(frozen=True)
class PredictionRunSummary:
    model_code: str
    output_rows: int
    inserted_rows: int
    batch_id: int | None = None
    run_id: int | None = None
    result_hash: str | None = None
    elapsed_seconds: float = 0.0


class PredictionPipeline:
    def __init__(self, config: AppConfig, model_runner):
        self.config = config
        self.db = Database(config.database)
        self.feature_repo = FeatureRepository(
            self.db,
            config.runtime.project_code,
            config.runtime.feature_mapping_version,
        )
        self.wide_builder = WideTableBuilder(self.feature_repo, config.runtime.time_step_minutes)
        self.model_runner = model_runner
        self.result_writer = PredictionResultWriter(
            self.db,
            self.feature_repo.project_id,
            config.runtime.time_step_minutes,
            config.runtime.prediction_horizon_minutes,
            config.runtime.prediction_horizon_minutes // config.runtime.time_step_minutes,
            config.runtime.pipeline_version,
            config.runtime.feature_mapping_version,
        )

    def run_models(self, model_codes: list[str]) -> list[PredictionRunSummary]:
        return self.run_rolling_models(model_codes)

    def run_rolling_models(self, model_codes: list[str]) -> list[PredictionRunSummary]:
        runtime = self.config.runtime
        if runtime.prediction_horizon_minutes % runtime.time_step_minutes != 0:
            raise ValueError(
                "prediction_horizon_minutes must be divisible by time_step_minutes: "
                f"{runtime.prediction_horizon_minutes} / {runtime.time_step_minutes}"
            )

        started = perf_counter()
        execution_started_at = datetime.now()
        models = [self.config.models[code] for code in model_codes]
        max_required_rows = max(model.required_history_rows for model in models)
        rolling_steps = runtime.expected_steps

        virtual_df = self.wide_builder.build(max_required_rows)
        base_time = pd.Timestamp(virtual_df["time"].iloc[-1]).to_pydatetime()
        base_time1 = float(virtual_df["time1"].iloc[-1])
        input_window_start = pd.Timestamp(virtual_df["time"].iloc[0]).to_pydatetime()
        prediction_run_id = (
            f"ROLLING_{runtime.prediction_horizon_minutes}M_{base_time:%Y%m%d%H%M%S}"
            f"_RUN_{execution_started_at:%Y%m%d%H%M%S%f}"
        )
        input_hash = _hash_wide_table(virtual_df)
        input_schema_hash = _hash_columns(virtual_df)
        feature_count = sum(self.config.prediction_target_counts[model.code] for model in models)

        pending_outputs: dict[str, list[pd.DataFrame]] = {model.code: [] for model in models}

        for global_step in range(1, rolling_steps + 1):
            round_predictions: dict[str, dict[str, float]] = {}
            future_time = base_time + timedelta(minutes=global_step * runtime.time_step_minutes)
            future_time1 = base_time1 + global_step

            for model in models:
                input_df = _input_window_for_model(virtual_df, model.required_history_rows)
                local_long_df = self.model_runner.run(model, input_df)
                first_step_df = _globalize_first_step(
                    local_long_df,
                    model.target_type,
                    global_step,
                    future_time,
                    future_time1,
                )
                pending_outputs[model.code].append(first_step_df)
                round_predictions.update(_prediction_values_by_feature(first_step_df, model.target_type))

            virtual_df = pd.concat(
                [
                    virtual_df,
                    pd.DataFrame([
                        _next_virtual_row(
                            virtual_df.iloc[-1],
                            round_predictions,
                            future_time,
                            future_time1,
                        )
                    ]),
                ],
                ignore_index=True,
            )

            elapsed = perf_counter() - started
            if elapsed > runtime.max_prediction_seconds:
                raise TimeoutError(
                    "Rolling prediction exceeded max_prediction_seconds: "
                    f"{elapsed:.2f}s > {runtime.max_prediction_seconds}s at step {global_step}/{rolling_steps}"
                )

        summaries: list[PredictionRunSummary] = []
        input_window_end = base_time
        batch_id = self.result_writer.create_batch(
            batch_code=prediction_run_id,
            base_time=base_time,
            model_count=len(models),
            feature_count=feature_count,
            started_at=execution_started_at,
            input_hash=input_hash,
        )
        result_hashes: list[str] = []
        for model in models:
            long_df = pd.concat(pending_outputs[model.code], ignore_index=True)
            _validate_rolling_output(model, long_df, rolling_steps)
            write_result = self.result_writer.write(
                model=model,
                long_df=long_df,
                base_time=base_time,
                input_window_start=input_window_start,
                input_window_end=input_window_end,
                prediction_run_id=prediction_run_id,
                batch_id=batch_id,
                runtime_seconds=perf_counter() - started,
                input_schema_hash=input_schema_hash,
            )
            result_hashes.append(write_result.result_hash)
            summaries.append(
                PredictionRunSummary(
                    model_code=model.code,
                    output_rows=len(long_df),
                    inserted_rows=write_result.inserted_rows,
                    batch_id=batch_id,
                    run_id=write_result.run_id,
                    result_hash=write_result.result_hash,
                    elapsed_seconds=perf_counter() - started,
                )
            )
        self.result_writer.finish_batch(
            batch_id,
            "success",
            output_hash=_hash_text("|".join(sorted(result_hashes))),
            finished_at=datetime.now(),
        )
        return summaries


def _input_window_for_model(virtual_df: pd.DataFrame, required_rows: int) -> pd.DataFrame:
    input_df = virtual_df.tail(required_rows).copy().reset_index(drop=True)
    input_df["time1"] = range(1, required_rows + 1)
    return input_df


def _validate_rolling_output(model: ModelConfig, long_df: pd.DataFrame, rolling_steps: int) -> None:
    if long_df.empty:
        raise ValueError(f"{model.code} rolling prediction returned no rows")
    if "step" not in long_df.columns or "point" not in long_df.columns:
        raise ValueError(f"{model.code} rolling prediction must contain point and step columns")

    steps = sorted(long_df["step"].astype(int).unique().tolist())
    expected_steps = list(range(1, rolling_steps + 1))
    if steps != expected_steps:
        raise ValueError(
            f"{model.code} rolling prediction step mismatch: "
            f"expected 1..{rolling_steps}, got {steps[:5]}...{steps[-5:] if steps else []}"
        )

    incomplete = (
        long_df.assign(step=long_df["step"].astype(int))
        .groupby("point")["step"]
        .nunique()
        .loc[lambda item: item != rolling_steps]
    )
    if not incomplete.empty:
        sample = ", ".join(f"{point}:{count}" for point, count in incomplete.head(5).items())
        raise ValueError(
            f"{model.code} rolling prediction has incomplete point steps: "
            f"expected {rolling_steps} steps per point, sample={sample}"
        )


def _globalize_first_step(
    long_df: pd.DataFrame,
    target_type: str,
    global_step: int,
    future_time,
    future_time1: float,
) -> pd.DataFrame:
    first_step = long_df[long_df["step"].astype(int) == 1].copy()
    if first_step.empty:
        raise ValueError(f"Model {target_type} did not return step=1 prediction rows")
    first_step["step"] = global_step
    first_step["future_time"] = future_time
    first_step["future_time1"] = future_time1
    return first_step


def _prediction_values_by_feature(df: pd.DataFrame, target_type: str) -> dict[str, dict[str, float]]:
    value_col = f"{target_type}_pred"
    if value_col not in df.columns:
        pred_cols = [col for col in df.columns if col.endswith("_pred")]
        if len(pred_cols) != 1:
            raise ValueError(f"Cannot determine prediction column for target_type={target_type}")
        value_col = pred_cols[0]

    values: dict[str, dict[str, float]] = {}
    for row in df.to_dict("records"):
        point = str(row["point"])
        value = row.get(value_col)
        if pd.isna(value):
            continue
        values[point] = {"value": float(value), "target_type": target_type}
    return values


def _next_virtual_row(
    last_row: pd.Series,
    predictions: dict[str, dict[str, float]],
    future_time,
    future_time1: float,
) -> dict:
    next_row = last_row.to_dict()
    next_row["time"] = future_time
    next_row["time1"] = future_time1
    for feature_name, item in predictions.items():
        if feature_name in next_row:
            next_row[feature_name] = item["value"]
    return next_row


def _hash_wide_table(df: pd.DataFrame) -> str:
    stable = df.copy()
    stable["time"] = pd.to_datetime(stable["time"]).astype(str)
    payload = stable.to_json(orient="records", force_ascii=False)
    return _hash_text(payload)


def _hash_columns(df: pd.DataFrame) -> str:
    return _hash_text("|".join([str(col) for col in df.columns]))


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
