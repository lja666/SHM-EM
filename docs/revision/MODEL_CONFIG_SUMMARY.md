# SHM-EM Six-Model Configuration Summary

Final Core Freeze v3: `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`.

This file is generated from the database-derived contract, immutable bundle metadata, actual inference scripts, parameter files, runtime manifest, and model weight shapes. Parameters that cannot be independently recovered are not guessed.

| Model | History | Inputs | Targets | d_model | Heads | FF dim | CNN channels/kernel | Dropout | Params source | Hashes |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| Pressure | 13 | 14 | 14 | 64 | 1 | 64 | 24/3 | 0.034925 | best_params_file | PASS |
| settlement | 12 | 50 | 10 | 96 | 8 | 256 | 48/5 | 0.222957 | best_params_file | PASS |
| Strain | 13 | 14 | 14 | 96 | 4 | 64 | 48/5 | 0.076803 | best_params_file | PASS |
| water | 13 | 2 | 2 | 96 | 1 | 128 | 16/3 | 0.001679 | best_params_file | PASS |
| XD | 12 | 42 | 42 | 64 | 8 | 128 | 64/7 | 0.230030 | best_params_file | PASS |
| YD | 16 | 42 | 42 | 128 | 4 | 64 | 32/3 | 0.055798 | script_fallback | PASS |

## Shared deployed architecture

Every bundle uses one custom Transformer encoder layer followed by response, environment, and transformed-feature 1-D convolution branches and one final convolution. `d_model` is the attention input dimension. The deployed rolling pipeline persists 40 future steps at 3-minute intervals; the model-internal direct-output chunk is `n=3` and the historical response window is `m=10` where encoded by the script/parameter contract.

The number of attention heads and dropout cannot be recovered uniquely from tensor shapes. They are therefore taken only from the checked best-parameter file, or from the inference script's explicit fallback contract for YD. YD is marked `script_fallback`; it has no separate best-parameter artifact.

## Reproducibility boundary

The current bundles are CPU-executed point-forecast models. They do not emit calibrated predictive intervals or probabilistic exceedance. The execution gate validates software/data integrity and eligibility; it does not convert a point forecast into a statistical confidence guarantee.

The full hashes, paths, tensor-derived dimensions, and parameter provenance are in `artifacts/revision/manuscript/model-config-summary.json`.
