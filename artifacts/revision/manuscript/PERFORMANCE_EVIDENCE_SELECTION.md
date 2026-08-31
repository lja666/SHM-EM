# Performance Evidence Selection

## Manuscript-ready

- Use `final-performance-table.csv` or `.md` as the only numerical source for the revised manuscript.
- The final Gate value is the corrected production benchmark: median 343.129 ms and p95 407.100 ms for 4,960 rows.
- S1 (4,960 rows) and S2 (49,600 rows) are a tenfold synthetic persisted-record and target-channel stress comparison. Both remained functionally valid after the targeted query correction.
- MySQL persistence and integrity values are single-run characterization, not repeated latency distributions.
- The current Gate inspection limit is 50,000 prediction-display rows. This is an implementation boundary, not a MySQL capacity limit.

## Reviewer-response only

- `artifacts/revision/benchmarks/route-p-repeat/` establishes controlled A/B semantic equivalence and absence of material reference regression.
- `artifacts/revision/benchmarks/route-p/result-set-equivalence.json` and `cross-project-safety.json` establish result-set preservation and corruption detection.
- The pre-correction timeout may be mentioned only to explain why the narrowly scoped Route P correction was made.

## Diagnostic only

- The six-level nonmonotonic sweep, JVM thread dumps, MySQL process lists, EXPLAIN captures, and localization traces remain repository audit evidence.
- They must not be presented as linear scaling or mixed into the final manuscript performance table.
- No further Gate, SQL, index, pagination, or 50,000-row-boundary engineering is authorized in Phase 2B.
