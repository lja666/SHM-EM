# SoftwareX Artifact Checklist

## Included and Verified

| Artifact expectation | Repository location |
|---|---|
| Backend source and tests | `src/backend` |
| Frontend source | `src/frontend` |
| Prediction runtime, tests, and six public model bundles | `src/pit_pre` |
| Installation | `README.md`, `docs/INSTALLATION.md` |
| Architecture and innovation boundary | `docs/ARCHITECTURE.md`, `docs/FORECAST_DRIVEN_INNOVATION.md` |
| Database contract | `docs/DATABASE.md`, `sql/shm_em_database` |
| De-identified minimum real-data sample | `sql/shm_em_database/02_SHM_EM_public_sample.sql` |
| Public conceptual plan image | `src/frontend/public/pit-point-layout.png` |
| Data and model statements | `docs/DATA_AVAILABILITY.md`, `docs/MODEL_CARD.md` |
| API guide and live OpenAPI | `docs/API.md`, `/swagger-ui/index.html` |
| Windows PowerShell reproduction | `docs/REPRODUCIBILITY.md`, `scripts/reproduce-local.ps1` |
| Automated CI | `.github/workflows/ci.yml` |
| File integrity | `docs/RELEASE_MANIFEST.md` |
| License and citation | `LICENSE.txt`, `DATA_LICENSE.txt`, `CITATION.cff`, `codemeta.json` |
| Third-party notice | `docs/THIRD_PARTY_NOTICES.md` |
| Change and contribution policy | `CHANGELOG.md`, `CONTRIBUTING.md` |

## Release Acceptance

- Fresh import of the four public numbered SQL files succeeds on MySQL 8.4.
- Backend tests, frontend type checking/build, and PIT_PRE tests pass.
- Six-model inference emits 4,960 engineering-value forecasts from the public
  16-step sample.
- Reproduction validates 16 API, database, hash, gate, event, response, and
  evidence check groups.
- Prediction input and output hashes match the public dataset manifest.
- Runtime credentials and map-provider credentials are not committed.
- The camera/stream/capture subsystem is absent; generic external media
  evidence remains supported.
- Release packaging excludes local dependencies, build outputs, runtime
  configuration, IDE metadata, logs, and named restricted-data files.

## Remaining Author Metadata

Before archival deposit, resolve the non-code decisions listed in
`docs/AUTHOR_ACTIONS.md`: copyright ownership and ORCIDs, repository and
archive DOI, article DOI when available, and a clean Windows acceptance record.
Full project data remain restricted and must not be added to the public
archive.
