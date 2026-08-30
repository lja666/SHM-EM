# Phase 1A.1 Final Staged Change Inventory

- HEAD before Commit D: `dba31094604eee60320fdd1638854b8611f5ac56`
- Staged files: 21
- Complete: `true`

## Production Core

- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashService.java`
- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java`
- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionBatch.java`
- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionDisplay.java`
- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionExecutionGate.java`
- `src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionRun.java`
- `src/backend/src/main/resources/mapper/modules/engineering/PredictionExecutionGateMapper.xml`
- `src/pit_pre/pit_pre/result_writer.py`

## Database/Schema

- `sql/shm_em_database/00_SHM_EM_complete_schema.sql`
- `sql/shm_em_database/04_SHM_EM_persisted_prediction_integrity.sql`
- `sql/shm_em_database/README.md`

## Tests

- `src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashServiceTest.java`
- `src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImplTest.java`
- `src/pit_pre/tests/fixtures/persisted-integrity-fixture.json`
- `src/pit_pre/tests/test_persisted_integrity.py`

## Revision Tools

- `tools/revision/backfill_persisted_integrity.py`
- `tools/revision/build_final_change_inventory.py`
- `tools/revision/build_phase1a1_review_package.py`
- `tools/revision/persisted_integrity_reference.py`
- `tools/revision/run_failure_matrix.py`
- `tools/revision/verify_phase1a1_integrity.py`

## Evidence

- None

## Documentation/Other

- None

## Staged Stat

```text
 sql/shm_em_database/00_SHM_EM_complete_schema.sql  |  11 ++
 .../04_SHM_EM_persisted_prediction_integrity.sql   | 104 ++++++++++++
 sql/shm_em_database/README.md                      |   1 +
 .../PersistedPredictionIntegrityHashService.java   | 117 +++++++++++++
 .../impl/PredictionExecutionGateServiceImpl.java   |  51 ++++++
 .../engineering/domain/model/PredictionBatch.java  |   2 +
 .../domain/model/PredictionDisplay.java            |   6 +
 .../domain/model/PredictionExecutionGate.java      |   1 +
 .../engineering/domain/model/PredictionRun.java    |   2 +
 .../engineering/PredictionExecutionGateMapper.xml  |   5 +-
 ...ersistedPredictionIntegrityHashServiceTest.java | 106 ++++++++++++
 .../PredictionExecutionGateServiceImplTest.java    | 120 ++++++++++++++
 src/pit_pre/pit_pre/result_writer.py               | 122 +++++++++++++-
 .../fixtures/persisted-integrity-fixture.json      |  67 ++++++++
 src/pit_pre/tests/test_persisted_integrity.py      |  46 ++++++
 tools/revision/backfill_persisted_integrity.py     |  60 +++++++
 tools/revision/build_final_change_inventory.py     | 103 ++++++++++++
 tools/revision/build_phase1a1_review_package.py    | 125 ++++++++++++++
 tools/revision/persisted_integrity_reference.py    | 105 ++++++++++++
 tools/revision/run_failure_matrix.py               |  97 ++++++-----
 tools/revision/verify_phase1a1_integrity.py        | 184 +++++++++++++++++++++
 21 files changed, 1393 insertions(+), 42 deletions(-)
```
