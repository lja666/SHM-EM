# Forecast-Driven Innovation and Traceability

## Scientific Software Positioning

SHM-EM implements a traceable prediction-warning-response loop for structural
health monitoring. Its contribution is not a new forecasting algorithm. It is
the software mechanism that turns heterogeneous observations and packaged time
series models into reviewable future-state assessments, governed event
execution, response tasks, and reproducible evidence.

```text
typed observations
  -> engineering conversion
  -> database model contract
  -> synchronized prediction batch
  -> strict execution gate
  -> observation/prediction rule evaluation
  -> formal event
  -> response workflow and evidence
```

## Implemented Mechanisms

### 1. One engineering-value series contract

`MetricSeriesPoint` represents both `OBSERVATION` and `PREDICTION` sources.
Every point carries object identity, metric, time, engineering value and unit,
raw value, conversion operator/version/status, and source provenance. Charts,
statistics, future-state aggregation, and rules therefore consume the same
physical quantity rather than repeating conversion logic in each UI or rule.

### 2. Database-authoritative model contracts

`em_prediction_model` and `em_prediction_feature_mapping` define the active
model set, artifact hashes, ordered training features, output targets, cadence,
horizon, and runtime policy. PIT_PRE accepts only database connectivity and a
working directory from local JSON. Contract drift or artifact drift fails
before inference.

The release contract has a 164-feature common aligned pool and 124 output targets.
Five frozen preprocessors select 114 ordered columns and the Settlement
preprocessor selects 164. A complete
batch contains six successful model runs and 4,960 engineering forecast points
(124 targets x 40 synchronized steps).

### 3. Explicit execution governance

`PredictionExecutionGateService` validates the complete model set, feature set,
40-step time axis, result quality, artifact/input/result hashes, and freshness.
Each decision is persisted in `em_prediction_execution_gate` with a canonical
gate hash.

- `OPERATIONAL` uses wall-clock freshness and protects formal event execution.
- `REPLAY` uses scenario reference time so historical experiments remain
  reproducible and are not permanently rejected by current wall-clock time.

Evaluate may inspect an ineligible historical batch in replay mode. Execute is
blocked unless an operational gate passes.

### 4. A formal project future state

`GET /api/em/projects/{id}/future-state` aggregates engineering predictions
against enabled rule thresholds and minimum consecutive-step requirements. It
returns observed open risk and forecast risk separately, their overall maximum,
the earliest forecast exceedance, target summaries, station contributors, a
40-step risk timeline, and the gate decision. Targets without an applicable
rule are labelled `unassessed`; they are never silently treated as normal.

The active policy JSON is canonical-hash verified and drives unit matching,
feature grouping, forecast-risk ranking, and observed/forecast aggregation.
Each response carries a `stateHash`. This future state is a project-level
forecast summary and does not replace the formal event-rule decision path.

### 5. Event-to-prediction provenance

Formal prediction events link to their batch, model run, and execution gate in
`em_event_prediction_link`. The trace endpoint exposes the input window,
artifact and schema hashes, batch hashes, first exceedance, lead time, forecast
snapshot, gate mode, gate decision, gate hash, and evaluation time. Response
and Evidence presents this trace through one shared evidence drawer.

## User Interface Responsibilities

| Page | Responsibility |
| --- | --- |
| Project Workspace | Compare current observed risk with the aggregated next-two-hour future state. |
| Observation & Prediction | Inspect engineering observations and forecasts on one time axis. |
| Prediction Runs | Inspect batch/model facts, completeness, hashes, and six gate checks. |
| Rules & Events | Evaluate either data source and create events only when execution policy permits. |
| Response & Evidence | Follow response tasks and inspect the linked prediction and gate evidence. |

Shared components render the unified trend, risk indicator, prediction batch
identity, and prediction evidence. The frontend does not infer project risk and
does not trigger model inference when a chart opens.

## Visual Evidence Boundary

The release removes the embedded camera, snapshot, stream, and video-capture
subsystem because it was not supported by a validated acquisition workflow.
The generic evidence model still accepts image and video attachments from
external systems. Prediction evidence, reports, notifications, audit records,
and hashes remain first-class evidence.

## Verification

- Java unit tests cover contract-feature omissions, operational versus replay
  freshness, engineering conversion, consecutive forecast exceedance, and
  observed/forecast risk separation.
- Python `unittest` tests cover database contract loading, bootstrap config
  rejection, and feature-schema drift.
- Frontend production type checking/build validates the shared API contracts.
- The SoftwareX PowerShell workflow reproduces database initialization,
  six-model inference, API startup, and the reference workflow independently
  of the UI.

## Deliberate Limits

- The current packaged models expose point forecasts, not calibrated
  uncertainty intervals. The UI must not claim probabilistic confidence.
- No speculative per-event multi-model detail table is introduced; the current
  event link records the model run that generated the evaluated feature.
- Project future state uses enabled single-condition thresholds. Unsupported
  complex rules remain unassessed rather than being approximated.
- Generic media attachment support is retained, but SHM-EM does not claim to be
  a camera or video acquisition platform.

These boundaries should also constrain the manuscript claims: emphasize
traceable assimilation, execution governance, future-state aggregation, and
closed-loop evidence rather than algorithmic novelty or unsupported sensing
capabilities.
