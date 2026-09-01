# Related Software Comparison

## Method and interpretation

The table compares documented software responsibilities rather than ranking products. Third-party cells use only `Yes`, `Partial`, `Not reported`, or `Not applicable`. `Not reported` means that the cited primary source does not explicitly document the capability; it must not be read as evidence of absence. No cross-system runtime or forecasting-accuracy superiority is claimed.

| Capability | OGC SensorThings | generic CEP | Predictive-SHM | SHM-EM |
|---|---|---|---|---|
| Heterogeneous observation access | Yes | Partial | Yes | Yes |
| Standardized observation semantics | Yes | Not applicable | Yes | Partial |
| Model-specific ordered input contract | Not applicable | Not applicable | Partial | Yes |
| Pluggable forecasting/model adapter | Not applicable | Not applicable | Yes | Yes |
| Artifact and input-schema hash validation | Not applicable | Not applicable | Not reported | Yes |
| Shared prediction origin and future timeline | Not applicable | Not applicable | Not reported | Yes |
| Project-level future-state aggregation | Not applicable | Not applicable | Not reported | Yes |
| Rule/event evaluation | Not applicable | Yes | Partial | Yes |
| Side-effect-free candidate evaluation | Not applicable | Not reported | Not reported | Yes |
| Rechecked formal execution | Not applicable | Not reported | Not reported | Yes |
| Persisted-result integrity revalidation | Not applicable | Not reported | Not reported | Yes |
| Event-to-model/input provenance | Not applicable | Not reported | Not reported | Yes |

## Capability notes

- **Heterogeneous observation access:** SensorThings standardizes heterogeneous observation access; CEP consumes flows from distributed sources but does not define an SHM observation schema; Predictive-SHM states multi-source ingestion; SHM-EM uses registered observation adapters.
- **Standardized observation semantics:** SensorThings defines sensing entities; Predictive-SHM reports ULDM; SHM-EM has a versioned internal registry rather than an external observation standard.
- **Model-specific ordered input contract:** Predictive-SHM adapters map ULDM views to model tensors; SHM-EM additionally persists versioned feature order, target bindings, units, transforms, and contract fingerprints.
- **Pluggable forecasting/model adapter:** Predictive-SHM explicitly reports pluggable prediction and model adapters; SHM-EM registers model bundles and PIT_PRE adapters.
- **Artifact and input-schema hash validation:** The Predictive-SHM publisher abstract does not report this control; SHM-EM verifies artifact, preprocessor, script, runtime-manifest, contract, and persisted-result hashes.
- **Shared prediction origin and future timeline:** Predictive-SHM reports standardized timestamped forecasts, but the primary source does not explicitly describe a common multi-model prediction origin or project-level synchronized future timeline. SHM-EM validates one batch origin and a common 40-step timeline.
- **Project-level future-state aggregation:** This is an SHM-EM domain mechanism that aggregates target, station, and project states under a versioned policy.
- **Rule/event evaluation:** CEP is designed for stream conditions and event derivation; Predictive-SHM reports residual- and threshold-based alerting; SHM-EM evaluates observation or prediction series against versioned rules.
- **Side-effect-free candidate evaluation:** SHM-EM Evaluate returns simulated candidates and creates no formal event, workflow, response step, or prediction link.
- **Rechecked formal execution:** SHM-EM Execute recomputes and persists the execution Gate before formal rule evaluation and event creation.
- **Persisted-result integrity revalidation:** SHM-EM independently recomputes persisted prediction-result integrity before formal execution.
- **Event-to-model/input provenance:** SHM-EM links a formal event to its rule, Gate, batch, run, model/hash, input window/schema hash, and forecast snapshot.

## Positioning

Predictive-SHM and SHM-EM have complementary scopes. Predictive-SHM covers multi-source ingestion, a unified logical time-series view, model adapters, standardized timestamped forecasts, visualization, and alert-oriented use. SHM-EM does not replace that scope; it formalizes the downstream boundary through which persisted forecasts become auditable inputs to a synchronized Project Future State and to controlled formal engineering-event workflows.

Generic CEP supplies established stream/window processing, condition matching, and event-generation concepts. SHM-EM uses related rule/event concepts but adds forecast-specific persisted contracts, synchronized project state, explicit execution eligibility, independent Evaluate and Execute paths, and event-to-model/input provenance. This is a domain-specific extension of responsibility, not a claim that CEP is incapable of implementing similar controls.

OGC SensorThings standardizes sensing resources and observation access. SHM-EM's observation registry is a separate internal abstraction. No SensorThings endpoint, adapter, Annex A conformance test, or compatibility claim is present in this release.

## Primary sources

- [Predictive-SHM journal article](https://doi.org/10.1016/j.softx.2026.102732), SoftwareX 35 (2026) 102732. Capabilities above are limited to those stated by the publisher abstract.
- [OGC SensorThings API Part 1: Sensing 1.1](https://docs.ogc.org/is/18-088/18-088.html), OGC 18-088.
- [Cugola and Margara, Processing flows of information](https://doi.org/10.1145/2187671.2187677), ACM Computing Surveys 44(3), 2012.
- SHM-EM evidence: `docs/revision/DATA_MODEL_CONTRACT_SPEC.md`, `docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md`, `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md`, and `docs/revision/PROVENANCE_TRACE_EXAMPLE.md`.

Sources were checked on 2026-09-01. Machine-readable source notes and per-row bases are stored beside this document.
