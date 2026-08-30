# SHM-EM Public Database Contract

This directory contains a de-identified minimum-window research sample. It is
large enough to execute every published prediction model, while excluding the
complete monitoring history, object metadata identifiers, site location, and
historical operational records. The two empty acceleration table definitions
retain the authorized schema suffixes `1426000125` and `1426000126`; their
instrument, gateway, module, and location metadata are de-identified.

| File | Public purpose |
|---|---|
| `00_SHM_EM_complete_schema.sql` | Creates the complete `em_*` database schema. |
| `01_SHM_EM_conversion_operators.sql` | Registers public engineering-conversion formulas without case parameters. |
| `02_SHM_EM_public_sample.sql` | Loads the de-identified 16-step model-input window and required contracts. |
| `03_SHM_EM_public_validation.sql` | Verifies the public sample boundary and expected record counts. |
| `04_SHM_EM_persisted_prediction_integrity.sql` | Migrates existing databases to the independent persisted-result integrity contract; legacy rows remain fail-closed until authorized backfill. |

The schema preserves four type-specific low-frequency observation tables and
the two explicitly retained acceleration sensor-table definitions. Runtime
APIs resolve physical storage through `em_observation_table_registry`.

## Restricted Case Package

The real research case is maintained outside this repository. An authorized
case package must provide three files:

1. observation, object, model-contract, rule, and workflow records;
2. calibration parameters, reference bindings, and converted case values;
3. case-specific validation queries and expected results.

Pass those files explicitly to `scripts/reproduce-local.ps1`. The script
rejects restricted files placed inside the public repository.

## Public Verification

Run `scripts/reproduce-local.ps1` without restricted-data arguments. The
default workflow initializes the public sample, runs all six models, verifies
4,960 forecast values, exercises prediction Evaluate/Execute, and validates
the response/evidence trace.
