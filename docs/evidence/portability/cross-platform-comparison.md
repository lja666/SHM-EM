# Cross-Platform Comparison

The frozen public Windows baseline is compared with the Docker/Linux execution without changing the model contract or applying a numerical tolerance.

| Check | Result |
|---|---|
| modelContractHashes | PASS |
| modelCount | PASS |
| targetCount | PASS |
| predictionSteps | PASS |
| resultCount | PASS |
| inputHashExact | PASS |
| normalizedOutputHashExact | FAIL |
| gateLogicalState | PASS |
| futureStateLogicalState | PASS |
| evaluateSemantics | PASS |
| executeProvenanceSemantics | PASS |

- Linux input hash: `d48674617d31b292e2f299af2f53ee8ae225b6db1df27911ee8f5073fdb21811`
- Linux normalized output hash: `828a440e5cc9429d05b16980ad2c3381cf0d6bb45f606ff9a72c02053c443aac`
- Future State `stateHash` is not compared bitwise because it includes environment-specific batch identity; logical eligibility and risk semantics are compared.
- No tolerance or relaxed hash contract was applied.
