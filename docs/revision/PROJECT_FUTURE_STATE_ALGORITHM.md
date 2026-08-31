# Project Future State Algorithm

## Algorithm 1: policy-bound forecast aggregation

```text
INPUT projectId, optional batchId, optional requestedHorizon,
      executionMode, optional referenceTime

1  require project(projectId)
2  policy <- active Future State policy for projectId
3  require policy JSON has exactly the five supported keys
4  require SHA256(canonical(policy JSON)) == policy.policyHash

5  batch <- resolve successful batch(projectId, batchId)
6  require batch.projectId == projectId and batch.status == success
7  horizon <- minPositive(requestedHorizon, batch.horizonMinutes)
8  gate <- inspectExecutionGate(batch.id, executionMode, referenceTime)

9  points <- engineeringPredictionSeries(
       projectId, batch.id, horizon, includeObserved=false, limit=50000)
10 points <- points where value != null and conversionStatus == success
11 sort points by timestamp, featureCode
12 require points is not empty

13 thresholds <- enabled rule levels for projectId
14 index thresholds by lower(metricCode)
15 assessedPoints <- empty list

16 for each feature group in points using policy.featureGroup:
17     sort group by step
18     streak[ruleId, levelCode] <- 0
19     for each point in group:
20         candidates <- thresholds[lower(point.metricCode)]
21         assessed <- candidates is not empty
22         risk <- UNASSESSED if not assessed else NORMAL
23         governingThreshold <- null
24         for each threshold in candidates:
25             if not unitsMatch(point.unit, threshold.unit, policy.unitPolicy):
26                 continue
27             streak[key] <- streak[key] + 1 if matches(point.value, threshold) else 0
28             assessed <- true
29             required <- max(1, threshold.minimumConsecutiveSteps or 1)
30             candidateRisk <- severity(threshold.levelCode, threshold.levelRank)
31             if streak[key] >= required and candidateRisk > risk:
32                 risk <- candidateRisk
33                 governingThreshold <- threshold
34         append (point, assessed, risk, governingThreshold)

35 forecastRisk <- maximum risk across assessedPoints
36 observedRisk, observedCount <- maximum and sum of open observed events
37 overallRisk <- policyMerge(observedRisk, forecastRisk)
38 earliest <- minimum timestamp where assessedPoint.risk > NORMAL

39 targets <- group assessedPoints by targetType
40 for each target:
41     count distinct features, assessed features, warnings, and alarms
42     targetRisk <- maximum risk
43     governing <- max by (risk rank, threshold distance)
44     targetFirstExceedance <- minimum activated exceedance timestamp

45 stations <- group assessedPoints with stationId by stationId
46 for each station:
47     stationRisk <- maximum risk
48     for each exceeding feature keep highest-risk row; on tie keep earlier row
49     order contributors by descending risk then ascending exceedance time

50 timeline <- group assessedPoints by future step
51 for each step:
52     timelineRisk <- maximum risk
53     exceedingFeatureCount <- distinct activated feature keys
54 order timeline by step

55 state <- project/batch/timeline/policy/gate fields plus observed, forecast,
            target, station, and timeline summaries
56 stateHash <- SHA256(canonical(batchId, horizon, policyHash,
                                 targets, stations, timeline))
57 return state
```

## Implementation correspondence

| Algorithm block | Production method |
|---|---|
| Lines 1-12 | `get`, `normalizeHorizon`, prediction-service query |
| Lines 13-34 | `assess`, `matches`, `unitsMatch`, `featureKey` |
| Lines 35-38 | `forecastRisk`, `observedRisk`, `overallRisk` |
| Lines 39-44 | `targets`, `thresholdDistance` |
| Lines 45-49 | `stations`, `contributor`, `earlier` |
| Lines 50-53 | `timeline` |
| Lines 54-57 | `stateHash`, canonical hash service |

## Boundary interpretation

- Exact equality does not activate `>` or `<`; it activates `>=` or `<=`.
- `between` includes both bounds.
- Consecutive streaks are independent for every feature and rule-level pair.
- A single nonmatching step resets that streak.
- Severity, not numeric forecast magnitude, governs target/station/project risk ordering.
- Earliest exceedance uses the timestamp at which the consecutive condition is satisfied.
- Gate eligibility is reported but does not alter the deterministic forecast summary; Execute remains the side-effect boundary.
