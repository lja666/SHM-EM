# Phase 1A.1 Failure-Path Matrix

- Core freeze: `df39ffb2b57d16cfdca419adf2492959fcc0931c`
- Freeze record: `6ea8ec64ed456fc7ea503e365107c1b3db82737a`
- Database policy: independent `shm_em_reproduce_phase1a1_*` database per case
- Production changes: restricted to the authorized persisted-integrity repair

| Case | Fault | Expected stage | Actual stage | Eligible | Formal event delta | Result | Finding |
|---|---|---|---|---:|---:|---|---|
| P00 | Valid reference control | POSITIVE_CONTROL | NONE | True | 1 | PASS | - |
| F01 | Incomplete forecast steps | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F02 | Stale prediction | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F03 | Incorrect model artifact hash | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F04 | Missing required target channel | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F05 | Invalid engineering unit | RULE_VALIDATION | RULE_VALIDATION | True | 0 | PASS | - |
| F06 | Input-schema mismatch | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F07 | Temporal misalignment | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F08 | Failed model run | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F09 | Corrupted persisted forecast values with stale hashes | PERSISTED_RESULT_INTEGRITY | PERSISTED_RESULT_INTEGRITY | False | 0 | PASS | - |
| F10 | Invalid prediction quality flag | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F11 | Batch status failure | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F12 | Evaluate then mutate then Execute recheck | EXECUTE_RECHECK | EXECUTE_RECHECK | False | 0 | PASS | - |
| I01 | Partial dropped observation | INPUT_ALIGNMENT_POLICY | INPUT_ALIGNMENT_POLICY | None | 0 | PASS | - |
| I02 | Entire required feature unavailable | INPUT_ASSEMBLY | INPUT_ASSEMBLY | None | 0 | PASS | - |

## Interpretation

Phase 1A.1 reruns the same isolated failure-path matrix against the authorized persisted-integrity repair. The original Phase 1A discovery evidence remains preserved separately.
