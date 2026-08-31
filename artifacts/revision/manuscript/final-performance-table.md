# Final Performance Table

All timings are milliseconds. Median and p95 are reported only for repeated measurements; single-run MySQL characterization is kept in a separate column. These results characterize the submitted reference implementation and do not establish linear scalability.

| Section | Operation | Workload | n | Median | p95 | Single elapsed |
|---|---|---|---:|---:|---:|---:|
| Reference workflow | Full six-model prediction batch | 6 models, 124 targets, 40 steps | 30 | 16778.359 | 18729.326 | - |
| Reference workflow | Input assembly | 6 models, 124 targets, 40 steps | 30 | 5632.700 | 6260.991 | - |
| Reference workflow | All-model inference | 6 models, 124 targets, 40 steps | 30 | 5257.484 | 6604.427 | - |
| Reference workflow | Engineering conversion | 6 models, 124 targets, 40 steps | 30 | 2951.386 | 3544.938 | - |
| Reference workflow | Prediction persistence (exclusive estimate) | 6 models, 124 targets, 40 steps | 30 | 1352.796 | 1535.914 | - |
| Reference workflow | Persisted-integrity hashing | 6 models, 124 targets, 40 steps | 30 | 531.599 | 693.269 | - |
| Reference workflow | Execution Gate inspection | 4,960 persisted prediction rows | 30 | 343.129 | 407.100 | - |
| Reference workflow | Project Future State | public reference case | 30 | 472.342 | 574.761 | - |
| Reference workflow | Single-target joint series | public reference case | 30 | 23.278 | 31.396 | - |
| Reference workflow | Full-batch joint series | public reference case | 30 | 278.823 | 336.932 | - |
| Reference workflow | Rule Evaluate | public reference case | 30 | 269.465 | 313.340 | - |
| Reference workflow | Rule Execute | public reference case | 10 | 317.238 | 336.361 | - |
| Reference workflow | Event provenance trace | public reference case | 30 | 2.578 | 20.692 | - |
| Tenfold Gate stress | Gate stress S1 | 4,960 rows; 124 targets; 40 steps | 10 | 2406.939 | 2666.804 | - |
| Tenfold Gate stress | Gate stress S2 | 49,600 rows; 1,240 targets; 40 steps | 10 | 3603.382 | 3843.174 | - |
| MySQL characterization | Prediction persistence S1 | 4,960 rows | 1 | - | - | 16131.595 |
| MySQL characterization | Independent integrity verification S1 | 4,960 rows | 1 | - | - | 316.746 |
| MySQL characterization | Prediction persistence S2 | 49,600 rows | 1 | - | - | 186431.707 |
| MySQL characterization | Independent integrity verification S2 | 49,600 rows | 1 | - | - | 4100.818 |
