# Public Reference Provenance Trace

This trace was captured from one formal reproduction event on the public reference database at Final Core Freeze v3 `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`. Formal tables were restored to their pre-run baseline after export.

## Trace chain

1. Event `FEVT-4-f61b7667dcc01721aa2a` (captured database ID `31`) was created by rule `PRED_GROUND_SETTLEMENT_WARNING` version `v2`.
2. The event resolves to prediction batch `ROLLING_120M_20250101004202_RUN_20260830232819008787` (ID `40`), base time `2025-01-01T00:42:02`.
3. It resolves to run `236`, model `settlement` version `pit_pre_v1`, artifact SHA-256 `3c18be8ae8fcdb1f8c740e8d0bf1c3e8775a5c0d1d11994d4360be1213c7ad40`.
4. The input window is `2024-12-31T23:57:02` through `2025-01-01T00:42:02` and the input-schema SHA-256 is `5c2f6f0f2351b15675fc223b36043729b1e7f8ab0bd08caa891593672daa65f1`.
5. First activated exceedance is `2025-01-01T00:45:02`, lead time `3` minutes, peak `9.43204345`, with `2` consecutive steps.
6. Gate `1` was eligible and independently reported persisted-result integrity `True`.

## API and persisted-integrity boundary

The Event Trace API exposes event, rule-linked prediction batch/run/model/input-window metadata, artifact and input-schema hashes, forecast snapshot, and gate identity/eligibility. It does **not** expose `persisted_result_hash`. The export therefore reports persisted run/batch hashes in a separate `persistedIntegrity` object queried from the isolated reproduction database; those hashes are independently revalidated by the execution gate.

## Side-effect boundary

The isolated Execute call created deltas `{"em_event_evaluation_run": 1, "em_event_evidence_link": 0, "em_event_handling_log": 0, "em_event_metric_snapshot": 0, "em_event_prediction_link": 1, "em_event_response_step": 4, "em_event_response_workflow": 1, "em_evidence_resource": 0, "em_monitoring_event": 1, "em_notification_delivery_log": 0, "em_notification_task": 0, "em_report_instance": 1}`. Evaluate/Execute evidence elsewhere shows Evaluate has zero formal deltas. After this artifact was written, the script restored every append-only formal table to its recorded baseline; the captured event is evidence, not seed data left in the database.

The complete machine-readable trace and selected 40-step engineering forecast series are in `artifacts/revision/manuscript/provenance-trace-final.json`.
