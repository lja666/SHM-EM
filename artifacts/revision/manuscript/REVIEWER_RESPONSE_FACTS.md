# Reviewer Response Facts

This is a fact sheet for the next response-writing phase, not the final polished response. Every item records the implemented change, evidence, manuscript destination, explicit non-claim, and a numerical or concrete result.

## R1-0 - Overall revision scope

- **What changed:** Retained the architecture and redirected the revision to software validation.
- **Evidence generated:** Contract, Future State, failure, reuse, runtime, provenance, and portability evidence packages.
- **Manuscript destination:** Introduction revision summary and expanded validation section.
- **Deliberately not claimed:** No new forecasting-algorithm comparison.
- **Key result:** 55 backend tests; 13 PIT_PRE tests; a 15-case validation matrix (P00, F01-F12, I01-I02); 7 reuse checks.
- **Repository evidence:** `artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md`

## R1-1 - Reuse/generalization beyond one excavation

- **What changed:** Added one synthetic bridge-monitoring configuration and a registration/change inventory.
- **Evidence generated:** Phase 1B functional B9-B15 regression on the performance-corrected frozen core.
- **Manuscript destination:** Section 3 cross-configuration reuse and Section 4.2.
- **Deliberately not claimed:** No external field validation or predictive generalization.
- **Key result:** 3 stations, 12 instruments, 2 compatible model bundles used solely as software-workflow fixtures, 1,120 forecast rows; B9-B15 = 7/7.
- **Repository evidence:** `artifacts/revision/benchmarks/route-p/phase1b-regression/PHASE1B_COMPLETION_REPORT.md`

## R1-2 - Software effectiveness and quantitative runtime

- **What changed:** Added software-level latency, persistence, integrity, Gate stress, and integration-effort evidence.
- **Evidence generated:** Final performance table and reuse registration inventory.
- **Manuscript destination:** Section 3 runtime/scalability and Section 4.1.
- **Deliberately not claimed:** No conventional-platform speedup, production throughput, or accuracy superiority.
- **Key result:** Prediction batch 16,778.359 ms median; Gate 343.129 ms; provenance 2.578 ms.
- **Repository evidence:** `artifacts/revision/manuscript/final-performance-table.md`

## R1-3 - Evaluate/Execute failure-path safety

- **What changed:** Added isolated failure-path and persisted-integrity testing and rechecked execution eligibility.
- **Evidence generated:** A 15-case validation matrix comprising one positive control, 12 failure-path cases, and two input-availability controls.
- **Manuscript destination:** Section 3 failure-path validation and sequence figure.
- **Deliberately not claimed:** No absolute safety claim beyond tested cases.
- **Key result:** All cases expected to be blocked produced zero formal side effects.
- **Repository evidence:** `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md`

## R1-4 - Novelty versus Predictive-SHM

- **What changed:** Added a source-grounded Predictive-SHM/SHM-EM capability comparison.
- **Evidence generated:** Related-software table and primary-source notes.
- **Manuscript destination:** Introduction/related software and reviewer response.
- **Deliberately not claimed:** No unsupported third-party absence or cross-system superiority.
- **Key result:** 12 comparison dimensions; every third-party cell uses Yes/Partial/Not reported/Not applicable.
- **Repository evidence:** `artifacts/revision/manuscript/claim-gap-matrix-final.md`; `docs/revision/RELATED_SOFTWARE_COMPARISON.md`; `artifacts/revision/manuscript/related-software-comparison.csv`

## R1-5 - Versioned data-model contract

- **What changed:** Formalized and exported the authoritative versioned data-model contract.
- **Evidence generated:** Contract specification, schema, compact example, and database-derived export.
- **Manuscript destination:** Section 2 contract subsection and compact example.
- **Deliberately not claimed:** No claim that the compact example covers arbitrary future models.
- **Key result:** 6 models, 164 ordered features, 124 targets; schema validation passed.
- **Repository evidence:** `docs/revision/DATA_MODEL_CONTRACT_SPEC.md`; `docs/revision/examples/data-model-contract.example.json`

## R1-6 - Project Future State definition

- **What changed:** Documented the code-accurate deterministic Project Future State algorithm and boundaries.
- **Evidence generated:** Algorithm/specification and six boundary tests.
- **Manuscript destination:** Section 2 algorithm and Section 3 boundary evidence.
- **Deliberately not claimed:** No probabilistic calibration or causal risk inference.
- **Key result:** 6/6 boundary cases passed; reference median 472.342 ms.
- **Repository evidence:** `docs/revision/PROJECT_FUTURE_STATE_SPEC.md`; `docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md`; `artifacts/revision/manuscript/future-state-boundary-tests.json`

## R1-7 - Six-model configuration

- **What changed:** Exported artifact- and database-derived configuration summaries for all model bundles.
- **Evidence generated:** Model configuration JSON/Markdown with tensor dimensions and hashes.
- **Manuscript destination:** Section 2 model table and repository link.
- **Deliberately not claimed:** No unrecorded training parameters or predictive-accuracy claim.
- **Key result:** 6 models; all recorded artifact/preprocessor/script/runtime/config hash checks passed.
- **Repository evidence:** `docs/revision/MODEL_CONFIG_SUMMARY.md`; `artifacts/revision/manuscript/model-config-summary.json`

## R1-8 - Point-forecast limitation

- **What changed:** Made the point-forecast boundary explicit.
- **Evidence generated:** Final limitation matrix and model summaries.
- **Manuscript destination:** Section 4.4 and future work.
- **Deliberately not claimed:** No confidence interval, quantile, calibrated uncertainty, or probabilistic risk claim.
- **Key result:** Current output: 40-step point forecasts; uncertainty fields are not implemented.
- **Repository evidence:** `artifacts/revision/manuscript/claim-gap-matrix-final.md`; `artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md`

## R1-9 - Runtime scalability

- **What changed:** Added repeated reference timings and selected synthetic Gate endpoints.
- **Evidence generated:** Final performance table and methodology.
- **Manuscript destination:** Section 3 runtime/scalability table.
- **Deliberately not claimed:** No linear-scaling or multi-user-capacity claim.
- **Key result:** Gate S1 2,406.939 ms median at 4,960 rows; S2 3,603.382 ms at 49,600 rows.
- **Repository evidence:** `artifacts/revision/manuscript/final-performance-table.md`

## R1-10 - MySQL scalability

- **What changed:** Characterized MySQL persistence/integrity and documented the bounded Gate query.
- **Evidence generated:** Scaling summary, final performance table, and storage-boundary document.
- **Manuscript destination:** Section 3 runtime table and Section 4.4.
- **Deliberately not claimed:** No MySQL optimality or 50k database-capacity claim.
- **Key result:** Single-run persistence: 16,131.595 ms at 4,960 rows and 186,431.707 ms at 49,600 rows.
- **Repository evidence:** `artifacts/revision/benchmarks/scaling/scaling-summary.json`; `artifacts/revision/manuscript/final-performance-table.md`

## R1-11 - Deployment security

- **What changed:** Added research-release security scope and recommended deployment controls.
- **Evidence generated:** SECURITY.md and deployment limitations.
- **Manuscript destination:** Section 4.4 and repository guidance.
- **Deliberately not claimed:** No implemented application authentication, certification, or tamper-proof hash claim.
- **Key result:** Documented TLS, identity, RBAC, least privilege, protected audit, secrets, network, and backup controls.
- **Repository evidence:** `SECURITY.md`; `docs/revision/DEPLOYMENT_LIMITATIONS.md`

## R1-12 - Windows-centric reproduction

- **What changed:** Added and exercised Docker Compose Linux component and logical E2E reproduction.
- **Evidence generated:** Phase 2C Linux/Docker, cross-platform comparison, and limitation evidence.
- **Manuscript destination:** Metadata C6, reproducibility section, and limitations.
- **Deliberately not claimed:** No native Ubuntu result or exact Linux numerical reproduction claim.
- **Key result:** 6 models/124 targets/40 steps/4,960 rows; max absolute difference 0.00285349; no tolerance.
- **Repository evidence:** `artifacts/revision/portability/cross-platform-comparison.md`; `artifacts/revision/portability/portability-limitations.md`; `artifacts/revision/manuscript/METADATA_C6_PROPOSED.md`

## R1-13 - Validation/evaluation/execution eligibility figure

- **What changed:** Created a code-crosschecked sequence that separates Gate validation, Future State, Evaluate, Execute recheck, formal side effects, and provenance.
- **Evidence generated:** Mermaid source and source-line/hash crosscheck.
- **Manuscript destination:** Section 2 controlled-transition figure.
- **Deliberately not claimed:** Does not imply Future State is an Execute prerequisite.
- **Key result:** Evaluate uses non-persisted REPLAY inspection; Execute recomputes and persists a Gate.
- **Repository evidence:** `artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md`; `docs/revision/figures/forecast-event-sequence.mmd`; `artifacts/revision/manuscript/sequence-code-crosscheck.json`

## R1-14 - Screenshots as scientific evidence

- **What changed:** Specified a one-page compact Figure 4 composite and reassigned space to scientific evidence.
- **Evidence generated:** Concrete crop/layout/capture/caption plan.
- **Manuscript destination:** Replace submitted three-page Figure 4.
- **Deliberately not claimed:** UI screenshots are not presented as validation evidence.
- **Key result:** Three submitted pages reduced to one 175 mm by 95-105 mm composite.
- **Repository evidence:** `artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md`; `artifacts/revision/manuscript/FIGURE4_REDUCTION_PLAN.md`

## R1-15 - Unsupported impact claims

- **What changed:** Rewrote the Impact plan around measured reuse, failure, runtime, provenance, and limitations.
- **Evidence generated:** Impact restructuring plan and claim-gap matrix.
- **Manuscript destination:** Replace Section 4.
- **Deliberately not claimed:** No universal no-code reuse, reliability improvement, or arbitrary deployment claim.
- **Key result:** Every proposed paragraph names its repository evidence.
- **Repository evidence:** `artifacts/revision/manuscript/claim-gap-matrix-final.md`; `artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md`

## R1-16 - Software testing summary

- **What changed:** Generated an explicit family-level software testing summary.
- **Evidence generated:** Automated test-summary JSON/CSV/Markdown.
- **Manuscript destination:** Section 3 testing table.
- **Deliberately not claimed:** No double-counted global total or unsupported coverage percentage.
- **Key result:** 55/55 backend, 13/13 PIT_PRE, a 15-case validation matrix (P00, F01-F12, I01-I02), 7/7 reuse, 2/2 frontend, and 1/1 reference reproduction.
- **Repository evidence:** `artifacts/revision/manuscript/software-test-summary.md`

## R1-17 - Concrete provenance demonstration

- **What changed:** Captured one formal event-to-input provenance chain and restored the isolated database afterward.
- **Evidence generated:** Human-readable and machine-readable provenance trace.
- **Manuscript destination:** Section 3 provenance example and sequence caption.
- **Deliberately not claimed:** No claim that every API directly exposes every persisted hash.
- **Key result:** Event FEVT-4-f61b7667dcc01721aa2a -> rule v2 -> batch 40 -> run 236 -> settlement model/input hashes -> 40-step forecast -> Gate 1.
- **Repository evidence:** `docs/revision/PROVENANCE_TRACE_EXAMPLE.md`; `artifacts/revision/manuscript/provenance-trace-final.json`

## R1-18 - OGC SensorThings relationship

- **What changed:** Documented SensorThings as an upstream observation standard and the possible adapter boundary.
- **Evidence generated:** SensorThings positioning document and related-software table.
- **Manuscript destination:** Related software and limitations.
- **Deliberately not claimed:** No SensorThings compatibility or conformance claim.
- **Key result:** No endpoint, adapter, or Annex A conformance test exists in v1.0.0.
- **Repository evidence:** `artifacts/revision/manuscript/claim-gap-matrix-final.md`; `docs/revision/SENSORTHINGS_POSITIONING.md`; `docs/revision/RELATED_SOFTWARE_COMPARISON.md`

## R1-19 - Repeated contribution text

- **What changed:** Mapped each contribution to one section-specific purpose and planned Figure 4 compression.
- **Evidence generated:** Repetition reduction map and Figure 4 plan.
- **Manuscript destination:** Introduction, Sections 2-4, and Conclusion.
- **Deliberately not claimed:** No repeated mechanism definitions in Impact or Conclusion.
- **Key result:** Three contribution explanations become one statement, one mechanism definition, one evidence treatment, and one compact synthesis.
- **Repository evidence:** `artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md`; `artifacts/revision/manuscript/REPETITION_REDUCTION_MAP.md`

## R2-1 - Predictive-SHM difference and empirical comparison

- **What changed:** Differentiated Predictive-SHM factually and added SHM-EM software-layer empirical evidence.
- **Evidence generated:** Primary-source comparison, runtime table, reuse inventory, and failure matrix.
- **Manuscript destination:** Introduction/related software and validation.
- **Deliberately not claimed:** No forecasting-accuracy or total-runtime contest between unlike software scopes.
- **Key result:** SHM-EM evaluation covers integration effort, Gate/runtime overhead, failure blocking, and provenance.
- **Repository evidence:** `artifacts/revision/manuscript/final-performance-table.md`; `artifacts/revision/manuscript/claim-gap-matrix-final.md`; `docs/revision/RELATED_SOFTWARE_COMPARISON.md`; `artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md`

## R2-2 - Related-framework comparison table

- **What changed:** Added a concise table covering SensorThings, generic CEP, Predictive-SHM, and SHM-EM.
- **Evidence generated:** 12-dimension related-software table with source notes.
- **Manuscript destination:** Related software section.
- **Deliberately not claimed:** No inferred third-party `No` values.
- **Key result:** All 36 third-party capability cells are controlled vocabulary with explicit bases.
- **Repository evidence:** `artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md`; `artifacts/revision/manuscript/related-software-comparison.md`; `artifacts/revision/manuscript/related-software-comparison.csv`

## R2-3 - Missing/dropped rolling-window data

- **What changed:** Formalized canonical cadence/alignment/fill policies and fail-closed required-input behavior.
- **Evidence generated:** Data-model contract and negative/input-availability matrix.
- **Manuscript destination:** Section 2 contract and Section 3 failure tests.
- **Deliberately not claimed:** Does not state that every partial gap is rejected; registered fill policies may resolve allowed gaps.
- **Key result:** A required feature that cannot form a complete window is rejected before inference; freshness is checked separately before Execute.
- **Repository evidence:** `docs/revision/DATA_MODEL_CONTRACT_SPEC.md`; `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md`

## R3-1 - MySQL and data-access abstraction

- **What changed:** Separated the logical observation contract, approved adapters/registry, and MySQL-specific implementation.
- **Evidence generated:** Storage adapter boundary and MySQL characterization.
- **Manuscript destination:** Architecture/storage subsection and limitations.
- **Deliberately not claimed:** No TimescaleDB/InfluxDB implementation or seamless-switch claim.
- **Key result:** MySQL is the only validated backend; 50,000 rows is an application Gate cap.
- **Repository evidence:** `docs/revision/STORAGE_ADAPTER_BOUNDARY.md`; `docs/DATABASE.md`

## R3-2 - Security pattern

- **What changed:** Added explicit recommended deployment-security patterns.
- **Evidence generated:** SECURITY.md.
- **Manuscript destination:** Section 4.4 and repository security section.
- **Deliberately not claimed:** No production-grade auth or privileged-attacker resistance claim.
- **Key result:** Execute privilege separation and protected provenance storage are deployment requirements, not built-in controls.
- **Repository evidence:** `SECURITY.md`

## R3-3 - Asynchronous sampling, latency, missing points

- **What changed:** Documented canonical temporal alignment, signed offsets/fill diagnostics, incomplete-window rejection, and separate freshness gating.
- **Evidence generated:** Contract specification and P00/F01-F12/I01-I02 evidence.
- **Manuscript destination:** Section 2 input assembly and Section 3 failure validation.
- **Deliberately not claimed:** No hidden universal interpolation policy.
- **Key result:** Partial gaps follow registered policy; unresolved required inputs fail before inference; stale batches fail before formal execution.
- **Repository evidence:** `docs/revision/DATA_MODEL_CONTRACT_SPEC.md`; `artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md`

## R3-4 - Linux/Docker portability

- **What changed:** Implemented and exercised Docker/Docker Compose Linux reproduction while preserving the numerical limitation.
- **Evidence generated:** Phase 2C portability report and comparison artifacts.
- **Manuscript destination:** Metadata C6, installation/reproduction, and limitations.
- **Deliberately not claimed:** No exact cross-platform hash equality or native Ubuntu-host claim.
- **Key result:** Linux logical E2E passed; 4,960/4,960 rows matched structurally; normalized output hashes differed.
- **Repository evidence:** `artifacts/revision/portability/linux-reference-reproduction.json`; `artifacts/revision/portability/cross-platform-comparison.md`; `artifacts/revision/portability/cross-platform-numeric-difference.json`; `artifacts/revision/manuscript/METADATA_C6_PROPOSED.md`; `artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md`
