# Phase 2A.2 Route P Completion Report

## Decision

`STOPPED_FOR_GPT_REVIEW` at RP-08. No follow-on optimization or performance workload was run.

## Passed Before Stop

- Phase 2A.1 evidence checkpoint: `84c13fa`.
- Authorized production correction is exactly one `projectId` scope assignment.
- Reference, S1, S2, and Phase 1B legal result sets are fully equivalent.
- S2 batch-only query: 226,077.22 ms; project+batch query: 6,394.26 ms.
- Cross-project moved-row case: Gate ineligible, integrity invalid, Execute rejected, formal event delta 0.

## Stop Trigger

Reference Gate measured median was `381.393750 ms`; the authorized stop line was `336.025813 ms` (`1.25 x` the Phase 2A median `268.820650 ms`). All calls were functionally valid, but the performance regression line is binding.

## Deliberately Not Run

- S1/S2 fresh Gate performance and sub-50k sweep.
- Corrected S1/S2 EXPLAIN ANALYZE.
- P00/F01-F12/I01-I02 and Phase 1B reruns.
- Final numerical/hash regression.

The production fix remains uncommitted. GPT must decide whether the Reference anomaly warrants a controlled repeat or another action.
