# Revision Change Map

**Authority:** Editorial Manager submission `SOFTX-D-26-00931.pdf`  
**Revised source:** `manuscript/SHM-EM_Revised_Manuscript_Source.md`  
**Production boundary:** Final Core Freeze v3 `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`; no production-core change in the manuscript phase.

## Structural map

| Submitted location | Revised location | Change | Reason/evidence |
|---|---|---|---|
| Abstract | Abstract | Adds second configuration, 15-case matrix, runtime/provenance, and bounded Docker result; retains non-algorithm scope | R1-0, R1-1, R1-3, R1-9, R1-12 |
| Metadata C2 | Metadata C2 | Replaces stale submitted fixed commit with Final Core Freeze v3 | Revision reproducibility boundary |
| Metadata C6 | Metadata C6 | Adds exercised Docker/Linux logical path and explicit non-bitwise output boundary | Phase 2C evidence; R1-12, R3-4 |
| Section 1 related work | Section 1 + Table 1 | Expands Predictive-SHM capabilities; adds SensorThings/CEP/Predictive-SHM/SHM-EM comparison | R1-4, R1-18, R2-1, R2-2 |
| Three contributions repeated across sections | Section 1 list + mechanism/evidence/synthesis placements | Keeps exactly three contributions and removes repetition | R1-19 |
| Section 2.1.1 | Section 2.1.1 | Clarifies logical model, approved adapters, and MySQL boundary | R3-1 |
| Section 2.1.2 prose | Section 2.1.2 + Table 2 + Listing 1 | Adds real contract, version/hash rules, correct model dimensions, full-export pointer | R1-5, R1-7 |
| Missing input behavior not explained | Section 2.1.2, “Missing and asynchronous observations” | Adds backward-asof, declared fill policy, signed offsets/diagnostics, unresolved-feature rejection, and separate freshness | R2-3, R3-3 |
| Submitted model inputs stated as 114/164 | Table 2 | Corrects to model-specific 42/42/14/14/2/50 inputs and 42/42/14/14/2/10 targets; common pool remains 164 | Database/artifact-derived contract |
| Section 2.1.3 descriptive Future State | Section 2.1.3 + Algorithm 1 | Adds code-derived deterministic aggregation, thresholds, streaks, risk, earliest time, state hash | R1-6 |
| Section 2.1.4 mechanism prose | Section 2.1.4 + revised Fig. 3 | Separates contract/integrity validation, rule validation, Evaluate, Execute recheck, side effects, provenance | R1-3, R1-13 |
| Section 2.1.5 | Section 2.1.5 | Adds precise provenance fields and generic-media-only boundary | R1-17; release scope |
| Submitted Fig. 4, three pages | Revised Fig. 4, one composite | Reduces screenshots to one compact three-panel illustrative figure | R1-14 |
| Section 2.3 | Section 2.3 | Adds Observation/Prediction input-source contract and unit semantics | Unified `MetricSeriesPoint` implementation |
| Section 3, “Illustrative examples” | Section 3, “Software validation” | Reframes evidence as validation rather than illustration | R1-0, R1-2 |
| Section 3.1 | Section 3.1 | Preserves public-case boundary; clarifies 16-step common window vs 12-16 model histories | Contract evidence |
| No second configuration | Section 3.2 + Table 4 | Adds synthetic bridge software fixture, inventory, 1,120 rows, 7/7 checks, zero frozen modifications | R1-1, R1-15 |
| Successful-path-only rule example | Section 3.3 + Table 5 | Adds 15-case matrix: P00 + F01-F12 + I01-I02 and zero side effects for expected blocked cases | R1-3 |
| No runtime table | Section 3.4 + Table 6 | Adds reference medians/p95 and S1/S2 bounded endpoints | R1-2, R1-9, R1-10 |
| General provenance claim | Section 3.5 + Table 7 | Adds event-to-rule/batch/model/input/forecast/Gate/response trace | R1-17 |
| Windows-only reproduction | Section 3.5 and 4.4 | Adds Docker/Linux logical E2E and explicit normalized-output mismatch/no-tolerance boundary | R1-12, R3-4 |
| Section 4.1-4.4 broad claims | Section 4.1-4.4 evidence-driven Impact | Rewrites around contract/testing, measured fixture reuse, controlled trace, and limitations | R1-2, R1-15 |
| “Reuse does not require changes ...” | “In the synthetic second-configuration experiment ...” | Replaces universal claim with measured experiment-specific result | R1-1, R1-15 |
| Limited limitations paragraph | Section 4.4 | Adds point forecasts, 50k app cap, MySQL-only, no TSDB/SensorThings, security, portability, synthetic-fixture, adapter/model scope | R1-8, R1-10-12, R1-18, R3-1-4 |
| Conclusions | Conclusions | Synthesizes three mechanisms and evidence; states non-claims | All reviewers |
| Data/software availability | Section 6 | Retains partial-public-data boundary; adds release synchronization requirement | Reproducibility and confidentiality |

## Mandatory wording corrections

| ID | Previous wording/problem | Revised controlled wording | Verification target |
|---|---|---|---|
| M1 | Predictive-SHM shared origin/timeline = `Partial` | `Not reported`; primary source reports timestamped forecasts but not a common multi-model origin/project timeline | Table 1 and related-software artifacts |
| M2 | Previous matrix label conflated P00 with failure cases | “15-case validation matrix comprising one positive control, 12 failure-path cases, and two input-availability controls”; expected blocked cases had zero side effects | Abstract, Tables 3/5, Sections 3.3/4.1, Response |
| M3 | Two bridge models insufficiently scoped | “Two registered compatible model bundles, used solely as software-workflow fixtures, produced 1,120 forecast rows”; no bridge prediction validation | Sections 3.2/4.2, Response |
| M4 | Risk of implying Linux equivalence | Normalized output hash differs; `exactPredictionReproduction=false`; `toleranceApplied=false`; row-wise artifact retained; max absolute difference 0.00285349 | Metadata C6, Sections 3.5/4.4, Response |

## Figure and table plan

| Item | Source | Final action |
|---|---|---|
| Fig. 1 | Submitted Fig. 1 | Retain, update terminology only |
| Fig. 2 | Submitted Fig. 2 | Retain, clarify MySQL/adapter boundary |
| Fig. 3 | `docs/revision/figures/forecast-event-sequence.mmd` | Replace/reshape as code-crosschecked sequence |
| Fig. 4 | `artifacts/revision/manuscript/FIGURE4_REDUCTION_PLAN.md` | Create one compact three-panel composite |
| Fig. 5 | Submitted Fig. 5 | Retain, correct model dimensions/validation labels |
| Table 1 | Related-software comparison artifacts | Add source-grounded responsibility comparison |
| Table 2 | `model-config-summary.json` + contract export | Replace incorrect submitted model-input table |
| Table 3 | `software-test-summary.md` | Add family-level testing summary |
| Table 4 | Phase 1B final functional evidence | Add software-reuse inventory |
| Table 5 | `failure-matrix-v2.md` | Add grouped validation matrix |
| Table 6 | `final-performance-table.md` | Add selected runtime and bounded-scaling evidence |
| Table 7 | `provenance-trace-final.json` | Add concrete provenance trace |

## Deferred until scientific-consistency approval

- Clean and marked DOCX generation.
- Final figure rendering/composition and journal layout.
- Public tag/release asset and checksum synchronization.
- Editorial line/page references, which require stable DOCX pagination.
