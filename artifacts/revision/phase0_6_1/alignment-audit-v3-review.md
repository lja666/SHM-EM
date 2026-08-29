# SHM-EM Phase 0.6.1 Input Alignment Audit v3

## Scope and attribution

This is an offline, read-only audit of the committed public sample. It does not connect to MySQL, modify data, change production inputs, or run model inference. Attribution reproduces the existing three-minute grid, backward `merge_asof`, bidirectional linear interpolation, `ffill`, `bfill`, and remaining-NaN check.

`fill_ratio` includes interior interpolation, leading/trailing boundary extension, ffill, and bfill, but excludes backward as-of. `non_exact_alignment_ratio` additionally includes backward as-of and describes synchronization to the canonical grid; it is not interpreted as missing-data imputation.

## Public-sample results

| Model | Features | As-of | Interior | Boundary | FFill | BFill | Max gap (s) | P95 |offset| (s) | Future cells | Max lead (s) | Max fill ratio | Missing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pressure | 114 | 114 | 12 | 0 | 0 | 0 | 193.0 | 172.0 | 24 | 166.0 | 0.153846 | 0 |
| Strain | 114 | 114 | 12 | 0 | 0 | 0 | 193.0 | 172.0 | 24 | 166.0 | 0.153846 | 0 |
| XD | 114 | 114 | 12 | 0 | 0 | 0 | 192.0 | 172.0 | 24 | 166.0 | 0.166667 | 0 |
| YD | 114 | 114 | 12 | 113 | 0 | 0 | 193.0 | 172.0 | 137 | 177.0 | 0.1875 | 0 |
| settlement | 164 | 164 | 12 | 0 | 0 | 0 | 192.0 | 172.0 | 24 | 166.0 | 0.166667 | 0 |
| water | 114 | 114 | 12 | 0 | 0 | 0 | 193.0 | 172.0 | 24 | 166.0 | 0.153846 | 0 |

Across `9606` model-input cells, `36` were exact, `9313` used backward as-of, `144` used interior interpolation, and `113` used boundary extension. Maximum raw gap was `193.0` seconds, p95 absolute source offset was `172.0` seconds, `257` cells had at least one later-source contributor, maximum future-source lead was `177.0` seconds, maximum fill ratio was `0.1875`, and unresolved missing cells totalled `0`.

## Required policy questions

1. **What is the current `merge_asof` tolerance?** One model time step: 180 seconds for the active public-sample contract.
2. **Where is tolerance defined?** `WideTableBuilder` creates `step = timedelta(minutes=time_step_minutes)` and passes that same value to `_align_series` as tolerance.
3. **Is tolerance tied to model sampling interval?** Yes. Active model contracts define `time_step_minutes=3`; contract loading requires a single shared value across active models.
4. **Which features are interpolated?** Every enabled model-input column in the common wide table is included in the DataFrame-wide interpolation operation when it contains a missing grid cell.
5. **Does `limit_direction="both"` allow boundary filling?** Yes. Leading and trailing gaps can be filled from the nearest available boundary value during the interpolation stage.
6. **Can `ffill`/`bfill` spread one point across multiple historical steps?** The sequence permits it in principle. In the audited implementation Pandas' bidirectional interpolation normally fills boundaries first, so the later fill calls only act if values remain. A sparse column can still derive multiple grid cells from one observed value during interpolation.
7. **Are fill counts recorded in production?** Phase 0.6 adds compact descriptive counts to each model run's `input_snapshot_json`; the numerical input remains unchanged.
8. **Is maximum gap recorded in production?** Phase 0.6 records the model-window maximum raw gap as descriptive provenance.
9. **Is there a stale cutoff?** Alignment has a one-step as-of tolerance, but interpolation and boundary filling have no separate temporal-offset cutoff. The execution gate checks completed-batch freshness, not per-feature source offset.
10. **Can the gate use the new diagnostics?** The values are provenance only. Phase 0.6.1 adds no fill, gap, or offset threshold and makes no eligibility decision from them.
11. **Does `input_snapshot_json` record alignment diagnostics?** Yes, as a compact policy/version and per-model quality summary; full feature rows remain revision evidence only.
12. **Can current behavior answer Reviewers 2 and 3?** Yes at the descriptive level: the method, stage counts, fill ratio, raw gap, signed temporal offsets, past lag, and future lead are explicit and reproducible.
13. **What remains deferred?** Scientifically justified acceptance thresholds and gate enforcement. They are not inferred from this single public sample.

## Phase 0.6.1 conclusion

Phase 0.6.1 makes source-time direction explicit without changing values, filling behavior, or eligibility. Later-source contributors remain inside the historical window available at the prediction origin; they are not observations beyond the forecast origin. Numerical equivalence is reported separately in the regression artifacts.
