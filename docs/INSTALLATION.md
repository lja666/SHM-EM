# Installation

## Requirements

- MySQL 8.0+ and the `mysql` command-line client (8.4 validated)
- Java 8 and Maven 3.8+
- Node.js 20 and npm
- Python 3.10 for PIT_PRE
- Windows 10 or later with PowerShell 7

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
python -m unittest discover -s tests -v
python -m pit_pre --config config.json --project-code SHM_EM_PUBLIC_SAMPLE
Pop-Location
```

PIT_PRE validates model, preprocessor, inference, runtime, bundle, and feature-
schema hashes before running.

## Optional Map

Set `VITE_AMAP_KEY` and `VITE_AMAP_SECURITY_JS_CODE` only in local environment
files. `src/frontend/public/pit-point-layout.png` is the included public
conceptual plan image.
