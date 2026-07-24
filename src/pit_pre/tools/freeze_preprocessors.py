from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib

from pit_pre.cached_model_runner import (
    _load_module,
    _read_data_and_columns_from_frame,
    _read_settlement_data_and_columns_from_frame,
    _target_columns,
)
from pit_pre.config import load_config
from pit_pre.contract import load_app_config
from pit_pre.db import Database
from pit_pre.features import FeatureRepository, WideTableBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze PIT_PRE inference preprocessors.")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--project-code", default="SHM_EM_PUBLIC_SAMPLE")
    args = parser.parse_args()

    bootstrap = load_config(args.config)
    config = load_app_config(bootstrap, args.project_code)
    repository = FeatureRepository(
        Database(config.database),
        config.runtime.project_code,
        config.runtime.feature_mapping_version,
    )
    builder = WideTableBuilder(repository, config.runtime.time_step_minutes)

    for model in config.models.values():
        frame = builder.build(model.required_history_rows)
        module = _load_module(model.script_path, f"pit_pre_freeze_{model.code}")
        if model.target_type == "settlement":
            prepared = _read_settlement_data_and_columns_from_frame(frame)
            data, settlement_columns, input_columns = prepared[0], prepared[5], prepared[8]
            target_columns = settlement_columns
        else:
            prepared = _read_data_and_columns_from_frame(frame)
            data, yd, xd, strain, pressure, water, input_columns = prepared
            target_columns = _target_columns(model.target_type, yd, xd, strain, pressure, water)

        input_scaler, output_scaler = module.fit_scalers(data, input_columns, target_columns)
        output_path = model.model_path.parent / "preprocessor.joblib"
        payload = {
            "format_version": "pit_pre_preprocessor_v1",
            "model_code": model.code,
            "model_version": model.model_version,
            "input_schema_hash": model.input_schema_hash,
            "input_columns": list(input_columns),
            "target_columns": list(target_columns),
            "input_scaler": input_scaler,
            "output_scaler": output_scaler,
        }
        joblib.dump(payload, output_path, compress=3)
        print(json.dumps({
            "model": model.code,
            "path": str(output_path),
            "sha256": sha256_file(output_path),
            "inputColumns": len(input_columns),
            "targetColumns": len(target_columns),
        }))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
