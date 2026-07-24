# Packaged Prediction Models

This directory contains the six frozen model bundles used by the SHM-EM
research release. Each bundle includes a PyTorch weight file, an inference
module, a frozen `preprocessor.joblib`, and, where applicable, the selected
hyperparameters in `best_params.json`.

| Model | Native target | Targets | Engineering output |
|---|---|---:|---|
| YD | Y-axis angle | 42 | Deep horizontal displacement Y (mm) |
| XD | X-axis angle | 42 | Deep horizontal displacement X (mm) |
| Strain | Earth-pressure strain | 14 | Microstrain |
| Pressure | Earth pressure | 14 | Earth pressure (MPa) |
| water | Differential water level | 2 | Groundwater elevation (m) |
| settlement | Static-level reading | 10 | Ground settlement (mm) |

The active rows in `em_prediction_model` are authoritative for model paths,
versions, cadence, horizon, history length, SHA-256 values, and runtime
settings. `em_prediction_feature_mapping` is authoritative for ordered inputs
and output targets. PIT_PRE verifies the database contract, model artifact,
frozen preprocessor, environment digest, and bundle hash before inference.

The inference modules are loaded by `pit_pre.cached_model_runner`; they are not
independent CSV-based release entrypoints. Run a complete prediction cycle
through `python -m pit_pre --config config.json` or the platform-level
`scripts/reproduce-local.*` workflow.

Some frozen training column names contain Chinese tokens. They are retained
only as model-native identifiers because renaming them would change the fitted
feature schema. Canonical SHM-EM feature codes, labels, APIs, and user-interface
text are English.
