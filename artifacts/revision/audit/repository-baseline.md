# SHM-EM Phase 0 Repository Baseline

> Structural audit only. No benchmark, inference, database mutation, or behavioral validation is claimed here.

## Baseline identity

| Item | Value |
| --- | --- |
| Schema | shm-em-repository-baseline-v1 |
| Branch | revision/softx-d-26-00931 |
| Commit | 1d2ab45e516ef4167c6c4c4265da5b533b2eab78 |
| Submitted tag | v1.0.0 |
| Submitted tag commit | 1d2ab45e516ef4167c6c4c4265da5b533b2eab78 |
| Tag matches audit commit | True |
| Source tree clean outside revision evidence | True |

## Environment

| Runtime | Detected | Version |
| --- | --- | --- |
| OS | True | Windows-10-10.0.22631-SP0 |
| Audit Python | True | 3.10.20 |
| PIT_PRE Python | True | Python 3.10.20 |
| Java | True | java version "1.8.0_221" |
| Maven | True | Apache Maven 3.9.16 (2bdd9fddda4b155ebf8000e807eb73fd829a51d5) |
| Node | True | v22.13.1 |
| npm | True | 10.9.2 |
| MySQL CLI | True | Ver 8.0.41 for Win64 on x86_64 (MySQL Community Server - GPL) |
| Git | True | git version 2.50.0.windows.1 |

MySQL CLI detection only indicates whether this audit process found the command-line client. It does not establish MySQL Server or database availability.

## Test inventory

| Component | Test files | Test classes | Test methods |
| --- | --- | --- | --- |
| Backend | 12 | 12 | 41 |
| PIT_PRE | 1 | 1 | 4 |

These are source-level counts, not execution results.

## Frontend scripts

| Script | Command |
| --- | --- |
| build | vue-tsc --noEmit && vite build |
| dev | vite --host 0.0.0.0 |
| preview | vite preview --host 0.0.0.0 |
| test:build | vue-tsc --noEmit && vite build --mode development |
| typecheck | vue-tsc --noEmit |

## CI and container baseline

- CI operating systems: `windows-latest`
- Docker/Compose present: `False`
- Docker/Compose files: `none`

## Model bundles

| Bundle | Files | Bytes |
| --- | --- | --- |
| src/pit_pre/models/Pressure__predict | 4 | 242712 |
| src/pit_pre/models/settlement_predict | 4 | 594675 |
| src/pit_pre/models/Strain__predict | 4 | 461892 |
| src/pit_pre/models/water__predict | 4 | 352650 |
| src/pit_pre/models/XD__predict | 4 | 941604 |
| src/pit_pre/models/YD__predict | 3 | 1059430 |

The JSON baseline records SHA-256 for all `23` files in model bundle directories.

## Database contracts and persistence

- Contract tables: `em_conversion_operator, em_conversion_parameter, em_dataset_manifest, em_expected_output, em_feature_operator, em_future_state_policy, em_instrument, em_metric, em_observation_table_registry, em_prediction_feature_mapping, em_prediction_model, em_project, em_reference_binding, em_scenario_profile, em_station, em_station_metric`
- Prediction/result tables: `em_event_prediction_link, em_expected_output, em_future_state_policy, em_prediction_batch, em_prediction_execution_gate, em_prediction_feature_mapping, em_prediction_model, em_prediction_result, em_prediction_run`
- Provenance tables: `em_audit_log, em_event_evaluation_run, em_event_evidence_link, em_event_metric_snapshot, em_event_prediction_link`
- Observation tables: `em_obs_acceleration_feature, em_obs_displacement, em_obs_earth_pressure, em_obs_pressure_water_level, em_obs_static_level`

## Key implementations

- Project Future State: `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/ProjectFutureStateServiceImpl.java`
- Prediction execution gate: `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java`
- Provenance endpoint: `GET /api/em/predictions/events/{eventId}/trace`
- Provenance services: `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionServiceImpl.java, src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/EventEvaluationServiceImpl.java`

## Runtime hardcoding inventory

| Category | Occurrences |
| --- | --- |
| Project-code literals | 2 |
| Numeric project IDs | 0 |
| Model/target literals | 21 |
| Physical observation-table literals | 4 |

Repository-relative paths, lines, identifiers, and source text are retained in `repository-baseline.json`.

## Audit findings

| Severity | Code | Finding |
| --- | --- | --- |
| PASS | BASELINE_TAG_MATCH | The audit commit matches immutable tag v1.0.0. |
| HIGH | CI_WINDOWS_ONLY | Current CI runs only on windows-latest. |
| HIGH | DOCKER_ABSENT | No Dockerfile or Compose file is present in the v1.0.0 baseline. |
| INFO | PROJECT_CODE_LITERAL_FOUND | Project-code literals are candidates for semantic review, not automatic evidence of coupling. |
| REVIEW | MODEL_TARGET_LITERAL_FOUND | Model/target literals require classification as display, domain-adapter, or runtime constraints. |
| REVIEW | OBSERVATION_TABLE_LITERAL_FOUND | Observation-table literals require security and extensibility review. |
| MEDIUM | PIT_PRE_TEST_SURFACE_NARROW | PIT_PRE has one test module in the submitted baseline. |
| INFO | PHASE0_STRUCTURAL_ONLY | Phase 0 inventories structure and does not claim that tests, inference, or reproduction passed. |

## Phase 0 boundary

This audit does not run Maven tests, PIT_PRE inference, frontend builds, MySQL reproduction, failure injection, benchmarks, or provenance reproduction. Those activities belong to later phases and must generate their own machine-readable evidence.
