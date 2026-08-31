# Phase 2A.2R Route P Completion Report

Status: `PASS_STOP_FOR_GPT_REVIEW`

## Controlled A/B

- Reference median A: `347.939200 ms`.
- Reference median B: `340.485850 ms`.
- Pooled B/A ratio: `0.978579` (`PASS`).
- Phase1B B median/p95: `681.946750` / `755.718900 ms`.

## Runtime and Safety

- S2 first/median/p95: `4476.774400` / `3603.382300` / `3843.173900 ms`.
- Failure matrix: `15/15 PASS`.
- Phase1B functional reuse B9-B15: `PASS`.
- Hash regression: `PASS`.
- Full-stack regression: `PASS`.
- Acceptance gates: `14/14 PASS`.

## Boundary

The production correction remains uncommitted. No index, Mapper/View, schema, integrity-hash, Future State, PIT_PRE, frontend, or 50,000-row-cap change was made. Final Core Freeze v3 is not recorded pending GPT review.
