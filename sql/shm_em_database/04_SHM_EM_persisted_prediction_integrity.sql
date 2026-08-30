-- Phase 1A.1: independent integrity metadata for decision-facing persisted forecasts.
-- Existing result_hash/output_hash columns retain their original reproducibility semantics.

SET @schema_name = DATABASE();

SET @ddl = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@schema_name AND table_name='em_prediction_run'
     AND column_name='persisted_result_hash')=0,
  'ALTER TABLE em_prediction_run ADD COLUMN persisted_result_hash varchar(128) NULL AFTER result_hash',
  'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@schema_name AND table_name='em_prediction_run'
     AND column_name='persisted_result_hash_version')=0,
  'ALTER TABLE em_prediction_run ADD COLUMN persisted_result_hash_version varchar(64) NULL AFTER persisted_result_hash',
  'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@schema_name AND table_name='em_prediction_batch'
     AND column_name='persisted_output_hash')=0,
  'ALTER TABLE em_prediction_batch ADD COLUMN persisted_output_hash varchar(128) NULL AFTER output_hash',
  'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@schema_name AND table_name='em_prediction_batch'
     AND column_name='persisted_output_hash_version')=0,
  'ALTER TABLE em_prediction_batch ADD COLUMN persisted_output_hash_version varchar(64) NULL AFTER persisted_output_hash',
  'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=@schema_name AND table_name='em_prediction_execution_gate'
     AND column_name='result_integrity_valid')=0,
  'ALTER TABLE em_prediction_execution_gate ADD COLUMN result_integrity_valid tinyint NOT NULL DEFAULT 0 AFTER freshness_valid',
  'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

DROP VIEW IF EXISTS em_prediction_display;
CREATE VIEW em_prediction_display AS
SELECT r.id,
       r.project_id,
       r.batch_id,
       b.batch_code,
       r.run_id,
       r.model_id,
       m.model_code,
       m.model_version,
       r.target_type,
       r.feature_code,
       COALESCE(f.feature_label, f.feature_name, r.feature_name, r.feature_code) AS feature_label,
       r.station_id,
       s.station_name,
       r.instrument_id,
       i.instrument_code,
       r.metric_code,
       r.engineering_metric_code,
       r.step,
       r.horizon_minutes,
       COALESCE(r.base_time, r.predicted_at) AS base_time,
       COALESCE(r.future_time, r.prediction_time) AS future_time,
       r.base_time AS persisted_base_time,
       r.future_time AS persisted_future_time,
       COALESCE(r.engineering_value, r.raw_predicted_value, r.predicted_value) AS predicted_value,
       COALESCE(r.engineering_unit, r.raw_predicted_unit, r.predicted_unit) AS predicted_unit,
       r.predicted_value AS stored_predicted_value,
       r.predicted_unit AS stored_predicted_unit,
       r.raw_predicted_value,
       r.raw_predicted_unit,
       r.engineering_value,
       r.engineering_unit,
       COALESCE(r.engineering_lower_bound, r.lower_bound) AS lower_bound,
       COALESCE(r.engineering_upper_bound, r.upper_bound) AS upper_bound,
       r.lower_bound AS raw_lower_bound,
       r.upper_bound AS raw_upper_bound,
       r.engineering_lower_bound,
       r.engineering_upper_bound,
       r.conversion_operator_code,
       r.conversion_version,
       r.conversion_status,
       r.conversion_remark,
       r.confidence,
       r.quality_flag,
       r.source_record_key,
       r.created_at
FROM em_prediction_result r
LEFT JOIN em_prediction_batch b ON b.id = r.batch_id
LEFT JOIN em_prediction_model m ON m.id = r.model_id
LEFT JOIN em_prediction_feature_mapping f
       ON f.project_id = r.project_id
      AND f.feature_code = r.feature_code
      AND f.enabled = 1
LEFT JOIN em_station s ON s.id = r.station_id
LEFT JOIN em_instrument i ON i.id = r.instrument_id;

-- Legacy successful batches intentionally remain NULL and therefore fail closed until
-- an authorized backfill computes hashes from their current persisted result rows.
