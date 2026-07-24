from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"


@dataclass(frozen=True)
class BootstrapConfig:
    database: DatabaseConfig
    working_directory: Path


@dataclass(frozen=True)
class RuntimeConfig:
    time_step_minutes: int
    project_code: str
    result_table: str
    prediction_mode: str
    prediction_horizon_minutes: int
    max_prediction_seconds: int
    pipeline_version: str
    feature_mapping_version: str
    expected_steps: int


@dataclass(frozen=True)
class ModelConfig:
    id: int
    code: str
    target_type: str
    script_path: Path
    model_path: Path
    preprocessor_path: Path
    runtime_manifest_path: Path
    required_history_rows: int
    model_version: str
    artifact_hash: str
    preprocessor_hash: str
    inference_script_hash: str
    best_params_hash: str | None
    runtime_manifest_hash: str
    environment_digest: str
    artifact_bundle_hash: str
    input_schema_hash: str
    contract_version: str
    expected_steps: int
    time_step_minutes: int
    max_operational_age_minutes: int
    best_params_path: Path | None = None


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    runtime: RuntimeConfig
    models: dict[str, ModelConfig]
    prediction_target_counts: dict[str, int]
    contract_fingerprint: str


def load_config(path: str | Path) -> BootstrapConfig:
    config_path = Path(path).resolve()
    raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    unsupported = sorted(set(raw) - {"database", "working_directory"})
    if unsupported:
        raise ValueError(
            "PIT_PRE config may only contain database and working_directory; "
            f"move runtime/model settings to SHM-EM database contracts: {', '.join(unsupported)}"
        )

    db = raw["database"]
    working_directory = Path(str(raw.get("working_directory", ".")))
    if not working_directory.is_absolute():
        working_directory = (config_path.parent / working_directory).resolve()
    return BootstrapConfig(
        database=DatabaseConfig(
            host=db["host"],
            port=int(db.get("port", 3306)),
            user=db["user"],
            password=db["password"],
            database=db["database"],
            charset=db.get("charset", "utf8mb4"),
        ),
        working_directory=working_directory,
    )
