# Prediction Model Card

## Intended Use

The six packaged PyTorch models demonstrate how SHM-EM assimilates frozen
time-series predictors into a traceable monitoring, warning, and response
workflow. They support the public de-identified reproduction sample and the
restricted source case from which it was derived. They are not presented as
universally validated safety models and must not be used as the sole basis for
engineering or emergency decisions.

| Model | Input features | Output targets | Engineering output |
|---|---:|---:|---|
| `YD` | 114 | 42 | Deep horizontal displacement Y (mm) |
| `XD` | 114 | 42 | Deep horizontal displacement X (mm) |
| `Strain` | 114 | 14 | Earth-pressure strain (microstrain) |
| `Pressure` | 114 | 14 | Earth pressure (MPa) |
| `water` | 114 | 2 | Groundwater elevation (m) |
| `settlement` | 164 | 10 | Ground settlement (mm) |

The aggregate engineering feature schema contains 164 unique input features.
The first five models use a 114-feature subset, while the settlement model
uses all 164 features. The six models produce 124 output targets in total. A
run uses a three-minute cadence and produces 40 future steps (120 minutes),
for 4,960 results per complete batch.

## Contract and Provenance

`em_prediction_model` is authoritative for active model paths, runtime module,
version, cadence, horizon, history length, weight, preprocessor, inference
script, best-parameter and runtime-manifest hashes, environment digest, and
bundle hash. `em_prediction_feature_mapping`
is authoritative for ordered inputs, output targets, monitoring-object links,
and source metrics. PIT_PRE rejects contract or artifact drift before running.

Each model bundle under `src/pit_pre/models` includes its weight file,
inference module, and frozen `preprocessor.joblib`. `best_params.json` is
included where available. `tools/freeze_preprocessors.py` is a maintainer tool,
not part of normal inference.

Some frozen training-column identifiers contain Chinese tokens. They remain
only in `training_feature_code` because renaming them would change the fitted
feature schema. Canonical feature codes, labels, APIs, and UI text are English.

## Output Governance

Model-native outputs are converted to engineering values before charts,
statistics, rule evaluation, future-state aggregation, and evidence snapshots.
`PredictionExecutionGateService` verifies the complete model set, feature set,
contract-defined time axis, quality, complete bundle hashes, and freshness.
`OPERATIONAL`, `REPLAY`, and the isolated reproduction mode use distinct
time-reference and side-effect policies.

## Known Limits

- Outputs are point forecasts; no calibrated uncertainty interval is bundled.
- The package does not claim transfer performance outside the source case.
- The public sample is an inference/reproduction window, not a training or
  independent model-evaluation dataset.
- Training cohort, split strategy, evaluation metrics, and model-development
  provenance must be supplied by the authors if the manuscript makes model-
  performance claims.
- Human review and independent engineering checks remain required.

Artifact hashes are listed in `docs/RELEASE_MANIFEST.md`.
The six frozen bundles and preprocessors are authorized for public inclusion
with the SHM-EM release.
