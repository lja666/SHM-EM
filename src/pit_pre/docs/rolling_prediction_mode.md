# PIT_PRE 2-Hour Rolling Prediction Mode

## Goal

When a user opens a monitored-object chart, the frontend should immediately
show:

1. Recent measured history from the registered type-specific observation table.
2. The latest precomputed 2-hour prediction trend from `em_prediction_result`.

The chart request must not trigger model inference. PIT_PRE precomputes the
prediction trend on a schedule and stores it in SHM-EM canonical prediction
tables.

## Runtime Contract

Rolling mode is defined by the active database model contract, not by a local
JSON runtime block. The release contract uses a 3-minute sampling interval and
a 120-minute horizon, which requires exactly 40 synchronized steps. The local
bootstrap JSON contains only database connectivity and the working directory.

## Prediction Flow

1. Resolve feature sources by registry code and load the latest historical wide table once.
2. Create one `em_prediction_batch`.
3. For each future time step, run selected models against the current virtual
   wide table.
4. Take only each model's local `step=1` output.
5. Rewrite that local step to the global step, from 1 to 40.
6. Merge all target predictions into one virtual future row.
7. Append the virtual row to the input table.
8. Repeat until the 2-hour horizon is complete.
9. Write one `em_prediction_run` per model and all forecast rows to
   `em_prediction_result`.
10. Update batch-level `output_hash`.

This is strict recursive prediction: predicted values become the next input.

## Query Pattern

Latest prediction for one feature:

```sql
SELECT
    step,
    horizon_minutes,
    base_time,
    future_time,
    predicted_value
FROM em_prediction_latest_display
WHERE project_id = ?
  AND target_type = ?
  AND feature_code = ?
ORDER BY step ASC;
```

Latest prediction for all features under one target type:

```sql
SELECT
    feature_code,
    feature_label,
    station_name,
    instrument_code,
    step,
    horizon_minutes,
    base_time,
    future_time,
    predicted_value
FROM em_prediction_latest_display
WHERE project_id = ?
  AND target_type = ?
ORDER BY feature_code ASC, step ASC;
```

The Spring Boot API layer exposes the same read-only pattern through:

```text
GET  /api/em/predictions/batches
GET  /api/em/predictions/models
GET  /api/em/predictions/features
GET  /api/em/predictions/latest
GET /api/em/predictions/latest
GET  /api/em/predictions/batches/{batchId}/execution-gate
GET  /api/em/projects/{projectId}/future-state
```

These endpoints only query existing prediction rows. If no prediction exists,
the frontend receives an empty array and should show a no-data state instead of
triggering model inference.
