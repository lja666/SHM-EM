-- Build a de-identified, minimum-window public reproduction sample in place.
-- Run only against a disposable shm_em_reproduce_public_* database created
-- from an authorized private case. The source database is never modified.

SET NAMES utf8mb4;
SET @sample_end = (
  SELECT base_time
  FROM em_prediction_batch
  WHERE status = 'success'
  ORDER BY base_time DESC, id DESC
  LIMIT 1
);
SET @sample_start = DATE_SUB(@sample_end, INTERVAL 48 MINUTE);
SET @public_end = TIMESTAMP('2025-01-01 00:45:00.000');
SET @time_shift_microseconds = TIMESTAMPDIFF(MICROSECOND, @sample_end, @public_end);

-- Keep only the source rows that can contribute to the contract-defined
-- 16-step, three-minute model input window (including one tolerance step).
DELETE FROM em_obs_displacement
WHERE observed_at < @sample_start OR observed_at > @sample_end;
DELETE FROM em_obs_earth_pressure
WHERE observed_at < @sample_start OR observed_at > @sample_end;
DELETE FROM em_obs_pressure_water_level
WHERE observed_at < @sample_start OR observed_at > @sample_end;
DELETE FROM em_obs_static_level
WHERE observed_at < @sample_start OR observed_at > @sample_end;

DELETE o FROM em_obs_displacement o
LEFT JOIN (
  SELECT f.id, f.project_id, f.station_id, f.instrument_id, f.source_metric_code
  FROM em_prediction_feature_mapping f
  JOIN em_observation_table_registry r ON r.registry_code = f.source_registry_code
  WHERE r.physical_table_name = 'em_obs_displacement' AND f.enabled = 1
) f ON f.project_id = o.project_id
   AND f.source_metric_code = o.metric_code
   AND (f.station_id IS NULL OR f.station_id = o.station_id)
   AND (f.instrument_id IS NULL OR f.instrument_id = o.instrument_id)
WHERE f.id IS NULL;
DELETE o FROM em_obs_earth_pressure o
LEFT JOIN (
  SELECT f.id, f.project_id, f.station_id, f.instrument_id, f.source_metric_code
  FROM em_prediction_feature_mapping f
  JOIN em_observation_table_registry r ON r.registry_code = f.source_registry_code
  WHERE r.physical_table_name = 'em_obs_earth_pressure' AND f.enabled = 1
) f ON f.project_id = o.project_id
   AND f.source_metric_code = o.metric_code
   AND (f.station_id IS NULL OR f.station_id = o.station_id)
   AND (f.instrument_id IS NULL OR f.instrument_id = o.instrument_id)
WHERE f.id IS NULL;
DELETE o FROM em_obs_pressure_water_level o
LEFT JOIN (
  SELECT f.id, f.project_id, f.station_id, f.instrument_id, f.source_metric_code
  FROM em_prediction_feature_mapping f
  JOIN em_observation_table_registry r ON r.registry_code = f.source_registry_code
  WHERE r.physical_table_name = 'em_obs_pressure_water_level' AND f.enabled = 1
) f ON f.project_id = o.project_id
   AND f.source_metric_code = o.metric_code
   AND (f.station_id IS NULL OR f.station_id = o.station_id)
   AND (f.instrument_id IS NULL OR f.instrument_id = o.instrument_id)
WHERE f.id IS NULL;
DELETE o FROM em_obs_static_level o
LEFT JOIN (
  SELECT f.id, f.project_id, f.station_id, f.instrument_id, f.source_metric_code
  FROM em_prediction_feature_mapping f
  JOIN em_observation_table_registry r ON r.registry_code = f.source_registry_code
  WHERE r.physical_table_name = 'em_obs_static_level' AND f.enabled = 1
) f ON f.project_id = o.project_id
   AND f.source_metric_code = o.metric_code
   AND (f.station_id IS NULL OR f.station_id = o.station_id)
   AND (f.instrument_id IS NULL OR f.instrument_id = o.instrument_id)
WHERE f.id IS NULL;

UPDATE em_obs_displacement
SET observed_at = TIMESTAMPADD(MICROSECOND, @time_shift_microseconds, observed_at),
    created_at = observed_at,
    source_record_key = CONCAT('PUBLIC-DISPLACEMENT-', id);
UPDATE em_obs_earth_pressure
SET observed_at = TIMESTAMPADD(MICROSECOND, @time_shift_microseconds, observed_at),
    created_at = observed_at,
    source_record_key = CONCAT('PUBLIC-PRESSURE-', id);
UPDATE em_obs_pressure_water_level
SET observed_at = TIMESTAMPADD(MICROSECOND, @time_shift_microseconds, observed_at),
    created_at = observed_at,
    source_record_key = CONCAT('PUBLIC-WATER-', id);
UPDATE em_obs_static_level
SET observed_at = TIMESTAMPADD(MICROSECOND, @time_shift_microseconds, observed_at),
    created_at = observed_at,
    source_record_key = CONCAT('PUBLIC-SETTLEMENT-', id);

SET FOREIGN_KEY_CHECKS = 0;
DELETE FROM em_accel_s_1426000125;
DELETE FROM em_accel_s_1426000126;
DELETE FROM em_accel_batch;
DELETE FROM em_obs_acceleration_feature;
DELETE FROM em_audit_log;
DELETE FROM em_data_quality_issue;
DELETE FROM em_event_evidence_link;
DELETE FROM em_event_handling_log;
DELETE FROM em_event_metric_snapshot;
DELETE FROM em_event_notification_state;
DELETE FROM em_event_prediction_link;
DELETE FROM em_event_response_step;
DELETE FROM em_event_response_workflow;
DELETE FROM em_event_state_candidate_log;
DELETE FROM em_event_state_transition;
DELETE FROM em_event_evaluation_run;
DELETE FROM em_evidence_resource;
DELETE FROM em_monitoring_event;
DELETE FROM em_notification_delivery_log;
DELETE FROM em_notification_task;
DELETE FROM em_notification_subscriber;
DELETE FROM em_prediction_execution_gate;
DELETE FROM em_prediction_result;
DELETE FROM em_prediction_run;
DELETE FROM em_prediction_batch;
DELETE FROM em_report_instance;
DELETE FROM em_report_template WHERE template_code <> 'EVENT_REPORT_DEFAULT';
DELETE FROM em_workflow_run_step;
DELETE FROM em_workflow_run;
DELETE FROM em_expected_output;
SET FOREIGN_KEY_CHECKS = 1;

-- Remove case identity while preserving the object relationships required by
-- model feature mappings and engineering conversions.
UPDATE em_project
SET project_code = 'SHM_EM_PUBLIC_SAMPLE',
    project_name = 'SHM-EM Public Reproduction Sample',
    scenario_label = 'deidentified_minimum_window',
    location_text = 'Anonymized',
    longitude = NULL,
    latitude = NULL,
    coordinate_system = 'local_layout',
    coordinate_source = 'concept_plan',
    coordinate_quality = 'illustrative',
    map_provider = NULL,
    spatial_context_json = JSON_OBJECT(
        'monitoringPointCount', 9,
        'siteNumbers', JSON_ARRAY(1, 2, 3, 4, 5, 6, 7, 8, 9),
        'sensorRecordCount', 74,
        'acquisitionModuleCount', 17,
        'dtuCount', 6,
        'layoutStatus', 'conceptual'
    ),
    description = 'De-identified minimum-window sample for software and model reproduction.',
    start_time = NULL,
    end_time = NULL;

UPDATE em_station
SET station_code = CONCAT('STATION-RECORD-', LPAD(id, 3, '0')),
    station_name = CONCAT('Station Record ', id),
    position_desc = CONCAT('Public sample installation record ', id),
    longitude = NULL,
    latitude = NULL,
    x = NULL,
    y = NULL,
    z = NULL,
    elevation = NULL,
    installation_time = NULL,
    metadata_json = JSON_OBJECT('sample', 'public-deidentified');

CREATE TEMPORARY TABLE public_module_map AS
SELECT module_no,
       CONCAT(
           'MODULE-',
           LPAD(
               DENSE_RANK() OVER (
                   ORDER BY
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM em_instrument i
                           WHERE i.module_no = modules.module_no
                             AND i.instrument_type = 'accelerometer'
                       ) THEN 1 ELSE 0 END,
                       module_no
               ),
               2,
               '0'
           )
       ) AS public_module_no
FROM (SELECT DISTINCT module_no FROM em_instrument WHERE module_no IS NOT NULL) modules;

CREATE TEMPORARY TABLE public_dtu_map AS
SELECT dtu_code,
       CONCAT('GATEWAY-', LPAD(DENSE_RANK() OVER (ORDER BY dtu_code), 2, '0')) AS public_dtu_code
FROM (SELECT DISTINCT dtu_code FROM em_instrument WHERE dtu_code IS NOT NULL) gateways;

UPDATE em_conversion_parameter p
JOIN public_module_map m ON m.module_no = p.module_no
SET p.module_no = m.public_module_no;
UPDATE em_reference_binding b
JOIN public_module_map m ON m.module_no = b.module_no
SET b.module_no = m.public_module_no;
UPDATE em_instrument i
LEFT JOIN public_module_map m ON m.module_no = i.module_no
LEFT JOIN public_dtu_map d ON d.dtu_code = i.dtu_code
SET i.instrument_code = CONCAT('DEVICE-', LPAD(i.id, 3, '0')),
    i.instrument_name = CONCAT('Public ', REPLACE(i.instrument_type, '_', ' '), ' device ', i.id),
    i.vendor = NULL,
    i.model = NULL,
    i.serial_no = NULL,
    i.dtu_code = d.public_dtu_code,
    i.module_no = m.public_module_no,
    i.module_name = m.public_module_no,
    i.channel_no = NULL,
    i.communication_mode = NULL,
    i.protocol_code = NULL,
    i.installation_time = NULL,
    i.calibration_json = NULL,
    i.metadata_json = JSON_OBJECT('sample', 'public-deidentified');

UPDATE em_conversion_parameter
SET source_record_key = CONCAT('PUBLIC-CONVERSION-', id),
    metadata_json = JSON_OBJECT('sample', 'public-deidentified');
UPDATE em_reference_binding
SET source_record_key = CONCAT('PUBLIC-REFERENCE-', id),
    metadata_json = JSON_OBJECT('sample', 'public-deidentified');
UPDATE em_metric_baseline_history
SET source_record_key = CONCAT('PUBLIC-BASELINE-', id),
    metadata_json = JSON_OBJECT('sample', 'public-deidentified');
UPDATE em_station_metric
SET metadata_json = JSON_OBJECT('sample', 'public-deidentified');
UPDATE em_prediction_feature_mapping
SET metadata_json = NULL;

UPDATE em_prediction_feature_mapping
SET source_registry_code = REPLACE(source_registry_code, 'IEM_EXCAVATION_REAL', 'SHM_EM_PUBLIC_SAMPLE');
UPDATE em_event_rule
SET registry_codes_json = CAST(
  REPLACE(CAST(registry_codes_json AS CHAR), 'IEM_EXCAVATION_REAL', 'SHM_EM_PUBLIC_SAMPLE')
  AS JSON
)
WHERE registry_codes_json IS NOT NULL;
UPDATE em_observation_table_registry
SET registry_code = REPLACE(registry_code, 'IEM_EXCAVATION_REAL', 'SHM_EM_PUBLIC_SAMPLE'),
    logical_series_name = REPLACE(logical_series_name, 'IEM_EXCAVATION_REAL', 'SHM_EM_PUBLIC_SAMPLE'),
    remark = 'Public de-identified sample registry';

UPDATE em_dataset_manifest
SET dataset_code = 'shm_em_public_sample_v1',
    dataset_name = 'SHM-EM De-identified Minimum-Window Sample',
    scenario_type = 'deidentified_excavation_sample',
    input_description = 'Sixteen-step de-identified model input window; no complete project history or operational records.',
    dataset_uri = 'sql://02_SHM_EM_public_sample.sql',
    time_start = TIMESTAMP('2024-12-31 23:57:00.000'),
    time_end = @public_end,
    expected_output_json = JSON_OBJECT(
      'modelCount', 6,
      'inputFeatureCount', 164,
      'predictionTargetCount', 124,
      'predictionSteps', 40,
      'predictionResultCount', 4960
    ),
    expected_result_hash = NULL,
    license = 'CC-BY-4.0',
    citation = 'Cite the SHM-EM software release and accompanying SoftwareX article.',
    reproducibility_level = 'public_deidentified_minimum_window';

UPDATE em_scenario_profile
SET scenario_name = 'Public excavation sample scenario',
    description = 'De-identified excavation sample configuration for software reproduction.'
WHERE scenario_code = 'excavation_reference_v1';

DROP TEMPORARY TABLE public_dtu_map;
DROP TEMPORARY TABLE public_module_map;
