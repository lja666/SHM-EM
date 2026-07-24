-- Public sample validation. These queries disclose only the documented
-- de-identified sample contract and contain no private case values.

SET NAMES utf8mb4;

SELECT 'project_code_expected_SHM_EM_PUBLIC_SAMPLE' AS check_item, COUNT(*) AS value
FROM em_project
WHERE project_code = 'SHM_EM_PUBLIC_SAMPLE'
  AND longitude IS NULL
  AND latitude IS NULL;

SELECT 'dataset_manifest_expected_1' AS check_item, COUNT(*) AS value
FROM em_dataset_manifest
WHERE dataset_code = 'shm_em_public_sample_v1'
  AND reproducibility_level = 'public_deidentified_minimum_window';

SELECT 'monitoring_point_count_expected_9' AS check_item,
       CAST(JSON_UNQUOTE(JSON_EXTRACT(spatial_context_json, '$.monitoringPointCount')) AS UNSIGNED) AS value
FROM em_project WHERE id = 1;
SELECT 'station_record_count_expected_73' AS check_item, COUNT(*) AS value FROM em_station;
SELECT 'sensor_record_count_expected_74' AS check_item, COUNT(*) AS value FROM em_instrument;
SELECT 'acquisition_module_count_expected_17' AS check_item, COUNT(DISTINCT module_no) AS value
FROM em_instrument WHERE module_no IS NOT NULL;
SELECT 'dtu_count_expected_6' AS check_item, COUNT(DISTINCT dtu_code) AS value
FROM em_instrument WHERE dtu_code IS NOT NULL;
SELECT 'model_count_expected_6' AS check_item, COUNT(*) AS value
FROM em_prediction_model WHERE status = 'active';
SELECT 'feature_count_expected_164' AS check_item, COUNT(*) AS value
FROM em_prediction_feature_mapping WHERE enabled = 1;
SELECT 'prediction_target_count_expected_124' AS check_item, COUNT(*) AS value
FROM em_prediction_feature_mapping WHERE enabled = 1 AND prediction_target = 1;
SELECT 'maximum_history_steps_expected_16' AS check_item, MAX(required_history_rows) AS value
FROM em_prediction_model WHERE status = 'active';

SELECT 'public_observation_rows_expected_2464' AS check_item,
       (SELECT COUNT(*) FROM em_obs_displacement)
     + (SELECT COUNT(*) FROM em_obs_earth_pressure)
     + (SELECT COUNT(*) FROM em_obs_pressure_water_level)
     + (SELECT COUNT(*) FROM em_obs_static_level) AS value;

SELECT 'displacement_rows_expected_1344' AS check_item, COUNT(*) AS value FROM em_obs_displacement;
SELECT 'earth_pressure_rows_expected_448' AS check_item, COUNT(*) AS value FROM em_obs_earth_pressure;
SELECT 'water_level_rows_expected_32' AS check_item, COUNT(*) AS value FROM em_obs_pressure_water_level;
SELECT 'static_level_rows_expected_640' AS check_item, COUNT(*) AS value FROM em_obs_static_level;

SELECT 'mapped_features_without_source_rows_expected_0' AS check_item, COUNT(*) AS value
FROM em_prediction_feature_mapping f
JOIN em_observation_table_registry r ON r.registry_code = f.source_registry_code
WHERE f.enabled = 1
  AND NOT (
    (r.physical_table_name = 'em_obs_displacement' AND EXISTS (
      SELECT 1 FROM em_obs_displacement o
      WHERE o.project_id = f.project_id AND o.metric_code = f.source_metric_code
        AND (f.station_id IS NULL OR o.station_id = f.station_id)
        AND (f.instrument_id IS NULL OR o.instrument_id = f.instrument_id)
    )) OR
    (r.physical_table_name = 'em_obs_earth_pressure' AND EXISTS (
      SELECT 1 FROM em_obs_earth_pressure o
      WHERE o.project_id = f.project_id AND o.metric_code = f.source_metric_code
        AND (f.station_id IS NULL OR o.station_id = f.station_id)
        AND (f.instrument_id IS NULL OR o.instrument_id = f.instrument_id)
    )) OR
    (r.physical_table_name = 'em_obs_pressure_water_level' AND EXISTS (
      SELECT 1 FROM em_obs_pressure_water_level o
      WHERE o.project_id = f.project_id AND o.metric_code = f.source_metric_code
        AND (f.station_id IS NULL OR o.station_id = f.station_id)
        AND (f.instrument_id IS NULL OR o.instrument_id = f.instrument_id)
    )) OR
    (r.physical_table_name = 'em_obs_static_level' AND EXISTS (
      SELECT 1 FROM em_obs_static_level o
      WHERE o.project_id = f.project_id AND o.metric_code = f.source_metric_code
        AND (f.station_id IS NULL OR o.station_id = f.station_id)
        AND (f.instrument_id IS NULL OR o.instrument_id = f.instrument_id)
    ))
  );

SELECT 'acceleration_samples_expected_0' AS check_item,
       (SELECT COUNT(*) FROM em_accel_s_1426000125)
     + (SELECT COUNT(*) FROM em_accel_s_1426000126) AS value;

SELECT 'preloaded_operational_records_expected_0' AS check_item,
       (SELECT COUNT(*) FROM em_monitoring_event)
     + (SELECT COUNT(*) FROM em_event_response_workflow)
     + (SELECT COUNT(*) FROM em_notification_task)
     + (SELECT COUNT(*) FROM em_report_instance)
     + (SELECT COUNT(*) FROM em_evidence_resource) AS value;

SELECT 'non_anonymized_object_codes_expected_0' AS check_item,
       (SELECT COUNT(*) FROM em_station WHERE station_code NOT LIKE 'STATION-RECORD-%')
     + (SELECT COUNT(*) FROM em_instrument WHERE instrument_code NOT LIKE 'DEVICE-%')
     + (SELECT COUNT(*) FROM em_instrument WHERE dtu_code IS NOT NULL AND dtu_code NOT LIKE 'GATEWAY-%')
     + (SELECT COUNT(*) FROM em_instrument WHERE module_no IS NOT NULL AND module_no NOT LIKE 'MODULE-%') AS value;

SELECT 'incomplete_model_artifact_contract_expected_0' AS check_item, COUNT(*) AS value
FROM em_prediction_model
WHERE status = 'active'
  AND (artifact_hash IS NULL OR preprocessor_hash IS NULL OR inference_script_hash IS NULL
       OR runtime_manifest_hash IS NULL OR environment_digest IS NULL
       OR artifact_bundle_hash IS NULL OR input_schema_hash IS NULL);

SELECT 'prediction_display_engineering_columns_expected_10' AS check_item, COUNT(*) AS value
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'em_prediction_display'
  AND column_name IN (
    'engineering_metric_code', 'raw_predicted_value', 'raw_predicted_unit',
    'engineering_value', 'engineering_unit', 'raw_lower_bound', 'raw_upper_bound',
    'conversion_operator_code', 'conversion_version', 'conversion_status'
  );

SELECT b.id AS prediction_batch_id,
       b.status,
       b.model_count,
       b.feature_count AS prediction_target_count,
       b.rolling_steps,
       (SELECT COUNT(*) FROM em_prediction_result r WHERE r.batch_id = b.id) AS result_count,
       b.output_hash,
       d.expected_result_hash,
       (b.output_hash = d.expected_result_hash) AS expected_hash_matched
FROM em_prediction_batch b
JOIN em_dataset_manifest d ON d.project_id = b.project_id
WHERE b.status = 'success'
ORDER BY b.id DESC
LIMIT 1;
