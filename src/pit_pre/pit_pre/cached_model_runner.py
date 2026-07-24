from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pandas as pd
import torch
import joblib

from pit_pre.config import ModelConfig


@dataclass
class CachedModel:
    config: ModelConfig
    module: ModuleType
    params: dict
    model: torch.nn.Module
    input_scaler: object
    output_scaler: object
    input_columns: list[str]
    target_columns: list[str]


class CachedModelRunner:
    """
    Keeps imported model modules and loaded PyTorch models in memory.

    The original packaged scripts load weights inside main(). This runner calls their
    helper functions directly so a daemon process can load each model once, then
    reuse it for repeated prediction cycles.
    """

    def __init__(self, models: dict[str, ModelConfig]):
        self.cache = {code: self._load_model(config) for code, config in models.items()}

    def run(self, model: ModelConfig, input_df: pd.DataFrame) -> pd.DataFrame:
        cached = self.cache[model.code]
        module = cached.module
        params = cached.params

        if model.target_type == "settlement":
            return self._run_settlement_from_frame(cached, input_df)

        df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols = (
            _read_data_and_columns_from_frame(input_df)
        )
        target_cols = _target_columns(model.target_type, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols)

        _validate_dimensions(
            model=model,
            params=params,
            yd_cols=yd_cols,
            xd_cols=xd_cols,
            strain_cols=strain_cols,
            pressure_cols=pressure_cols,
            water_cols=water_cols,
            target_cols=target_cols,
        )

        _validate_preprocessor_columns(cached, input_cols, target_cols)
        scaler_all, scaler_response = cached.input_scaler, cached.output_scaler
        if model.target_type == "water":
            x_response, x_env, x_cat, latest_time, latest_time1 = module.build_latest_input(
                df,
                input_cols,
                water_cols,
                scaler_all,
                params,
            )
        else:
            x_response, x_env, x_cat, latest_time, latest_time1 = module.build_latest_input(
                df,
                input_cols,
                target_cols,
                water_cols,
                scaler_all,
                params,
            )

        with torch.no_grad():
            pred_scaled = cached.model(
                x_response.to(module.DEVICE),
                x_env.to(module.DEVICE),
                x_cat.to(module.DEVICE),
            )

        pred_scaled_2d = pred_scaled.cpu().numpy().reshape(-1, int(params["response_dim"]))
        pred_inverse = scaler_response.inverse_transform(pred_scaled_2d)
        _, long_df = module.make_output(pred_inverse, target_cols, latest_time, latest_time1, params)
        return long_df

    def _run_settlement_from_frame(
        self,
        cached: CachedModel,
        input_df: pd.DataFrame,
    ) -> pd.DataFrame:
        model = cached.config
        module = cached.module
        params = cached.params

        (
            df,
            yd_cols,
            xd_cols,
            strain_cols,
            pressure_cols,
            settlement_cols,
            settlement_aux_cols,
            water_cols,
            input_cols,
        ) = _read_settlement_data_and_columns_from_frame(input_df)

        _validate_settlement_dimensions(
            model=model,
            params=params,
            yd_cols=yd_cols,
            xd_cols=xd_cols,
            strain_cols=strain_cols,
            pressure_cols=pressure_cols,
            settlement_cols=settlement_cols,
            settlement_aux_cols=settlement_aux_cols,
            water_cols=water_cols,
        )

        _validate_preprocessor_columns(cached, input_cols, settlement_cols)
        scaler_all, scaler_response = cached.input_scaler, cached.output_scaler
        x_response, x_env, x_cat, latest_time, latest_time1 = module.build_latest_input(
            df,
            input_cols,
            settlement_cols,
            water_cols,
            scaler_all,
            params,
        )

        with torch.no_grad():
            pred_scaled = cached.model(
                x_response.to(module.DEVICE),
                x_env.to(module.DEVICE),
                x_cat.to(module.DEVICE),
            )

        pred_scaled_2d = pred_scaled.cpu().numpy().reshape(-1, int(params["response_dim"]))
        pred_inverse = scaler_response.inverse_transform(pred_scaled_2d)
        _, long_df = module.make_output(pred_inverse, settlement_cols, latest_time, latest_time1, params)
        return long_df

    def _load_model(self, config: ModelConfig) -> CachedModel:
        module = _load_module(config.script_path, f"pit_pre_cached_model_{config.code}")

        if config.best_params_path and hasattr(module, "BEST_PARAMS_PATH"):
            module.BEST_PARAMS_PATH = str(config.best_params_path)

        state = module.load_state_dict(config.model_path)
        if hasattr(module, "load_best_params"):
            base_params = module.load_best_params(config.best_params_path)
        else:
            base_params = module.FALLBACK_PARAMS

        params = module.infer_params_from_best_model(state, base_params)
        loaded_model = module.build_and_load_model(state, params)
        preprocessor = joblib.load(config.preprocessor_path)
        if not isinstance(preprocessor, dict) or preprocessor.get("format_version") != "pit_pre_preprocessor_v1":
            raise ValueError(f"Unsupported preprocessor artifact for {config.code}")
        if preprocessor.get("model_code") != config.code:
            raise ValueError(f"Preprocessor model mismatch for {config.code}")
        if preprocessor.get("input_schema_hash") != config.input_schema_hash:
            raise ValueError(f"Preprocessor input schema mismatch for {config.code}")
        return CachedModel(
            config=config,
            module=module,
            params=params,
            model=loaded_model,
            input_scaler=preprocessor["input_scaler"],
            output_scaler=preprocessor["output_scaler"],
            input_columns=list(preprocessor["input_columns"]),
            target_columns=list(preprocessor["target_columns"]),
        )


def _load_module(script_path: Path, module_name: str) -> ModuleType:
    if not script_path.exists():
        raise FileNotFoundError(f"Model script not found: {script_path}")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load model script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_preprocessor_columns(cached: CachedModel, input_columns, target_columns) -> None:
    if list(input_columns) != cached.input_columns:
        raise ValueError(f"Frozen preprocessor input columns do not match {cached.config.code} input")
    if list(target_columns) != cached.target_columns:
        raise ValueError(f"Frozen preprocessor target columns do not match {cached.config.code} output")


def _target_columns(target_type: str, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols):
    if target_type == "YD":
        return yd_cols
    if target_type == "XD":
        return xd_cols
    if target_type == "Strain":
        return strain_cols
    if target_type == "Pressure":
        return pressure_cols
    if target_type == "water":
        return water_cols
    raise ValueError(f"Unsupported cached model target_type={target_type}")


def _read_data_and_columns_from_frame(input_df: pd.DataFrame):
    df = input_df.copy()
    if "time1" not in df.columns:
        raise ValueError("Prediction input must contain time1 column.")

    df["time1"] = pd.to_numeric(df["time1"], errors="coerce")
    if df["time1"].isna().sum() > 0:
        raise ValueError("time1 contains non-numeric values.")

    df = df.sort_values("time1").reset_index(drop=True)
    yd_cols = [c for c in df.columns if c.endswith("YD_value")]
    xd_cols = [c for c in df.columns if c.endswith("XD_value")]
    strain_cols = [c for c in df.columns if c.endswith("Strain_value")]
    pressure_cols = [c for c in df.columns if c.endswith("Pressure_value")]
    water_cols = [c for c in df.columns if c.endswith("water_value")]

    missing_groups = []
    if not yd_cols:
        missing_groups.append("YD_value")
    if not xd_cols:
        missing_groups.append("XD_value")
    if not strain_cols:
        missing_groups.append("Strain_value")
    if not pressure_cols:
        missing_groups.append("Pressure_value")
    if not water_cols:
        missing_groups.append("water_value")
    if missing_groups:
        raise ValueError(f"Prediction input missing required columns: {', '.join(missing_groups)}")

    input_cols = yd_cols + xd_cols + strain_cols + pressure_cols + water_cols
    return df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols


def _read_settlement_data_and_columns_from_frame(input_df: pd.DataFrame):
    df = input_df.copy()
    if "time1" not in df.columns:
        raise ValueError("Prediction input must contain time1 column.")

    df["time1"] = pd.to_numeric(df["time1"], errors="coerce")
    if df["time1"].isna().sum() > 0:
        raise ValueError("time1 contains non-numeric values.")

    df = df.sort_values("time1").reset_index(drop=True)
    yd_cols = [c for c in df.columns if c.endswith("YD_value")]
    xd_cols = [c for c in df.columns if c.endswith("XD_value")]
    strain_cols = [c for c in df.columns if c.endswith("Strain_value")]
    pressure_cols = [c for c in df.columns if c.endswith("Pressure_value")]
    settlement_cols = [c for c in df.columns if c.endswith("settlement_value")]
    settlement_baseline_cols = [c for c in df.columns if c.endswith("settlementbaseline_value")]
    settlement_delta_cols = [c for c in df.columns if c.endswith("settlementdelta_value")]
    settlement_data2_cols = [c for c in df.columns if c.endswith("settlementdata2_value")]
    settlement_temperature_cols = [c for c in df.columns if c.endswith("settlementtemperature_value")]
    settlement_aux_cols = (
        settlement_baseline_cols
        + settlement_delta_cols
        + settlement_data2_cols
        + settlement_temperature_cols
    )
    water_cols = [c for c in df.columns if c.endswith("water_value")]

    missing_groups = []
    if not yd_cols:
        missing_groups.append("YD_value")
    if not xd_cols:
        missing_groups.append("XD_value")
    if not strain_cols:
        missing_groups.append("Strain_value")
    if not pressure_cols:
        missing_groups.append("Pressure_value")
    if not settlement_cols:
        missing_groups.append("settlement_value")
    if not water_cols:
        missing_groups.append("water_value")
    if missing_groups:
        raise ValueError(f"Prediction input missing required columns: {', '.join(missing_groups)}")

    input_cols = yd_cols + xd_cols + strain_cols + pressure_cols + settlement_cols + settlement_aux_cols + water_cols
    return (
        df,
        yd_cols,
        xd_cols,
        strain_cols,
        pressure_cols,
        settlement_cols,
        settlement_aux_cols,
        water_cols,
        input_cols,
    )


def _validate_dimensions(
    model: ModelConfig,
    params: dict,
    yd_cols,
    xd_cols,
    strain_cols,
    pressure_cols,
    water_cols,
    target_cols,
) -> None:
    actual_response_dim = len(target_cols)
    actual_env_dim = len(water_cols)
    actual_raw_trans_dim = len(yd_cols) + len(xd_cols) + len(strain_cols) + len(pressure_cols)

    if actual_response_dim != int(params["response_dim"]):
        raise ValueError(
            f"{model.code} response column count mismatch: "
            f"data={actual_response_dim}, model={params['response_dim']}"
        )
    if actual_env_dim != int(params["env_dim"]):
        raise ValueError(
            f"{model.code} water column count mismatch: "
            f"data={actual_env_dim}, model={params['env_dim']}"
        )
    if actual_raw_trans_dim != int(params["raw_trans_dim"]):
        raise ValueError(
            f"{model.code} YD+XD+Strain+Pressure column count mismatch: "
            f"data={actual_raw_trans_dim}, model={params['raw_trans_dim']}"
        )


def _validate_settlement_dimensions(
    model: ModelConfig,
    params: dict,
    yd_cols,
    xd_cols,
    strain_cols,
    pressure_cols,
    settlement_cols,
    settlement_aux_cols,
    water_cols,
) -> None:
    actual_response_dim = len(settlement_cols)
    actual_env_dim = len(water_cols)
    actual_raw_trans_dim = (
        len(yd_cols)
        + len(xd_cols)
        + len(strain_cols)
        + len(pressure_cols)
        + len(settlement_cols)
        + len(settlement_aux_cols)
    )

    if actual_response_dim != int(params["response_dim"]):
        raise ValueError(
            f"{model.code} settlement response column count mismatch: "
            f"data={actual_response_dim}, model={params['response_dim']}"
        )
    if actual_env_dim != int(params["env_dim"]):
        raise ValueError(
            f"{model.code} water column count mismatch: "
            f"data={actual_env_dim}, model={params['env_dim']}"
        )
    if actual_raw_trans_dim != int(params["raw_trans_dim"]):
        raise ValueError(
            f"{model.code} YD+XD+Strain+Pressure+settlement+settlement_aux column count mismatch: "
            f"data={actual_raw_trans_dim}, model={params['raw_trans_dim']}"
        )
