# SHM-EM Software Testing Summary

Test families are reported as independent evidence scopes. The overall total is intentionally not computed because backend cases, failure injections, end-to-end checks, and reproduction benchmarks overlap in behavior and would otherwise be double-counted.

| Test family | Cases/checks | Passed | Status | Evidence |
|---|---:|---:|---|---|
| Backend unit/service/API tests | 55 | 55 | PASS | `src/backend/target/surefire-reports/TEST-*.xml` |
| PIT_PRE contract/alignment/integrity tests | 13 | 13 | PASS | `artifacts/revision/manuscript/phase2b-final-regression.json` |
| Negative and persisted-integrity matrix | 15 | 15 | PASS | `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.json` |
| Second-configuration end-to-end acceptance | 7 | 7 | PASS | `artifacts/revision/benchmarks/route-p/phase1b-regression.json` |
| Frontend typecheck and production build | 2 | 2 | PASS | `artifacts/revision/manuscript/phase2b-final-regression.json` |
| Public reference end-to-end reproduction | 1 | 1 | PASS | `artifacts/revision/benchmarks/reference/reference-summary.json` |

## Counting policy

- Maven Surefire is the primary count for backend test methods at this checkout.
- PIT_PRE test methods are counted from source and their status is taken from the final recorded unittest run.
- P00/F01-F12/I01-I02 are reported as a 15-case validation matrix comprising one positive control, 12 failure-path cases, and two input-availability controls, even when a case is also represented by a unit test.
- Phase 1B B9-B15 are seven acceptance checks for one end-to-end second-configuration workflow, not seven independent unit tests.
- Frontend type checking and production build are two checks from one build pipeline.
- No statement about code-coverage percentage is made because no stable coverage instrument is part of the submitted release.
