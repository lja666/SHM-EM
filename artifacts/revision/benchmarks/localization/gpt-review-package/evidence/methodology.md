# Phase 2A.1 Gate Performance Localization Methodology

## Scope

This phase localizes the 180-second S2 Gate timeout. It does not optimize or modify production code, schema, indexes, views, model artifacts, PIT_PRE, or frontend code. Final Core Freeze v2 remains unchanged.

## Environment and workload

- Concurrency: 1.
- Backend: the same packaged SHM-EM JAR and JVM options used by Phase 2A.
- Database: MySQL 8.0.41 on the recorded reference host.
- Prediction horizon: 40 steps.
- Sweep: 124, 248, 496, 744, 992, and 1,240 target channels (4,960 to 49,600 persisted rows).
- S1/S2 fixtures: the valid persisted fixtures retained from Phase 2A.
- Intermediate fixtures: generated with the same schema, contract, persistence, and cross-language integrity procedure.

## Fresh-process isolation

Each Gate-first scale and D01-D04 operation-order case starts a fresh backend JVM. Readiness uses only `/api/em/projects?limit=1`. Residual connections are removed only from the disposable benchmark database after its JVM stops, and the cleanup is recorded.

## Runtime diagnostics

For Gate calls longer than 5 seconds, the harness samples RSS, JVM GC counters, and `SHOW FULL PROCESSLIST` approximately once per second. `jstack` and `jstat` samples are captured at 5, 15, 30, 60, and 120 seconds. Diagnostics add observational overhead and are used for localization rather than manuscript latency statistics.

## SQL controls

The Gate-equivalent batch-only view query, feature-contract query, base-table integrity-field query, and project-scoped view control are measured independently. `EXPLAIN ANALYZE` is retained for S1/S2 and Reference controls. A 180-second session statement limit is used only for direct diagnostic queries; production Gate calls retain the original 180-second client boundary.

## Repetition policy

Each sweep scale has one fresh-process first call. Three measured calls are added only when the first call is below 60 seconds. A first call at or above 60 seconds is not repeated; a 180-second timeout stops the sweep. No OS or InnoDB cache flush is performed, matching Phase 2A's warm-cache policy.

## Evidence checkpoint

The untouched Phase 2A boundary evidence was committed first as `60b2df8`. Phase 2A.1 diagnostics remain separate for GPT review.
