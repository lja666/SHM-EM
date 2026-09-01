# Installation

## Requirements

- MySQL 8.0+ and the `mysql` command-line client (8.4 validated)
- Java 8 and Maven 3.8+
- Node.js 20 and npm
- Python 3.10 for PIT_PRE
- Windows 10 or later with PowerShell 7 for the native workflow, or Docker
  Desktop / Docker Engine with Compose v2 for the container workflow

## Recommended Public Reproduction

The release entry points create an isolated database, load the public sample,
install dependencies, run tests/builds, execute all six models, start the
backend with the `reproduce` profile, and write acceptance JSON.

```powershell
.\scripts\reproduce-local.ps1 `
  -MySqlExe 'D:\MySQL Server 8.4\bin\mysql.exe' `
  -AdminPassword <mysql-root-password> `
  -AppPassword <app-password> `
  -PythonExe 'D:\anaconda3\envs\py310\python.exe'
```

The default database is `shm_em_reproduce_local`, project code is
`SHM_EM_PUBLIC_SAMPLE`, and temporary backend port is 5111. Populated databases
are not overwritten implicitly. Use `-ForceReset` only for an isolated
`shm_em_reproduce_*` database.

## Database Only

```powershell
.\scripts\init-mysql.ps1 -MySqlExe mysql -User root `
  -Password <mysql-root-password> -Database shm_em_reproduce_local `
  -AppUser shm_em_reproduce -AppPassword <app-password>
```

Without restricted-data arguments, initialization always loads the four public
numbered SQL files.

## Authorized Full-Data Mode

Authorized researchers may keep the three restricted SQL files outside the
repository and pass them explicitly. Windows example:

```powershell
.\scripts\reproduce-local.ps1 `
  -DataSqlPath 'D:\private\01_SHM_EM_real_data.sql' `
  -ConversionSqlPath 'D:\private\02_SHM_EM_engineering_conversion.sql' `
  -ValidationSqlPath 'D:\private\03_SHM_EM_validation_queries.sql' `
  -ProjectCode IEM_EXCAVATION_REAL `
  -AdminPassword <mysql-root-password> -AppPassword <app-password>
```

The PowerShell script rejects restricted files inside the public repository.

## Development Backend and Frontend

```powershell
.\scripts\start-dev.ps1 -DbUsername shm_em -DbPassword <app-password>
```

Manual startup:

```powershell
$env:DB_USERNAME = 'shm_em'
$env:DB_PASSWORD = '<app-password>'
Push-Location src/backend
mvn spring-boot:run
Pop-Location

Push-Location src/frontend
npm ci
npm run dev
Pop-Location
```

## Prediction Runtime

Create `src/pit_pre/config.json` from `config.example.json` and set only the
database connection and working directory.

```powershell
Push-Location src/pit_pre
python -m pip install -r requirements.lock.txt
# Required when the MySQL account uses caching_sha2_password:
python -m pip install -r requirements-mysql-auth.lock.txt
python -m unittest discover -s tests -v
python -m pit_pre --config config.json --project-code SHM_EM_PUBLIC_SAMPLE
Pop-Location
```

PIT_PRE validates model, preprocessor, inference, runtime, bundle, and feature-
schema hashes before running.

## Docker Compose Reproduction

The Compose path initializes a disposable MySQL database, runs all six PIT_PRE
models as a one-shot service, starts the backend and frontend, and exercises
the complete reference workflow. It requires Bash, Python 3, Docker Engine,
and Docker Compose v2; the application runtimes themselves execute in Linux
containers. The validator is deliberately fail-closed: it also compares the
normalized prediction-output hash with the frozen Windows baseline and exits
nonzero when the hashes differ.

```bash
./scripts/reproduce-compose.sh
```

The script generates process-local database credentials unless they are
provided explicitly, accepts only an isolated `shm_em_reproduce_*` database,
uses readiness checks instead of a fixed startup sleep, and removes the stack
and volume after validation. Set `SHM_EM_KEEP_COMPOSE=1` only for local
inspection. On a restricted network, an operator may set an optional official-
image mirror prefix without editing Compose:

```bash
export SHM_EM_DOCKERHUB_PREFIX=docker.m.daocloud.io/library/
./scripts/reproduce-compose.sh
```

The default remains the official Docker Hub namespace. No restricted dataset,
mail credential, map key, or host-specific path is built into the images.

The Phase 2C container run reached the complete logical workflow with matching
input and contract hashes, but its normalized prediction-output hash differed
from the frozen Windows baseline. No tolerance was introduced. Therefore the
native Windows procedure remains the validated exact-reproduction path; see
`artifacts/revision/portability/portability-limitations.md` for the recorded
cross-platform boundary.

## Optional Map

Set `VITE_AMAP_KEY` and `VITE_AMAP_SECURITY_JS_CODE` only in local environment
files. `src/frontend/public/pit-point-layout.png` is the included public
conceptual plan image.
