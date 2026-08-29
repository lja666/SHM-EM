# Phase 0.6 Scope Decision Summary

## Approved

- Correct alignment terminology and produce alignment audit v2.
- Add descriptive alignment diagnostics without changing numerical inputs.
- Persist compact policy/version and quality metadata in `input_snapshot_json`.
- Add C11 for the shared 16-step source window versus model-specific 12-16-step histories.
- Prove aligned inputs, predictions, engineering values, counts, and frozen artifacts are unchanged.

## Deferred or prohibited

- No fill-ratio, raw-gap, or source-age acceptance threshold.
- No new model, batch, Execute, or gate rejection rule.
- No Gate, Evaluate, Execute, Future State, model dispatch, conversion, weight, or preprocessor change.
- No core freeze, failure-path phase, or second heterogeneous configuration.

## Stop condition

After Phase 0.6 evidence is complete, work stops for GPT regression review. Core freeze remains unauthorized.
