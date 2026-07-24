# Local Release Validation

Validation date: 2026-07-24. Release candidate: SHM-EM 1.0.0.

This record was produced from the packaged release archive and a newly rebuilt
isolated database using only the four public SQL files. Six public model bundles
generated a synchronized batch before Evaluate and controlled REPRODUCTION
Execute were called.

## Build and Test Results

```text
Backend tests: 41 passed, 0 failed, 0 errors, 0 skipped
Backend package: passed
Frontend TypeScript and production build: passed
Frontend production dependency audit: 0 vulnerabilities
PIT_PRE tests: 4 passed
Six-model inference: passed (4,960 synchronized results)
Native PowerShell orchestration: passed
```

## Reproduction Result

```json
{
  "projectCode": "SHM_EM_PUBLIC_SAMPLE",
  "predictionBatchId": 5,
  "modelCount": 6,
  "targetCount": 124,
  "predictionSteps": 40,
  "resultCount": 4960,
  "conversionFailures": 0,
  "integrityFailures": 0,
  "eventLinkCount": 1,
  "predictionInputHash": "d48674617d31b292e2f299af2f53ee8ae225b6db1df27911ee8f5073fdb21811",
  "expectedPredictionInputHash": "d48674617d31b292e2f299af2f53ee8ae225b6db1df27911ee8f5073fdb21811",
  "predictionOutputHash": "e1d1a5a739fcc7637fc707757c3dace02d6a9e13c2cc0776910f850e2fa29475",
  "expectedPredictionOutputHash": "e1d1a5a739fcc7637fc707757c3dace02d6a9e13c2cc0776910f850e2fa29475",
  "checks": {
    "projectApi": true,
    "eventApi": true,
    "dataset": true,
    "modelSet": true,
    "resultCompleteness": true,
    "engineeringConversion": true,
    "referentialIntegrity": true,
    "predictionInputHash": true,
    "predictionOutputHash": true,
    "replayGate": true,
    "futureState": true,
    "evaluateCandidate": true,
    "evaluateOperationalSideEffectFree": true,
    "reproductionExecute": true,
    "eventTrace": true,
    "responseWorkflow": true
  }
}
```

The public sample is sufficient for complete software-path validation. Windows
PowerShell is the declared and validated reproduction environment for this
release.
