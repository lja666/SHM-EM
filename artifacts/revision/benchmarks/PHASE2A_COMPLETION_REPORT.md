# Phase 2A Completion Report

## 1. Baseline

- Final Core Freeze v2: `b41c1894f75561c8ef682062a5e6dab35c3916a7`
- Phase 1B commit: `2107674`
- Reference DB: `shm_em_reproduce_benchmark_reference`
- Scaling DBs: `shm_em_reproduce_benchmark_scaling_s1`, `shm_em_reproduce_benchmark_scaling_s2`
- Frozen production core modified: **NO**

## 2. Environment

- CPU: 13th Gen Intel(R) Core(TM) i7-13700H (14 physical / 20 logical cores)
- RAM bytes: 68376010752
- Storage: `[{"FriendlyName": "KBG5AZNV1T02 LA KIOXIA", "MediaType": "SSD", "BusType": "NVMe", "Size": 1024209543168}, {"FriendlyName": "E680 40E SSD M.2 2280s PCIe4.0 1TB", "MediaType": "SSD", "BusType": "NVMe", "Size": 1024209543168}, {"FriendlyName": "Seagate Basic", "MediaType": "Unspecified", "BusType": "USB", "Size": 4000787029504}]`
- MySQL: 8.0.41; buffer pool 134217728 bytes; max connections 200; engine InnoDB
- Python: 3.10.20
- Java: `openjdk version "1.8.0_482"`

## 3. Reference Workflow

Public reference workload: 6 packaged models, 124 target channels, 40 future steps, 4,960 persisted forecast rows, concurrency 1.

| Component | median | p95 | measured repetitions |
| --- | ---: | ---: | ---: |
| PIT_PRE full batch | 16778.359 ms | 18729.326 ms | 30 |
| All-model inference | 5257.484 ms | 6604.427 ms | 30 |
| Gate inspect | 268.821 ms | 331.778 ms | 30 |
| Future State | 472.342 ms | 574.761 ms | 30 |
| Evaluate | 269.465 ms | 313.340 ms | 30 |
| Execute | 317.238 ms | 336.361 ms | 10 |
| Provenance trace | 2.578 ms | 20.692 ms | 30 |
| Full-batch series | 278.823 ms | 336.932 ms | 30 |

## 4. PIT_PRE

- Input assembly: 5632.700 ms / 6260.991 ms / 30
- All-model inference: 5257.484 ms / 6604.427 ms / 30
- Engineering conversion: 2951.386 ms / 3544.938 ms / 30
- Prediction write total: 4833.835 ms / 5646.176 ms / 30
- Persistence-exclusive estimate: 1352.796 ms / 1535.914 ms / 30
- Persisted-integrity hash generation: 531.599 ms / 693.269 ms / 30
- Full batch: 16778.359 ms / 18729.326 ms / 30
- Model loading/cache preparation (one-time): 1086.124 ms
- No repetitions or outliers were removed.

## 5. Backend

- Gate inspect: 268.821 ms / 331.778 ms / 30
- Gate evaluate: 259.932 ms / 300.642 ms / 30
- Future State: 472.342 ms / 574.761 ms / 30
- Single-target series: 23.278 ms / 31.396 ms / 30
- Full-batch series: 278.823 ms / 336.932 ms / 30
- Evaluate: 269.465 ms / 313.340 ms / 30
- Execute: 317.238 ms / 336.361 ms / 10; 10 independent repetitions restored to the same formal-state baseline.
- Provenance trace: 2.578 ms / 20.692 ms / 30

## 6. Scaling

The scaling experiment is a **synthetic backend/storage scalability fixture**, not model-inference or predictive-accuracy evidence. It fixes 10 stations, 10 instruments, one model contract, and 40 future steps while increasing target channels and persisted rows.

| scale | rows | targets | persist rows/s | integrity recomputation | full-series median/p95 | Gate | DB data+index |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| S1 | 4960 | 124 | 307.471 | 313.092 ms | 2368.036/2600.864 ms | PASS, 2308.912/2534.455 ms | 4603904 bytes |
| S2 | 49600 | 1240 | 266.049 | 4038.473 ms | 3684.524/3868.852 ms | STOP: first call timed out at 180.008 s | 39698432 bytes |

## 7. Maximum Tested Workload

- Maximum persisted and independently integrity-verified: **49,600 rows / 1,240 targets / 40 steps**.
- Maximum fully functional Gate + Future State workload: **4,960 rows / 124 targets / 40 steps**.
- S2 completed all 1 first + 5 warm-up + 30 measured single/full-series calls. The first Gate inspect did not return within the fixed 180-second client timeout.
- Future State at S2 and S3-S5 were not attempted after the STOP trigger.

## 8. MySQL Boundary

On this single recorded machine/configuration, ordinary S2 series retrieval remained functional, while the frozen Gate path exceeded 180 seconds. This is an observed application-service boundary, **not a universal MySQL capacity limit**. The experiment does not support claims about other hardware, concurrency levels, database tuning, or topology scaling.

## 9. Integrity

- Reference cross-language persisted hash recomputation: median 437.475 ms, p95 644.797 ms, 30/30 matches.
- S1 independent persisted-integrity verification: PASS.
- S2 independent persisted-integrity verification: PASS for all 49,600 rows, before backend Gate invocation.
- S2 Gate result integrity status is unavailable because the first Gate call timed out; it must not be reported as an integrity mismatch.

## 10. Regression Tests

- Backend Maven test/package: PASS.
- PIT_PRE unittest discovery: PASS.
- Frontend production build: PASS.

## 11. Frozen Core Diff

- Modified frozen files: `[]`
- Result: **NONE**

## 12. Acceptance Matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| P2A-01 | PASS | Frozen production-core diff is empty. |
| P2A-02 | PASS | Environment and MySQL runtime configuration captured. |
| P2A-03 | PASS | Reference PIT_PRE and all required backend/API timings captured. |
| P2A-04 | PASS | Reference uses 1 first + 5 warm-up + 30 measured; Execute uses 10 isolated repetitions. |
| P2A-05 | STOP | S1 passed; S2 Gate first call timed out at 180 s, so S3-S5 were not run. |
| P2A-06 | PARTIAL | S1 Gate integrity passed; S2 independent persisted integrity passed before Gate timeout. |
| P2A-07 | PASS | Per-scale InnoDB data/index storage captured. |
| P2A-08 | PASS | Scaling fixture is explicitly backend/storage only, with no inference or accuracy claim. |
| P2A-09 | PASS | Backend, PIT_PRE, and frontend regression results recorded. |
| P2A-10 | PASS | Evidence and review-package SHA-256 manifests generated and revalidated. |

## 13. Findings Requiring Core Change

1. The frozen Gate inspect path did not complete within 180 seconds for the valid S2 workload (49,600 rows), although full-batch series retrieval and independent persisted-integrity recomputation completed. Localization and optimization require a separately authorized production-core phase.
2. No Phase 2A production optimization was attempted. The known 50,000-row series cap was not reached because STOP occurred first at S2.

## 14. Evidence

- `artifacts/revision/benchmarks/reference/`
- `artifacts/revision/benchmarks/scaling/s1/`
- `artifacts/revision/benchmarks/scaling/s2/`
- `artifacts/revision/benchmarks/integrity/`
- `artifacts/revision/benchmarks/environment.json`
- `artifacts/revision/benchmarks/regression-tests.json`
- `artifacts/revision/benchmarks/phase2a-manifest.json`
- `artifacts/revision/benchmarks/gpt-review-package/`

## 15. STOP

Phase 2A is stopped at the first valid-workload runtime boundary. Await GPT review before any production-core change or additional scalability run.
