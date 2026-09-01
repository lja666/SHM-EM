# Impact Restructuring Plan

This plan replaces broad architectural promises with claims already demonstrated by repository evidence. It prepares Section 4 but does not edit the submitted manuscript.

## 4.1 Reproducible software validation

### Manuscript-ready draft

The revised validation separates overlapping evidence families instead of reporting an inflated global test total. The frozen release passed 55 backend unit/service/API tests, 13 PIT_PRE contract/alignment/integrity tests, a 15-case negative and persisted-integrity matrix, seven second-configuration end-to-end checks, two frontend build checks, and one public-reference reproduction. The reference six-model batch produced 124 targets over 40 future steps. Median runtime was 16,778.359 ms for the full prediction batch, 343.129 ms for Gate inspection, 472.342 ms for Project Future State, 269.465 ms for Evaluate, 317.238 ms for Execute, and 2.578 ms for event-trace retrieval under the documented single-process workloads. These measurements characterize the reference implementation; they do not establish production throughput or linear scalability.

Evidence: `artifacts/revision/manuscript/software-test-summary.md` and `artifacts/revision/manuscript/final-performance-table.md`.

## 4.2 Cross-configuration reuse

### Manuscript-ready draft

Functional reuse was evaluated with one independently registered synthetic bridge-monitoring configuration. The performance-corrected frozen core completed the seven functional checks B9-B15: two registered model fixtures produced 1,120 forecast rows; persisted-result integrity and execution eligibility passed; Project Future State was assessed; Evaluate produced no formal side effects; Execute created a formal event, a response workflow, four response steps, and a prediction provenance link; a missing required mapping was rejected before inference; and the existing frontend routes and joint-series API remained usable. The configuration registered one project, three stations, 12 instruments, 26 metric bindings, four observation mappings, 164 feature mappings, two models, and one rule. This experiment demonstrates software/configuration reuse for one synthetic second configuration, not forecasting accuracy, cross-domain predictive generalization, or universal no-code onboarding.

Evidence: `artifacts/revision/benchmarks/route-p/phase1b-regression.json` and its `phase1b-regression/` evidence directory. Do not cite the earlier 13/15 report without explaining that B4/B7 are legacy freeze-baseline checks superseded by the authorized one-line Route P correction and Final Core Freeze v3.

## 4.3 Operational traceability and controlled execution

### Manuscript-ready draft

The controlled transition was exercised through P00, F01-F12, and I01-I02 in isolated databases. All 15 negative/integrity cases passed after explicit persisted-result integrity revalidation: invalid prediction states were blocked before formal event, response-workflow, response-step, report, evidence, or prediction-link side effects. Evaluate remained side-effect free, while Execute reloaded the canonical series, recomputed and persisted the Gate, validated engineering units and rule semantics, and only then created formal records. One captured event trace resolves the event to rule version v2, prediction batch 40, run 236, the settlement model artifact hash, its input window and schema hash, a 40-step forecast snapshot, Gate 1, the first exceedance, and the response workflow. The reproduction database was restored after export.

Evidence: `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md`, `docs/revision/PROVENANCE_TRACE_EXAMPLE.md`, and `artifacts/revision/manuscript/provenance-trace-final.json`.

## 4.4 Current scope and deployment limitations

### Manuscript-ready draft

The current release integrates six compatible point-forecast model bundles and does not quantify predictive uncertainty; Gate eligibility concerns data, artifact, timeline, integrity, quality, and freshness controls rather than probabilistic forecast confidence. The 50,000-row Gate inspection cap is an application-level bounded-query safeguard, not a measured MySQL capacity limit. MySQL is the only implemented persistence backend, and neither a time-series-native database adapter nor OGC SensorThings conformance has been validated. Docker Compose reproduced the Linux logical workflow, including six models, 124 targets, 40 steps, 4,960 rows, Gate, Project Future State, Evaluate, Execute, and provenance. Input and model-contract hashes matched the Windows reference, but normalized prediction-output hashes were not identical; the maximum persisted absolute difference was 0.00285349 and no tolerance was applied. Native Ubuntu-host validation was not separately captured. The release is a research reference implementation without application-level authentication; production use requires the controls documented in `SECURITY.md`.

Evidence: `artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md`, `artifacts/revision/portability/cross-platform-comparison.md`, `docs/revision/STORAGE_ADAPTER_BOUNDARY.md`, and `SECURITY.md`.

## Claim discipline

- Do not compare SHM-EM and Predictive-SHM runtime or forecasting accuracy without a controlled common benchmark.
- Do not generalize the synthetic bridge fixture to arbitrary projects or predictive validity.
- Do not call the 4,960-to-49,600 Gate endpoints linear scalability. They show continued function under a tenfold synthetic persisted-row/target increase after project-and-batch query scoping.
- Do not describe SHA-256 metadata as tamper-proof against a privileged attacker.
- Do not describe Docker Linux output as exact reproduction.
