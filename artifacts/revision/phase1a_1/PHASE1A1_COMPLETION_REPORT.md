# Phase 1A.1 Persisted Prediction Integrity Completion Report

## Stop State

- Branch: `revision/softx-d-26-00931`
- Phase 1A evidence commit: `dba3109`
- Initial core freeze: `df39ffb2b57d16cfdca419adf2492959fcc0931c`
- Freeze record: `6ea8ec64ed456fc7ea503e365107c1b3db82737a`
- Phase 1A.1 production fix commit: `b41c1894f75561c8ef682062a5e6dab35c3916a7`
- Final Core Freeze v2: `b41c1894f75561c8ef682062a5e6dab35c3916a7`
- Second heterogeneous configuration: **NOT STARTED**

Phase 1A.1 is complete. GPT approved the production fix and Final Core Freeze v2;
the evidence and freeze record are captured separately in Commit E.

The seven pre-existing worktree entries under the six model inference scripts and
`src/pit_pre/requirements.lock.txt` are inherited EOL/index-state differences. They
were present before Phase 1A.1, have no content diff in this phase, and are excluded
from the implementation boundary and review source snapshot.

## Implemented Boundary

1. Preserved the original `em_prediction_run.result_hash` and
   `em_prediction_batch.output_hash` fields and values.
2. Added versioned `persisted_result_hash` and `persisted_output_hash` metadata.
3. Hashes are computed only after engineering conversion and cover all
   decision-facing persisted fields specified by the handoff.
4. Added a shared canonical fixture proving Python/Java hash parity.
5. Added fail-closed Gate revalidation through `resultIntegrityValid`.
6. Reused the single result-set load already performed by the Gate; no model-loop
   query was introduced.
7. Added an idempotent existing-database migration and an isolated authorized
   backfill tool. Legacy `NULL` integrity metadata remains ineligible until backfilled.

## H01-H10 Evidence

| Case | Evidence | Result |
|---|---|---|
| H01 | Shared fixture in Python and Java | PASS |
| H02 | Valid batch, including PIT_PRE-written I01 batch | PASS |
| H03 | Missing integrity hash | PASS, fail-closed |
| H04 | Unsupported integrity version | PASS, fail-closed |
| H05 | Persisted prediction value mutation | PASS, rejected |
| H06 | Engineering value mutation | PASS, rejected |
| H07 | Unit mutation with stale hash | PASS, rejected |
| H08 | F05 unit mutation with independently recomputed hash | PASS, Gate accepts and rule semantics reject |
| H09 | Batch aggregate mismatch | PASS, rejected |
| H10 | Evaluate, mutate persisted row, Execute | PASS, Execute recheck rejects |

## Full Failure Matrix

`P00 + F01-F12 + I01-I02 = 15/15 PASS`. The v2 evidence is stored under
`artifacts/revision/phase1a_1/failure-path-v2`; the original Phase 1A discovery
evidence remains under `artifacts/revision/failure-path`.

- F09: `resultIntegrityValid=false`, `executionEligible=false`, formal side effects `0`.
- F12-v2: Evaluate was valid and side-effect-free; a persisted engineering value
  was changed without updating the integrity hash; Execute revalidation rejected it.
- F05-v2: the invalid engineering unit was included in newly recomputed integrity
  hashes, so Gate remained eligible and rule unit validation rejected it with no
  formal event.
- I01: PIT_PRE completed with the expected 4,960 forecast rows and produced hashes
  that the Java Gate independently accepted.

## Regression

- Backend Maven test suite: PASS.
- PIT_PRE unittest suite: PASS, 13 tests.
- Prediction rows before/after: `4960 / 4960`.
- Prediction payload SHA-256 before/after:
  `bf06b5632adc751b3da435a3bf6e016f772de9a0e4d063e1ad4a21b1ecda0864`.
- Original run `result_hash` values: unchanged for all six models.
- Original batch `input_hash/output_hash`: unchanged.
- Fresh schema import: PASS.
- Existing-database migration applied twice: PASS and idempotent.

## Gate Overhead

The benchmark used the newly written I01 batch and revalidated 4,960 rows per call.

- Warm-up calls: 3
- Measured calls: 20
- Median: 435.789 ms
- p95: 484.335 ms
- Max: 493.007 ms
- `selectSeries` calls in `inspect`: 1
- N+1 detected: false

These are local end-to-end HTTP timings including database read, all existing Gate
checks, canonicalization, SHA-256, persistence of the gate record, and response
serialization. They are not presented as a standalone hash microbenchmark.

## Approved Transition

GPT approved Commit D, Final Core Freeze v2, and entry into Phase 1B after the
freeze-record commit. No tag was created, and Phase 1B must treat the Final Core
Freeze v2 SHA as the immutable source baseline.
