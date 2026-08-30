# Phase 1B Workflow Fixture Model Card

## Scope

The Phase 1B bridge configuration reuses the repository's packaged `Strain`
and `Pressure` model artifacts solely to validate software workflow reuse.

## Intended Use

- Verify database-authoritative model contracts.
- Verify feature registration and PIT_PRE input assembly.
- Verify prediction persistence and artifact/result integrity checks.
- Verify Future State, Evaluate, Execute, response, and provenance APIs.

## Prohibited Interpretation

The output must not be interpreted as:

- bridge-domain predictive validation;
- evidence of model transferability from excavation to bridges;
- an accuracy, calibration, uncertainty, or safety claim;
- engineering advice for a real bridge.

## Artifacts

The fixture references the existing immutable `Strain` and `Pressure` bundles.
Their artifact, preprocessor, inference-script, parameter, runtime-manifest,
environment, and bundle hashes are loaded from `em_prediction_model` and
verified by the frozen PIT_PRE contract and the Java execution Gate.

## Data

Inputs are deterministic synthetic time series distributed over three bridge
stations. They are designed for contract coverage and repeatability, not for
physical realism or model evaluation.
