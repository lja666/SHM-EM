# Phase 1B Second Heterogeneous Configuration

## Purpose

`SHM_EM_SYNTH_BRIDGE` is a synthetic, non-excavation configuration used to
validate SHM-EM software configurability and end-to-end workflow reuse. It is
not a bridge prediction benchmark and makes no claim about cross-domain model
accuracy or engineering transferability.

## Configuration Differences

The fixture changes more than a project label:

| Category | Public excavation sample | Phase 1B fixture |
| --- | --- | --- |
| Infrastructure | Excavation | Bridge |
| Topology | Nine field locations with attachment records | Three bridge stations: west pier, midspan, east pier |
| Instruments | Excavation monitoring inventory | Twelve synthetic instruments in four functional families |
| Metric composition | Six prediction target groups | Two prediction target groups, Strain and Pressure |
| Model composition | Six active model bundles | Two active workflow-fixture bundles |
| Rule policy | Excavation warning thresholds | Three-step synthetic pressure workflow trigger |
| Response policy | Notification/report/evidence policy | Report/evidence-only reproduction policy |

The existing typed observation adapters are reused without schema changes:

- `em_obs_displacement`
- `em_obs_earth_pressure`
- `em_obs_pressure_water_level`
- `em_obs_static_level`

No new physical observation table is created and no `em_obs_*` table is
altered.

## Model Route

Phase 1B uses handoff route B: the packaged `Strain` and `Pressure` bundles are
loaded unchanged as workflow fixtures. This route directly exercises the
frozen database contract, cached runner, persistence, integrity Gate, Future
State, rule engine, response workflow, and provenance chain. The synthetic
inputs and resulting predictions are used only to exercise software contracts.

The 164 ordered training columns remain unchanged because they are part of the
frozen preprocessor contract. SHM-EM identities, stations, instruments,
registries, model subset, prediction targets, and rule configuration are
registered independently for the bridge fixture.

## Expected Workflow

```text
project and object registration
  -> existing observation adapters
  -> database model contract
  -> PIT_PRE input assembly
  -> two-model forecast batch
  -> persisted-result integrity
  -> execution Gate
  -> Project Future State
  -> side-effect-free Evaluate
  -> reproduction Execute
  -> formal event and response workflow
  -> event-prediction provenance trace
```

## Negative Onboarding Control

The validation harness disables one required feature mapping before the first
PIT_PRE attempt. Contract validation must reject the incomplete schema and must
not persist a successful prediction batch. The mapping is then restored and
the same frozen core must complete the positive workflow.
