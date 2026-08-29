# Phase 1A Failure-Path Matrix

- Core freeze: `df39ffb2b57d16cfdca419adf2492959fcc0931c`
- Freeze record: `6ea8ec64ed456fc7ea503e365107c1b3db82737a`
- Database policy: independent `shm_em_reproduce_phase1a_*` database per case
- Production core changes: prohibited

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
| F09 | Corrupted persisted forecast values with stale hashes | PERSISTED_RESULT_INTEGRITY | NONE | True | 1 | FAIL | PERSISTED_RESULT_INTEGRITY_GAP |
| F10 | Invalid prediction quality flag | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F11 | Batch status failure | EXECUTION_GATE | EXECUTION_GATE | False | 0 | PASS | - |
| F12 | Evaluate then mutate then Execute recheck | EXECUTE_RECHECK | EXECUTE_RECHECK | False | 0 | PASS | - |
| I01 | Partial dropped observation | INPUT_ALIGNMENT_POLICY | INPUT_ALIGNMENT_POLICY | None | 0 | PASS | - |
| I02 | Entire required feature unavailable | INPUT_ASSEMBLY | INPUT_ASSEMBLY | None | 0 | PASS | - |

## Interpretation

A failed discovery case is retained as an empirical finding. This Phase 1A harness does not repair production code.
