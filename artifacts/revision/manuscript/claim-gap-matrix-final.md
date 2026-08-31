# Final Claim-Gap Matrix

| Candidate claim | Evidence status | Permitted wording | Prohibited overclaim |
|---|---|---|---|
| A second heterogeneous configuration can be registered without production-core changes | Demonstrated by the Phase 1B synthetic bridge | Functional reuse was demonstrated for one independently registered synthetic configuration | Generalization across arbitrary projects or external field validation |
| Prediction execution is fail-closed | Demonstrated by P00, F01-F12, and I01-I02 | Missing, stale, misaligned, or corrupted prediction state blocks Execute without a formal-event side effect | Absolute safety under every failure mode |
| Evaluate and Execute have distinct side effects | Demonstrated | Evaluate is side-effect free; Execute revalidates persisted state and may create a formal event | Evaluate guarantees subsequent Execute eligibility |
| Runtime is quantitatively characterized | Demonstrated for the reference workflow and selected synthetic stress endpoints | Report only `final-performance-table` values and their workloads | Linear scaling, production throughput, or multi-user capacity |
| The Gate remains functional under tenfold synthetic persisted-row/target stress | Demonstrated at 4,960 and 49,600 rows | The targeted correction kept the 49,600-row endpoint within a few seconds | Full Gate validation above 50,000 rows |
| MySQL behavior is characterized | Demonstrated for persistence, integrity, and selected queries | The current MySQL reference implementation was measured under the stated workloads | MySQL is optimal or is the system's absolute scalability limit |
| A versioned model/data contract exists | Formally specified and exported from the authoritative database | Contract versions, hashes, ordered features, targets, units, and timeline are auditable | The compact JSON example defines every supported future model |
| Project Future State is deterministic | Specified and boundary-tested | For equivalent canonical inputs, policy version, and batch, the state hash is deterministic | Probabilistic calibration or causal risk inference |
| Six trained forecasting models are integrated | Artifact- and database-derived configuration verified | Report actual tensor/configuration metadata and artifact hashes | Unrecorded training parameters or comparative accuracy not measured here |
| Forecast uncertainty is represented | Not implemented | The current release produces point forecasts; uncertainty quantification is future work | Calibrated intervals, confidence, or probabilistic risk |
| Provenance is end-to-end traceable | Demonstrated by one formal event trace plus independent Gate/hash evidence | Trace observation/contract/batch/Gate/rule/event/evidence identifiers and hashes | Every API exposes every persisted integrity field directly |
| Linux or Docker reproduction is supported | Not validated in this release | Native Windows reproduction is the validated path; portability remains future work | Cross-platform or container portability |
| The deployment is secure by default | Not established | Security is deployment-dependent and requires network, authentication, authorization, secret, and TLS controls | Production-grade security certification |
| OGC SensorThings compatibility exists | Not implemented as conformance | Compare concepts and identify a possible adapter boundary | SensorThings API conformance |
| SHM-EM outperforms Predictive-SHM or related software | No cross-system empirical benchmark | Compare documented architectural responsibilities and evidence coverage | Runtime or accuracy superiority |
