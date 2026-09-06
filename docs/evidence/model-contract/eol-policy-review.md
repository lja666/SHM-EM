# Phase 0.6.1 EOL and Public Contract Review

- Overall raw-byte validation: `true`
- Active models: `6`
- Unique contract-sensitive assets: `25`
- Hash method: raw file bytes; no LF normalization is performed by the validator.
- Checkout simulation: a real Git clone with `core.autocrlf=true`.

| Path | Contract role | Current raw hash | autocrlf checkout raw hash | text / eol attribute |
| --- | --- | --- | --- | --- |
| `src/pit_pre/models/Pressure__predict/best_model_Pressure_optuna.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/Pressure__predict/best_params.json` | best_params | true | true | set / lf |
| `src/pit_pre/models/Pressure__predict/predict_Pressure_future_fixed_best_params_annotated.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/Pressure__predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/models/Strain__predict/best_model_Strain_optuna.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/Strain__predict/best_params.json` | best_params | true | true | set / lf |
| `src/pit_pre/models/Strain__predict/predict_Strain_future_fixed_best_params_annotated.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/Strain__predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/models/XD__predict/best_model_XD_optuna.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/XD__predict/best_params.json` | best_params | true | true | set / lf |
| `src/pit_pre/models/XD__predict/predict_XD_future_direct_comment_enhanced.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/XD__predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/models/YD__predict/best_model_YD_custom_m10_n3.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/YD__predict/predict_YD_future_direct.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/YD__predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/models/settlement_predict/best_model_settlement_optuna.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/settlement_predict/best_params.json` | best_params | true | true | set / lf |
| `src/pit_pre/models/settlement_predict/predict_settlement_future_fixed_best_params_annotated.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/settlement_predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/models/water__predict/best_model_water_optuna.pth` | model_artifact | true | true | unset / unspecified |
| `src/pit_pre/models/water__predict/best_params.json` | best_params | true | true | set / lf |
| `src/pit_pre/models/water__predict/predict_water_future_fixed_best_params_annotated.py` | inference_script | true | true | set / lf |
| `src/pit_pre/models/water__predict/preprocessor.joblib` | preprocessor | true | true | unset / unspecified |
| `src/pit_pre/requirements.lock.txt` | dependency_lock | true | true | set / lf |
| `src/pit_pre/runtime-manifest.json` | runtime_manifest | true | true | set / lf |

Binary `.pth` and `.joblib` artifacts are marked `-text`. Inference scripts, best-parameter JSON files, the runtime manifest, and the dependency lock use deterministic LF checkout bytes.
