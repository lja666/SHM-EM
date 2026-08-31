# Phase 2A.1 Root-Cause Analysis

## Primary bottleneck

**CONFIRMED: Gate's batch-only `em_prediction_display` query selects an unfavorable feature-mapping join plan at synthetic high cardinality.**

D01-D04 all timed out at approximately 180 seconds. Every retained request-thread sample was in JDBC/MySQL read, and every timeout processlist sample showed the same active view query. S2 `EXPLAIN ANALYZE` required 218.756 seconds; adding the already-known project predicate reduced the analyzed query to 3.030 seconds (72.2x) by changing the feature-mapping branch to a hash join.

## Secondary bottlenecks

**SUPPORTED: response allocation raises RSS after 36 full-series calls, but it does not cause the Gate timeout.** D03/D04 reached high RSS, while D01 timed out in a fresh JVM with lower and decreasing RSS. All four cases stopped in the same SQL read path.

**SUPPORTED: result sorting and base-row transfer are measurable secondary costs.** The S2 base-row control is about 4.188 seconds and the scoped view/API path remains several seconds, but neither approaches 180 seconds.

## Not the bottleneck

- **NOT SUPPORTED: benchmark order / heap pressure.** D01 Gate-first and D02-D04 all have the same timeout mechanism.
- **NOT SUPPORTED: GC.** Sampled GC time did not increase during the long Gate calls.
- **NOT SUPPORTED: Java feature/timeline validation.** The request did not return from `PredictionMapper.selectSeries` in any timeout sample.
- **NOT SUPPORTED: persisted integrity hashing.** Independent S2 recomputation completed in 7.420 seconds.
- **NOT SUPPORTED: canonical contract hashing.** Thread samples never reached this stage; the contract query itself was about 70.653 ms.
- **NOT SUPPORTED: response serialization.** Gate response serialization was not reached.
- **NOT SUPPORTED: MySQL storage capacity.** The base table, project-scoped view, and integrity controls all completed.

## S1/reference discrepancy

**CONFIRMED: the discrepancy is fixture/query-plan shape, not row count.** Fresh Reference versus S1 Gate medians were 331.972 and 2332.957 ms (7.03x); full-series medians were 357.065 and 2460.087 ms (6.89x). Reference uses a feature hash join, whereas S1 repeatedly scans its project feature subset.

## S2 180-second timeout mechanism

**CONFIRMED:** the Gate request remains blocked while MySQL executes the batch-only view query. It does not spend the 180 seconds in validation, integrity hashing, canonical hashing, GC, or serialization.

## 50,000-row structural cap

**CONFIRMED structural boundary, NOT SUPPORTED as the cause of S2 latency.** S2 has 49,600 rows and is below the hard query limit of 50000. S3+ cannot be validly assessed by the frozen Gate because results would be truncated even if query performance were acceptable.

## Route P: minimal core correction

- Candidate file: `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java`.
- Candidate change: set `resultQuery.projectId` from the already-loaded batch before `selectSeries`.
- Expected benefit: preserve the same project/batch result set while enabling the measured project-scoped plan; S2 SQL control improved 72.2x.
- Risk: low but non-zero because optimizer behavior and cross-project isolation must be regression-tested.
- Required regression: F01-F12, I01-I02, second heterogeneous configuration, result-count/hash equality, and fresh S1/S2 timing.
- No Mapper, view, schema, index, hash, pagination, or architecture change is indicated by current evidence.

## Route L: retain bounded core

- Manuscript limitation: current Gate is reliable for the 4,960-row reference workload but shows nonlinear latency on synthetic high-cardinality contracts.
- Maximum valid sub-180-second workload demonstrated: 39,680 rows / 992 targets / 40 steps at 136.208 seconds.
- S2 boundary: 49,600 rows did not return within 180 seconds.
- Structural limit: 50,000 prediction-display rows.

## Recommendation

The evidence favors Route P as a narrow, explainable correction, but **do not implement it until GPT approval**. Phase 2A.1 stops here.
