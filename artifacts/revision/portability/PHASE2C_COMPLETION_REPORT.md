# Phase 2C Completion Report

## 1. Baseline

- Final Core Freeze v3: `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`
- Evidence preparation HEAD: `f4f9ad25734a0b415e9a329c019d015d468909bb`

## 2. Ubuntu Validation

- Backend: CI matrix configured; native Ubuntu result not captured.
- PIT_PRE: CI matrix configured; native Ubuntu result not captured.
- Frontend: CI matrix configured; native Ubuntu result not captured.

## 3. Docker/Compose

- Images: backend, PIT_PRE, and frontend built successfully.
- Services: MySQL, backend, and frontend healthy; PIT_PRE one-shot exited 0.
- Bounded secret scan: PASS.

## 4. Linux Reference Reproduction

- Models: 6
- Targets: 124
- Steps: 40
- Prediction rows: 4960
- Integrity/Gate/Future State/Evaluate/Execute/provenance: logically complete.

## 5. Cross-Platform Comparison

- Input hash: exact.
- Normalized output hash: differs.
- Persisted row coverage: 4,960 / 4,960.
- Maximum persisted absolute difference: `0.00285349`.
- Maximum persisted relative difference: `0.3918730158730158730158730159`.
- Tolerance: not applied.

## 6. Security Documentation

- Research-release scope and recommended deployment controls documented.
- Persisted SHA-256 is explicitly not presented as tamper-proof against a privileged database attacker.

## 7. Storage Adapter Boundary

- Logical observation contract, approved adapters, and MySQL implementation are separated.
- No alternative database validation is claimed.
- The 50,000-row Gate cap is identified as an application boundary.

## 8. Reviewer Map

- R1-11, R3-1, and R3-2: documentation complete.
- R1-12 and R3-4: partially supported.
- R2-3 and R3-3: corrected missing-data wording retained.

## 9. Production-Core Diff

- **NONE** relative to Final Core Freeze v3.

## 10. STOP

`STOP_EXACT_CROSS_PLATFORM_REPRODUCTION`. Await GPT review before any numerical-tolerance, production-core, or Phase 2D work.
