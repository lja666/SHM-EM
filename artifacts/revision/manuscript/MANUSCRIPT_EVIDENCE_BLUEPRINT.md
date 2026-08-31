# Manuscript Evidence Blueprint

This blueprint converts repository evidence into compact scientific material. It does not modify the manuscript.

## Table A: Versioned data-model contract

Source: `docs/revision/DATA_MODEL_CONTRACT_SPEC.md` and the compact schema-validated example. Show contract version/hash, ordered feature binding, target binding, units/transforms, 40-step timeline, and fail-closed missing-data policy.

## Table B: Six-model configuration

Source: `docs/revision/MODEL_CONFIG_SUMMARY.md`. Show model type/version, history length, feature/target counts, tensor-derived dimensions, parameter source, and verified artifact hashes. Do not infer unrecorded hyperparameters.

## Algorithm 1: Project Future State aggregation

Source: `docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md`. Present canonical policy verification, per-feature consecutive threshold evaluation, target/station/project aggregation, earliest exceedance, observed/forecast separation, and deterministic state hashing.

## Table C: Software validation

Source: `artifacts/revision/manuscript/software-test-summary.md`. Report test families separately: 55 backend tests, 13 PIT_PRE tests, 15 negative/integrity cases, 7 second-configuration checks, 2 frontend checks, and one reference reproduction. Do not sum overlapping families into a global total.

## Table D: Runtime and scalability characterization

Source: `artifacts/revision/manuscript/final-performance-table.csv`. Include the public reference workflow plus S1/S2 Gate endpoints. State concurrency, sample count, workload dimensions, and the 50,000-row Gate boundary. Do not use the diagnostic six-level sweep as linear-scaling evidence.

## Table E: Related-software capability comparison

Build during manuscript revision from primary publications and official documentation. Candidate columns: versioned model/data contract; authoritative prediction batch; persisted integrity gate; Evaluate/Execute separation; deterministic project future state; formal event/provenance linkage; failure-path validation; quantitative runtime evidence. Use `not reported` rather than inferring absence.

## Figure: Validation-to-response evidence chain

Redraw the workflow as: observation and canonical alignment -> versioned contract -> prediction batch/run/results -> integrity/freshness Gate -> rule Evaluate -> rule Execute -> formal event -> response/evidence archive. Clearly separate validation, evaluation, and execution eligibility. Use the concrete trace in `docs/revision/PROVENANCE_TRACE_EXAMPLE.md` as the caption-level example.

## Revision placement

- Software description: Tables A-B and Algorithm 1.
- Validation section: Tables C-D and the provenance figure.
- Impact/limitations: claim-gap matrix wording.
- Related software: Table E.
- Repository/data availability: identify public sample data, open model artifacts, and private field-data boundary precisely.
