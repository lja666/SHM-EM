-- SHM-EM Phase 1B second heterogeneous configuration.
--
-- This fixture validates software configuration and workflow reuse only. The
-- packaged excavation models are reused as deterministic workflow fixtures;
-- their outputs are not evidence of bridge-domain predictive accuracy.
--
-- Prerequisite: import 00, 01, 02, 03 and 04 in order. Run this file only in
-- an isolated shm_em_reproduce_phase1b_* database.

SET @source_project_id := (
  SELECT id FROM em_project WHERE project_code = 'SHM_EM_PUBLIC_SAMPLE' LIMIT 1
);

INSERT INTO em_project (
  project_code, project_name, infrastructure_type, scenario_label,
  location_text, coordinate_system, coordinate_source, coordinate_quality,
  spatial_context_json, description, status
) VALUES (
  'SHM_EM_SYNTH_BRIDGE',
  'SHM-EM Synthetic Bridge Reuse Fixture',
  'bridge',
  'phase1b_cross_configuration_reuse',
  'Synthetic software-validation site',
  'local_layout',
  'synthetic_fixture',
  'validated_fixture',
  JSON_OBJECT(
    'stationCount', 3,
    'stationTopology', JSON_ARRAY('west_pier', 'midspan', 'east_pier'),
    'fixtureScope', 'software_reuse_only',
    'predictiveAccuracyClaim', FALSE
  ),
  'Synthetic non-excavation configuration for validating SHM-EM registration, prediction, gating, event, response, and provenance reuse.',
  'active'
);
SET @bridge_project_id := LAST_INSERT_ID();

INSERT INTO em_station (
  project_id, station_code, station_name, station_type, position_desc,
  x, y, z, layout_x, layout_y, status, enabled, metadata_json
) VALUES
  (@bridge_project_id, 'BR-WEST', 'West Pier', 'custom', 'Synthetic west support station', 0, 0, 0, 0.15, 0.55, 'active', 1, JSON_OBJECT('role', 'support', 'fixture', TRUE)),
  (@bridge_project_id, 'BR-MID', 'Midspan', 'custom', 'Synthetic deck midspan station', 50, 0, 5, 0.50, 0.35, 'active', 1, JSON_OBJECT('role', 'span', 'fixture', TRUE)),
  (@bridge_project_id, 'BR-EAST', 'East Pier', 'custom', 'Synthetic east support station', 100, 0, 0, 0.85, 0.55, 'active', 1, JSON_OBJECT('role', 'support', 'fixture', TRUE));

SET @bridge_station_1 := (SELECT id FROM em_station WHERE project_id=@bridge_project_id AND station_code='BR-WEST');
SET @bridge_station_2 := (SELECT id FROM em_station WHERE project_id=@bridge_project_id AND station_code='BR-MID');
SET @bridge_station_3 := (SELECT id FROM em_station WHERE project_id=@bridge_project_id AND station_code='BR-EAST');

INSERT INTO em_instrument (
  project_id, station_id, instrument_code, instrument_name, instrument_type,
  vendor, model, sampling_mode, sampling_frequency, raw_unit_desc,
  install_location, status, enabled, metadata_json
) VALUES
  (@bridge_project_id, @bridge_station_1, 'BR-WEST-TILT', 'West Pier Tilt Sensor', 'displacement', 'Synthetic', 'FIX-TILT', 'low_frequency', 0.0056, 'degree', 'West pier cap', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_1, 'BR-WEST-FORCE', 'West Pier Force Sensor', 'earth_pressure', 'Synthetic', 'FIX-FORCE', 'low_frequency', 0.0056, 'microstrain/MPa', 'West bearing', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_1, 'BR-WEST-WATER', 'West Pier Water Sensor', 'pressure_water_level', 'Synthetic', 'FIX-WATER', 'low_frequency', 0.0056, 'mm', 'West drainage bay', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_1, 'BR-WEST-LEVEL', 'West Pier Level Sensor', 'static_level', 'Synthetic', 'FIX-LEVEL', 'low_frequency', 0.0056, 'mm', 'West reference beam', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_2, 'BR-MID-TILT', 'Midspan Tilt Sensor', 'displacement', 'Synthetic', 'FIX-TILT', 'low_frequency', 0.0056, 'degree', 'Midspan deck', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_2, 'BR-MID-FORCE', 'Midspan Force Sensor', 'earth_pressure', 'Synthetic', 'FIX-FORCE', 'low_frequency', 0.0056, 'microstrain/MPa', 'Midspan girder', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_2, 'BR-MID-WATER', 'Midspan Water Sensor', 'pressure_water_level', 'Synthetic', 'FIX-WATER', 'low_frequency', 0.0056, 'mm', 'Midspan drainage bay', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_2, 'BR-MID-LEVEL', 'Midspan Level Sensor', 'static_level', 'Synthetic', 'FIX-LEVEL', 'low_frequency', 0.0056, 'mm', 'Midspan deck', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_3, 'BR-EAST-TILT', 'East Pier Tilt Sensor', 'displacement', 'Synthetic', 'FIX-TILT', 'low_frequency', 0.0056, 'degree', 'East pier cap', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_3, 'BR-EAST-FORCE', 'East Pier Force Sensor', 'earth_pressure', 'Synthetic', 'FIX-FORCE', 'low_frequency', 0.0056, 'microstrain/MPa', 'East bearing', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_3, 'BR-EAST-WATER', 'East Pier Water Sensor', 'pressure_water_level', 'Synthetic', 'FIX-WATER', 'low_frequency', 0.0056, 'mm', 'East drainage bay', 'online', 1, JSON_OBJECT('fixture', TRUE)),
  (@bridge_project_id, @bridge_station_3, 'BR-EAST-LEVEL', 'East Pier Level Sensor', 'static_level', 'Synthetic', 'FIX-LEVEL', 'low_frequency', 0.0056, 'mm', 'East reference beam', 'online', 1, JSON_OBJECT('fixture', TRUE));

SET @bridge_s1_tilt := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-WEST-TILT');
SET @bridge_s1_force := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-WEST-FORCE');
SET @bridge_s1_water := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-WEST-WATER');
SET @bridge_s1_level := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-WEST-LEVEL');
SET @bridge_s2_tilt := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-MID-TILT');
SET @bridge_s2_force := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-MID-FORCE');
SET @bridge_s2_water := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-MID-WATER');
SET @bridge_s2_level := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-MID-LEVEL');
SET @bridge_s3_tilt := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-EAST-TILT');
SET @bridge_s3_force := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-EAST-FORCE');
SET @bridge_s3_water := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-EAST-WATER');
SET @bridge_s3_level := (SELECT id FROM em_instrument WHERE project_id=@bridge_project_id AND instrument_code='BR-EAST-LEVEL');

INSERT INTO em_observation_table_registry (
  registry_code, project_id, instrument_type, metric_group, storage_backend,
  storage_mode, logical_series_name, physical_table_name, schema_version,
  sample_frequency_hz, time_precision, is_queryable, is_event_source,
  field_mapping_json, enabled, remark
) VALUES
  ('SHM_EM_SYNTH_BRIDGE_DISPLACEMENT', @bridge_project_id, 'displacement', 'deformation', 'mysql', 'type_table', 'Synthetic bridge tilt series', 'em_obs_displacement', 'v1', 0.0056, 'millisecond', 1, 1, JSON_OBJECT('value', 'metric_value', 'time', 'observed_at'), 1, 'Phase 1B existing-adapter fixture'),
  ('SHM_EM_SYNTH_BRIDGE_EARTH_PRESSURE', @bridge_project_id, 'earth_pressure', 'force', 'mysql', 'type_table', 'Synthetic bridge force series', 'em_obs_earth_pressure', 'v1', 0.0056, 'millisecond', 1, 1, JSON_OBJECT('value', 'metric_value', 'time', 'observed_at'), 1, 'Phase 1B existing-adapter fixture'),
  ('SHM_EM_SYNTH_BRIDGE_PRESSURE_WATER_LEVEL', @bridge_project_id, 'pressure_water_level', 'hydraulic', 'mysql', 'type_table', 'Synthetic bridge water series', 'em_obs_pressure_water_level', 'v1', 0.0056, 'millisecond', 1, 1, JSON_OBJECT('value', 'metric_value', 'time', 'observed_at'), 1, 'Phase 1B existing-adapter fixture'),
  ('SHM_EM_SYNTH_BRIDGE_STATIC_LEVEL', @bridge_project_id, 'static_level', 'deformation', 'mysql', 'type_table', 'Synthetic bridge level series', 'em_obs_static_level', 'v1', 0.0056, 'millisecond', 1, 1, JSON_OBJECT('value', 'metric_value', 'time', 'observed_at'), 1, 'Phase 1B existing-adapter fixture');

INSERT INTO em_prediction_model (
  project_id, model_code, model_name, model_type, target_type,
  target_metric_code, input_metrics_json, artifact_uri, artifact_hash,
  preprocessor_uri, preprocessor_hash, inference_script_hash, best_params_hash,
  runtime_manifest_hash, environment_digest, artifact_bundle_hash,
  model_version, runtime_config_json, required_history_rows, input_schema_hash,
  contract_version, expected_steps, time_step_minutes,
  max_operational_age_minutes, status
)
SELECT
  @bridge_project_id, model_code,
  CONCAT('Workflow fixture: ', model_name), model_type, target_type,
  target_metric_code,
  JSON_SET(input_metrics_json, '$.fixtureScope', 'software_reuse_only'),
  artifact_uri, artifact_hash, preprocessor_uri, preprocessor_hash,
  inference_script_hash, best_params_hash, runtime_manifest_hash,
  environment_digest, artifact_bundle_hash, model_version, runtime_config_json,
  required_history_rows, input_schema_hash, contract_version, expected_steps,
  time_step_minutes, max_operational_age_minutes, status
FROM em_prediction_model
WHERE project_id=@source_project_id AND model_code='Strain' AND status='active'
ORDER BY id LIMIT 1;
SET @bridge_strain_model := LAST_INSERT_ID();

INSERT INTO em_prediction_model (
  project_id, model_code, model_name, model_type, target_type,
  target_metric_code, input_metrics_json, artifact_uri, artifact_hash,
  preprocessor_uri, preprocessor_hash, inference_script_hash, best_params_hash,
  runtime_manifest_hash, environment_digest, artifact_bundle_hash,
  model_version, runtime_config_json, required_history_rows, input_schema_hash,
  contract_version, expected_steps, time_step_minutes,
  max_operational_age_minutes, status
)
SELECT
  @bridge_project_id, model_code,
  CONCAT('Workflow fixture: ', model_name), model_type, target_type,
  target_metric_code,
  JSON_SET(input_metrics_json, '$.fixtureScope', 'software_reuse_only'),
  artifact_uri, artifact_hash, preprocessor_uri, preprocessor_hash,
  inference_script_hash, best_params_hash, runtime_manifest_hash,
  environment_digest, artifact_bundle_hash, model_version, runtime_config_json,
  required_history_rows, input_schema_hash, contract_version, expected_steps,
  time_step_minutes, max_operational_age_minutes, status
FROM em_prediction_model
WHERE project_id=@source_project_id AND model_code='Pressure' AND status='active'
ORDER BY id LIMIT 1;
SET @bridge_pressure_model := LAST_INSERT_ID();

INSERT INTO em_prediction_feature_mapping (
  project_id, model_id, feature_code, feature_name, feature_label,
  training_feature_code, feature_group, target_type, feature_role,
  station_id, instrument_id, source_metric_code, source_registry_code,
  source_field, source_value_column, input_value_mode, schema_version,
  feature_operator_code, output_conversion_operator_code,
  output_conversion_version, window_type, window_size_seconds, feature_order,
  required, prediction_target, transform_json, metadata_json, enabled
)
SELECT
  @bridge_project_id,
  CASE WHEN f.feature_group='Pressure' THEN @bridge_pressure_model ELSE @bridge_strain_model END,
  CONCAT('bridge_', f.feature_code),
  CONCAT('bridge_', COALESCE(f.feature_name, f.feature_code)),
  CONCAT('Synthetic bridge fixture / ', COALESCE(f.feature_label, f.feature_code)),
  f.training_feature_code,
  f.feature_group,
  f.target_type,
  f.feature_role,
  CASE MOD(f.feature_order - 1, 3)
    WHEN 0 THEN @bridge_station_1
    WHEN 1 THEN @bridge_station_2
    ELSE @bridge_station_3
  END,
  CASE f.feature_group
    WHEN 'YD' THEN CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_tilt WHEN 1 THEN @bridge_s2_tilt ELSE @bridge_s3_tilt END
    WHEN 'XD' THEN CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_tilt WHEN 1 THEN @bridge_s2_tilt ELSE @bridge_s3_tilt END
    WHEN 'Strain' THEN CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_force WHEN 1 THEN @bridge_s2_force ELSE @bridge_s3_force END
    WHEN 'Pressure' THEN CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_force WHEN 1 THEN @bridge_s2_force ELSE @bridge_s3_force END
    WHEN 'water' THEN CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_water WHEN 1 THEN @bridge_s2_water ELSE @bridge_s3_water END
    ELSE CASE MOD(f.feature_order - 1, 3) WHEN 0 THEN @bridge_s1_level WHEN 1 THEN @bridge_s2_level ELSE @bridge_s3_level END
  END,
  f.source_metric_code,
  CASE f.feature_group
    WHEN 'YD' THEN 'SHM_EM_SYNTH_BRIDGE_DISPLACEMENT'
    WHEN 'XD' THEN 'SHM_EM_SYNTH_BRIDGE_DISPLACEMENT'
    WHEN 'Strain' THEN 'SHM_EM_SYNTH_BRIDGE_EARTH_PRESSURE'
    WHEN 'Pressure' THEN 'SHM_EM_SYNTH_BRIDGE_EARTH_PRESSURE'
    WHEN 'water' THEN 'SHM_EM_SYNTH_BRIDGE_PRESSURE_WATER_LEVEL'
    ELSE 'SHM_EM_SYNTH_BRIDGE_STATIC_LEVEL'
  END,
  f.source_field,
  f.source_value_column,
  f.input_value_mode,
  f.schema_version,
  f.feature_operator_code,
  NULL,
  NULL,
  f.window_type,
  f.window_size_seconds,
  f.feature_order,
  1,
  CASE WHEN f.feature_group IN ('Strain', 'Pressure') THEN f.prediction_target ELSE 0 END,
  f.transform_json,
  JSON_OBJECT(
    'fixtureScope', 'software_reuse_only',
    'sourceProjectCode', 'SHM_EM_PUBLIC_SAMPLE',
    'sourceFeatureCode', f.feature_code,
    'predictiveAccuracyClaim', FALSE
  ),
  1
FROM em_prediction_feature_mapping f
WHERE f.project_id=@source_project_id
  AND f.schema_version='pit_pre_v1'
  AND f.enabled=1
  AND f.required=1
  AND LOWER(COALESCE(f.feature_role, 'model_input'))='model_input'
ORDER BY f.feature_order, f.id;

INSERT INTO em_station_metric (
  project_id, station_id, instrument_id, metric_code, display_name,
  raw_unit, metric_unit, conversion_operator_code, warning_enabled,
  display_order, enabled, metadata_json
)
SELECT DISTINCT
  f.project_id, f.station_id, f.instrument_id, f.source_metric_code,
  CONCAT('Bridge fixture / ', m.metric_name),
  m.default_unit, m.default_unit, 'identity', 1, f.display_order, 1,
  JSON_OBJECT('fixtureScope', 'software_reuse_only')
FROM (
  SELECT project_id, station_id, instrument_id, source_metric_code,
         MIN(feature_order) AS display_order
  FROM em_prediction_feature_mapping
  WHERE project_id=@bridge_project_id
  GROUP BY project_id, station_id, instrument_id, source_metric_code
) f
JOIN em_metric m ON m.metric_code=f.source_metric_code;

CREATE TEMPORARY TABLE phase1b_bridge_steps (step_no int NOT NULL PRIMARY KEY);
INSERT INTO phase1b_bridge_steps (step_no) VALUES
  (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12),(13),(14),(15),(16);
SET @bridge_base_time := TIMESTAMP('2026-06-24 10:00:00');

INSERT INTO em_obs_displacement (
  project_id, station_id, instrument_id, metric_code, engineering_metric_code,
  observed_at, raw_value, raw_unit, metric_value, metric_unit, baseline_value,
  quality_flag, conversion_operator_code, conversion_version,
  conversion_status, conversion_remark, source_record_key
)
SELECT
  q.project_id, q.station_id, q.instrument_id, q.metric_code, q.metric_code,
  TIMESTAMPADD(MINUTE, (s.step_no-16)*3, @bridge_base_time),
  0.08 + MOD(q.station_id, 3)*0.01 + s.step_no*0.001,
  m.default_unit,
  0.08 + MOD(q.station_id, 3)*0.01 + s.step_no*0.001,
  m.default_unit,
  0.08 + MOD(q.station_id, 3)*0.01,
  'normal', 'identity', 'phase1b-fixture-v1', 'success',
  'Synthetic deterministic software-reuse fixture',
  CONCAT('PHASE1B-DISP-', q.instrument_id, '-', q.metric_code, '-', LPAD(s.step_no, 2, '0'))
FROM (
  SELECT DISTINCT f.project_id, f.station_id, f.instrument_id, f.source_metric_code AS metric_code
  FROM em_prediction_feature_mapping f
  WHERE f.project_id=@bridge_project_id
    AND f.source_registry_code='SHM_EM_SYNTH_BRIDGE_DISPLACEMENT'
) q
JOIN em_metric m ON m.metric_code=q.metric_code
CROSS JOIN phase1b_bridge_steps s;

INSERT INTO em_obs_earth_pressure (
  project_id, station_id, instrument_id, metric_code, engineering_metric_code,
  observed_at, raw_value, raw_unit, metric_value, metric_unit, baseline_value,
  quality_flag, conversion_operator_code, conversion_version,
  conversion_status, conversion_remark, source_record_key
)
SELECT
  q.project_id, q.station_id, q.instrument_id, q.metric_code, q.metric_code,
  TIMESTAMPADD(MINUTE, (s.step_no-16)*3, @bridge_base_time),
  CASE WHEN q.metric_code='earth_pressure_p'
    THEN 0.25 + MOD(q.station_id, 3)*0.02 + s.step_no*0.001
    ELSE 90 + MOD(q.station_id, 3)*5 + s.step_no*0.2 END,
  m.default_unit,
  CASE WHEN q.metric_code='earth_pressure_p'
    THEN 0.25 + MOD(q.station_id, 3)*0.02 + s.step_no*0.001
    ELSE 90 + MOD(q.station_id, 3)*5 + s.step_no*0.2 END,
  m.default_unit,
  CASE WHEN q.metric_code='earth_pressure_p' THEN 0.25 ELSE 90 END,
  'normal', 'identity', 'phase1b-fixture-v1', 'success',
  'Synthetic deterministic software-reuse fixture',
  CONCAT('PHASE1B-FORCE-', q.instrument_id, '-', q.metric_code, '-', LPAD(s.step_no, 2, '0'))
FROM (
  SELECT DISTINCT f.project_id, f.station_id, f.instrument_id, f.source_metric_code AS metric_code
  FROM em_prediction_feature_mapping f
  WHERE f.project_id=@bridge_project_id
    AND f.source_registry_code='SHM_EM_SYNTH_BRIDGE_EARTH_PRESSURE'
) q
JOIN em_metric m ON m.metric_code=q.metric_code
CROSS JOIN phase1b_bridge_steps s;

INSERT INTO em_obs_pressure_water_level (
  project_id, station_id, instrument_id, metric_code, engineering_metric_code,
  observed_at, raw_value, raw_unit, metric_value, metric_unit, baseline_value,
  quality_flag, conversion_operator_code, conversion_version,
  conversion_status, conversion_remark, source_record_key
)
SELECT
  q.project_id, q.station_id, q.instrument_id, q.metric_code, q.metric_code,
  TIMESTAMPADD(MINUTE, (s.step_no-16)*3, @bridge_base_time),
  100 + MOD(q.station_id, 3) + s.step_no*0.1,
  m.default_unit,
  100 + MOD(q.station_id, 3) + s.step_no*0.1,
  m.default_unit,
  100 + MOD(q.station_id, 3),
  'normal', 'identity', 'phase1b-fixture-v1', 'success',
  'Synthetic deterministic software-reuse fixture',
  CONCAT('PHASE1B-WATER-', q.instrument_id, '-', q.metric_code, '-', LPAD(s.step_no, 2, '0'))
FROM (
  SELECT DISTINCT f.project_id, f.station_id, f.instrument_id, f.source_metric_code AS metric_code
  FROM em_prediction_feature_mapping f
  WHERE f.project_id=@bridge_project_id
    AND f.source_registry_code='SHM_EM_SYNTH_BRIDGE_PRESSURE_WATER_LEVEL'
) q
JOIN em_metric m ON m.metric_code=q.metric_code
CROSS JOIN phase1b_bridge_steps s;

INSERT INTO em_obs_static_level (
  project_id, station_id, instrument_id, metric_code, engineering_metric_code,
  observed_at, raw_value, raw_unit, metric_value, metric_unit, baseline_value,
  quality_flag, conversion_operator_code, conversion_version,
  conversion_status, conversion_remark, source_record_key
)
SELECT
  q.project_id, q.station_id, q.instrument_id, q.metric_code, q.metric_code,
  TIMESTAMPADD(MINUTE, (s.step_no-16)*3, @bridge_base_time),
  40 + MOD(q.station_id, 3) + s.step_no*0.05,
  m.default_unit,
  40 + MOD(q.station_id, 3) + s.step_no*0.05,
  m.default_unit,
  40 + MOD(q.station_id, 3),
  'normal', 'identity', 'phase1b-fixture-v1', 'success',
  'Synthetic deterministic software-reuse fixture',
  CONCAT('PHASE1B-LEVEL-', q.instrument_id, '-', q.metric_code, '-', LPAD(s.step_no, 2, '0'))
FROM (
  SELECT DISTINCT f.project_id, f.station_id, f.instrument_id, f.source_metric_code AS metric_code
  FROM em_prediction_feature_mapping f
  WHERE f.project_id=@bridge_project_id
    AND f.source_registry_code='SHM_EM_SYNTH_BRIDGE_STATIC_LEVEL'
) q
JOIN em_metric m ON m.metric_code=q.metric_code
CROSS JOIN phase1b_bridge_steps s;

DROP TEMPORARY TABLE phase1b_bridge_steps;

INSERT INTO em_action_policy (
  project_id, policy_code, policy_name, policy_scope,
  notification_enabled, report_enabled, evidence_archive_enabled,
  policy_json, enabled
) VALUES (
  @bridge_project_id,
  'BRIDGE_FIXTURE_RESPONSE',
  'Synthetic bridge workflow response',
  'event', 0, 1, 1,
  JSON_OBJECT('fixtureScope', 'software_reuse_only', 'report', 'event_report'),
  1
);
SET @bridge_action_policy := LAST_INSERT_ID();

SET @bridge_pressure_feature := (
  SELECT feature_code
  FROM em_prediction_feature_mapping
  WHERE project_id=@bridge_project_id AND feature_group='Pressure' AND prediction_target=1
  ORDER BY feature_order LIMIT 1
);
SET @bridge_pressure_station := (
  SELECT station_id
  FROM em_prediction_feature_mapping
  WHERE project_id=@bridge_project_id AND feature_code=@bridge_pressure_feature
  LIMIT 1
);
SET @bridge_pressure_instrument := (
  SELECT instrument_id
  FROM em_prediction_feature_mapping
  WHERE project_id=@bridge_project_id AND feature_code=@bridge_pressure_feature
  LIMIT 1
);

INSERT INTO em_event_rule (
  project_id, rule_code, rule_name, metric_code, source_instrument_type,
  input_source, prediction_model_code, prediction_target_type,
  prediction_feature_code, forecast_horizon_minutes,
  minimum_consecutive_steps, series_quality_filter, station_scope,
  station_ids_json, instrument_ids_json, registry_codes_json, rule_mode,
  event_type, event_level, time_window, aggregation_method, operator,
  threshold_value, threshold_unit, baseline_strategy, quality_policy,
  missing_data_policy, result_policy, continuous_count, cooldown_minutes,
  current_version, rule_snapshot_json, action_policy_id, enabled
) VALUES (
  @bridge_project_id,
  'BRIDGE_PRESSURE_WORKFLOW_FIXTURE',
  'Synthetic bridge pressure workflow fixture',
  'earth_pressure_p',
  'earth_pressure',
  'PREDICTION',
  'Pressure',
  'Pressure',
  @bridge_pressure_feature,
  120,
  3,
  'normal',
  'selected',
  JSON_ARRAY(@bridge_pressure_station),
  JSON_ARRAY(@bridge_pressure_instrument),
  JSON_ARRAY('SHM_EM_SYNTH_BRIDGE_EARTH_PRESSURE'),
  'threshold',
  'forecast_warning',
  'yellow',
  'forecast',
  'latest',
  '>=',
  -1000.00000000,
  'MPa',
  'none',
  'normal_only',
  'fail',
  'highest_level',
  3,
  0,
  'phase1b-v1',
  JSON_OBJECT(
    'fixtureScope', 'software_reuse_only',
    'predictiveAccuracyClaim', FALSE,
    'modelCode', 'Pressure',
    'featureCode', @bridge_pressure_feature,
    'thresholdPurpose', 'deterministic workflow trigger'
  ),
  @bridge_action_policy,
  1
);
SET @bridge_rule_id := LAST_INSERT_ID();

INSERT INTO em_event_rule_level (
  rule_id, level_code, level_rank, action_policy_id,
  combine_logic, explanation_template
) VALUES (
  @bridge_rule_id, 'yellow', 10, @bridge_action_policy, 'any',
  'Synthetic bridge workflow fixture threshold reached'
);
SET @bridge_rule_level_id := LAST_INSERT_ID();

INSERT INTO em_event_rule_condition (
  rule_id, level_id, condition_code, metric_code, feature_code,
  window_type, window_size, aggregation_method, operator,
  threshold_value, threshold_unit, reference_value_source,
  required, condition_json
) VALUES (
  @bridge_rule_id,
  @bridge_rule_level_id,
  'BRIDGE_PRESSURE_FIXTURE_THRESHOLD',
  'earth_pressure_p',
  @bridge_pressure_feature,
  'forecast',
  '120m',
  'latest',
  '>=',
  -1000.00000000,
  'MPa',
  'prediction_engineering_value',
  1,
  JSON_OBJECT(
    'fixtureScope', 'software_reuse_only',
    'thresholdPurpose', 'deterministic workflow trigger'
  )
);
