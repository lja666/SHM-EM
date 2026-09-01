# Local Release Validation

Validation date: 2026-09-01. Release candidate: SHM-EM 1.0.1.

Release 1.0.1 preserves the production core recorded at Final Core Freeze v3
and synchronizes the revision evidence, documentation, packaging, and
publication metadata. The public-reference and portability results below are
the retained evidence for that unchanged core; release-candidate component and
packaging checks were rerun on 2026-09-01.

## Build and Test Results

```text
Backend tests: 55 passed, 0 failed, 0 errors, 0 skipped
Backend package: passed
Frontend TypeScript and production build: passed
PIT_PRE contract/alignment/integrity tests: 13 passed
Validation matrix: 15/15 passed (P00 + F01-F12 + I01-I02)
Sanitized package preflight: passed (382 entries, 25 test entries)
Restricted/private files in package: 0
Production-core diff from Final Core Freeze v3: none
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
    "evaluateAuditRunPersisted": true,
    "evaluateFormalBusinessSideEffects": false,
    "reproductionExecute": true,
    "eventTrace": true,
    "responseWorkflow": true
  }
}
```

The public sample exercises the documented software path. Windows PowerShell is
the exact-output reference. The exercised Docker/Linux path completed the same
logical six-model workflow and matched the input hash and all 4,960 row keys,
but its normalized output hash differed; no numerical tolerance was applied.
Native Ubuntu-host execution was not separately captured.
