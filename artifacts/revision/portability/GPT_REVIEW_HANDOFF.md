# Phase 2C GPT Review Handoff

## Decision requested

Review the Phase 2C exact cross-platform STOP. Do not infer a portability PASS and do not authorize a tolerance or frozen-core change without examining the attached numerical differences.

## Baseline

- Final Core Freeze v3: `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`
- Evidence HEAD: `f4f9ad25734a0b415e9a329c019d015d468909bb`
- Production business-core diff: **NONE**

## Result

- Docker builds and service readiness: PASS
- Linux-container logical reference workflow: COMPLETE
- Input and model-contract hashes: EXACT
- Normalized prediction output hash: **DIFFERS**
- Persisted rows matched: 4,960 / 4,960
- Maximum persisted absolute difference: `0.00285349`
- Maximum persisted relative difference: `0.3918730158730158730158730159`
- Tolerance applied: NO
- Native Ubuntu component PASS: NOT CLAIMED

## GPT decision point

Decide whether the recorded difference requires a narrowly scoped investigation under a new authorization, or whether the revision should retain Windows exact reproduction and report Docker/Linux only as partial portability evidence. Phase 2D remains on hold.
