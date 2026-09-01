#!/usr/bin/env python3
"""Build Phase 2D related-software, figure, impact, and reviewer evidence."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"
ACCESSED = date(2026, 9, 1).isoformat()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_line(path: Path, needle: str) -> int:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return number
    raise RuntimeError(f"Code anchor not found in {path}: {needle}")


SOURCES = [
    {
        "id": "predictive-shm",
        "type": "journal article",
        "citation": (
            "S. Yang, M. Li, J. Liao, J. Wang, D. Zhao, Z. Li, and Z. Wang, "
            "Predictive-SHM: An open-source, extensible software toolkit for multi-sensor "
            "structural health monitoring and time-series prediction, SoftwareX 35 (2026) 102732."
        ),
        "doi": "10.1016/j.softx.2026.102732",
        "url": "https://doi.org/10.1016/j.softx.2026.102732",
        "publisherPage": "https://www.sciencedirect.com/science/article/pii/S2352711026002244",
        "claimsUsed": [
            "multi-source ingestion and unified preprocessing",
            "metadata-driven registration and model adapters",
            "ULDM-to-model-tensor mapping",
            "standardized timestamped forecasts",
            "residual- and threshold-based alerting",
        ],
        "evidenceBoundary": "Only capabilities explicitly stated by the publisher abstract are marked Yes or Partial.",
        "accessed": ACCESSED,
    },
    {
        "id": "ogc-sensorthings-1.1",
        "type": "official implementation standard",
        "citation": "OGC SensorThings API Part 1: Sensing Version 1.1, OGC 18-088, 2021.",
        "url": "https://docs.ogc.org/is/18-088/18-088.html",
        "claimsUsed": [
            "open and unified access to observations and metadata from heterogeneous IoT sensor systems",
            "Thing, Location, Datastream, Sensor, ObservedProperty, Observation, and FeatureOfInterest entities",
            "conformance requires the relevant normative Annex A tests",
        ],
        "evidenceBoundary": "SHM-EM has not implemented or run those conformance tests.",
        "accessed": ACCESSED,
    },
    {
        "id": "generic-cep",
        "type": "peer-reviewed survey",
        "citation": (
            "G. Cugola and A. Margara, Processing flows of information: From data stream to complex "
            "event processing, ACM Computing Surveys 44(3) (2012) Article 15."
        ),
        "doi": "10.1145/2187671.2187677",
        "url": "https://doi.org/10.1145/2187671.2187677",
        "authorHostedPdf": "https://margara.faculty.polimi.it/papers/persys_book.pdf",
        "claimsUsed": [
            "continuous processing of information flows",
            "pre-deployed processing rules and stream/window operations",
            "condition and event-pattern recognition leading to derived events",
        ],
        "evidenceBoundary": "Generic CEP is a paradigm, not one fixed implementation or SHM-specific product.",
        "accessed": ACCESSED,
    },
]


COMPARISON = [
    {
        "capability": "Heterogeneous observation access",
        "OGC SensorThings": "Yes",
        "generic CEP": "Partial",
        "Predictive-SHM": "Yes",
        "SHM-EM": "Yes",
        "basis": "SensorThings standardizes heterogeneous observation access; CEP consumes flows from distributed sources but does not define an SHM observation schema; Predictive-SHM states multi-source ingestion; SHM-EM uses registered observation adapters.",
    },
    {
        "capability": "Standardized observation semantics",
        "OGC SensorThings": "Yes",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Yes",
        "SHM-EM": "Partial",
        "basis": "SensorThings defines sensing entities; Predictive-SHM reports ULDM; SHM-EM has a versioned internal registry rather than an external observation standard.",
    },
    {
        "capability": "Model-specific ordered input contract",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Partial",
        "SHM-EM": "Yes",
        "basis": "Predictive-SHM adapters map ULDM views to model tensors; SHM-EM additionally persists versioned feature order, target bindings, units, transforms, and contract fingerprints.",
    },
    {
        "capability": "Pluggable forecasting/model adapter",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Yes",
        "SHM-EM": "Yes",
        "basis": "Predictive-SHM explicitly reports pluggable prediction and model adapters; SHM-EM registers model bundles and PIT_PRE adapters.",
    },
    {
        "capability": "Artifact and input-schema hash validation",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "The Predictive-SHM publisher abstract does not report this control; SHM-EM verifies artifact, preprocessor, script, runtime-manifest, contract, and persisted-result hashes.",
    },
    {
        "capability": "Shared prediction origin and future timeline",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Partial",
        "SHM-EM": "Yes",
        "basis": "Predictive-SHM reports standardized timestamped forecasts; a synchronized multi-model project origin is not stated. SHM-EM validates one batch origin and a common 40-step timeline.",
    },
    {
        "capability": "Project-level future-state aggregation",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not applicable",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "This is an SHM-EM domain mechanism that aggregates target, station, and project states under a versioned policy.",
    },
    {
        "capability": "Rule/event evaluation",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Yes",
        "Predictive-SHM": "Partial",
        "SHM-EM": "Yes",
        "basis": "CEP is designed for stream conditions and event derivation; Predictive-SHM reports residual- and threshold-based alerting; SHM-EM evaluates observation or prediction series against versioned rules.",
    },
    {
        "capability": "Side-effect-free candidate evaluation",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not reported",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "SHM-EM Evaluate returns simulated candidates and creates no formal event, workflow, response step, or prediction link.",
    },
    {
        "capability": "Rechecked formal execution",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not reported",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "SHM-EM Execute recomputes and persists the execution Gate before formal rule evaluation and event creation.",
    },
    {
        "capability": "Persisted-result integrity revalidation",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not reported",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "SHM-EM independently recomputes persisted prediction-result integrity before formal execution.",
    },
    {
        "capability": "Event-to-model/input provenance",
        "OGC SensorThings": "Not applicable",
        "generic CEP": "Not reported",
        "Predictive-SHM": "Not reported",
        "SHM-EM": "Yes",
        "basis": "SHM-EM links a formal event to its rule, Gate, batch, run, model/hash, input window/schema hash, and forecast snapshot.",
    },
]


def build_related_software(repo: Path, output: Path) -> None:
    write_json(output / "related-software-sources.json", {"accessed": ACCESSED, "sources": SOURCES})
    csv_path = output / "related-software-comparison.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COMPARISON[0]))
        writer.writeheader()
        writer.writerows(COMPARISON)

    table = [
        "| Capability | OGC SensorThings | generic CEP | Predictive-SHM | SHM-EM |",
        "|---|---|---|---|---|",
    ]
    for row in COMPARISON:
        table.append(
            f"| {row['capability']} | {row['OGC SensorThings']} | {row['generic CEP']} | "
            f"{row['Predictive-SHM']} | {row['SHM-EM']} |"
        )
    body = "\n".join(table)
    related = f"""# Related Software Comparison

## Method and interpretation

The table compares documented software responsibilities rather than ranking products. Third-party cells use only `Yes`, `Partial`, `Not reported`, or `Not applicable`. `Not reported` means that the cited primary source does not explicitly document the capability; it must not be read as evidence of absence. No cross-system runtime or forecasting-accuracy superiority is claimed.

{body}

## Capability notes

""" + "\n".join(f"- **{row['capability']}:** {row['basis']}" for row in COMPARISON) + """

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
"""
    write_text(output / "related-software-comparison.md", related)
    write_text(repo / "docs/revision/RELATED_SOFTWARE_COMPARISON.md", related)

    sensor = """# OGC SensorThings Positioning

## Standards boundary

OGC SensorThings API Part 1: Sensing 1.1 provides an open, geospatially enabled interface for managing and retrieving observations and metadata from heterogeneous IoT sensor systems. Its sensing model includes Thing, Location, Datastream, Sensor, ObservedProperty, Observation, and FeatureOfInterest resources. A conformance claim requires the relevant normative Annex A tests.

SHM-EM v1.0.0 does **not** implement a SensorThings API endpoint, a SensorThings ingestion adapter, or the OGC conformance tests. It therefore makes no claim of SensorThings API conformance or compatibility.

## Relationship to SHM-EM

SHM-EM's observation registry is an internal engineering/data-source abstraction. It resolves approved physical observation tables through registered metadata and exposes canonical engineering-valued metric series to downstream services. A future SensorThings adapter could map SensorThings resources as follows:

| SensorThings resource | Possible SHM-EM registry role |
|---|---|
| Thing / FeatureOfInterest | project, station, or monitored-object identity |
| Sensor | instrument identity and type |
| ObservedProperty | metric code and engineering unit |
| Datastream | registered observation source and cadence |
| Observation | timestamped raw/engineering value plus quality metadata |

This mapping is a prospective adapter boundary, not an implemented feature. SHM-EM's versioned model-specific feature ordering, model artifacts, persisted forecast batches, execution Gate, Project Future State, Evaluate/Execute separation, and formal event provenance operate downstream of the observation interface and are outside SensorThings Sensing's stated responsibility.

## Manuscript-ready wording

> OGC SensorThings standardizes observation and sensor-resource access. SHM-EM's observation registry is a separate internal engineering/data-source abstraction. A SensorThings ingestion adapter could map compliant observations into that registry, but no SensorThings API conformance is implemented or claimed in the current release. SHM-EM's model-specific data contract and forecast-to-event controls operate downstream of the observation interface.

Source: [OGC SensorThings API Part 1: Sensing Version 1.1](https://docs.ogc.org/is/18-088/18-088.html), accessed 2026-09-01.
"""
    write_text(repo / "docs/revision/SENSORTHINGS_POSITIONING.md", sensor)


def build_sequence(repo: Path, output: Path) -> None:
    source = """sequenceDiagram
    autonumber
    actor Operator
    participant PIT_PRE as PIT_PRE forecast runner
    participant Store as Registered data and forecast store
    participant Gate as PredictionExecutionGateService
    participant Future as ProjectFutureStateService
    participant Rules as EventEvaluationService
    participant Events as Formal event store
    participant Response as Response orchestrator
    participant Trace as Event trace API

    Operator->>PIT_PRE: Start registered prediction batch
    PIT_PRE->>Store: Read active observation/model contract
    PIT_PRE->>Store: Persist batch, runs, point forecasts, and hashes

    opt Project-level future-state view (independent read path)
        Operator->>Future: Request Future State(batch, horizon, mode)
        Future->>Gate: inspect(batch, mode, referenceTime)
        Gate->>Store: Read contract, runs, results, and hashes
        Gate->>Gate: Validate model/feature sets, timeline, quality, artifacts, persisted integrity, freshness
        Gate-->>Future: Eligibility and blockers (not persisted)
        Future->>Store: Read engineering forecast series, policy, thresholds, observed risk
        Future->>Future: Aggregate target -> station -> project state
        Future-->>Operator: Deterministic state and state hash
    end

    Operator->>Rules: Evaluate(rule, batch)
    Rules->>Store: Load rule and canonical engineering series
    Rules->>Gate: inspect(batch, REPLAY, referenceTime)
    Gate->>Store: Re-read contract, runs, results, and hashes
    Gate->>Gate: Validate execution eligibility without persisting a Gate record
    Gate-->>Rules: Eligibility and blockers
    Rules->>Rules: Validate units and rule semantics; compute simulated candidates
    Rules-->>Operator: Candidate result (no formal event/workflow/link side effects)

    Operator->>Rules: Execute(rule, batch, executionMode)
    Rules->>Store: Reload rule and canonical engineering series
    Rules->>Gate: evaluate(batch, mode, referenceTime)
    Gate->>Store: Re-read and revalidate persisted prediction state
    Gate->>Store: Persist the new Gate record
    alt executionEligible is false
        Gate-->>Rules: Blockers
        Rules-->>Operator: Reject before formal-event side effects
    else executionEligible is true
        Gate-->>Rules: Eligible Gate identity
        Rules->>Rules: Validate units and rule semantics; compute formal event candidate
        Rules->>Events: Persist formal event
        Rules->>Events: Persist event-to-batch/run/model/Gate link
        Rules->>Response: Orchestrate response workflow
        Response->>Events: Persist workflow, steps, report/evidence state
        Rules-->>Operator: Formal execution result
    end

    Operator->>Trace: Request trace(event)
    Trace->>Events: Resolve rule, Gate, batch, run, model/hash, input window, and forecast snapshot
    Trace-->>Operator: Auditable provenance chain
"""
    path = repo / "docs/revision/figures/forecast-event-sequence.mmd"
    write_text(path, source)

    event_service = repo / "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/EventEvaluationServiceImpl.java"
    gate_service = repo / "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java"
    future_service = repo / "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/ProjectFutureStateServiceImpl.java"
    engine = repo / "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/MetricRuleEventEngine.java"
    crosscheck = {
        "schemaVersion": "shm-em-phase2d-sequence-crosscheck-v1",
        "finalCoreFreezeV3": FREEZE,
        "diagram": "docs/revision/figures/forecast-event-sequence.mmd",
        "futureStateIsIndependentReadPath": True,
        "anchors": [
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "public Map<String, Object> evaluate"), "claim": "Evaluate entry point"},
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "PredictionExecutionMode.REPLAY, false"), "claim": "Evaluate uses non-persisted REPLAY Gate inspection"},
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "public Map<String, Object> execute"), "claim": "Execute entry point"},
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "requirePredictionExecutionEligible"), "claim": "Execute rechecks eligibility before formal evaluation"},
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "persistEvent(event)"), "claim": "Formal event persistence"},
            {"path": str(event_service.relative_to(repo)).replace("\\", "/"), "line": find_line(event_service, "persistPredictionTrace(event, predictionGate)"), "claim": "Formal event-to-prediction linkage"},
            {"path": str(gate_service.relative_to(repo)).replace("\\", "/"), "line": find_line(gate_service, "public PredictionExecutionGate evaluate"), "claim": "Gate evaluate calls inspect then persists the record"},
            {"path": str(gate_service.relative_to(repo)).replace("\\", "/"), "line": find_line(gate_service, "validatePersistedResultIntegrity"), "claim": "Persisted-result integrity validation"},
            {"path": str(future_service.relative_to(repo)).replace("\\", "/"), "line": find_line(future_service, "executionGateService.inspect"), "claim": "Future State reports a non-persisted Gate inspection"},
            {"path": str(engine.relative_to(repo)).replace("\\", "/"), "line": find_line(engine, "requireCompatibleUnit"), "claim": "Rule unit validation occurs in the rule engine"},
        ],
        "sourceHashes": {
            str(path.relative_to(repo)).replace("\\", "/"): sha256(path)
            for path in (event_service, gate_service, future_service, engine)
        },
    }
    write_json(output / "sequence-code-crosscheck.json", crosscheck)


def build_figure_and_impact(output: Path) -> None:
    figure = """# Figure 4 Reduction Plan

## Problem in the submitted manuscript

Submitted Figure 4 occupies three consecutive PDF pages (PDF pages 8-10; printed pages 7-9) with full-page screenshots of Project Workspace, Observation and Prediction, and Prediction Runs. Persistent navigation, headers, filters, and empty table areas dominate the area while evidence-bearing details become too small to read. The figure illustrates the interface but does not constitute scientific validation.

## Revised composition

Replace the three pages with one landscape compact composite, approximately 175 mm wide and 95-105 mm high:

| Panel | Relative area | Keep | Remove |
|---|---:|---|---|
| (a) Project Workspace | 40% | observed/forecast risk cards, site map risk symbols, earliest predicted exceedance | sidebar, global header, lower event inventory, decorative whitespace |
| (b) Observation and Prediction | 35% | shared observed/forecast timeline, base time, first exceedance marker, engineering unit, batch badge | object tree, large filter toolbar, raw table, secondary rate chart |
| (c) Prediction Runs | 25% | batch identity, six-model/124-target/40-step completeness, Gate eligibility/blocker state | sidebar, empty batch-table body, duplicate KPI cards, action buttons |

Use a 2-by-2 asymmetric layout: panel (a) spans the left column; panels (b) and (c) are stacked on the right. The curve in panel (b) must remain at least 85 mm wide in the final print layout. Add simple `(a)`, `(b)`, `(c)` labels outside the screenshots. Do not add explanatory callouts inside the UI.

## Capture and production specification

- Re-capture each crop at 2x device scale or higher from the same release and reference dataset.
- Export each source crop as lossless PNG; assemble the composite in a vector document so resizing does not resample text more than once.
- Target at least 300 dpi at final print dimensions and verify that the smallest retained UI label is readable at 100% PDF zoom.
- Keep the observed line, forecast line, base-time marker, Gate state, and all engineering units visible.
- Remove private project identifiers and any non-English labels before capture.
- Preserve source crops and the editable composite separately from the manuscript PDF.

## Caption boundary

Suggested caption: **Task-oriented interface views of SHM-EM: (a) project-level observed and forecast risk, (b) a joint engineering-valued observation/forecast series, and (c) prediction-batch completeness and execution eligibility. The interface is illustrative; quantitative validation is reported in the contract, failure-path, runtime, reuse, and provenance evidence.**

## Reallocated manuscript space

Use the recovered space for the compact data-model contract, Project Future State algorithm, 15-case failure matrix, runtime table, second-configuration reuse table, and one provenance trace. This directly addresses the reviewer's concern that screenshots should not substitute for scientific evidence.
"""
    write_text(output / "FIGURE4_REDUCTION_PLAN.md", figure)

    impact = """# Impact Restructuring Plan

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
"""
    write_text(output / "IMPACT_RESTRUCTURING_PLAN.md", impact)

    repetition = """# Repetition Reduction Map

The submitted manuscript repeatedly redefines the versioned data-model contract, Project Future State, and controlled forecast-to-event transition. The revision should assign one purpose to each section and use cross-references elsewhere.

| Manuscript location | Current role | Revision action | Content retained | Content removed or moved |
|---|---|---|---|---|
| Introduction | research gap and contribution list | Keep one compact contribution paragraph | one sentence per mechanism and the downstream relationship to Predictive-SHM | implementation sequence, repeated feature lists, and validation detail move to Sections 2 and 3 |
| Section 2.1 Software description | mechanism definition | Keep the only full technical explanation | contract fields/versioning; Future State algorithm/policy; Evaluate/Execute/Gate side-effect boundaries; provenance schema | broad impact claims and benchmark language move to Sections 3 and 4 |
| Section 2.2 Main functionalities | task-oriented feature overview | Compress to one short paragraph plus API/UI cross-references | observation/prediction query, prediction runs, rules/events, response/evidence entry points | redefinitions of the same three mechanisms and repeated architecture narrative |
| Section 3 Validation and examples | empirical evidence | Expand and make evidence primary | second configuration; failure matrix; runtime/scalability; testing summary; provenance trace; containerized workflow | generic statements that the architecture is reusable or safe without measurements |
| Section 4 Impact | consequences supported by Section 3 | Replace current prose with four evidence-driven subsections | reproducible validation; observed reuse effort; controlled execution/traceability; limitations | all mechanism redefinitions and absolute claims about any project, operational reliability, or portability |
| Conclusion | compact synthesis | Limit to one short paragraph | software scope, strongest validation result, and principal limitations | third repetition of the three mechanisms, new claims, and future-work detail |

## Contribution-specific ownership

| Contribution | Introduction | Section 2 | Section 3 | Section 4 | Conclusion |
|---|---|---|---|---|---|
| Versioned data-model contract | state contribution once | define and show compact contract | validate hashes, failure paths, and six-model configuration | state reproducibility consequence only | mention once in synthesis |
| Project Future State | state contribution once | define algorithm and deterministic policy | report boundary tests and runtime | state project-level decision-support consequence only | mention once in synthesis |
| Controlled transition | state contribution once | define Evaluate, Gate, Execute, and side effects | report 15-case matrix and provenance trace | state controlled-execution consequence only | mention once in synthesis |

## Space budget

- Remove approximately two paragraphs of repeated contribution prose from Section 2.2.
- Replace the current abstract Impact wording with the four evidence paragraphs in `IMPACT_RESTRUCTURING_PLAN.md`.
- Reduce Figure 4 from three pages to one compact composite.
- Use the recovered space for the contract example, algorithm, failure table, runtime table, reuse table, and provenance sequence.

The cover letter and final response will be rewritten in the final manuscript phase; they must summarize the revision rather than repeat the paper's mechanism definitions.
"""
    write_text(output / "REPETITION_REDUCTION_MAP.md", repetition)


LIMITATIONS = [
    ("Point forecasts only", "The six current model bundles emit point forecasts; Gate validity is workflow/data eligibility, not quantified predictive uncertainty.", "Do not claim calibrated confidence, intervals, quantiles, or probabilistic risk.", "Prediction intervals, quantiles, and probabilistic threshold exceedance."),
    ("50,000-row Gate inspection cap", "Gate inspection uses a bounded 50,000-row prediction query.", "Classify it as an application safeguard, not a MySQL capacity or universal scalability limit.", "Pagination/chunked integrity validation under a separately versioned contract."),
    ("MySQL current backend", "MySQL 8 is the implemented reference persistence backend.", "Do not claim backend neutrality or effortless database substitution.", "Implement and validate an explicit storage adapter for another backend."),
    ("No alternative TSDB validation", "No TimescaleDB, InfluxDB, or other time-series-native adapter was tested.", "Do not infer performance or compatibility for those systems.", "Adapter implementation plus equivalent contract/integrity tests."),
    ("No SensorThings conformance", "No SensorThings endpoint, ingestion adapter, or Annex A conformance test exists.", "Do not say SensorThings compatible or conformant.", "A tested adapter mapping standard sensing entities into the observation registry."),
    ("Cross-platform numerical identity", "Docker Linux completed the logical E2E workflow, but its normalized prediction-output hash differed from Windows; maximum persisted absolute difference was 0.00285349 and no tolerance was applied.", "Do not call Linux output exact, tolerance-equivalent, or negligible.", "Only investigate deterministic numerical identity if a future requirement justifies it."),
    ("Native Ubuntu host not separately captured", "Ubuntu CI is configured, while a native-host result was not captured; Linux-container checks passed.", "Do not claim native Ubuntu validation.", "Archive a future CI run as supplemental evidence if naturally available."),
    ("Research-reference security", "The release has no application-level authentication and assumes the documented controlled deployment boundary.", "Do not claim secure-by-default, production-ready authentication, or tamper-proof hashes.", "TLS/reverse proxy, OIDC/OAuth2, RBAC, Execute privilege separation, least-privilege storage, protected audit, and secret management."),
    ("Synthetic second configuration", "One synthetic bridge configuration demonstrated software/configuration reuse and seven functional checks.", "Do not treat it as external field validation, forecasting accuracy, or cross-domain predictive generalization.", "Independent field configurations and model-validity studies."),
    ("Compatible model-bundle scope", "Six registered Transformer-CNN bundles and two fixture routes satisfy the current declared contract shape.", "Do not claim arbitrary forecasting frameworks can be dropped in without adapter/contract work.", "Document and validate additional adapter families under the same contract."),
    ("Approved observation-adapter scope", "Only registry-approved table/adapters participate in canonical engineering series.", "Do not equate any physical table with an automatically supported observation source.", "Implement new adapters with explicit mapping, conversion, quality, and temporal policies."),
]


def build_limitations_and_metadata(output: Path) -> None:
    lines = [
        "# Final Limitation Matrix",
        "",
        "| Limitation | Current evidence boundary | Manuscript constraint | Future work |",
        "|---|---|---|---|",
    ]
    for row in LIMITATIONS:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend([
        "",
        "These limitations are release boundaries, not hidden failures. They must remain visible in the revised manuscript and response wherever the corresponding claim is made.",
    ])
    write_text(output / "FINAL_LIMITATION_MATRIX.md", "\n".join(lines))

    metadata = """# Metadata C6 Proposed Wording

## Full version

Back end: Java 8 and Maven 3.8+; database: MySQL 8.0+; front end: Node.js 20+ and npm; forecasting runtime: Python 3.10 with locked dependencies. Exact reference-output reproduction was validated on Windows 10/11 with PowerShell 7. The revision additionally provides and exercises a Docker Compose Linux workflow for database initialization, component checks, six-model inference, Gate, Project Future State, Evaluate, Execute, and provenance. The Linux container run matched the reference input/model contracts and workflow semantics but did not produce a bitwise-identical normalized prediction-output hash.

## Compact metadata-cell version

Java 8/Maven 3.8+, MySQL 8.0+, Node.js 20+/npm, and Python 3.10 with locked dependencies. Windows 10/11 + PowerShell 7 is the exact-output reference. An exercised Docker Compose Linux workflow reproduces component checks and the logical six-model-to-provenance path; input/model contracts match, but the normalized prediction-output hash is not bitwise identical.

## Required accompanying limitation

The Docker run reproduced six models, 124 targets, 40 steps, and 4,960 persisted rows with complete Gate, Future State, Evaluate, Execute, and provenance semantics. Its normalized output hash differed from the Windows reference; maximum persisted absolute difference was `0.00285349`, maximum relative difference was `0.3918730158730158730158730159`, and no tolerance was applied. Native Ubuntu-host validation was not separately captured.
"""
    write_text(output / "METADATA_C6_PROPOSED.md", metadata)


FACTS = {
    "R1-0": ("Retained the architecture and redirected the revision to software validation.", "Contract, Future State, failure, reuse, runtime, provenance, and portability evidence packages.", "Introduction revision summary and expanded validation section.", "No new forecasting-algorithm comparison.", "55 backend tests; 13 PIT_PRE tests; 15 negative/integrity cases; 7 reuse checks."),
    "R1-1": ("Added one synthetic bridge-monitoring configuration and a registration/change inventory.", "Phase 1B functional B9-B15 regression on the performance-corrected frozen core.", "Section 3 cross-configuration reuse and Section 4.2.", "No external field validation or predictive generalization.", "3 stations, 12 instruments, 2 model fixtures, 1,120 forecast rows; B9-B15 = 7/7."),
    "R1-2": ("Added software-level latency, persistence, integrity, Gate stress, and integration-effort evidence.", "Final performance table and reuse registration inventory.", "Section 3 runtime/scalability and Section 4.1.", "No conventional-platform speedup, production throughput, or accuracy superiority.", "Prediction batch 16,778.359 ms median; Gate 343.129 ms; provenance 2.578 ms."),
    "R1-3": ("Added isolated failure-path and persisted-integrity testing and rechecked execution eligibility.", "P00, F01-F12, and I01-I02 failure matrix.", "Section 3 failure-path validation and sequence figure.", "No absolute safety claim beyond tested cases.", "15/15 cases passed; invalid states produced zero formal side effects."),
    "R1-4": ("Added a source-grounded Predictive-SHM/SHM-EM capability comparison.", "Related-software table and primary-source notes.", "Introduction/related software and reviewer response.", "No unsupported third-party absence or cross-system superiority.", "12 comparison dimensions; every third-party cell uses Yes/Partial/Not reported/Not applicable."),
    "R1-5": ("Formalized and exported the authoritative versioned data-model contract.", "Contract specification, schema, compact example, and database-derived export.", "Section 2 contract subsection and compact example.", "No claim that the compact example covers arbitrary future models.", "6 models, 164 ordered features, 124 targets; schema validation passed."),
    "R1-6": ("Documented the code-accurate deterministic Project Future State algorithm and boundaries.", "Algorithm/specification and six boundary tests.", "Section 2 algorithm and Section 3 boundary evidence.", "No probabilistic calibration or causal risk inference.", "6/6 boundary cases passed; reference median 472.342 ms."),
    "R1-7": ("Exported artifact- and database-derived configuration summaries for all model bundles.", "Model configuration JSON/Markdown with tensor dimensions and hashes.", "Section 2 model table and repository link.", "No unrecorded training parameters or predictive-accuracy claim.", "6 models; all recorded artifact/preprocessor/script/runtime/config hash checks passed."),
    "R1-8": ("Made the point-forecast boundary explicit.", "Final limitation matrix and model summaries.", "Section 4.4 and future work.", "No confidence interval, quantile, calibrated uncertainty, or probabilistic risk claim.", "Current output: 40-step point forecasts; uncertainty fields are not implemented."),
    "R1-9": ("Added repeated reference timings and selected synthetic Gate endpoints.", "Final performance table and methodology.", "Section 3 runtime/scalability table.", "No linear-scaling or multi-user-capacity claim.", "Gate S1 2,406.939 ms median at 4,960 rows; S2 3,603.382 ms at 49,600 rows."),
    "R1-10": ("Characterized MySQL persistence/integrity and documented the bounded Gate query.", "Scaling summary, final performance table, and storage-boundary document.", "Section 3 runtime table and Section 4.4.", "No MySQL optimality or 50k database-capacity claim.", "Single-run persistence: 16,131.595 ms at 4,960 rows and 186,431.707 ms at 49,600 rows."),
    "R1-11": ("Added research-release security scope and recommended deployment controls.", "SECURITY.md and deployment limitations.", "Section 4.4 and repository guidance.", "No implemented application authentication, certification, or tamper-proof hash claim.", "Documented TLS, identity, RBAC, least privilege, protected audit, secrets, network, and backup controls."),
    "R1-12": ("Added and exercised Docker Compose Linux component and logical E2E reproduction.", "Phase 2C Linux/Docker, cross-platform comparison, and limitation evidence.", "Metadata C6, reproducibility section, and limitations.", "No native Ubuntu result or exact Linux numerical reproduction claim.", "6 models/124 targets/40 steps/4,960 rows; max absolute difference 0.00285349; no tolerance."),
    "R1-13": ("Created a code-crosschecked sequence that separates Gate validation, Future State, Evaluate, Execute recheck, formal side effects, and provenance.", "Mermaid source and source-line/hash crosscheck.", "Section 2 controlled-transition figure.", "Does not imply Future State is an Execute prerequisite.", "Evaluate uses non-persisted REPLAY inspection; Execute recomputes and persists a Gate."),
    "R1-14": ("Specified a one-page compact Figure 4 composite and reassigned space to scientific evidence.", "Concrete crop/layout/capture/caption plan.", "Replace submitted three-page Figure 4.", "UI screenshots are not presented as validation evidence.", "Three submitted pages reduced to one 175 mm by 95-105 mm composite."),
    "R1-15": ("Rewrote the Impact plan around measured reuse, failure, runtime, provenance, and limitations.", "Impact restructuring plan and claim-gap matrix.", "Replace Section 4.", "No universal no-code reuse, reliability improvement, or arbitrary deployment claim.", "Every proposed paragraph names its repository evidence."),
    "R1-16": ("Generated an explicit family-level software testing summary.", "Automated test-summary JSON/CSV/Markdown.", "Section 3 testing table.", "No double-counted global total or unsupported coverage percentage.", "55/55 backend, 13/13 PIT_PRE, 15/15 negative, 7/7 reuse, 2/2 frontend, 1/1 reference reproduction."),
    "R1-17": ("Captured one formal event-to-input provenance chain and restored the isolated database afterward.", "Human-readable and machine-readable provenance trace.", "Section 3 provenance example and sequence caption.", "No claim that every API directly exposes every persisted hash.", "Event FEVT-4-f61b7667dcc01721aa2a -> rule v2 -> batch 40 -> run 236 -> settlement model/input hashes -> 40-step forecast -> Gate 1."),
    "R1-18": ("Documented SensorThings as an upstream observation standard and the possible adapter boundary.", "SensorThings positioning document and related-software table.", "Related software and limitations.", "No SensorThings compatibility or conformance claim.", "No endpoint, adapter, or Annex A conformance test exists in v1.0.0."),
    "R1-19": ("Mapped each contribution to one section-specific purpose and planned Figure 4 compression.", "Repetition reduction map and Figure 4 plan.", "Introduction, Sections 2-4, and Conclusion.", "No repeated mechanism definitions in Impact or Conclusion.", "Three contribution explanations become one statement, one mechanism definition, one evidence treatment, and one compact synthesis."),
    "R2-1": ("Differentiated Predictive-SHM factually and added SHM-EM software-layer empirical evidence.", "Primary-source comparison, runtime table, reuse inventory, and failure matrix.", "Introduction/related software and validation.", "No forecasting-accuracy or total-runtime contest between unlike software scopes.", "SHM-EM evaluation covers integration effort, Gate/runtime overhead, failure blocking, and provenance."),
    "R2-2": ("Added a concise table covering SensorThings, generic CEP, Predictive-SHM, and SHM-EM.", "12-dimension related-software table with source notes.", "Related software section.", "No inferred third-party `No` values.", "All 36 third-party capability cells are controlled vocabulary with explicit bases."),
    "R2-3": ("Formalized canonical cadence/alignment/fill policies and fail-closed required-input behavior.", "Data-model contract and negative/input-availability matrix.", "Section 2 contract and Section 3 failure tests.", "Does not state that every partial gap is rejected; registered fill policies may resolve allowed gaps.", "A required feature that cannot form a complete window is rejected before inference; freshness is checked separately before Execute."),
    "R3-1": ("Separated the logical observation contract, approved adapters/registry, and MySQL-specific implementation.", "Storage adapter boundary and MySQL characterization.", "Architecture/storage subsection and limitations.", "No TimescaleDB/InfluxDB implementation or seamless-switch claim.", "MySQL is the only validated backend; 50,000 rows is an application Gate cap."),
    "R3-2": ("Added explicit recommended deployment-security patterns.", "SECURITY.md.", "Section 4.4 and repository security section.", "No production-grade auth or privileged-attacker resistance claim.", "Execute privilege separation and protected provenance storage are deployment requirements, not built-in controls."),
    "R3-3": ("Documented canonical temporal alignment, signed offsets/fill diagnostics, incomplete-window rejection, and separate freshness gating.", "Contract specification and P00/F01-F12/I01-I02 evidence.", "Section 2 input assembly and Section 3 failure validation.", "No hidden universal interpolation policy.", "Partial gaps follow registered policy; unresolved required inputs fail before inference; stale batches fail before formal execution."),
    "R3-4": ("Implemented and exercised Docker/Docker Compose Linux reproduction while preserving the numerical limitation.", "Phase 2C portability report and comparison artifacts.", "Metadata C6, installation/reproduction, and limitations.", "No exact cross-platform hash equality or native Ubuntu-host claim.", "Linux logical E2E passed; 4,960/4,960 rows matched structurally; normalized output hashes differed."),
}


def build_response_and_map(repo: Path, output: Path) -> None:
    current = load_json(output / "reviewer-evidence-map.json")
    entries = current["entries"]
    if len(entries) != 27 or set(FACTS) != {entry["reviewerItem"] for entry in entries}:
        raise RuntimeError("Reviewer fact coverage does not match the 27-item reviewer map")

    evidence_additions = {
        "R1-4": ["docs/revision/RELATED_SOFTWARE_COMPARISON.md", "artifacts/revision/manuscript/related-software-comparison.csv"],
        "R1-8": ["artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md"],
        "R1-12": ["artifacts/revision/manuscript/METADATA_C6_PROPOSED.md"],
        "R1-13": ["docs/revision/figures/forecast-event-sequence.mmd", "artifacts/revision/manuscript/sequence-code-crosscheck.json"],
        "R1-14": ["artifacts/revision/manuscript/FIGURE4_REDUCTION_PLAN.md"],
        "R1-15": ["artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md"],
        "R1-18": ["docs/revision/SENSORTHINGS_POSITIONING.md", "docs/revision/RELATED_SOFTWARE_COMPARISON.md"],
        "R1-19": ["artifacts/revision/manuscript/REPETITION_REDUCTION_MAP.md"],
        "R2-1": ["docs/revision/RELATED_SOFTWARE_COMPARISON.md", "artifacts/revision/manuscript/IMPACT_RESTRUCTURING_PLAN.md"],
        "R2-2": ["artifacts/revision/manuscript/related-software-comparison.md", "artifacts/revision/manuscript/related-software-comparison.csv"],
        "R3-4": ["artifacts/revision/manuscript/METADATA_C6_PROPOSED.md", "artifacts/revision/manuscript/FINAL_LIMITATION_MATRIX.md"],
    }
    status_updates = {
        "R1-4": "DOCUMENTATION_COMPLETE",
        "R1-8": "LIMITATION_DOCUMENTED",
        "R1-12": "PARTIALLY_SUPPORTED_DOCUMENTED",
        "R1-13": "FIGURE_SOURCE_COMPLETE",
        "R1-14": "REDUCTION_PLAN_COMPLETE",
        "R1-15": "MANUSCRIPT_PLAN_COMPLETE",
        "R1-18": "DOCUMENTATION_COMPLETE",
        "R1-19": "REDUCTION_PLAN_COMPLETE",
        "R2-1": "DOCUMENTATION_COMPLETE",
        "R2-2": "DOCUMENTATION_COMPLETE",
        "R3-4": "SUBSTANTIALLY_ADDRESSED_WITH_LIMITATION",
    }
    for entry in entries:
        item = entry["reviewerItem"]
        entry["status"] = status_updates.get(item, entry["status"])
        for path in evidence_additions.get(item, []):
            if path not in entry["evidence"]:
                entry["evidence"].append(path)
        entry["nextAction"] = "Insert the prepared evidence and bounded wording during Final Manuscript Revision + Response."
    final_map = {
        "schemaVersion": "shm-em-reviewer-evidence-map-final-v1",
        "reviewerItems": 27,
        "phase": "Phase 2D manuscript preparation",
        "finalCoreFreezeV3": FREEZE,
        "entries": entries,
    }
    write_json(output / "reviewer-evidence-map-final.json", final_map)

    map_md = [
        "# Final Reviewer Evidence Map",
        "",
        "This map closes Phase 2D evidence preparation. Manuscript insertion and polished response prose remain for the next GPT-authorized phase.",
        "",
        "| Item | Topic | Phase 2D status | Evidence | Next action |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        evidence = "<br>".join(f"`{path}`" for path in entry["evidence"])
        map_md.append(f"| {entry['reviewerItem']} | {entry['topic']} | {entry['status']} | {evidence} | {entry['nextAction']} |")
    write_text(output / "reviewer-evidence-map-final.md", "\n".join(map_md))

    response = [
        "# Reviewer Response Facts",
        "",
        "This is a fact sheet for the next response-writing phase, not the final polished response. Every item records the implemented change, evidence, manuscript destination, explicit non-claim, and a numerical or concrete result.",
        "",
    ]
    for entry in entries:
        item = entry["reviewerItem"]
        change, evidence_summary, manuscript, nonclaim, result = FACTS[item]
        response.extend([
            f"## {item} - {entry['topic']}",
            "",
            f"- **What changed:** {change}",
            f"- **Evidence generated:** {evidence_summary}",
            f"- **Manuscript destination:** {manuscript}",
            f"- **Deliberately not claimed:** {nonclaim}",
            f"- **Key result:** {result}",
            "- **Repository evidence:** " + "; ".join(f"`{path}`" for path in entry["evidence"]),
            "",
        ])
    write_text(output / "REVIEWER_RESPONSE_FACTS.md", "\n".join(response))


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    output = repo / "artifacts/revision/manuscript"
    build_related_software(repo, output)
    build_sequence(repo, output)
    build_figure_and_impact(output)
    build_limitations_and_metadata(output)
    build_response_and_map(repo, output)
    print(f"Phase 2D manuscript evidence generated under {output}")


if __name__ == "__main__":
    main()
