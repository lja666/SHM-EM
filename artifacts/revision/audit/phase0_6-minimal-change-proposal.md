# Phase 0.6 Minimal Change Proposal

> Proposal only. Phase 0.5 does not authorize implementing any item below.

## Category A - Must resolve before core freeze

| ID | Problem | Current implementation | Reviewer impact | Recommendation | Files | Risk | Business behavior | Reproduction hash | DB migration | Pre-freeze | Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Alignment diagnostics without changing numeric filling | WideTableBuilder performs implicit as-of/interpolation/fill processing without persisting stage counts. | Reviewer concerns cannot be answered or gated from persisted run evidence. | Refactor the existing alignment helper to return values plus diagnostics; preserve the exact resulting values. Persist policy version, counts, gap, age, and ratio in input_snapshot_json. Public-sample statistics are available and must be used to set any threshold. | src/pit_pre/pit_pre/features.py; pipeline.py; result_writer.py | MEDIUM | NO for numeric inputs; YES for persisted metadata | POSSIBLE | NO | YES | CODE_CHANGE |
| A2 | Versioned input-quality acceptance policy | No explicit contract fields currently bound tolerated age/imputation to eligibility. | Gate quality flags do not describe the provenance of filled model inputs. | After A1 evidence is reviewed, add only enforced policy fields that are scientifically justified; reject or mark ineligible when declared limits are exceeded. | em_prediction_model.runtime_config_json; PIT_PRE contract/pipeline; gate input-quality check | HIGH | YES | YES | POSSIBLE | YES | CODE_CHANGE |

## Category B - Prefer claim boundary or conditional change

| ID | Problem | Current implementation | Reviewer impact | Recommendation | Files | Risk | Business behavior | Reproduction hash | DB migration | Pre-freeze | Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Observation-registry scope | PIT_PRE uses registry mappings plus a four-table security allowlist. | An unrestricted registration-only claim is broader than the implementation. | State that v1.x supports registered mappings over approved reference observation adapters; evaluate registry-backed identifier approval only if the second configuration needs a new table. | src/pit_pre/pit_pre/features.py; manuscript claim | LOW | NO | NO | NO | CONDITIONAL | CLAIM_CHANGE |
| B2 | Compatible-model scope | CachedModelRunner dispatches the six packaged target adapter signatures and rejects unknown target types. | Arbitrary-model plug-in wording would overclaim the runtime boundary. | Replace 'a new model' with 'a compatible model bundle under the existing PIT_PRE adapter contract'. | src/pit_pre/pit_pre/cached_model_runner.py; result_writer.py | LOW | NO | NO | NO | NO | CLAIM_CHANGE |
| B3 | Engineering conversion adapter scope | Non-identity YD, XD, water, and settlement outputs use target-specific conversion branches; other targets use identity mapping. | A new engineering quantity may need an adapter and reference data. | Document the identity fallback and require a validated engineering conversion adapter for non-identity quantities. | src/pit_pre/pit_pre/result_writer.py | LOW | NO | NO | NO | NO | CLAIM_CHANGE |

## Category C - Do not change core; add evidence

| ID | Problem | Current implementation | Reviewer impact | Recommendation | Files | Risk | Business behavior | Reproduction hash | DB migration | Pre-freeze | Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Execution-gate failure matrix | Gate mechanisms already exist. | Safety evidence is missing. | Run F01-F12 and verify zero formal-event, response, and provenance deltas for blocked cases. | tests and tools/revision only | LOW | NO | NO | NO | NO | EXPERIMENT_ONLY |
| C2 | Evaluate/Execute mutation test | Execute rechecks current state in source. | Independence is not experimentally demonstrated. | Run F12 without modifying production logic. | tests and tools/revision only | LOW | NO | NO | NO | NO | EXPERIMENT_ONLY |
| C3 | Future State formalization | Aggregation and hashing logic already exist. | Formal specification and boundary evidence are incomplete. | Derive pseudocode from implementation and add boundary tests; do not alter the algorithm. | docs/revision and tests | LOW | NO | NO | NO | NO | EXPERIMENT_ONLY |
| C4 | Provenance trace demonstration | Trace API and persistence exist. | No fixed end-to-end trace artifact exists. | Generate one deterministic reproduction event and export the complete chain. | tools/revision and artifacts/revision | LOW | NO | NO | NO | NO | EXPERIMENT_ONLY |
| C5 | Post-freeze reuse and portability evidence | No second configuration, Linux run, Docker run, or scalability result is currently evidenced. | Several reviewer-facing claims remain untested. | After core freeze, run the second configuration, reuse inventory, benchmarks, and an approved portability path in their authorized phases. | later revision phases | MEDIUM | NO | NO | NO | NO | EXPERIMENT_ONLY |
