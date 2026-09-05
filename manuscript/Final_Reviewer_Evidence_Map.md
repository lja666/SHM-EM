# Final Reviewer Evidence Map

| Reviewer item | Revised manuscript location | Primary repository evidence | Quantitative result / boundary |
|---|---|---|---|
| R1-0 | Abstract; Sections 2-3 | Contract, Future State, failure, runtime, reuse, provenance packages | Architecture retained; no algorithm comparison |
| R1-1 | Sections 3.2, 4.2; Table 4 | `phase1b-regression.json` and final Git diff | 3 stations; 12 instruments; 1,120 rows; 7/7 end-to-end functional checks; zero core changes |
| R1-2 | Sections 3.2-3.5; Tables 4-7 | `final-performance-table.md`; reuse/failure/provenance artifacts | Prediction median 16,778.359 ms; Gate 343.129 ms; trace 2.578 ms |
| R1-3 | Sections 2.1.4, 3.3; Fig. 3; Table 5 | `failure-matrix-v2.md/json` | 1 positive + 12 failure + 2 input controls; expected blocked cases zero side effects |
| R1-4 | Section 1; Table 1 | `RELATED_SOFTWARE_COMPARISON.md`; source JSON | 8 manuscript dimensions; full source-grounded comparison retained; no unsupported third-party `No` |
| R1-5 | Section 2.1.2; Listing 1 | `DATA_MODEL_CONTRACT_SPEC.md`; schema/example/export | 6 models; 164 ordered common features; 124 targets |
| R1-6 | Section 2.1.3; Algorithm 1 | `PROJECT_FUTURE_STATE_ALGORITHM.md`; boundary tests | 6/6 boundary cases; median 472.342 ms |
| R1-7 | Section 2.1.2; Table 2 | `MODEL_DIMENSION_RECONCILIATION.md/json`; model summary | 6 bundles; histories 12-16; aligned inputs 114 for five models and 164 for Settlement; targets total 124; checks pass |
| R1-8 | Sections 2.1.3, 4.4, 5 | `FINAL_LIMITATION_MATRIX.md` | Point forecasts only; no quantified uncertainty |
| R1-9 | Section 3.4; Table 6 | `final-performance-table.md` | n=30 reference; Gate S1/S2 4,960/49,600 rows |
| R1-10 | Sections 3.4, 4.4 | Runtime table; `STORAGE_ADAPTER_BOUNDARY.md` | S1/S2 persistence and integrity timings; no MySQL-limit claim |
| R1-11 | Section 4.4 | `SECURITY.md` | Research release; no application authentication; recommended controls |
| R1-12 | Metadata C6; Sections 3.5, 4.4 | Phase 2C comparison and numeric-difference artifacts | Logical Docker E2E; 4,960/4,960 rows; hash differs; max abs 0.00285349; no tolerance |
| R1-13 | Section 2.1.4; Fig. 3 | Mermaid source; sequence code crosscheck; Evaluate reconciliation | Evaluate retains an audit run with no formal business side effects; Execute recomputes/persists Gate |
| R1-14 | Section 2.2; Fig. 4 | `FIGURE4_REDUCTION_PLAN.md` | Three pages reduced to one 175-mm composite |
| R1-15 | Sections 3.2, 4.2 | `IMPACT_RESTRUCTURING_PLAN.md`; Phase 1B evidence | Experiment-specific reuse wording; no universal claim |
| R1-16 | Section 3; Table 3 | `software-test-summary.md/json` | 55 backend; 13 PIT_PRE; 15-case matrix; 7 reuse; 2 frontend; 1 reference |
| R1-17 | Section 3.5; Table 7 | `PROVENANCE_TRACE_EXAMPLE.md`; provenance JSON | Event -> rule v2 -> batch 40 -> run 236 -> model/input hashes -> Gate 1 |
| R1-18 | Sections 1, 4.4; Table 1 | `SENSORTHINGS_POSITIONING.md` | No endpoint, adapter, or conformance test |
| R1-19 | Entire structure | `REPETITION_REDUCTION_MAP.md` | Three contributions retained; integrity safeguard nested under contribution 3 |
| R2-1 | Section 1; Sections 3.2-3.5 | Comparison + runtime/reuse/failure/provenance | Software evidence, not cross-system forecast accuracy |
| R2-2 | Section 1; Table 1 | Related-software comparison artifacts | 8 manuscript dimensions; full repository matrix; controlled vocabulary |
| R2-3 | Section 2.1.2; Section 3.3 | `features.py`; contract spec; I01-I02 | Partial gap may resolve; entire unavailable feature rejects |
| R3-1 | Sections 2.1, 2.1.1, 4.4 | `STORAGE_ADAPTER_BOUNDARY.md` | MySQL only; alternative adapter responsibilities documented |
| R3-2 | Section 4.4 | `SECURITY.md` | TLS, identity, RBAC, Execute privilege, least privilege, protected audit |
| R3-3 | Section 2.1.2 | `features.py`; `pipeline.py`; alignment diagnostics | 16-step common window; model histories 12-16; backward-asof + declared fill |
| R3-4 | Metadata C6; Sections 3.5, 4.4 | Docker/Compose and Phase 2C artifacts | Functional/logical Linux E2E; output non-identity retained |

## Cross-cutting claim controls

- **Predictive-SHM:** upstream forecasting software is credited; shared multi-model origin/timeline is *Not reported*, not inferred absent.
- **Second configuration:** software-workflow fixture only; no bridge predictive validation.
- **Validation matrix:** P00 is a positive control; not all 15 cases are invalid.
- **Scalability:** S1/S2 are bounded endpoints; no linear/O(N) or MySQL-capacity claim.
- **Portability:** Windows is exact-output reference; Docker/Linux is logical E2E only; no tolerance or equivalence claim.
- **Security/storage/standards:** recommendations and extension boundaries are not implemented-feature claims.
