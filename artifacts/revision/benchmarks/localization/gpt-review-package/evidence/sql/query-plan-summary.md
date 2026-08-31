# Query Plan Summary

## Gate-equivalent batch-only query

- S1: 2623.381 ms for 4,960 rows.
- S2: 218756.238 ms for 49,600 rows.
- S2 plan: 49,600 result rows each probe 1,240 project feature mappings through `uk_em_prediction_feature_schema`; the feature-mapping branch accounts for approximately 215 seconds of the analyzed execution.

## Project-scoped control

- S2: 3030.351 ms for 49,600 rows.
- The optimizer changes the feature-mapping branch to a one-time hash input and hash join.
- Observed EXPLAIN speedup: 72.2x.
- The ordinary series API includes both project and batch predicates; the frozen Gate constructs a batch-only query.

## Base-table and contract controls

- S2 base persisted-row query median: 4188.114 ms.
- S2 feature-contract query median: 70.653 ms.
- S2 independent persisted integrity recomputation: 7419.927 ms.

These controls show that persistence capacity, contract loading, and independent integrity hashing do not explain the 180-second Gate timeout.

## Reference versus S1

The Reference plan hash-joins the feature-mapping table once, while S1 repeatedly probes 124 feature rows per prediction row. The two 4,960-row workloads therefore have different optimizer plans despite equal row counts. This explains why synthetic S1 remains slower and confirms that row count alone is not a sufficient workload descriptor.

## Variability note

Some project-scoped direct calls changed plans across repetitions at intermediate cardinalities. The conclusion relies on the retained plans, repeated API observations, and process/thread evidence rather than a single fast direct query.
