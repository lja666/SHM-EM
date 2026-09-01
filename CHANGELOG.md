# Changelog

## 1.0.1 - 2026-09-01

- Added Linux-container portability evidence and documented the observed
  cross-platform numerical difference without introducing a tolerance.
- Added source-grounded model-contract, runtime, failure-matrix, provenance,
  related-software, security, and storage-boundary evidence for the SoftwareX
  minor revision.
- Corrected the public model-dimension description by distinguishing the
  common aligned pool, per-model input matrices, mapping records, targets, and
  temporal histories.
- Clarified that Evaluate persists one audit run while creating no formal
  event, response, notification, report, evidence, Gate, or prediction link.
- Preserved the submitted `v1.0.0` tag and production core; this release changes
  validation evidence, documentation, packaging, and publication metadata.

## 1.0.0 - 2026-07-20

- Consolidated source code under `src/backend`, `src/frontend`, and
  `src/pit_pre`.
- Added immutable raw values and versioned engineering conversion for
  observations and predictions.
- Added database-authoritative six-model contracts, frozen preprocessors,
  artifact hashes, and synchronized 40-step rolling inference.
- Added prediction execution gates with separate OPERATIONAL and REPLAY
  freshness policies.
- Added unified observation/prediction series, project future-state
  aggregation, and prediction-event provenance.
- Unified rule evaluation and execution under project-scoped APIs.
- Removed historical migration fields, duplicate global rule endpoints,
  synthetic project padding, and the embedded camera/video-capture subsystem.
- Added the canonical schema, public conversion operators, a de-identified
  minimum real-data window, validation, CI, and a validated Windows PowerShell
  reproduction workflow; the complete case remains outside the public release.
- Extended portable model bundles to hash inference scripts, best parameters,
  the runtime manifest, and the dependency environment.
- Made the hash-verified future-state policy executable and added a canonical
  future-state result hash.
- Added isolated `REPRODUCTION` execution, from-scratch six-model validation,
  prediction-event trace verification, and deterministic response reports.
- Removed duplicate PIT_PRE entry points and replaced frontend feature-name
  inference with explicit engineering-contract fields.
- Made latest-series selection batch-deterministic so prediction runs sharing
  one base time cannot be merged into an invalid multi-batch trend.
- Established a canonical Windows PowerShell reproduction orchestrator and
  Windows component CI coverage.
