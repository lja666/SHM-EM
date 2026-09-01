# Model Dimension Reconciliation

## Decision

**PASS - Case A.** The frozen preprocessors receive 114 aligned feature columns for YD, XD, Strain, Pressure, and Water, and 164 for Settlement. The previously reported values 42/42/14/14/2/50 were database model-feature mapping counts; 42/42/14/14/2 are also output widths, while 50 is the Settlement-owned mapping count. They are not complete model input widths.

The common aligned input is a `16 x 164` numerical feature matrix; `time` and `time1` are excluded from that count. Each model selects the ordered columns declared by its frozen preprocessor before scaling. The Transformer-CNN receives three tensors rather than one unsplit tensor: a response branch, a two-channel water/environment branch, and a contextual transformed-feature branch.

No model inference, training, or production-core change was performed for this reconciliation.

## Reconciled dimensions

| Model | History rows | Common/wide columns | Columns passed to preprocessor | Tensor feature width entering model | Internal branch width (response/environment/context) | Output targets | Evidence |
|---|---:|---:|---:|---|---|---:|---|
| YD | 16 | 164 | 114 | response `1x10x42`; environment `1x6x2`; contextual `1x10x112` | 42/2/112 | 42 | Phase 0.6 `16x114`; `src/pit_pre/models/YD__predict/preprocessor.joblib`; `src/pit_pre/models/YD__predict/predict_YD_future_direct.py` |
| XD | 12 | 164 | 114 | response `1x10x42`; environment `1x2x2`; contextual `1x10x112` | 42/2/112 | 42 | Phase 0.6 `12x114`; `src/pit_pre/models/XD__predict/preprocessor.joblib`; `src/pit_pre/models/XD__predict/predict_XD_future_direct_comment_enhanced.py` |
| Strain | 13 | 164 | 114 | response `1x10x14`; environment `1x3x2`; contextual `1x10x112` | 14/2/112 | 14 | Phase 0.6 `13x114`; `src/pit_pre/models/Strain__predict/preprocessor.joblib`; `src/pit_pre/models/Strain__predict/predict_Strain_future_fixed_best_params_annotated.py` |
| Pressure | 13 | 164 | 114 | response `1x10x14`; environment `1x2x2`; contextual `1x10x112` | 14/2/112 | 14 | Phase 0.6 `13x114`; `src/pit_pre/models/Pressure__predict/preprocessor.joblib`; `src/pit_pre/models/Pressure__predict/predict_Pressure_future_fixed_best_params_annotated.py` |
| Water | 13 | 164 | 114 | response `1x10x2`; environment `1x3x2`; contextual `1x10x112` | 2/2/112 | 2 | Phase 0.6 `13x114`; `src/pit_pre/models/water__predict/preprocessor.joblib`; `src/pit_pre/models/water__predict/predict_water_future_fixed_best_params_annotated.py` |
| Settlement | 12 | 164 | 164 | response `1x10x10`; environment `1x2x2`; contextual `1x10x162` | 10/2/162 | 10 | Phase 0.6 `12x164`; `src/pit_pre/models/settlement_predict/preprocessor.joblib`; `src/pit_pre/models/settlement_predict/predict_settlement_future_fixed_best_params_annotated.py` |

## Evidence chain

1. `WideTableBuilder` creates the common 164-feature aligned table; the Phase 0.6 capture removes `time` and `time1` before recording its `16 x 164` matrix.
2. `CachedModelRunner` reconstructs ordered feature groups, requires exact equality with each frozen preprocessor's `input_columns`, and invokes the model with `x_response`, `x_env`, and `x_cat`. The inference scripts select their final `m + lag` rows before scaling. Pressure declares a conservative 13-row runner window but consumes its final 12 rows (`m=10`, `lag=2`); the other five declared windows equal `m + lag`.
3. Each frozen inference script slices those three tensors from the scaled 114- or 164-column matrix. Weight-derived `responseDimension`, `environmentDimension`, and `contextualInputDimension` agree with the slice widths.
4. The Phase 0.6 per-model matrices are exactly `history rows x preprocessor input columns`: Pressure `13 x 114`, Strain `13 x 114`, XD `12 x 114`, YD `16 x 114`, Settlement `12 x 164`, and Water `13 x 114`.
5. The machine-readable companion records source paths, SHA-256 values, source anchors, tensor shapes, and all equality checks.

## Contract terminology correction

Public contract exports now distinguish `modelFeatureMappingCount` from `alignedInputFeatureCount` and `outputTargetCount`. The model-feature mapping count is retained because it describes database ownership and target binding, but it must not be labelled as the complete inference input width.
