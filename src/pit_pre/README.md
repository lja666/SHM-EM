# PIT_PRE

PIT_PRE is the Python-side rolling prediction runner assimilated into the
SHM-EM data model. It keeps PyTorch inference outside Spring Boot, but uses
SHM-EM `em_*` tables as the only prediction fact source.

It is responsible for:

1. Resolving each feature's typed observation table through
   `em_observation_table_registry`.
2. Building the model wide-table input from `em_prediction_feature_mapping`
   with the exact column order used during training.
3. Running the packaged YD, XD, Strain, Pressure, water, and settlement models.
4. Writing normalized prediction batches, model runs, and forecast rows to
   `em_prediction_batch`, `em_prediction_run`, and `em_prediction_result`.

## SHM-EM Feature Mapping

The model feature mapping now binds three identities together:

| Layer | Example | Purpose |
| --- | --- | --- |
| SHM-EM feature code | `point1_0.8YD_value`, `dtu1_point1_settlement_value` | Canonical feature identity used by SHM-EM tables and APIs. |
| Training feature code | `point10.8YD_value` | Stored in `training_feature_code`; stable model input column name. Do not rename without retraining. |
| SHM-EM object source | `station_id`, `instrument_id` | Trace the feature to a monitored object and device. |
| SHM-EM metric source | `source_registry_code`, `source_metric_code`, `source_value_column` | Resolve and query the canonical typed observation source. |

Target semantics:

| PIT_PRE target | SHM-EM metric source | Meaning |
| --- | --- | --- |
| `YD` | `displacement_tilt_y_deg` | Raw Y-angle measurement. |
| `XD` | `displacement_tilt_x_deg` | Raw X-angle measurement. |
| `Strain` | `earth_pressure_strain_ue` | Raw earth-pressure strain. |
| `Pressure` | `earth_pressure_p` | Engineering earth-pressure value. |
| `water` | `pressure_water_level_mm` | Raw differential pressure water-level reading. |
| `settlement` | `static_level_value_mm` | Raw static-level measurement. |

Some model-native training feature codes contain Chinese tokens, such as
`point第二条线...`, `1point7基准点...`, or `2point1基准点...`. These codes are
preserved only in `training_feature_code` for model compatibility.
`feature_code` and `feature_name` use SHM-EM canonical names such as
`line2_point1_0.6YD_value`, `dtu1_point7_ref_settlement_value`, or
`dtu2_point1_ref_settlement_value`; human-facing labels are stored in
`feature_label`.

The packaged contract contains 164 ordered input columns after excluding
`time` and `time1`: 42 YD, 42 XD, 14 Strain, 14 Pressure, 2 water, and 50
settlement features. The six models produce 124 forecast targets because only
10 settlement raw-value features are model outputs; the remaining settlement
columns are input covariates. `prediction_target` records this distinction.

## Runtime Flow

```text
em_prediction_feature_mapping
    -> registry resolves a validated type-specific observation table
    -> PIT_PRE builds the ordered model input frame in memory
    -> PIT_PRE runs synchronized 40-step rolling prediction
    -> em_prediction_batch
    -> em_prediction_run
    -> em_prediction_result
    -> Spring Boot query / forecast-event evaluation
```

## Quick Start

1. Initialize the public SHM-EM reproduction database from the repository root:

```powershell
mysql shm_em < sql/shm_em_database/00_SHM_EM_complete_schema.sql
mysql shm_em < sql/shm_em_database/01_SHM_EM_conversion_operators.sql
mysql shm_em < sql/shm_em_database/02_SHM_EM_public_sample.sql
mysql shm_em < sql/shm_em_database/03_SHM_EM_public_validation.sql
```

2. Install the locked release dependencies:

```powershell
pip install -r requirements.lock.txt
```

3. Create a local bootstrap configuration. It may contain only the database
connection and working directory:

```json
{
  "database": {
    "host": "127.0.0.1",
    "port": 3306,
    "database": "shm_em",
    "user": "shm_em",
    "password": "change-me"
  },
  "working_directory": "."
}
```

Model paths, versions, hashes, feature order, cadence, horizon, and quality
policy are loaded from the active database contract. The runner rejects any
runtime or model setting placed in `config.json`.

4. Run one prediction cycle:

```powershell
python -m pit_pre --config config.json --project-code SHM_EM_PUBLIC_SAMPLE
```

For local development, create `config.json` from `config.example.json`. The
example contains no usable password.

Configured model artifact directories:

```text
models/YD__predict
models/XD__predict
models/Strain__predict
models/Pressure__predict
models/water__predict
models/settlement_predict
```

## Scheduled Operation

`python -m pit_pre.daemon` loads the six model bundles once and executes the
database-defined rolling prediction at a configurable interval. The canonical
local reproduction scripts invoke `python -m pit_pre` for one deterministic
cycle; host schedulers may use the daemon when continuous operation is
required.

The model files under `models/` are imported as model definitions. They are not
release entrypoints and must not be edited to point at ad hoc CSV files. See
`models/README.md` for the artifact contract.

## SHM-EM Query and Rule APIs

Spring Boot exposes prediction facts through these query APIs:

```text
GET  /api/em/predictions/batches
GET  /api/em/predictions/batches/{batchId}
GET  /api/em/predictions/batches/{batchId}/runs
GET  /api/em/predictions/batches/{batchId}/execution-gate?mode=OPERATIONAL|REPLAY
GET  /api/em/predictions/models
GET  /api/em/predictions/features
GET  /api/em/predictions/latest
GET  /api/em/predictions/series
GET  /api/em/predictions/events/{eventId}/trace
GET  /api/em/projects/{projectId}/future-state
```

`/series` returns the common `MetricSeriesPoint` contract. A request with
`includeObserved=true` resolves `featureCode` through
`em_prediction_feature_mapping` and returns only the matching observation and
prediction series. It never mixes metrics, instruments, or physical units.

Rules use the same evaluate/execute endpoints for both input sources. Set
`inputSource` to `OBSERVATION` or `PREDICTION`; prediction requests also carry
the batch, feature, horizon, consecutive-step count, and quality policy.

- `Evaluate` returns candidate events and uses `REPLAY` by default, so historical
  experiments are judged against scenario time rather than wall-clock time.
- `Execute` uses `OPERATIONAL`, requires a passing persisted gate record, and
  then persists the formal event and response workflow.
- Forecast execution also writes `em_event_prediction_link` in the same
  transaction so the model, batch, gate record, input window, hashes, first
  exceedance, lead time, and forecast snapshot remain traceable.

Every prediction result stores both model-native and engineering values. The
registered output conversion operator is applied before charts, rules, future
state aggregation, and evidence snapshots consume the forecast.

## Frontend Display

The frontend should render:

- history from the feature's registered typed observation table as a solid line;
- prediction from `em_prediction_result.future_time` as a dashed line;
- `base_time` as the observed/forecast divider;
- threshold and first exceedance markers from forecast-event evaluation.

The frontend must not trigger model inference when a chart is opened.

## Important Constraint

The feature rows in `em_prediction_feature_mapping` must match the training
feature list through `training_feature_code`:

- same feature count;
- same training feature code;
- same feature order;
- same physical point meaning;
- same raw/engineering measurement semantics.

Missing source measurements should not remove columns. PIT_PRE keeps all
configured columns and fails fast when the latest prediction window is
incomplete unless imputation is explicitly configured later.
