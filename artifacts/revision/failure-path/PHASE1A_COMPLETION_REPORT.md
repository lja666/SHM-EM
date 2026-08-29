# Phase 1A Completion Report

## 1. Baseline

- Core freeze SHA: `df39ffb2b57d16cfdca419adf2492959fcc0931c`
- Freeze record SHA: `6ea8ec64ed456fc7ea503e365107c1b3db82737a`
- Source branch: `revision/softx-d-26-00931`
- Isolated database strategy: one independently restored `shm_em_reproduce_phase1a_*` database per case
- Baseline data: public de-identified sample, 6 models, 124 prediction targets, 40 steps, 4,960 prediction rows
- Baseline batch: `ROLLING_120M_20250101004202_RUN_20260829144344538252`

## 2. Positive Control

- Gate eligible: `true` in `REPRODUCTION`
- Gate dimensions: all six validation dimensions passed
- Evaluate result: at least one forecast candidate; no formal side effects
- Execute result: one formal event, one prediction link, one response workflow, four response steps, and one report
- Notification and external-delivery side effects: zero
- Result: **PASS**

## 3. Failure Matrix

| Case | Expected stage | Actual stage | Eligible | Formal event delta | Result |
|---|---|---|---:|---:|---|
| P00 | Positive control | None | true | 1 | PASS |
| F01 | Execution Gate | Execution Gate | false | 0 | PASS |
| F02 | Execution Gate | Execution Gate | false | 0 | PASS |
| F03 | Execution Gate | Execution Gate | false | 0 | PASS |
| F04 | Execution Gate | Execution Gate | false | 0 | PASS |
| F05 | Rule Validation | Rule Validation | true | 0 | PASS |
| F06 | Execution Gate | Execution Gate | false | 0 | PASS |
| F07 | Execution Gate | Execution Gate | false | 0 | PASS |
| F08 | Execution Gate | Execution Gate | false | 0 | PASS |
| F09 | Persisted Result Integrity | None | true | 1 | **FAIL** |
| F10 | Execution Gate | Execution Gate | false | 0 | PASS |
| F11 | Execution Gate | Execution Gate | false | 0 | PASS |
| F12 | Execute Recheck | Execute Recheck | false | 0 | PASS |
| I01 | Input Alignment Policy | Input Alignment Policy | n/a | 0 | PASS |
| I02 | Input Assembly | Input Assembly | n/a | 0 | PASS |

Summary: 15 cases executed, 14 passed, and 1 discovery case failed.

## 4. Reviewer-Required Cases

- Incomplete steps: Gate set `timelineValid=false`; Execute rejected; no formal side effects.
- Stale prediction: OPERATIONAL Gate set `freshnessValid=false`; Execute rejected.
- Incorrect model hash: Gate set `artifactHashValid=false`; Execute rejected.
- Missing target: Gate set both `featureSetValid=false` and `timelineValid=false`; Execute rejected.
- Invalid unit: Gate remained eligible; rule validation rejected `kPa` against the `mm` threshold.
- Schema mismatch: Gate set `artifactHashValid=false`; Execute rejected.
- Temporal misalignment: a 10-second timestamp shift set `timelineValid=false`; Execute rejected.
- Failed model run: Gate set `modelSetValid=false`; Execute rejected.
- Corrupted persisted values: recorded as the F09 discovery gap below.
- Invalid quality flag: Gate set `qualityValid=false`; Execute rejected.
- Failed batch status: Gate rejected the non-success batch.

## 5. F09 Integrity Discovery

- Mutation: all 40 persisted values for `dtu1_point1_settlement_value` were changed to `109.42900000`.
- Stored hashes left unchanged: `em_prediction_run.result_hash` and `em_prediction_batch.output_hash` were intentionally preserved.
- Gate result: all validation dimensions remained `true`; `executionEligible=true`.
- Execute result: not rejected; one formal event and its response/provenance chain were created.
- Finding code: `PERSISTED_RESULT_INTEGRITY_GAP`
- Interpretation: the frozen Gate validates stored hash presence and contract hashes but does not recompute integrity from current `em_prediction_result` content.
- Phase 1A action: finding recorded only; production core was not modified.

## 6. F12 Evaluate to Execute Recheck

- Evaluate: valid REPLAY candidate returned with `executionEligible=true` and no formal side effects.
- Mutation after Evaluate: one required run artifact hash was changed.
- Execute: independently rechecked the batch and rejected it with an artifact-hash mismatch.
- Formal side effects: zero across every tracked formal table.
- Persisted Gate audit delta: zero because the rejecting Execute transaction rolled back; the Execute error and post-attempt Gate inspection independently show the changed state.
- Result: **PASS**

## 7. Missing and Asynchronous Input Supplement

- I01: deleting one interior observation increased fill/interpolation cells from 24 to 25, left unresolved missing cells at 0, and still produced 4,960 results. **PASS**
- I02: deleting an entire required feature history produced 16 unresolved values for `point10.12Pressure_value`; PIT_PRE exited non-zero and created no new run or result set. **PASS**

## 8. Test Results

- Backend: `mvn -q test` passed.
- PIT_PRE: 10 tests passed.
- Integration matrix: all 15 cases ran against isolated databases.

## 9. Production Core Diff

**NONE**

The following frozen paths have no substantive diff:

- `src/backend/src/main/**`
- `src/frontend/**`
- `src/pit_pre/pit_pre/**`
- `.gitattributes`

## 10. Evidence Paths

- `artifacts/revision/failure-path/failure-matrix.csv`
- `artifacts/revision/failure-path/failure-matrix.json`
- `artifacts/revision/failure-path/failure-matrix.md`
- `artifacts/revision/failure-path/cases/P00/`
- `artifacts/revision/failure-path/cases/F01/` through `F12/`
- `artifacts/revision/failure-path/cases/I01/` and `I02/`
- `artifacts/revision/failure-path/regression-tests.json`
- `artifacts/revision/failure-path/production-core-diff.json`
- `artifacts/revision/failure-path/phase1a-manifest.json`
- `tools/revision/run_failure_matrix.py`

Each case contains `mutation.sql`, `state-before.json`, `gate.json`, `api-response.json`, `state-after.json`, and `case-summary.json`.

## 11. Git Status

- No Phase 1A commit was created.
- Revision-only harness and evidence remain uncommitted for GPT review.
- Seven pre-existing Windows EOL status entries remain untouched; prior core-freeze evidence established that their Git object content is unchanged.

## 12. Next Step

**STOP.** GPT must review the real failure matrix, especially F09, before authorizing either a narrow Phase 1A.1 integrity correction or the second heterogeneous configuration.
