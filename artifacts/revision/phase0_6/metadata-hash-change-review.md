# Phase 0.6 Metadata Hash Change Review

## Expected metadata change

`input_snapshot_json` gains a descriptive alignment policy version and compact quality diagnostics. An external hash of that JSON is therefore expected to change (`EXPECTED_METADATA_HASH_CHANGE`).

| Model | Baseline alignment payload SHA-256 | Instrumented payload SHA-256 | Classification |
| --- | --- | --- | --- |
| Pressure | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `4642d7b5fe0afa913396d0004bab99f75f4bdf5fca88b36014e99f0890ee82d7` | EXPECTED_METADATA_HASH_CHANGE |
| Strain | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `4642d7b5fe0afa913396d0004bab99f75f4bdf5fca88b36014e99f0890ee82d7` | EXPECTED_METADATA_HASH_CHANGE |
| XD | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `e2ef33fce848521c196301f93b156b640b37a6a5fb0c625d4e8df36bb637d8b1` | EXPECTED_METADATA_HASH_CHANGE |
| YD | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `1f9adbc799d8ed6ec90436e40ffbd2b4076dbfb6d1a3b0fa7408f6f2d45c7ec5` | EXPECTED_METADATA_HASH_CHANGE |
| settlement | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `35c8ba31c539096f2b977313dc5e039ab9ac55c259fc22901ddbef41cd0fb7c0` | EXPECTED_METADATA_HASH_CHANGE |
| water | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | `4642d7b5fe0afa913396d0004bab99f75f4bdf5fca88b36014e99f0890ee82d7` | EXPECTED_METADATA_HASH_CHANGE |

## Unchanged numerical hashes

- Batch input matrix hash: unchanged when calculated over the numerical wide table.
- Per-model result hash: unchanged because it remains calculated from point, step, and predicted value.
- Batch output hash: unchanged because constituent result hashes are unchanged.
- Model artifact, preprocessor, inference-script, runtime-manifest, environment, bundle, and input-schema hashes: unchanged.

## Pre-existing Windows checkout normalization

The public contract stores SHA-256 values for LF-normalized inference scripts. This Windows worktree uses `core.autocrlf=true`, so checked-out script bytes are CRLF and strict byte-hash loading is blocked before Phase 0.6 changes. The regression records declared and actual hashes separately; LF-normalized content matches the declared contract. No model contract, script, weight, or preprocessor was modified in this phase.

No diagnostic value participates in model input construction, engineering conversion, event eligibility, or gate decisions.
