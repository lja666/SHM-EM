from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pit_pre.config import BootstrapConfig, DatabaseConfig, load_config
from pit_pre.contract import ModelContractRepository


class FakeDatabase:
    def __init__(self, model_rows: list[dict], feature_rows: list[dict]):
        self.model_rows = model_rows
        self.feature_rows = feature_rows

    def read_frame(self, sql: str, params=None) -> pd.DataFrame:
        if "FROM em_project" in sql:
            return pd.DataFrame([{"id": 1, "project_code": "SHM_EM_PUBLIC_SAMPLE"}])
        if "FROM em_prediction_model" in sql:
            return pd.DataFrame(self.model_rows)
        if "FROM em_prediction_feature_mapping" in sql:
            return pd.DataFrame(self.feature_rows)
        raise AssertionError(f"Unexpected SQL: {sql}")


class ModelContractRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        artifact = self.root / "model.pth"
        preprocessor = self.root / "preprocessor.joblib"
        script = self.root / "predict.py"
        requirements = self.root / "requirements.lock.txt"
        runtime_manifest = self.root / "runtime-manifest.json"
        artifact.write_bytes(b"model")
        preprocessor.write_bytes(b"preprocessor")
        script.write_text("print('ok')\n", encoding="utf-8")
        requirements.write_text("numpy==2.2.6\n", encoding="utf-8")
        runtime_manifest.write_text(
            json.dumps({"dependencyLock": "requirements.lock.txt"}, sort_keys=True),
            encoding="utf-8",
        )
        self.artifact_hash = hashlib.sha256(b"model").hexdigest()
        self.preprocessor_hash = hashlib.sha256(b"preprocessor").hexdigest()
        self.inference_script_hash = hashlib.sha256(script.read_bytes()).hexdigest()
        self.runtime_manifest_hash = hashlib.sha256(runtime_manifest.read_bytes()).hexdigest()
        requirements_hash = hashlib.sha256(requirements.read_bytes()).hexdigest()
        self.environment_digest = hashlib.sha256(
            f"{requirements_hash}|{self.runtime_manifest_hash}".encode("utf-8")
        ).hexdigest()
        self.schema_hash = hashlib.sha256(b"time|time1|point1_value").hexdigest()
        self.bundle_hash = hashlib.sha256("|".join([
            self.artifact_hash,
            self.preprocessor_hash,
            self.inference_script_hash,
            "",
            self.schema_hash,
            "pit_pre_contract_v1",
            self.runtime_manifest_hash,
            self.environment_digest,
        ]).encode("utf-8")).hexdigest()
        self.bootstrap = BootstrapConfig(
            database=DatabaseConfig("localhost", 3306, "root", "password", "shm_em"),
            working_directory=self.root,
        )
        runtime = {
            "scriptPath": "predict.py",
            "bestParamsPath": None,
            "runtimeManifestPath": "runtime-manifest.json",
            "predictionMode": "rolling",
            "predictionHorizonMinutes": 120,
            "timeStepMinutes": 3,
            "maxPredictionSeconds": 60,
            "schemaVersion": "pit_pre_v1",
        }
        self.models = [{
            "id": 7,
            "model_code": "water",
            "target_type": "water",
            "artifact_uri": "model.pth",
            "artifact_hash": self.artifact_hash,
            "preprocessor_uri": "preprocessor.joblib",
            "preprocessor_hash": self.preprocessor_hash,
            "inference_script_hash": self.inference_script_hash,
            "best_params_hash": None,
            "runtime_manifest_hash": self.runtime_manifest_hash,
            "environment_digest": self.environment_digest,
            "artifact_bundle_hash": self.bundle_hash,
            "model_version": "v1",
            "runtime_config_json": json.dumps(runtime),
            "required_history_rows": 13,
            "input_schema_hash": self.schema_hash,
            "contract_version": "pit_pre_contract_v1",
            "expected_steps": 40,
            "time_step_minutes": 3,
            "max_operational_age_minutes": 15,
        }]
        self.features = [{
            "model_id": 7,
            "feature_code": "point1_11.5water_value",
            "training_feature_code": "point1_value",
            "feature_order": 1,
            "prediction_target": 1,
        }]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_loads_runtime_and_models_only_from_database_contract(self) -> None:
        config = ModelContractRepository(
            self.bootstrap,
            db=FakeDatabase(self.models, self.features),
        ).load("SHM_EM_PUBLIC_SAMPLE")

        self.assertEqual(40, config.runtime.expected_steps)
        self.assertEqual(120, config.runtime.prediction_horizon_minutes)
        self.assertTrue(
            os.path.samefile(self.root / "model.pth", config.models["water"].model_path)
        )
        self.assertTrue(
            os.path.samefile(
                self.root / "preprocessor.joblib",
                config.models["water"].preprocessor_path,
            )
        )
        self.assertEqual({"water": 1}, config.prediction_target_counts)
        self.assertEqual(64, len(config.contract_fingerprint))

    def test_rejects_feature_schema_drift(self) -> None:
        changed_schema_hash = "0" * 64
        changed_bundle_hash = hashlib.sha256("|".join([
            self.artifact_hash,
            self.preprocessor_hash,
            self.inference_script_hash,
            "",
            changed_schema_hash,
            "pit_pre_contract_v1",
            self.runtime_manifest_hash,
            self.environment_digest,
        ]).encode("utf-8")).hexdigest()
        models = [dict(
            self.models[0],
            input_schema_hash=changed_schema_hash,
            artifact_bundle_hash=changed_bundle_hash,
        )]
        with self.assertRaisesRegex(ValueError, "Input schema hash mismatch"):
            ModelContractRepository(
                self.bootstrap,
                db=FakeDatabase(models, self.features),
            ).load("SHM_EM_PUBLIC_SAMPLE")

    def test_rejects_inference_script_drift(self) -> None:
        (self.root / "predict.py").write_text("print('changed')\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Inference script hash mismatch"):
            ModelContractRepository(
                self.bootstrap,
                db=FakeDatabase(self.models, self.features),
            ).load("SHM_EM_PUBLIC_SAMPLE")

    def test_bootstrap_file_rejects_runtime_or_model_settings(self) -> None:
        path = self.root / "config.json"
        path.write_text(json.dumps({
            "database": {
                "host": "localhost",
                "user": "root",
                "password": "password",
                "database": "shm_em",
            },
            "working_directory": ".",
            "runtime": {"time_step_minutes": 3},
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "may only contain"):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
