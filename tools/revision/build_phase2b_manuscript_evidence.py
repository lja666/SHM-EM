#!/usr/bin/env python3
"""Build the final Phase 2B manuscript evidence tables and reviewer map."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def timing_row(
    section: str,
    operation: str,
    workload: str,
    samples: int,
    median_ms: float | None,
    p95_ms: float | None,
    source: str,
    note: str,
    single_elapsed_ms: float | None = None,
) -> dict[str, Any]:
    return {
        "section": section,
        "operation": operation,
        "workload": workload,
        "samples": samples,
        "medianMs": median_ms,
        "p95Ms": p95_ms,
        "singleElapsedMs": single_elapsed_ms,
        "source": source,
        "note": note,
    }


def build_performance(repo: Path, output: Path) -> None:
    pit = load(repo / "artifacts/revision/benchmarks/reference/pitpre-summary.json")
    backend = load(repo / "artifacts/revision/benchmarks/reference/backend-summary.json")
    route_p = load(repo / "artifacts/revision/benchmarks/route-p/scaling-sweep-v2-summary.json")
    mysql = load(repo / "artifacts/revision/benchmarks/scaling/scaling-summary.json")
    pit_source = "artifacts/revision/benchmarks/reference/pitpre-summary.json"
    backend_source = "artifacts/revision/benchmarks/reference/backend-summary.json"
    route_source = "artifacts/revision/benchmarks/route-p/scaling-sweep-v2-summary.json"
    mysql_source = "artifacts/revision/benchmarks/scaling/scaling-summary.json"
    rows: list[dict[str, Any]] = []
    pit_names = [
        ("Full six-model prediction batch", "fullBatch"),
        ("Input assembly", "inputAssembly"),
        ("All-model inference", "allModelInference"),
        ("Engineering conversion", "engineeringConversion"),
        ("Prediction persistence (exclusive estimate)", "predictionPersistenceExclusiveEstimate"),
        ("Persisted-integrity hashing", "persistedIntegrityHash"),
    ]
    for label, key in pit_names:
        item = pit["components"][key]
        rows.append(timing_row("Reference workflow", label, "6 models, 124 targets, 40 steps", item["count"], item["medianMs"], item["p95Ms"], pit_source, "One process, concurrency 1; model artifacts cached."))
    corrected_gate = route_p["reference"]["measured"]
    rows.append(timing_row("Reference workflow", "Execution Gate inspection", "4,960 persisted prediction rows", corrected_gate["count"], corrected_gate["medianMs"], corrected_gate["p95Ms"], route_source, "Final corrected production benchmark after project-and-batch query scoping."))
    for label, key in [
        ("Project Future State", "future-state"),
        ("Single-target joint series", "series-single-target"),
        ("Full-batch joint series", "series-full-batch"),
        ("Rule Evaluate", "evaluate"),
        ("Rule Execute", "execute"),
        ("Event provenance trace", "provenance-trace"),
    ]:
        item = backend["operations"][key]
        rows.append(timing_row("Reference workflow", label, "public reference case", item["count"], item["medianMs"], item["p95Ms"], backend_source, "Concurrency 1; Execute uses baseline restoration between calls." if key == "execute" else "Concurrency 1."))
    for label, key in [("Gate stress S1", "s1"), ("Gate stress S2", "s2")]:
        item = route_p[key]
        measured = item["measured"]
        rows.append(timing_row("Tenfold Gate stress", label, f"{item['rows']:,} rows; {item['targets']:,} targets; {item['steps']} steps", measured["count"], measured["medianMs"], measured["p95Ms"], route_source, "Synthetic functional stress endpoint; no linear-scaling claim."))
    for scale in mysql["scales"]:
        persistence = scale["persistence"]
        integrity = scale["integrity"]
        workload = f"{persistence['rowCount']:,} rows"
        rows.append(timing_row("MySQL characterization", f"Prediction persistence {scale['scale']}", workload, 1, None, None, mysql_source, f"{persistence['rowsPerSecond']:.3f} rows/s; autocommit per 2,000-row executemany chunk.", persistence["elapsedMs"]))
        rows.append(timing_row("MySQL characterization", f"Independent integrity verification {scale['scale']}", workload, 1, None, None, mysql_source, "Independent recomputation matched the persisted hash.", integrity["verificationMs"]))
    csv_path = output / "final-performance-table.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    md = [
        "# Final Performance Table",
        "",
        "All timings are milliseconds. Median and p95 are reported only for repeated measurements; single-run MySQL characterization is kept in a separate column. These results characterize the submitted reference implementation and do not establish linear scalability.",
        "",
        "| Section | Operation | Workload | n | Median | p95 | Single elapsed |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        value = lambda item: "-" if item is None else f"{item:.3f}"
        md.append(f"| {row['section']} | {row['operation']} | {row['workload']} | {row['samples']} | {value(row['medianMs'])} | {value(row['p95Ms'])} | {value(row['singleElapsedMs'])} |")
    (output / "final-performance-table.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    selection = """# Performance Evidence Selection

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
"""
    (output / "PERFORMANCE_EVIDENCE_SELECTION.md").write_text(selection, encoding="utf-8", newline="\n")


def reviewer_entries() -> list[dict[str, Any]]:
    def item(identifier: str, topic: str, status: str, evidence: list[str], next_action: str) -> dict[str, Any]:
        return {"reviewerItem": identifier, "topic": topic, "status": status, "evidence": evidence, "nextAction": next_action}
    return [
        item("R1-0", "Overall revision scope", "EVIDENCE_COMPLETE", ["artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md"], "Use the evidence-first revision structure."),
        item("R1-1", "Reuse/generalization beyond one excavation", "EVIDENCE_COMPLETE", ["artifacts/revision/benchmarks/route-p/phase1b-regression/PHASE1B_COMPLETION_REPORT.md"], "Report the synthetic second configuration as functional reuse evidence, not external validation."),
        item("R1-2", "Software effectiveness and quantitative runtime", "EVIDENCE_COMPLETE", ["artifacts/revision/manuscript/final-performance-table.md"], "Insert the compact final table."),
        item("R1-3", "Evaluate/Execute failure-path safety", "EVIDENCE_COMPLETE", ["artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md"], "Summarize P00/F01-F12/I01-I02 and side-effect isolation."),
        item("R1-4", "Novelty versus Predictive-SHM", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Complete the related-software comparison in the manuscript response."),
        item("R1-5", "Versioned data-model contract", "EVIDENCE_COMPLETE", ["docs/revision/DATA_MODEL_CONTRACT_SPEC.md", "docs/revision/examples/data-model-contract.example.json"], "Cite the formal contract and compact real example."),
        item("R1-6", "Project Future State definition", "EVIDENCE_COMPLETE", ["docs/revision/PROJECT_FUTURE_STATE_SPEC.md", "docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md", "artifacts/revision/manuscript/future-state-boundary-tests.json"], "Include the algorithm and boundary semantics."),
        item("R1-7", "Six-model configuration", "EVIDENCE_COMPLETE", ["docs/revision/MODEL_CONFIG_SUMMARY.md", "artifacts/revision/manuscript/model-config-summary.json"], "Use the database- and artifact-derived model table."),
        item("R1-8", "Point-forecast limitation", "LIMITATION_ONLY", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "State that uncertainty quantification is not implemented."),
        item("R1-9", "Runtime scalability", "EVIDENCE_COMPLETE", ["artifacts/revision/manuscript/final-performance-table.md"], "Report reference and tenfold stress without linear-scaling language."),
        item("R1-10", "MySQL scalability", "EVIDENCE_COMPLETE", ["artifacts/revision/benchmarks/scaling/scaling-summary.json", "artifacts/revision/manuscript/final-performance-table.md"], "Report persistence, integrity, retrieval, and the 50,000-row Gate boundary."),
        item("R1-11", "Deployment security", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Add the deployment-security limitation and recommended reverse-proxy/authentication controls."),
        item("R1-12", "Windows-centric reproduction", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Document the validated Windows path and list Linux portability as unverified."),
        item("R1-13", "Validation/evaluation/execution eligibility figure", "MANUSCRIPT_PENDING", ["artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md"], "Redraw the workflow with distinct validation, Evaluate, and Execute boundaries."),
        item("R1-14", "Screenshots as scientific evidence", "MANUSCRIPT_PENDING", ["artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md"], "Replace screenshot-heavy evidence with tables, algorithm, and provenance trace."),
        item("R1-15", "Unsupported impact claims", "MANUSCRIPT_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Narrow claims to demonstrated behavior."),
        item("R1-16", "Software testing summary", "EVIDENCE_COMPLETE", ["artifacts/revision/manuscript/software-test-summary.md"], "Insert family-level counts without a double-counted global total."),
        item("R1-17", "Concrete provenance demonstration", "EVIDENCE_COMPLETE", ["docs/revision/PROVENANCE_TRACE_EXAMPLE.md", "artifacts/revision/manuscript/provenance-trace-final.json"], "Present one complete observation/contract/batch/Gate/rule/event/evidence chain."),
        item("R1-18", "OGC SensorThings relationship", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Add a precise interoperability comparison and avoid claiming conformance."),
        item("R1-19", "Repeated contribution text", "MANUSCRIPT_PENDING", ["artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md"], "Compress repeated contribution statements during manuscript revision."),
        item("R2-1", "Predictive-SHM difference and empirical comparison", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/final-performance-table.md", "artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Add a claim-level comparison; do not invent a cross-system runtime benchmark."),
        item("R2-2", "Related-framework comparison table", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/MANUSCRIPT_EVIDENCE_BLUEPRINT.md"], "Build the manuscript comparison table from verifiable published capabilities."),
        item("R2-3", "Missing/dropped rolling-window data", "EVIDENCE_COMPLETE", ["docs/revision/DATA_MODEL_CONTRACT_SPEC.md", "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md"], "Describe the registered temporal alignment/fill policy for partial gaps, and the fail-closed rejection when a required feature cannot produce a complete input window."),
        item("R3-1", "MySQL and data-access abstraction", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/final-performance-table.md", "artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Document current MySQL characterization and the bounded adapter seam without claiming an implemented alternative backend."),
        item("R3-2", "Security pattern", "DOCUMENTATION_PENDING", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "Add deployment boundary and security recommendations."),
        item("R3-3", "Asynchronous sampling, latency, missing points", "EVIDENCE_COMPLETE", ["docs/revision/DATA_MODEL_CONTRACT_SPEC.md", "artifacts/revision/benchmarks/route-p/failure-regression/failure-matrix-v2.md"], "Explain the canonical temporal alignment policy, signed source-offset/fill diagnostics, required-input rejection, and the separate fail-closed freshness/execution Gate."),
        item("R3-4", "Linux/Docker portability", "LIMITATION_ONLY", ["artifacts/revision/manuscript/claim-gap-matrix-final.md"], "State that this release validates native Windows reproduction and does not claim Docker/Linux validation."),
    ]


def build_reviewer_map(output: Path) -> None:
    entries = reviewer_entries()
    payload = {"schemaVersion": "shm-em-reviewer-evidence-map-v1", "reviewerItems": len(entries), "entries": entries}
    dump(output / "reviewer-evidence-map.json", payload)
    lines = ["# Reviewer Evidence Map", "", "| Item | Topic | Status | Primary evidence | Next action |", "|---|---|---|---|---|"]
    for entry in entries:
        evidence = "<br>".join(f"`{path}`" for path in entry["evidence"])
        lines.append(f"| {entry['reviewerItem']} | {entry['topic']} | {entry['status']} | {evidence} | {entry['nextAction']} |")
    (output / "reviewer-evidence-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_claim_gap(output: Path) -> None:
    text = """# Final Claim-Gap Matrix

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
"""
    (output / "claim-gap-matrix-final.md").write_text(text, encoding="utf-8", newline="\n")


def build_blueprint(output: Path) -> None:
    text = """# Manuscript Evidence Blueprint

This blueprint converts repository evidence into compact scientific material. It does not modify the manuscript.

## Table A: Versioned data-model contract

Source: `docs/revision/DATA_MODEL_CONTRACT_SPEC.md` and the compact schema-validated example. Show contract version/hash, ordered feature binding, target binding, units/transforms, 40-step timeline, and fail-closed missing-data policy.

## Table B: Six-model configuration

Source: `docs/revision/MODEL_CONFIG_SUMMARY.md`. Show model type/version, history length, feature/target counts, tensor-derived dimensions, parameter source, and verified artifact hashes. Do not infer unrecorded hyperparameters.

## Algorithm 1: Project Future State aggregation

Source: `docs/revision/PROJECT_FUTURE_STATE_ALGORITHM.md`. Present canonical policy verification, per-feature consecutive threshold evaluation, target/station/project aggregation, earliest exceedance, observed/forecast separation, and deterministic state hashing.

## Table C: Software validation

Source: `artifacts/revision/manuscript/software-test-summary.md`. Report test families separately: 55 backend tests, 13 PIT_PRE tests, 15 negative/integrity cases, 7 second-configuration checks, 2 frontend checks, and one reference reproduction. Do not sum overlapping families into a global total.

## Table D: Runtime and scalability characterization

Source: `artifacts/revision/manuscript/final-performance-table.csv`. Include the public reference workflow plus S1/S2 Gate endpoints. State concurrency, sample count, workload dimensions, and the 50,000-row Gate boundary. Do not use the diagnostic six-level sweep as linear-scaling evidence.

## Table E: Related-software capability comparison

Build during manuscript revision from primary publications and official documentation. Candidate columns: versioned model/data contract; authoritative prediction batch; persisted integrity gate; Evaluate/Execute separation; deterministic project future state; formal event/provenance linkage; failure-path validation; quantitative runtime evidence. Use `not reported` rather than inferring absence.

## Figure: Validation-to-response evidence chain

Redraw the workflow as: observation and canonical alignment -> versioned contract -> prediction batch/run/results -> integrity/freshness Gate -> rule Evaluate -> rule Execute -> formal event -> response/evidence archive. Clearly separate validation, evaluation, and execution eligibility. Use the concrete trace in `docs/revision/PROVENANCE_TRACE_EXAMPLE.md` as the caption-level example.

## Revision placement

- Software description: Tables A-B and Algorithm 1.
- Validation section: Tables C-D and the provenance figure.
- Impact/limitations: claim-gap matrix wording.
- Related software: Table E.
- Repository/data availability: identify public sample data, open model artifacts, and private field-data boundary precisely.
"""
    (output / "MANUSCRIPT_EVIDENCE_BLUEPRINT.md").write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    output = repo / "artifacts/revision/manuscript"
    output.mkdir(parents=True, exist_ok=True)
    build_performance(repo, output)
    build_reviewer_map(output)
    build_claim_gap(output)
    build_blueprint(output)
    print(json.dumps({"performanceRows": sum(1 for _ in csv.DictReader((output / 'final-performance-table.csv').open(encoding='utf-8-sig'))), "reviewerItems": len(reviewer_entries()), "output": output.relative_to(repo).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
