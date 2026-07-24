# PIT_PRE Prediction Pipeline

## Input Construction

PIT_PRE reads `em_prediction_feature_mapping` and builds one wide-table row per
sampling time. Each feature row links a canonical SHM-EM feature identity, the
stable model training column, and a canonical observation source:

```text
feature_code                 -- SHM-EM canonical identity, e.g. point1_0.8XD_value
                             -- or dtu1_point1_settlement_value
training_feature_code        -- model column, e.g. point10.8XD_value
  -> station_id / instrument_id
  -> source_registry_code
  -> source_metric_code
  -> source_value_column
  -> registered type-specific observation table
```

PIT_PRE builds model input with `training_feature_code`, while prediction
results are written with canonical `feature_code` / `feature_name`. This keeps
trained model artifacts compatible without leaking model-native names into
SHM-EM-facing tables and APIs.

Current mapping semantics:

```text
displacement_tilt_y_deg.metric_value      -> YD_value
displacement_tilt_x_deg.metric_value      -> XD_value
earth_pressure_strain_ue.metric_value     -> Strain_value
earth_pressure_p.metric_value             -> Pressure_value
pressure_water_level_mm.metric_value      -> water_value
static_level_value_mm.metric_value        -> settlement_value
static_level_value_mm.baseline_value      -> settlementbaseline_value
ground_settlement.metric_value            -> settlementdelta_value
static_level_aux_mm.metric_value          -> settlementdata2_value
static_level_temperature_c.metric_value   -> settlementtemperature_value
```

The active schema currently maps 164 model input features:

```text
YD          42
XD          42
Strain      14
Pressure    14
water        2
settlement  50
```

Only rows with `prediction_target=1` are expected as result features. This
produces 124 targets per step: 42 YD, 42 XD, 14 Strain, 14 Pressure, 2 water,
and 10 settlement raw-value targets. Gate completeness is therefore
`124 targets x 40 steps = 4,960` forecast points for the full model set.

Settlement features are normalized from the updated DTU-split training columns,
for example:

```text
1point1settlement_value          -> dtu1_point1_settlement_value
1point7基准点settlement_value    -> dtu1_point7_ref_settlement_value
2point1基准点settlement_value    -> dtu2_point1_ref_settlement_value
```

## Output Organization

Prediction output is stored in the SHM-EM canonical tables:

```text
em_prediction_batch   -- one synchronized rolling forecast cycle
em_prediction_run     -- one model run inside a batch
em_prediction_result  -- one target feature at one future step
```

The runner writes raw model output first and then applies the registered
engineering conversion operator. `raw_predicted_value` remains immutable;
`engineering_value`, `engineering_unit`, `conversion_operator_code`,
`conversion_version`, and `conversion_status` form the consumable prediction
fact used by Spring Boot.

Each result row represents:

```text
one batch + one model + one target type + one feature + one future step
```

Time fields:

```text
input_window_start -> first historical timestamp used by a model run
input_window_end   -> last historical timestamp used by a model run
base_time          -> prediction origin, equal to input_window_end
horizon_minutes    -> future offset from base_time, e.g. 3/6/.../120
future_time        -> actual predicted timestamp for chart x-axis
```

`future_time` is always written. If a model script does not return it, PIT_PRE
derives it as:

```text
future_time = base_time + step * runtime.time_step_minutes
```

For frontend display, query `em_prediction_latest_display` or a Spring Boot API
built on top of it.

## Model Notes

The packaged code contains runnable prediction scripts for:

```text
models/YD__predict
models/XD__predict
models/Strain__predict
models/Pressure__predict
models/water__predict
models/settlement_predict
```

With the default 3-minute interval and 120-minute horizon, rolling mode writes:

```text
step=1  -> next 3 minutes
step=2  -> next 6 minutes
...
step=40 -> next 120 minutes
```

PIT_PRE only computes and persists forecast rows. Forecast-event evaluation,
formal event creation, response workflows, and evidence archiving belong to
Spring Boot.

## Contract Authority

`em_prediction_model` and `em_prediction_feature_mapping` are the authoritative
runtime contract. PIT_PRE validates the active model set, artifact SHA-256,
ordered feature schema, input schema hash, 40-step cadence, and output target
binding before inference. `config.json` is intentionally limited to database
connectivity and the working directory.
