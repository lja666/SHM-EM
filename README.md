# SHM-EM

SHM-EM is a research software platform for forecast-driven structural health
monitoring and early warning. It integrates typed observations, versioned
engineering conversion, six packaged time-series models, governed rule
execution, formal events, response workflows, and traceable evidence.

```text
monitoring objects -> raw observations -> engineering values
                   -> synchronized prediction batch
                   -> execution gate -> rule evaluation -> formal event
                   -> response workflow -> reports and evidence
```

The public release includes a de-identified minimum-window sample derived from
real monitoring observations. It is not synthetic UI filler. The complete
project history and operational records remain outside the public repository.

## Release Baseline

The 1.0.0 public artifact includes:

- metadata for 9 numbered field monitoring points and 74 sensor records,
  traceable to 17 acquisition modules and 6 DTUs; identifiers and location are
  removed or replaced in the public sample, except for two authorized
  schema-only acceleration table suffixes whose public tables contain no
  waveform rows;
- 2,464 low-frequency observations covering the longest required 16-step model
  input window;
- six public frozen PyTorch model bundles with 164 ordered inputs;
- 124 prediction targets over 40 synchronized three-minute steps;
- deterministic generation of 4,960 engineering-value forecast results;
- prediction gating, side-effect-free Evaluate, controlled Execute, event
  provenance, response workflow, report, and evidence verification;
- the public conceptual plan image used by the frontend.

The two acceleration sensor-table definitions remain part of the schema, but
the public sample contains no acceleration waveform rows.

## Repository Layout

| Path | Contents |
|---|---|
| `src/backend` | Spring Boot 2.6 and MyBatis API |
| `src/frontend` | Vue 3, TypeScript, Element Plus, and ECharts workbench |
| `src/pit_pre` | Database-contract-driven PyTorch inference runtime and public model bundles |
| `sql/shm_em_database` | Schema, conversion operators, public sample, and validation |
| `scripts` | Windows PowerShell initialization, startup, reproduction, and packaging |
| `docs` | Architecture, installation, reproducibility, model, data, and API documentation |

Count definitions for field points, sensors, modules, DTUs, and internal
installation records are documented in `docs/MONITORING_INVENTORY.md`.

## One-Command Reproduction

The canonical SoftwareX procedure targets Windows 10 or later with PowerShell
7. It creates an isolated database, loads the public sample, installs locked
dependencies, runs tests and builds, executes all six models, starts the
backend in `reproduce` mode, and verifies the forecast-event-response chain.

```powershell
.\scripts\reproduce-local.ps1 `
  -MySqlExe 'D:\MySQL Server 8.4\bin\mysql.exe' `
  -AdminPassword <mysql-root-password> `
  -AppPassword <app-db-password> `
  -PythonExe 'D:\anaconda3\envs\py310\python.exe'
```

The script refuses to reset a database outside the `shm_em_reproduce_*`
namespace. Repeat runs require `-ForceReset`. The acceptance record is written
to `artifacts/reproduction-windows.json` and excluded from release archives.

## Local Installation

Requirements are Windows 10 or later, PowerShell 7, Java 8, Maven 3.8+,
Node.js 20+, MySQL 8.0+, and Python 3.10. MySQL 8.4 is the validated release
baseline.

```powershell
.\scripts\init-mysql.ps1 -MySqlExe mysql -User root `
  -Password <mysql-root-password> -Database shm_em_reproduce_local `
  -AppUser shm_em_reproduce -AppPassword <app-db-password>

.\scripts\start-dev.ps1 `
  -DbUrl 'jdbc:mysql://localhost:3306/shm_em_reproduce_local?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai' `
  -DbUsername shm_em_reproduce -DbPassword <app-db-password> `
  -SpringProfilesActive reproduce
```

Detailed instructions, including the optional authorized full-data path, are
in [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Verification

```powershell
Push-Location src/backend; mvn clean test; Pop-Location
Push-Location src/frontend; npm ci; npm run build; Pop-Location
Push-Location src/pit_pre; python -m unittest discover -s tests -v; Pop-Location
```

Public database inputs are applied in this order:

```text
00_SHM_EM_complete_schema.sql
01_SHM_EM_conversion_operators.sql
02_SHM_EM_public_sample.sql
03_SHM_EM_public_validation.sql
```

## Core Contracts

- Frontend and APIs use English labels.
- APIs use project-scoped routes and logical observation registry codes.
- Raw measurements are preserved; charts, statistics, rules, and forecasts use
  versioned engineering values.
- `em_prediction_model` and `em_prediction_feature_mapping` are the
  authoritative model contract.
- `Evaluate` is side-effect free. `Execute` creates formal events only after a
  persisted prediction gate passes.
- `OPERATIONAL` uses wall-clock freshness; `REPLAY` and isolated
  `REPRODUCTION` use scenario-time policies.
- SHM-EM accepts generic image/video attachments but contains no camera,
  stream, snapshot scheduler, or capture subsystem.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Reproducibility](docs/REPRODUCIBILITY.md)
- [Database Contract](docs/DATABASE.md)
- [Prediction Model Card](docs/MODEL_CARD.md)
- [API Guide](docs/API.md)
- [Data Availability](docs/DATA_AVAILABILITY.md)
- [Forecast-Driven Innovation](docs/FORECAST_DRIVEN_INNOVATION.md)
- [Release Manifest](docs/RELEASE_MANIFEST.md)
- [SoftwareX Submission Checklist](docs/SOFTWAREX_ARTIFACTS.md)
- [Third-Party Notices](docs/THIRD_PARTY_NOTICES.md)
- [Author Actions Before Publication](docs/AUTHOR_ACTIONS.md)

## Citation and License

Citation metadata is provided in `CITATION.cff` and `codemeta.json`. Software
source and packaged models are distributed under the MIT license. The
de-identified public sample and conceptual plan image are distributed under
CC BY 4.0; see `LICENSE.txt`, `DATA_LICENSE.txt`, and
[docs/DATA_AVAILABILITY.md](docs/DATA_AVAILABILITY.md). The complete research
dataset remains restricted and is not licensed for public redistribution.
