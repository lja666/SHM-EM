# SHM-EM Phase 0.5 Runtime Literal Semantic Review

- Source commit: `1d2ab45e516ef4167c6c4c4265da5b533b2eab78`
- Classified literals: `27`
- Conclusion: No literal is classified as unconditional project-specific event-workflow coupling. The material boundaries are the approved observation-table set, packaged model adapters, and target-specific engineering conversion adapters.

## Category totals

| Category | Count |
| --- | --- |
| HARMLESS_DEFAULT | 2 |
| UI_DISPLAY_ONLY | 3 |
| SECURITY_WHITELIST | 4 |
| ENGINEERING_DOMAIN_ADAPTER | 5 |
| MODEL_ADAPTER_CONSTRAINT | 13 |
| GENUINE_ARCHITECTURAL_COUPLING | 0 |

## Itemized review

| ID | File | Line | Literal | Category | Core coupling | Code change | Claim change | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L001 | src/frontend/src/views/projects/ProjectWorkspace.vue | 301 | settlement | UI_DISPLAY_ONLY | NO | NO | NO | Retain as presentation behavior; it is not evidence of workflow coupling. |
| L002 | src/frontend/src/views/projects/ProjectWorkspace.vue | 303 | settlement | UI_DISPLAY_ONLY | NO | NO | NO | Retain as presentation behavior; it is not evidence of workflow coupling. |
| L003 | src/frontend/src/views/workflow/LowFrequencyBrowse.vue | 1003 | Strain | UI_DISPLAY_ONLY | NO | NO | NO | Retain as presentation behavior; it is not evidence of workflow coupling. |
| L004 | src/pit_pre/pit_pre/cached_model_runner.py | 44 | settlement | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L005 | src/pit_pre/pit_pre/cached_model_runner.py | 65 | water | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L006 | src/pit_pre/pit_pre/cached_model_runner.py | 203 | YD | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L007 | src/pit_pre/pit_pre/cached_model_runner.py | 205 | XD | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L008 | src/pit_pre/pit_pre/cached_model_runner.py | 207 | Strain | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L009 | src/pit_pre/pit_pre/cached_model_runner.py | 209 | Pressure | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L010 | src/pit_pre/pit_pre/cached_model_runner.py | 211 | water | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | CONDITIONAL | YES | Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under the existing PIT_PRE adapter contract unless a later approved change generalizes the runner. |
| L011 | src/pit_pre/pit_pre/daemon.py | 19 | SHM_EM_PUBLIC_SAMPLE | HARMLESS_DEFAULT | NO | NO | NO | Keep unless a later reuse experiment proves that the override path fails. |
| L012 | src/pit_pre/pit_pre/features.py | 19 | em_obs_displacement | SECURITY_WHITELIST | CONDITIONAL | CONDITIONAL | YES | Safe for existing approved tables. A new physical table currently requires a whitelist edit; the registration-only claim must state this boundary unless validation becomes registry-backed. |
| L013 | src/pit_pre/pit_pre/features.py | 20 | em_obs_earth_pressure | SECURITY_WHITELIST | CONDITIONAL | CONDITIONAL | YES | Safe for existing approved tables. A new physical table currently requires a whitelist edit; the registration-only claim must state this boundary unless validation becomes registry-backed. |
| L014 | src/pit_pre/pit_pre/features.py | 21 | em_obs_pressure_water_level | SECURITY_WHITELIST | CONDITIONAL | CONDITIONAL | YES | Safe for existing approved tables. A new physical table currently requires a whitelist edit; the registration-only claim must state this boundary unless validation becomes registry-backed. |
| L015 | src/pit_pre/pit_pre/features.py | 22 | em_obs_static_level | SECURITY_WHITELIST | CONDITIONAL | CONDITIONAL | YES | Safe for existing approved tables. A new physical table currently requires a whitelist edit; the registration-only claim must state this boundary unless validation becomes registry-backed. |
| L016 | src/pit_pre/pit_pre/main.py | 25 | SHM_EM_PUBLIC_SAMPLE | HARMLESS_DEFAULT | NO | NO | NO | Keep unless a later reuse experiment proves that the override path fails. |
| L017 | src/pit_pre/pit_pre/result_writer.py | 17 | YD | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L018 | src/pit_pre/pit_pre/result_writer.py | 18 | XD | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L019 | src/pit_pre/pit_pre/result_writer.py | 19 | Strain | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L020 | src/pit_pre/pit_pre/result_writer.py | 20 | Pressure | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L021 | src/pit_pre/pit_pre/result_writer.py | 21 | water | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L022 | src/pit_pre/pit_pre/result_writer.py | 22 | settlement | MODEL_ADAPTER_CONSTRAINT | CONDITIONAL | NO | YES | A single *_pred fallback exists, but compatibility still depends on the packaged output shape; describe new models as compatible model bundles. |
| L023 | src/pit_pre/pit_pre/result_writer.py | 242 | YD | ENGINEERING_DOMAIN_ADAPTER | CONDITIONAL | CONDITIONAL | YES | Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs a validated conversion adapter and prerequisites. |
| L024 | src/pit_pre/pit_pre/result_writer.py | 264 | XD | ENGINEERING_DOMAIN_ADAPTER | CONDITIONAL | CONDITIONAL | YES | Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs a validated conversion adapter and prerequisites. |
| L025 | src/pit_pre/pit_pre/result_writer.py | 283 | water | ENGINEERING_DOMAIN_ADAPTER | CONDITIONAL | CONDITIONAL | YES | Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs a validated conversion adapter and prerequisites. |
| L026 | src/pit_pre/pit_pre/result_writer.py | 301 | settlement | ENGINEERING_DOMAIN_ADAPTER | CONDITIONAL | CONDITIONAL | YES | Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs a validated conversion adapter and prerequisites. |
| L027 | src/pit_pre/pit_pre/result_writer.py | 316 | settlement | ENGINEERING_DOMAIN_ADAPTER | CONDITIONAL | CONDITIONAL | YES | Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs a validated conversion adapter and prerequisites. |

## Interpretation boundary

Literal presence alone is not proof of architectural coupling. The classifications above distinguish harmless defaults, display behavior, identifier security controls, engineering-domain adapters, and packaged-model adapter constraints.
