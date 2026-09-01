# Database Contract

The public database package uses four numbered files in
`sql/shm_em_database` for clean initialization. The complete schema is the
release contract; the public sample is a bounded, de-identified reproduction
input rather than an alternate schema.

## Design Rules

1. Business tables use the `em_*` namespace.
2. Low-frequency observations remain type-specific; no duplicate generic fact
   table is maintained.
3. The two acceleration sensor-table definitions are intentionally retained.
4. API clients use logical registry codes, never physical table names.
5. Raw measurements remain immutable.
6. Engineering values include operator, version, status, and parameter
   snapshot provenance.
7. Prediction batches, execution gates, and event links are first-class
   provenance records.
8. Runtime services do not create or alter tables.

## Public Inputs

| Order | File | Purpose |
|---:|---|---|
| 1 | `00_SHM_EM_complete_schema.sql` | Complete `em_*` schema and views |
| 2 | `01_SHM_EM_conversion_operators.sql` | Public conversion formulas |
| 3 | `02_SHM_EM_public_sample.sql` | De-identified 16-step observations and contracts |
| 4 | `03_SHM_EM_public_validation.sql` | Boundary, count, and view-contract checks |

## Domain Tables

| Domain | Tables |
|---|---|
| Project and dataset | `em_project`, `em_dataset_manifest` |
| Objects and metrics | `em_station`, `em_instrument`, `em_metric`, `em_station_metric`, `em_metric_baseline_history` |
| Routing | `em_observation_table_registry` |
| Low-frequency observations | `em_obs_displacement`, `em_obs_earth_pressure`, `em_obs_pressure_water_level`, `em_obs_static_level` |
| Acceleration | `em_accel_batch`, two `em_accel_s_*` tables, `em_obs_acceleration_feature` |
| Conversion | `em_conversion_operator`, `em_conversion_parameter`, `em_reference_binding` |
| Prediction | `em_prediction_model`, `em_prediction_feature_mapping`, `em_prediction_batch`, `em_prediction_run`, `em_prediction_result`, `em_prediction_execution_gate` |
| Rules and events | `em_event_rule`, `em_rule_evaluation_run`, `em_monitoring_event`, `em_event_prediction_link` |
| Response and evidence | `em_event_notification_state`, `em_event_state_candidate_log`, `em_event_state_transition`, `em_notification_*`, `em_report_*`, `em_evidence_*` |

Migration-source table names, source-system primary keys, compatibility columns,
and staging tables are absent from the public contract.

## Engineering Values

Observation rows preserve device-native and engineering values with fields
such as:

```text
raw_value / raw_unit
metric_value / metric_unit
baseline_value
conversion_operator_code
conversion_version
conversion_status
conversion_parameter_snapshot_json
source_record_key
```

Prediction rows preserve `raw_predicted_value` and expose engineering value,
bounds, metric code, unit, conversion operator, version, status, and parameter
snapshot. `em_prediction_display` is defined in the canonical schema and
exposes both representations; it does not depend on a private migration file.

## Public Sample Baseline

| Check | Expected |
|---|---:|
| Numbered field monitoring points | 9 |
| Internal station records | 73 |
| Sensor records | 74 |
| Low-frequency rows | 2,464 |
| Acceleration samples | 0 |
| Active prediction models | 6 |
| Required model inputs | 164 |
| Prediction targets | 124 |
| Maximum history steps | 16 |
| Prediction steps | 40 |
| Generated prediction results | 4,960 |
| Conversion parameters | 54 |
| Reference bindings | 2 |
| Preloaded operational records | 0 |

Run `03_SHM_EM_public_validation.sql` after initialization. The complete
restricted case uses the same schema but supplies external data, calibration,
and validation SQL as described in `sql/shm_em_database/README.md`.

## Storage Boundary

The logical observation contract is the project/station/instrument/metric
registry and its engineering-value provenance. The public release implements
that contract with approved, allowlisted MySQL tables resolved through
`em_observation_table_registry`; it does not accept arbitrary physical table
names. MyBatis mappings, JDBC/MySQL connection behavior, SQL views, JSON
functions, and the current schema are implementation-specific.

Integrating TimescaleDB, InfluxDB, or another time-series store would require a
new repository/adapter that returns the same logical observation and
`MetricSeriesPoint` semantics, plus conformance tests for ordering, time zones,
units, conversion provenance, and rule inputs. No alternative database adapter
is implemented or experimentally validated in this release. See
`docs/revision/STORAGE_ADAPTER_BOUNDARY.md`.

The execution Gate currently inspects at most 50,000 prediction-display rows.
That is an application implementation boundary, not a measured MySQL capacity
limit. The validated reference contains 4,960 rows; a 49,600-row synthetic
workload was used only as functional stress evidence.
