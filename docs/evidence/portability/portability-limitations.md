# Phase 2C Portability Limitations

The Docker/Linux reference run completed the six-model, 124-target, 40-step workflow and persisted 4,960 results. Input and model-contract hashes matched, persisted integrity and the execution Gate passed, Project Future State succeeded, Evaluate had no formal side effect, and Execute created the expected event/response/provenance chain.

Exact cross-platform prediction reproduction did **not** pass. The frozen Windows normalized output hash is `e1d1a5a739fcc7637fc707757c3dace02d6a9e13c2cc0776910f850e2fa29475`, whereas the Docker/Linux hash is `828a440e5cc9429d05b16980ad2c3381cf0d6bb45f606ff9a72c02053c443aac`. All 4,960 persisted rows matched by target and step, with no missing or additional rows; the maximum persisted absolute numeric difference was `0.00285349` and the maximum relative difference was `0.3918730158730158730158730159`. No tolerance was applied and the deterministic hash contract was not changed.

Native Ubuntu component validation is also not claimed: the available WSL Ubuntu installation has unresolved host package-manager dependencies, and no successful GitHub Actions run was captured in this phase. The CI matrix is configured for Ubuntu, but configuration alone is not evidence.

Accordingly, native Windows remains the validated exact-reproduction environment. The container path is reported as partial portability evidence and a diagnostic reproduction path, not as exact Linux equivalence.
