# SHM-EM Data-Model Contract Specification

## Status and scope

This document specifies the persisted observation-to-model contract implemented by SHM-EM at Performance-Corrected Final Core Freeze v3 (`eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`). It describes the current rolling point-forecast implementation; it does not define a generic training-data format or a probabilistic forecast contract.

The machine-readable sources are:

- `em_prediction_model`: model identity, runtime contract, timeline, artifact locations, and SHA-256 digests;
- `em_prediction_feature_mapping`: ordered feature bindings, source fields, target mappings, required flags, and conversions;
- `em_station_metric` and `em_metric`: raw and engineering units plus metric metadata;
- `src/pit_pre/runtime-manifest.json`: Python/runtime dependency contract;
- `src/pit_pre/pit_pre/contract.py`: authoritative loading and validation behavior.

The complete database-derived export is `artifacts/revision/manuscript/data-model-contract-export.json`. The compact example and its JSON Schema are in `docs/revision/examples/`. The compact file intentionally shows one model, four representative inputs, and two representative targets; it is not a replacement for the full 6-model, 164-feature, 124-target export.

## Contract identity and versions

| Field | Authority | Current meaning |
|---|---|---|
| `contractVersion` | `em_prediction_model.contract_version` | Pipeline-level contract version shared by every active model |
| `featureMappingVersion` | `em_prediction_feature_mapping.schema_version` | Ordered feature-schema version selected by every active runtime configuration |
| `model.code/version` | `em_prediction_model` | Stable model identity used by runs and provenance |
| `runtime.schemaVersion` | runtime manifest | Runtime environment schema, independent of feature mapping version |
| conversion version | feature mapping | Version of the output engineering conversion |
| integrity version | prediction run/batch | Version used to canonicalize and verify persisted forecast rows |

All active models must agree on contract version, mapping schema, prediction mode, expected future steps, time-step duration, horizon, and runtime manifest. A version change requires a new database contract row or mapping version; silently mutating an existing immutable artifact is invalid because its digest will no longer match.

## Model contract

Each active model must provide:

1. a non-empty model code, target type, and model version;
2. positive history-row, future-step, time-step, maximum-age, and runtime-timeout values;
3. existing model artifact, preprocessor, inference script, and runtime-manifest files;
4. a best-parameter file and digest when `bestParamsPath` is declared;
5. SHA-256 digests for the artifact, preprocessor, inference script, runtime manifest, input schema, environment, and complete bundle;
6. one or more enabled required prediction targets;
7. rolling mode, where `horizonMinutes = expectedSteps * timeStepMinutes`.

The bundle digest is calculated from the artifact, preprocessor, inference script, optional best-parameter digest, input-schema digest, contract version, runtime-manifest digest, and environment digest. The environment digest binds the dependency-lock digest to the runtime-manifest digest.

## Ordered feature contract

The runtime selects mappings where `enabled=1`, `required=1`, and `featureRole=model_input`. For the current public contract:

- feature order is globally contiguous from 1 through 164;
- every mapping is bound to an active `modelId`;
- every `trainingFeatureCode` is non-empty and unique;
- the exact training input columns are `time`, `time1`, followed by the 164 training feature codes in order;
- the SHA-256 of the pipe-delimited ordered column list must equal every active model's `inputSchemaHash`.

Each mapping records the logical feature code separately from the training-column code. This preserves engineering names such as `point1_0.8YD_value` while retaining the immutable column name used by the trained bundle.

## Source, unit, and transformation semantics

Each feature identifies its source registry, station, instrument, metric, physical value column, and value mode. `RAW` means that the model consumes the stored raw measurement semantics defined by the contract. `ENGINEERING` means that the mapped engineering value is consumed. The current six-model public contract uses `RAW` inputs and records both raw and engineering units from `em_station_metric`.

Input transformations and output engineering conversions are separate:

- `featureOperatorCode` and `transformJson` describe preprocessing before model input;
- `stationConversionOperatorCode` identifies the registered observation conversion;
- `outputConversionOperatorCode` and `outputConversionVersion` define how a predicted raw target becomes an engineering forecast.

No implicit unit conversion is inferred from a label. Missing conversion metadata, a failed conversion, or a rule threshold whose unit is incompatible with the engineering series is rejected at the relevant conversion, evaluation, or execution boundary.

## Prediction targets and timeline

`predictionTarget=true` marks a mapped feature as an output target of its model. A successful batch has one shared base time, six successful model runs, 40 future steps at 3-minute intervals, and 124 target channels in the public reference configuration. Persisted results retain raw predicted values, engineering values, conversion operator/version/status, target identity, model/run/batch identity, and future timestamps.

The execution gate verifies the complete model set, required features, target set, 40-step timeline, units/conversion status, artifact and contract hashes, persisted-result hashes, batch-output hash, quality, and mode-specific freshness. The current gate inspection boundary is at most 50,000 prediction-display rows.

## Failure behavior

SHM-EM fails closed at the following boundaries:

| Condition | Behavior |
|---|---|
| Missing/duplicate model or required feature | Reject contract loading or inference |
| Non-contiguous order or schema-hash drift | Reject contract loading |
| Missing artifact or digest mismatch | Reject contract loading before inference |
| Unsupported mode or inconsistent horizon | Reject contract loading |
| Missing target, incomplete steps, temporal misalignment, failed run, stale operational batch, or corrupted persisted result | Gate is ineligible |
| Failed engineering conversion or incompatible rule unit | Rule evaluation/execution is rejected |
| State changes after Evaluate | Execute re-inspects the latest persisted batch and rejects before formal side effects |

Evaluate is side-effect-free with respect to formal events and response workflows. Execute may create those records only after a fresh eligible gate result. This contract therefore covers both data assembly and the controlled transition from persisted forecasts to formal events.

## Missing and asynchronous observations

The public reference policy does not silently impute a missing required feature. Input assembly aligns observations to the configured cadence and shared prediction origin; missing required values, timestamps outside the configured alignment tolerance, or an incomplete required history window are rejected before inference. Alignment diagnostics are persisted with the run input snapshot. This is a fail-closed software policy, not a claim that the forecasting model is robust to arbitrary sensor dropout.

## Reproduction

After preparing the public reference database, regenerate and validate the contract with:

```powershell
$env:SHM_EM_DB_PASSWORD = '<local-password>'
python tools/revision/export_data_model_contract.py
Remove-Item Env:SHM_EM_DB_PASSWORD
```

The password is never serialized. The export records only the source database name, table names, source paths, hashes, and Freeze v3 commit.
