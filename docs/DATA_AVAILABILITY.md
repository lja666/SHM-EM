# Data Availability

## Public Reproduction Sample

`sql/shm_em_database/02_SHM_EM_public_sample.sql` is a de-identified,
minimum-window sample derived from real monitoring observations. It provides
the full input needed to execute all six released models and verify the
forecast-driven software workflow without publishing the complete project
history.

| Property | Public release value |
|---|---|
| Project code | `SHM_EM_PUBLIC_SAMPLE` |
| Shifted time window | 2024-12-31 23:57:00 to 2025-01-01 00:45:00 |
| Maximum model history | 16 three-minute steps |
| Field monitoring points / sensor records | 9 / 74, de-identified metadata |
| Internal station records | 73 installation-position rows |
| Acquisition modules / DTUs | 17 / 6 before de-identification |
| Low-frequency rows | 2,464 |
| Acceleration samples | 0 |
| Active prediction models | 6 |
| Input features / prediction targets | 164 / 124 |
| Deterministic forecast results | 4,960 |
| Preloaded events or operational records | 0 |

The sample replaces station, instrument, gateway, module, source-record, and
location identifiers used by data rows and object metadata. Two empty
acceleration table definitions retain the authorized schema suffixes
`1426000125` and `1426000126` for compatibility with the published
type-specific storage contract. They contain no waveform records, and the
associated instrument, gateway, module, and location metadata are
de-identified. Timestamps are shifted while cadence and cross-series alignment
are preserved. Required engineering-conversion parameters and reference
bindings are retained under anonymous identifiers. Historical events, response
records, notifications, reports, evidence, and previously computed predictions
are excluded; the reproduction workflow creates fresh records in an isolated
database.

## Restricted Full Dataset

The complete observation history, original identifiers and location, waveform
samples, and historical operational records are maintained outside this public
repository. They are not required to reproduce the published software path.
Access, when permitted, is subject to institutional approval and the original
research-data governance conditions.

Authorized users may supply the three external SQL files described in
`sql/shm_em_database/README.md`. Initialization rejects restricted data files
located inside the public repository.

## Models and Concept Image

The six frozen model bundles and preprocessors under `src/pit_pre/models` are
included in the public release. The frontend asset
`src/frontend/public/pit-point-layout.png` is a conceptual project-plan image,
not a survey drawing or a source of monitoring values, and is also included in
the public release.

## License and Citation

The repository MIT license covers the software source and the six distributed
prediction-model bundles. The de-identified public sample and conceptual plan
image are distributed under CC BY 4.0; see `DATA_LICENSE.txt`. Cite the SHM-EM
release and accompanying SoftwareX article when using the software, models,
concept image, or public sample. No public license is granted for the
restricted full dataset.
