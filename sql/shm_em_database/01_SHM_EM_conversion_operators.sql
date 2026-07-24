-- Public SHM-EM engineering-conversion operator definitions.
-- This file contains formulas only. It contains no observations, instrument
-- identifiers, calibration values, reference bindings, or project metadata.

SET NAMES utf8mb4;

INSERT INTO em_conversion_operator
  (operator_code, operator_name, input_unit, output_unit, output_metric_code,
   formula_text, formula_json, version, enabled)
VALUES
  ('identity', 'Identity mapping', NULL, NULL, NULL,
   'metric_value = raw_value', JSON_OBJECT('type','identity'), 'v1', 1),
  ('mm_to_m', 'Millimeter to meter', 'mm', 'm', 'groundwater_level_change',
   'metric_value = raw_value / 1000', JSON_OBJECT('type','linear','scale',0.001), 'v1', 1),
  ('tilt_y_to_deep_displacement', 'Y-axis inclination to deep horizontal displacement', 'degree', 'mm', 'deep_horizontal_displacement_y',
   '1000*SIN(RADIANS(data1_value))-1000*SIN(RADIANS(data1_baseline_value))+initial_y_value',
   JSON_OBJECT('type','formula','source','calibration record'), 'v1', 1),
  ('special_water_cm_plus_5', 'Differential water level conversion', 'mm', 'cm', 'special_differential_water_level_cm',
   'metric_value = raw_mm / 10 + 5', JSON_OBJECT('type','formula','offset_cm',5), 'v1', 1),
  ('displacement_y_engineering', 'Y displacement engineering conversion', 'degree', 'mm', 'deep_horizontal_displacement_y',
   '1000*sin(raw*pi/180)-1000*sin(baseline*pi/180)+initial_y',
   JSON_OBJECT('type','formula','parameter','initial_y_mm'), 'displacement-v2-20260714', 1),
  ('displacement_x_engineering', 'X displacement engineering conversion', 'degree', 'mm', 'deep_horizontal_displacement_x',
   '1000*sin(raw*pi/180)-1000*sin(baseline*pi/180)',
   JSON_OBJECT('type','formula','initial',0), 'displacement-v2-20260714', 1),
  ('static_level_reference_compensation', 'Static-level reference compensation', 'mm', 'mm', 'ground_settlement',
   '(point_raw-point_baseline)-(reference_raw-reference_baseline)',
   JSON_OBJECT('type','reference_difference','toleranceMinutes',5), 'static-level-v2-positive-20260713', 1),
  ('pit_water_elevation', 'Excavation groundwater elevation', 'mm', 'm', 'groundwater_elevation_m',
   'module_elevation_m-raw_mm/1000',
   JSON_OBJECT('type','formula','parameter','module_elevation_m'), 'pit-water-v2-20260714', 1),
  ('pit_water_cumulative_change', 'Excavation groundwater cumulative change', 'mm', 'm', 'groundwater_level_change',
   'raw_mm/1000-cumulative_baseline_m',
   JSON_OBJECT('type','formula','parameter','cumulative_baseline_m'), 'pit-water-v2-20260714', 1),
  ('laboratory_water_level', 'Laboratory differential water level', 'mm', 'cm', 'special_differential_water_level_cm',
   'raw_mm/10-initial_error_cm+installation_offset_cm',
   JSON_OBJECT('type','formula','parameters',JSON_ARRAY('initial_error_cm','installation_offset_cm')), 'lab-water-v2-20260714', 1)
ON DUPLICATE KEY UPDATE
  operator_name=VALUES(operator_name),
  input_unit=VALUES(input_unit),
  output_unit=VALUES(output_unit),
  output_metric_code=VALUES(output_metric_code),
  formula_text=VALUES(formula_text),
  formula_json=VALUES(formula_json),
  version=VALUES(version),
  enabled=VALUES(enabled);
