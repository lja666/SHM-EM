# Project Future State Specification

## Purpose and authority

Project Future State is a deterministic, policy-versioned summary of one persisted prediction batch. This specification is derived from `ProjectFutureStateServiceImpl` at Final Core Freeze v3. It does not redefine or simplify the production algorithm.

The service combines three distinct facts:

1. **Observed risk**: the maximum severity and count of currently open observation-sourced events.
2. **Forecast risk**: rule assessment of engineering prediction series on a common batch timeline.
3. **Execution eligibility**: the independent prediction execution gate result and its blockers.

A Future State may be returned for diagnostic inspection when the gate is ineligible. Its `executionEligible` field controls whether downstream formal execution is permitted; computing a summary is not itself a formal event side effect.

## Inputs

- an existing project identifier;
- an optional successful prediction batch identifier, otherwise the successful batch resolved by the prediction service;
- an optional requested forecast horizon;
- execution mode (`OPERATIONAL`, `REPLAY`, or `REPRODUCTION`);
- an optional mode-specific reference time;
- one active policy row from `em_future_state_policy`;
- engineering prediction points for the resolved project and batch;
- enabled event-rule levels used as forecast thresholds;
- open observed-event severity counts and station names.

The effective horizon is the smaller of a positive request and the batch horizon. If no positive request is supplied, the batch horizon is used; 120 minutes is the fallback only when the batch has no positive horizon.

## Policy contract

The policy JSON must contain exactly five non-empty keys:

| Key | Supported values |
|---|---|
| `unitPolicy` | `exactMatch`, `normalizedExactMatch` |
| `overallRisk` | `maxObservedAndForecast`, `observedOnly`, `forecastOnly` |
| `featureGroup` | `targetType+featureCode`, `metricCode+featureCode` |
| `forecastRisk` | `maxRiskRank` |
| `thresholdSource` | `enabledEventRuleLevels` |

The canonical SHA-256 of these five values must equal `policy_hash`. Missing keys, extra keys, unsupported values, malformed JSON, and hash drift are rejected before aggregation.

## Common timeline and series eligibility

The prediction service is queried with project ID, batch ID, effective horizon, `includeObserved=false`, `valueMode=ENGINEERING`, and a 50,000-row inspection limit. Points without a value or without `conversionStatus=success` are excluded. Remaining points are ordered by future timestamp and feature code.

The batch's execution gate independently validates the complete model/feature/target set, persisted integrity, 40-step timeline, quality, and mode-specific freshness. Future State exposes the gate ID, eligibility, and blockers without replacing that gate.

## Feature assessment

Let a feature key be:

```text
targetType + ':' + featureCode
```

for the current policy. Points are grouped by this key and ordered by future step. For every threshold whose metric code and unit match the point:

1. evaluate the configured operator;
2. increment that rule-level streak when true, otherwise reset it to zero;
3. activate the threshold severity at the current step only when the streak reaches `max(1, minimumConsecutiveSteps)`;
4. retain the highest active severity for that point.

Supported operators are `>`, `>=`, `<`, `<=`, `abs_gt`, `abs_gte`, and inclusive `between`. Severity ordering is:

```text
unassessed (-1) < normal (0) < yellow (10) < orange (20) < red (30)
```

A feature with no applicable metric threshold is `unassessed`. A feature with applicable thresholds but no activated level is `normal`. The broader rule-validation boundary rejects incompatible engineering units before formal execution.

The recorded first exceedance is the time at which the required consecutive-step condition first becomes true, not the time of the first isolated threshold crossing.

## Target aggregation

Points are grouped by `targetType`. Each target state contains:

- distinct feature and assessed-feature counts;
- distinct warning (`rank >= 10`) and alarm (`rank >= 30`) feature counts;
- highest risk rank across its points;
- minimum and maximum predicted values;
- a governing point selected first by highest risk, then by greatest threshold distance;
- governing value, threshold, signed threshold distance, unit, and first activated exceedance.

For `<`/`<=`, threshold distance is `threshold - value`; for absolute operators it is `abs(value) - abs(threshold)`; for `between` it is the negated distance to the nearest bound; otherwise it is `value - threshold`.

## Station aggregation

Points with a station ID are grouped by station. Station risk is the maximum risk rank in the group. For every exceeding feature, one contributor is retained: the highest-risk row, with the earlier timestamp used on an equal-rank tie. Contributors are ordered by descending risk rank and then ascending exceedance time.

Station aggregation does not average or sum model outputs. It preserves the governing feature, metric, value, unit, threshold, operator, rule code, severity, and first activated exceedance.

## Project and timeline aggregation

Forecast project risk is the highest assessed forecast risk. Observed project risk is the highest severity among open observed events; their counts are summed. Overall project risk follows the policy:

- `maxObservedAndForecast`: maximum of observed and forecast ranks;
- `observedOnly`: observed rank;
- `forecastOnly`: forecast rank.

The project earliest-exceedance time is the minimum timestamp among points whose activated risk rank is greater than zero.

For each future step, timeline risk is the maximum point risk at that step and `exceedingFeatureCount` is the number of distinct feature keys with activated risk. Timeline rows are ordered by step.

## Assessed and unassessed targets

`assessedFeatureCount` counts distinct feature keys with at least one applicable threshold. `unassessedFeatureCount` is the number of distinct series feature keys not assessed by any applicable threshold. Unassessed features remain visible; they are not silently treated as normal.

## Deterministic state hash

The service calculates a canonical SHA-256 over:

- batch ID, effective horizon, and policy hash;
- ordered target summaries;
- ordered station summaries and contributors;
- ordered timeline states.

The current state hash intentionally does not include the observed-risk counters or the embedded execution-gate object. Those values remain explicit response fields with their own provenance and gate hash. Equivalent ordered forecast inputs and policy material produce the same state hash.

## Formal event boundary

Project Future State is read-only. Evaluate computes candidates without formal event, workflow, response-step, or prediction-link side effects. Execute independently rechecks the latest persisted gate state before creating formal records. An ineligible gate or a changed/corrupted batch therefore prevents the Future State from being used as authorization for formal execution.

## Verified boundaries

The test evidence covers:

- no applicable rule;
- strict versus inclusive exact-threshold behavior;
- one-step versus required consecutive-step activation;
- multiple target types and stations;
- severity ordering and earliest exceedance;
- policy hash drift rejection;
- deterministic state hashing.

Machine-readable results are exported to `artifacts/revision/manuscript/future-state-boundary-tests.json`.
