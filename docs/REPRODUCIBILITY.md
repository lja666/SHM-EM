# Reproducibility

SHM-EM 1.0.1 includes a de-identified minimum real-data window and a machine-
checkable workflow. Public reproduction rebuilds the schema, loads the sample,
runs six packaged models, and verifies engineering conversion, prediction
hashes, execution gates, future-state aggregation, rule behavior, event
provenance, response, report, and evidence records.

## Canonical Local Procedure

```powershell
.\scripts\reproduce-local.ps1 `
  -MySqlExe 'D:\MySQL Server 8.4\bin\mysql.exe' `
  -AdminPassword <mysql-root-password> `
  -AppPassword <app-password> `
  -PythonExe 'D:\anaconda3\envs\py310\python.exe'
```

The script uses project `SHM_EM_PUBLIC_SAMPLE` and database
`shm_em_reproduce_local` by default. Reset is rejected outside the
`shm_em_reproduce_*` namespace. Successful runs write machine-readable JSON to
`artifacts/reproduction-windows.json`.

The script stops its temporary backend and removes generated build outputs
after completion. They do not alter an operational `shm_em` database.

## Public Database Inputs

Initialization applies:

1. `sql/shm_em_database/00_SHM_EM_complete_schema.sql`
2. `sql/shm_em_database/01_SHM_EM_conversion_operators.sql`
3. `sql/shm_em_database/02_SHM_EM_public_sample.sql`
4. `sql/shm_em_database/03_SHM_EM_public_validation.sql`

The 16-step sample is the smallest published window that satisfies all model
contracts; the YD model sets the maximum history requirement. The complete
project dataset is not needed for software reproduction.

## Acceptance Contract

| Check | Expected value |
|---|---:|
| Project and event APIs | Success; no preloaded event is required |
| Dataset manifests | 1 |
| Successful models | 6 |
| Prediction targets / future steps | 124 / 40 |
| Prediction results | 4,960 |
| Failed engineering conversions | 0 |
| Referential-integrity failures | 0 |
| Prediction input hash | Matches dataset manifest |
| Prediction output hash | Matches dataset manifest |
| REPLAY execution gate and project future state | Eligible |
| Evaluate | At least one candidate; one audit run may be retained; no formal event, response, report, notification, Gate, or prediction-link records |
| REPRODUCTION Execute | Creates event, gate link, response, and report |
| Notification delivery | 0 tasks in isolated reproduction |
| Event prediction trace | Present |
| Response workflow | One workflow with at least four steps |

Canonical public-sample hashes:

```text
input  d48674617d31b292e2f299af2f53ee8ae225b6db1df27911ee8f5073fdb21811
output e1d1a5a739fcc7637fc707757c3dace02d6a9e13c2cc0776910f850e2fa29475
```

The response reproduction hash contains newly generated identities and varies
between runs. Input and model-output hashes are deterministic.

`REPRODUCTION` execution requires the `reproduce` Spring profile, an isolated
database name, and disabled notification delivery. `REPLAY` is evaluation-only
and cannot create formal events. `OPERATIONAL` applies wall-clock freshness.

## Lower-Level Tools

| Script | Responsibility |
|---|---|
| `init-mysql.ps1` | Initialize public sample or an explicitly authorized external case |
| `start-dev.ps1` | Start the inspectable frontend and backend |
| `reproduce-softwarex-example.ps1` | Validate an already running isolated stack |
| `reproduce-local.ps1` | Orchestrate complete release reproduction |
| `package-release.ps1` | Build a sanitized source archive |

## Direct Component Tests

```powershell
Push-Location src/backend; mvn clean test; Pop-Location
Push-Location src/frontend; npm ci; npm run build; Pop-Location
Push-Location src/pit_pre; python -m unittest discover -s tests -v; Pop-Location
```

See `docs/LOCAL_RELEASE_VALIDATION.md` for the latest local acceptance record
and `docs/DATA_AVAILABILITY.md` for the public/restricted data boundary.
