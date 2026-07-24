# Architecture

## Scope

SHM-EM separates observation storage, model inference, and user-facing
operations into three runtimes connected by one MySQL contract:

```mermaid
flowchart LR
  A["Typed observation tables"] --> B["Engineering conversion"]
  B --> C["PIT_PRE rolling inference"]
  C --> D["Prediction batch and results"]
  D --> E["Execution gate"]
  B --> F["Unified MetricSeriesPoint"]
  D --> F
  F --> G["Rule evaluation"]
  E --> G
  G --> H["Formal monitoring event"]
  H --> I["Response workflow"]
  I --> J["Reports, attachments, and audit evidence"]
```

- The Spring Boot backend owns APIs, conversion, rule evaluation, event state,
  response orchestration, reports, evidence, and prediction governance.
- PIT_PRE owns PyTorch inference and writes normalized prediction facts.
- The Vue frontend reads backend APIs and never accesses database tables or
  triggers model inference.

## Backend Boundaries

The Java package `modules.engineering` follows four layers:

| Layer | Responsibility |
|---|---|
| `api` | HTTP controllers and request binding |
| `application` | Use cases, policies, and orchestration |
| `domain` | Engineering and workflow models |
| `infrastructure` | MyBatis interfaces and SQL mappings |

Project-scoped routes are canonical for project rules and events. Observation
requests carry a registry code; the routing service resolves the allowlisted
physical table internally.

## Observation Storage

Low-frequency data remains in four type-specific tables:

- `em_obs_displacement`
- `em_obs_earth_pressure`
- `em_obs_pressure_water_level`
- `em_obs_static_level`

High-frequency acceleration samples remain in
`em_accel_s_1426000125` and `em_accel_s_1426000126`, with shared batch and
derived-feature metadata.

Raw measurements are immutable. Versioned engineering values are calculated by
registered conversion operators and consumed by charts, statistics, rules,
future-state aggregation, and evidence snapshots.

## Prediction Contract

`em_prediction_model` and `em_prediction_feature_mapping` are authoritative
for the six-model set, artifact locations and hashes, input order, output
targets, cadence, history length, and 40-step horizon. Local PIT_PRE JSON
contains only database connectivity and the repository working directory.

A complete run creates one `em_prediction_batch`, six
`em_prediction_run` rows, and 4,960 `em_prediction_result` rows. The
execution gate validates model, feature, timeline, quality, hash, and freshness
constraints before a prediction may create a formal event.

`em_future_state_policy.policy_json` is parsed, hash-verified, and restricted
to supported aggregation operators at runtime. The future-state response
includes a canonical `stateHash`. This state is a synchronized project-level
risk preview; it does not replace the formal event-rule decision path. Complex
rules that cannot be represented by the enabled single-condition threshold
projection remain unassessed.

## Evaluate and Execute

`Evaluate` returns candidate events without writing operational event,
notification, or response state. It does retain an evaluation-run audit row.
`Execute` creates a formal event and response workflow. Prediction execution
also writes `em_event_prediction_link`, which binds the event to the exact
batch, model run, gate decision, first exceedance, lead time, and forecast
snapshot.

`OPERATIONAL` applies wall-clock freshness. `REPLAY` uses a scenario
reference time for evaluation and cannot create formal events. The isolated
`REPRODUCTION` mode is available only under the `reproduce` profile, requires
an independent `shm_em_reproduce_*` database with notifications disabled, and
marks generated events with `run_type=reproduction`.

## Evidence Boundary

SHM-EM stores reports, notification records, audit records, generic file
attachments, and prediction provenance. Generic attachments may reference
images or videos supplied by an external acquisition system. The release does
not include camera control, video streaming, snapshot scheduling, or media
transcoding.
