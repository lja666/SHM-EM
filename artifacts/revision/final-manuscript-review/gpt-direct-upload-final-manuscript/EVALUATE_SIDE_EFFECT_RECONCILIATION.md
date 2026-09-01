# Evaluate Side-Effect Reconciliation

## Decision

The frozen implementation does **not** support the unqualified phrase "side-effect-free Evaluate". Evaluate persists one evaluation/audit record in `em_event_evaluation_run`. It does not persist an execution Gate and does not create formal event, response, notification, report, evidence, or event-to-prediction provenance records.

The publication-facing description is therefore:

> Evaluate returns candidate calculations and retains an evaluation/audit record, without creating formal event, response-workflow, response-step, notification, report, evidence, execution-Gate, or prediction-link records.

This is described as **no formal business side effects**, not as zero persistence.

## Frozen implementation trace

| Record or behavior | Evaluate writes it? | Evidence |
|---|---|---|
| Candidate calculations and snapshots | Returned, not formalized | `EventEvaluationServiceImpl.java:75-95` calls `evaluateBySeverity(..., false)` and returns candidates/snapshots. |
| Evaluation/audit run (`em_event_evaluation_run`) | **Yes** | `EventEvaluationServiceImpl.java:82` calls `createRun`; lines 301-326 construct the run and call `runMapper.insert(run)`; `EventEvaluationRunMapper.xml` contains the insert. |
| Prediction execution Gate row | No | Evaluate calls `predictionGate(..., REPLAY, false)` at line 80. Lines 462-476 route `record=false` to `PredictionExecutionGateService.inspect`, while only `PredictionExecutionGateService.evaluate` inserts a Gate. |
| Formal event (`em_monitoring_event`) | No | Evaluate uses `persistMode=false` and never calls `persistEvent`; event persistence occurs only in Execute at lines 100-125 and 394-401. |
| Event-to-prediction link (`em_event_prediction_link`) | No | `persistPredictionTrace` is called only by Execute at line 120; the mapper insert is reached at line 419. |
| Response workflow and response steps | No | `orchestrator.orchestrate(event)` is called only in Execute at lines 122-125. |
| Notification tasks/delivery logs | No | Notification processing is called only in Execute at lines 126-129. |
| Report instance or evidence records | No | These are downstream Execute/orchestrator responsibilities; the Evaluate path contains no report/evidence service or mapper call. |
| Other audit record | No additional write identified | The frozen Evaluate path has one mapper write: `runMapper.insert(run)`. |

## Wording boundary

Allowed concise forms:

- "candidate evaluation without formal business side effects";
- "Evaluate persists an audit run but creates no formal event, response, notification, report, evidence, Gate, or prediction link";
- "blocked cases produced zero formal side effects" when the formal tables are explicitly defined.

Disallowed form:

- bare "side-effect-free Evaluate", because it obscures the legitimate evaluation/audit insertion.

## Scope

This reconciliation inspected the fixed revised implementation only. It changed no production code and ran no new experiment.
