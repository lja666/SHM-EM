# Phase 2A Benchmark Methodology

## Scope

The real public reference workflow measures six packaged models and the complete frozen forecast-to-event path. The synthetic scaling fixture measures backend, MySQL storage, persisted integrity, Gate, and Future State behavior only. It is not a model-inference or predictive-accuracy experiment.

## Repetition Policy

- Concurrency: 1.
- First call retained separately.
- Warm-up: 5 calls/runs.
- Measured: 30 calls/runs.
- Execute: 10 measured calls, each restored to the same formal-state baseline.
- No outlier deletion.
- Application warm-cache conditions; OS page cache was not flushed.

## Scaling Axes

Forty forecast steps are fixed. Target channels and persisted rows increase. Ten stations and ten instruments are fixed, so this is target/row scaling rather than topology scaling.

## STOP Policy

The experiment stops on the first valid persisted workload that fails or cannot complete a frozen service path. No frozen production optimization is permitted during Phase 2A.
