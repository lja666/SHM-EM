-- MySQL dump 10.13  Distrib 8.4.0, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: shm_em
-- ------------------------------------------------------
-- Server version	8.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `em_accel_batch`
--

DROP TABLE IF EXISTS `em_accel_batch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_accel_batch` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint NOT NULL,
  `sensor_no` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `batch_no` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_time` datetime(3) NOT NULL,
  `end_time` datetime(3) DEFAULT NULL,
  `sample_rate_hz` decimal(12,4) DEFAULT NULL,
  `sample_count` int DEFAULT NULL,
  `axis_count` int DEFAULT '3',
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_accel_batch` (`instrument_id`,`batch_no`),
  KEY `idx_em_accel_batch_project_time` (`project_id`,`start_time`),
  KEY `idx_em_accel_batch_instrument_time` (`instrument_id`,`start_time`)
) ENGINE=InnoDB AUTO_INCREMENT=401 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='High-frequency acceleration batch metadata';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_accel_s_1426000125`
--

DROP TABLE IF EXISTS `em_accel_s_1426000125`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_accel_s_1426000125` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint NOT NULL,
  `batch_id` bigint DEFAULT NULL,
  `sample_index` int NOT NULL,
  `sample_offset_ms` int DEFAULT NULL,
  `sample_time` datetime(3) NOT NULL,
  `x_raw` int DEFAULT NULL,
  `y_raw` int DEFAULT NULL,
  `z_raw` int DEFAULT NULL,
  `x_accel` decimal(20,10) DEFAULT NULL,
  `y_accel` decimal(20,10) DEFAULT NULL,
  `z_accel` decimal(20,10) DEFAULT NULL,
  `accel_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'm/s^2',
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_accel_source` (`project_id`,`source_record_key`),
  KEY `idx_em_accel_wave_time` (`instrument_id`,`sample_time`),
  KEY `idx_em_accel_wave_batch` (`batch_id`,`sample_index`),
  KEY `idx_em_accel_wave_project_time` (`project_id`,`sample_time`)
) ENGINE=InnoDB AUTO_INCREMENT=10001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='High-frequency acceleration samples for sensor 1426000125';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_accel_s_1426000126`
--

DROP TABLE IF EXISTS `em_accel_s_1426000126`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_accel_s_1426000126` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint NOT NULL,
  `batch_id` bigint DEFAULT NULL,
  `sample_index` int NOT NULL,
  `sample_offset_ms` int DEFAULT NULL,
  `sample_time` datetime(3) NOT NULL,
  `x_raw` int DEFAULT NULL,
  `y_raw` int DEFAULT NULL,
  `z_raw` int DEFAULT NULL,
  `x_accel` decimal(20,10) DEFAULT NULL,
  `y_accel` decimal(20,10) DEFAULT NULL,
  `z_accel` decimal(20,10) DEFAULT NULL,
  `accel_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'm/s^2',
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_accel_source` (`project_id`,`source_record_key`),
  KEY `idx_em_accel_wave_time` (`instrument_id`,`sample_time`),
  KEY `idx_em_accel_wave_batch` (`batch_id`,`sample_index`),
  KEY `idx_em_accel_wave_project_time` (`project_id`,`sample_time`)
) ENGINE=InnoDB AUTO_INCREMENT=20001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='High-frequency acceleration samples for sensor 1426000126';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_action_policy`
--

DROP TABLE IF EXISTS `em_action_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_action_policy` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint DEFAULT NULL,
  `policy_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `policy_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `policy_scope` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event',
  `notification_enabled` tinyint NOT NULL DEFAULT '1',
  `report_enabled` tinyint NOT NULL DEFAULT '1',
  `evidence_archive_enabled` tinyint NOT NULL DEFAULT '1',
  `policy_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_action_policy` (`project_id`,`policy_code`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Response policy bound to rules or event levels';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_audit_log`
--

DROP TABLE IF EXISTS `em_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint DEFAULT NULL,
  `actor_id` bigint DEFAULT NULL,
  `actor_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `object_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `object_id` bigint DEFAULT NULL,
  `object_code` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `before_json` json DEFAULT NULL,
  `after_json` json DEFAULT NULL,
  `request_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_address` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_audit_project_time` (`project_id`,`created_at`),
  KEY `idx_em_audit_object` (`object_type`,`object_id`),
  KEY `idx_em_audit_action` (`action_type`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Audit log for configuration and workflow changes';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_conversion_operator`
--

DROP TABLE IF EXISTS `em_conversion_operator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_conversion_operator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `operator_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `input_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `output_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `output_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `formula_text` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `formula_json` json DEFAULT NULL,
  `version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_conversion_operator_version` (`operator_code`,`version`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Raw-to-engineering conversion operators';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_conversion_parameter`
--

DROP TABLE IF EXISTS `em_conversion_parameter`;
CREATE TABLE `em_conversion_parameter` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `module_no` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parameter_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `parameter_value` decimal(20,8) NOT NULL,
  `parameter_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `effective_from` datetime(3) NOT NULL DEFAULT '1970-01-01 00:00:00.000',
  `effective_to` datetime(3) DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_conversion_parameter_source` (`project_id`,`source_record_key`),
  KEY `idx_em_conversion_parameter_lookup` (`project_id`,`instrument_id`,`module_no`,`parameter_code`,`effective_from`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Versioned parameters used by engineering-value conversion';

--
-- Table structure for table `em_reference_binding`
--

DROP TABLE IF EXISTS `em_reference_binding`;
CREATE TABLE `em_reference_binding` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `instrument_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `module_no` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reference_instrument_id` bigint NOT NULL,
  `tolerance_minutes` int NOT NULL DEFAULT '5',
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_reference_binding` (`project_id`,`instrument_type`,`module_no`),
  UNIQUE KEY `uk_em_reference_binding_source` (`project_id`,`source_record_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Reference instruments used by engineering-value conversion';

--
-- Table structure for table `em_data_quality_issue`
--

DROP TABLE IF EXISTS `em_data_quality_issue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_data_quality_issue` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issue_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `issue_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'warning',
  `observed_at` datetime(3) DEFAULT NULL,
  `source_registry_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issue_message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_quality_project_time` (`project_id`,`observed_at`),
  KEY `idx_em_quality_status` (`project_id`,`status`,`issue_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Observation data quality issues';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_dataset_manifest`
--

DROP TABLE IF EXISTS `em_dataset_manifest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_dataset_manifest` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dataset_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dataset_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scenario_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint DEFAULT NULL,
  `input_description` text COLLATE utf8mb4_unicode_ci,
  `dataset_uri` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_start` datetime(3) DEFAULT NULL,
  `time_end` datetime(3) DEFAULT NULL,
  `expected_output_json` json DEFAULT NULL,
  `expected_result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `license` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `citation` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reproducibility_level` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'unclassified',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_dataset_code` (`dataset_code`),
  KEY `idx_em_dataset_project` (`project_id`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Dataset manifests for SoftwareX reproducibility';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_dictionary`
--

DROP TABLE IF EXISTS `em_dictionary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_dictionary` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dict_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dict_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dict_label` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dict_value` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `display_order` int DEFAULT '0',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_dictionary` (`dict_type`,`dict_code`),
  KEY `idx_em_dictionary_type` (`dict_type`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System dictionaries for infrastructure types, event levels, statuses, etc.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_evaluation_run`
--

DROP TABLE IF EXISTS `em_event_evaluation_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_evaluation_run` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `rule_id` bigint DEFAULT NULL,
  `run_mode` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'evaluate/execute/replay/scheduled',
  `rule_version` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_registry_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_start` datetime(3) DEFAULT NULL,
  `time_end` datetime(3) DEFAULT NULL,
  `input_params_json` json DEFAULT NULL,
  `event_count` int NOT NULL DEFAULT '0',
  `result_summary_json` json DEFAULT NULL,
  `result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `created_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_eval_project_time` (`project_id`,`finished_at`),
  KEY `idx_em_eval_rule` (`rule_id`),
  KEY `idx_em_eval_hash` (`result_hash`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rule evaluation / execution / replay runs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_evidence_link`
--

DROP TABLE IF EXISTS `em_event_evidence_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_evidence_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint NOT NULL,
  `evidence_id` bigint NOT NULL,
  `link_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'workflow',
  `confidence` decimal(6,4) DEFAULT NULL,
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_evidence` (`event_id`,`evidence_id`),
  KEY `idx_em_event_evidence_event` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Event-evidence relation';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_handling_log`
--

DROP TABLE IF EXISTS `em_event_handling_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_handling_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint NOT NULL,
  `project_id` bigint NOT NULL,
  `action_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attachments_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_handling_event` (`event_id`,`created_at`),
  KEY `idx_em_handling_project` (`project_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Event handling log';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_metric_snapshot`
--

DROP TABLE IF EXISTS `em_event_metric_snapshot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_metric_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint DEFAULT NULL,
  `evaluation_run_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aggregation_method` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `window_start` datetime(3) DEFAULT NULL,
  `window_end` datetime(3) DEFAULT NULL,
  `sample_count` int DEFAULT NULL,
  `trigger_value` decimal(20,8) DEFAULT NULL,
  `threshold_value` decimal(20,8) DEFAULT NULL,
  `snapshot_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_snapshot_event` (`event_id`),
  KEY `idx_em_snapshot_eval` (`evaluation_run_id`),
  KEY `idx_em_snapshot_metric` (`metric_code`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Evidence snapshots generated during rule evaluation or dataset import';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_notification_state`
--

DROP TABLE IF EXISTS `em_event_notification_state`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_notification_state` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `monitor_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `source_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RULE_EVENT',
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `rule_id` bigint DEFAULT NULL,
  `state_schema_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'state-v1',
  `decision_model_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'state-transition-v1',
  `current_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'NORMAL',
  `current_rank` int NOT NULL DEFAULT '0',
  `current_value` decimal(20,8) DEFAULT NULL,
  `current_event_id` bigint DEFAULT NULL,
  `current_event_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_transition_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_transition_at` datetime DEFAULT NULL,
  `last_input_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_state_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_notification_at` datetime DEFAULT NULL,
  `last_notification_level` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_notification_value` decimal(20,8) DEFAULT NULL,
  `state_vector_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_notification_state_key` (`monitor_key`),
  KEY `idx_em_event_notification_state_project` (`project_id`,`current_level`),
  KEY `idx_em_event_notification_state_notify` (`project_id`,`last_notification_at`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SHM-EM event notification latest state';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_prediction_link`
--

DROP TABLE IF EXISTS `em_event_prediction_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_prediction_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint NOT NULL,
  `prediction_batch_id` bigint NOT NULL,
  `prediction_run_id` bigint DEFAULT NULL,
  `prediction_gate_id` bigint DEFAULT NULL,
  `model_id` bigint DEFAULT NULL,
  `first_exceedance_time` datetime(3) DEFAULT NULL,
  `lead_time_minutes` int DEFAULT NULL,
  `peak_predicted_value` decimal(20,8) DEFAULT NULL,
  `consecutive_exceedance_steps` int DEFAULT NULL,
  `forecast_snapshot_json` json DEFAULT NULL,
  `result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_prediction_link` (`event_id`,`prediction_batch_id`,`prediction_run_id`),
  KEY `idx_em_event_prediction_batch` (`prediction_batch_id`),
  KEY `idx_em_event_prediction_run` (`prediction_run_id`),
  KEY `idx_em_event_prediction_gate` (`prediction_gate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Trace link from formal forecast events to prediction batches and model runs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_response_step`
--

DROP TABLE IF EXISTS `em_event_response_step`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_response_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `workflow_id` bigint NOT NULL,
  `step_order` int NOT NULL,
  `step_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `step_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `related_task_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `related_task_id` bigint DEFAULT NULL,
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_response_step_code` (`workflow_id`,`step_code`),
  KEY `idx_em_response_step_workflow` (`workflow_id`,`step_order`)
) ENGINE=InnoDB AUTO_INCREMENT=97 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Event response workflow steps';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_response_workflow`
--

DROP TABLE IF EXISTS `em_event_response_workflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_response_workflow` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint NOT NULL,
  `project_id` bigint NOT NULL,
  `workflow_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `workflow_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `workflow_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'running',
  `trigger_mode` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event_triggered',
  `result_summary_json` json DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_response_workflow` (`event_id`,`workflow_code`),
  KEY `idx_em_response_project` (`project_id`,`started_at`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Event response workflow';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_rule`
--

DROP TABLE IF EXISTS `em_event_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_rule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `rule_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rule_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_instrument_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_source` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'OBSERVATION' COMMENT 'OBSERVATION or PREDICTION',
  `prediction_model_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prediction_target_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prediction_feature_code` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `forecast_horizon_minutes` int DEFAULT NULL,
  `minimum_consecutive_steps` int DEFAULT '1',
  `series_quality_filter` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal' COMMENT 'Prediction-series query filter; does not relax execution gating',
  `station_scope` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'all',
  `station_ids_json` json DEFAULT NULL,
  `instrument_ids_json` json DEFAULT NULL,
  `registry_codes_json` json DEFAULT NULL,
  `rule_mode` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'threshold',
  `event_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'yellow',
  `time_window` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aggregation_method` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operator` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `threshold_value` decimal(20,8) DEFAULT NULL,
  `threshold_value_upper` decimal(20,8) DEFAULT NULL,
  `threshold_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_strategy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'none',
  `quality_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'allow_suspect',
  `missing_data_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'skip',
  `result_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'highest_level',
  `continuous_count` int DEFAULT '1',
  `cooldown_minutes` int DEFAULT '0',
  `cooldown_seconds` int DEFAULT '0',
  `current_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1',
  `rule_snapshot_json` json DEFAULT NULL,
  `action_policy_id` bigint DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_rule_project_code` (`project_id`,`rule_code`),
  KEY `idx_em_event_rule_project_metric` (`project_id`,`metric_code`),
  KEY `idx_em_event_rule_input_source` (`project_id`,`input_source`,`enabled`),
  KEY `idx_em_event_rule_enabled` (`project_id`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Executable custom event rules';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_rule_condition`
--

DROP TABLE IF EXISTS `em_event_rule_condition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_rule_condition` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rule_id` bigint NOT NULL,
  `level_id` bigint DEFAULT NULL,
  `condition_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `window_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `window_size` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aggregation_method` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operator` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `threshold_value` decimal(20,8) NOT NULL,
  `threshold_value_upper` decimal(20,8) DEFAULT NULL,
  `threshold_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reference_value_source` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `weight` decimal(10,4) DEFAULT NULL,
  `required` tinyint NOT NULL DEFAULT '1',
  `condition_json` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_rule_condition_code` (`rule_id`,`condition_code`),
  KEY `idx_em_rule_condition_rule` (`rule_id`),
  KEY `idx_em_rule_condition_level` (`level_id`),
  KEY `idx_em_rule_condition_metric` (`metric_code`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Atomic conditions under each custom rule level';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_rule_level`
--

DROP TABLE IF EXISTS `em_event_rule_level`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_rule_level` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rule_id` bigint NOT NULL,
  `level_code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'yellow/orange/red/custom',
  `level_rank` int NOT NULL,
  `action_policy_id` bigint DEFAULT NULL,
  `combine_logic` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'any',
  `explanation_template` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_rule_level_code` (`rule_id`,`level_code`),
  KEY `idx_em_rule_level_rule` (`rule_id`,`level_rank`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rule warning/event levels';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_rule_version`
--

DROP TABLE IF EXISTS `em_event_rule_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_rule_version` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rule_id` bigint NOT NULL,
  `version_no` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rule_snapshot_json` json NOT NULL,
  `created_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `change_note` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_rule_version` (`rule_id`,`version_no`),
  KEY `idx_em_rule_version_rule` (`rule_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rule version history for reproducibility';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_state_candidate_log`
--

DROP TABLE IF EXISTS `em_event_state_candidate_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_state_candidate_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `monitor_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `source_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RULE_EVENT',
  `event_id` bigint DEFAULT NULL,
  `event_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `previous_level` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `current_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `previous_rank` int DEFAULT NULL,
  `current_rank` int NOT NULL DEFAULT '0',
  `previous_value` decimal(20,8) DEFAULT NULL,
  `current_value` decimal(20,8) DEFAULT NULL,
  `transition_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `decision` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `decision_model_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'state-transition-v1',
  `action_required` tinyint NOT NULL DEFAULT '0',
  `reason` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content_digest` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `evidence_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_state_candidate_source` (`project_id`,`source_record_key`),
  KEY `idx_em_event_state_candidate_project` (`project_id`,`created_at`),
  KEY `idx_em_event_state_candidate_digest` (`project_id`,`input_digest`),
  KEY `idx_em_event_state_candidate_decision` (`decision`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SHM-EM event notification candidate decisions';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_event_state_transition`
--

DROP TABLE IF EXISTS `em_event_state_transition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_event_state_transition` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `monitor_key` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `source_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RULE_EVENT',
  `event_id` bigint DEFAULT NULL,
  `event_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `rule_id` bigint DEFAULT NULL,
  `previous_level` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `current_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `previous_rank` int DEFAULT NULL,
  `current_rank` int NOT NULL DEFAULT '0',
  `previous_value` decimal(20,8) DEFAULT NULL,
  `current_value` decimal(20,8) DEFAULT NULL,
  `transition_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `decision_model_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'state-transition-v1',
  `action_required` tinyint NOT NULL DEFAULT '1',
  `input_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `previous_state_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `current_state_digest` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `evidence_json` json DEFAULT NULL,
  `window_start` datetime(3) DEFAULT NULL,
  `window_end` datetime(3) DEFAULT NULL,
  `subject` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_emails` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notification_task_id` bigint DEFAULT NULL,
  `delivery_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'created',
  `reason` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_state_transition_source` (`project_id`,`source_record_key`),
  KEY `idx_em_event_state_transition_project` (`project_id`,`created_at`),
  KEY `idx_em_event_state_transition_digest` (`project_id`,`input_digest`),
  KEY `idx_em_event_state_transition_task` (`notification_task_id`),
  KEY `idx_em_event_state_transition_event` (`event_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SHM-EM event notification state transitions';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_evidence_resource`
--

DROP TABLE IF EXISTS `em_evidence_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_evidence_resource` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `resource_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'rule_snapshot/video/image/report/file/log',
  `resource_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `captured_at` datetime DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hash_value` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_evidence_source` (`project_id`,`source_record_key`),
  KEY `idx_em_evidence_project` (`project_id`,`created_at`),
  KEY `idx_em_evidence_station` (`station_id`,`captured_at`),
  KEY `idx_em_evidence_hash` (`hash_value`)
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Evidence resources';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_expected_output`
--

DROP TABLE IF EXISTS `em_expected_output`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_expected_output` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dataset_id` bigint DEFAULT NULL,
  `workflow_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_output_json` json NOT NULL,
  `expected_result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_expected_output` (`dataset_id`,`workflow_code`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Expected outputs for reproducibility checks';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_feature_operator`
--

DROP TABLE IF EXISTS `em_feature_operator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_feature_operator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `operator_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `input_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `window_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `formula_desc` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `formula_json` json DEFAULT NULL,
  `version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_feature_operator_version` (`operator_code`,`version`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Feature extraction operators';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_instrument`
--

DROP TABLE IF EXISTS `em_instrument`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_instrument` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Canonical device identifier within the project',
  `instrument_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instrument_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'static_level/displacement/earth_pressure/pressure_water_level/accelerometer/custom',
  `vendor` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtu_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `module_no` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `module_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `channel_no` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sampling_mode` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'low_frequency' COMMENT 'low_frequency/high_frequency/manual',
  `sampling_frequency` decimal(12,4) DEFAULT NULL,
  `raw_unit_desc` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `communication_mode` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protocol_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `install_location` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `installation_time` datetime DEFAULT NULL,
  `calibration_json` json DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'online',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_instrument_project_code` (`project_id`,`instrument_code`),
  KEY `idx_em_instrument_project` (`project_id`),
  KEY `idx_em_instrument_station` (`station_id`),
  KEY `idx_em_instrument_type` (`project_id`,`instrument_type`),
  KEY `idx_em_instrument_status` (`project_id`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sensors, instruments, acquisition devices';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_future_state_policy`
--

DROP TABLE IF EXISTS `em_future_state_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_future_state_policy` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint DEFAULT NULL COMMENT 'NULL applies to all projects',
  `policy_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `policy_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `policy_json` json NOT NULL,
  `policy_hash` char(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_future_state_policy` (`project_id`,`policy_code`,`policy_version`),
  KEY `idx_em_future_state_policy_active` (`project_id`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Versioned project future-state aggregation policy';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_metric`
--

DROP TABLE IF EXISTS `em_metric`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_metric` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metric_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metric_category` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'deformation/vibration/force/hydraulic/environment/device/quality/custom',
  `value_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'raw/engineering/feature/vector/status',
  `default_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `risk_direction` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'both' COMMENT 'increase/decrease/both/absolute',
  `description` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_metric_code` (`metric_code`),
  KEY `idx_em_metric_category` (`metric_category`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Canonical monitoring metric catalogue';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_metric_baseline_history`
--

DROP TABLE IF EXISTS `em_metric_baseline_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_metric_baseline_history` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_metric_id` bigint DEFAULT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `baseline_value` decimal(20,8) NOT NULL,
  `baseline_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_time` datetime(3) DEFAULT NULL,
  `effective_from` datetime(3) NOT NULL,
  `effective_to` datetime(3) DEFAULT NULL,
  `source_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'manual' COMMENT 'manual/validation/calibration/model',
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `approved_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_metric_baseline_source` (`project_id`,`source_record_key`),
  KEY `idx_em_metric_baseline_station_metric` (`station_metric_id`,`effective_from`),
  KEY `idx_em_metric_baseline_project_metric` (`project_id`,`metric_code`,`effective_from`),
  KEY `idx_em_metric_baseline_station` (`station_id`,`metric_code`,`effective_from`)
) ENGINE=InnoDB AUTO_INCREMENT=203 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Baseline value history for reproducible engineering-value conversion';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_monitoring_event`
--

DROP TABLE IF EXISTS `em_monitoring_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_monitoring_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rule_id` bigint DEFAULT NULL,
  `evaluation_run_id` bigint DEFAULT NULL,
  `event_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_level` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'new' COMMENT 'new/open/acknowledged/resolved/closed',
  `source_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'OBSERVATION' COMMENT 'OBSERVATION or FORECAST',
  `run_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'operational' COMMENT 'operational or reproduction',
  `detected_at` datetime(3) NOT NULL,
  `window_start` datetime(3) DEFAULT NULL,
  `window_end` datetime(3) DEFAULT NULL,
  `trigger_value` decimal(20,8) DEFAULT NULL,
  `threshold_value` decimal(20,8) DEFAULT NULL,
  `unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trigger_reason` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_registry_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calculation_snapshot_json` json DEFAULT NULL,
  `acknowledged_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acknowledged_at` datetime DEFAULT NULL,
  `resolved_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `closed_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `closed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_event_code` (`event_code`),
  KEY `idx_em_event_project_time` (`project_id`,`detected_at`),
  KEY `idx_em_event_level_status` (`event_level`,`event_status`),
  KEY `idx_em_event_source` (`project_id`,`source_type`,`detected_at`),
  KEY `idx_em_event_run_type` (`project_id`,`run_type`,`detected_at`),
  KEY `idx_em_event_station_metric` (`station_id`,`metric_code`),
  KEY `idx_em_event_rule` (`rule_id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Explainable monitoring events';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_notification_channel`
--

DROP TABLE IF EXISTS `em_notification_channel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_notification_channel` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `channel_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `channel_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `channel_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'email' COMMENT 'email',
  `endpoint` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auth_config_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_notification_channel` (`project_id`,`channel_code`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Notification channels';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_notification_delivery_log`
--

DROP TABLE IF EXISTS `em_notification_delivery_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_notification_delivery_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` bigint NOT NULL,
  `project_id` bigint NOT NULL,
  `subscriber_id` bigint DEFAULT NULL,
  `channel_id` bigint DEFAULT NULL,
  `recipient` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `delivery_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'email',
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `attempt_no` int NOT NULL DEFAULT '1',
  `provider_message_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `acknowledged_at` datetime DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `transition_id` bigint DEFAULT NULL COMMENT 'event state transition id',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_delivery_source` (`project_id`,`source_record_key`),
  KEY `idx_em_delivery_task` (`task_id`,`attempt_no`),
  KEY `idx_em_delivery_project_status` (`project_id`,`status`,`created_at`),
  KEY `idx_em_delivery_subscriber` (`subscriber_id`,`created_at`),
  KEY `idx_em_delivery_transition` (`transition_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Per-recipient notification delivery attempts and results';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_notification_subscriber`
--

DROP TABLE IF EXISTS `em_notification_subscriber`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_notification_subscriber` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `subscriber_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `subscriber_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_phone` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `channel_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'email' COMMENT 'email',
  `min_event_level` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'yellow',
  `infrastructure_scope` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `station_scope_json` json DEFAULT NULL,
  `instrument_scope_json` json DEFAULT NULL,
  `metric_scope_json` json DEFAULT NULL,
  `rule_scope_json` json DEFAULT NULL,
  `quiet_time_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_notification_subscriber` (`project_id`,`subscriber_code`),
  KEY `idx_em_notification_subscriber_project` (`project_id`,`enabled`),
  KEY `idx_em_notification_subscriber_level` (`project_id`,`min_event_level`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Notification subscribers and alert subscription scopes';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_notification_task`
--

DROP TABLE IF EXISTS `em_notification_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_notification_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` bigint DEFAULT NULL,
  `project_id` bigint NOT NULL,
  `channel_id` bigint DEFAULT NULL,
  `notification_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event_alert',
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content` text COLLATE utf8mb4_unicode_ci,
  `target_json` json DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `retry_count` int NOT NULL DEFAULT '0',
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `max_retry` int NOT NULL DEFAULT '3' COMMENT 'maximum retry count',
  `transition_id` bigint DEFAULT NULL COMMENT 'event state transition id',
  `action_backend` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'email' COMMENT 'email/webhook backend',
  `provenance_json` json DEFAULT NULL COMMENT 'state inference provenance for reproducible notification',
  `sending_time` datetime DEFAULT NULL COMMENT 'time when task entered sending',
  `last_attempt_time` datetime DEFAULT NULL COMMENT 'latest send attempt time',
  `next_retry_time` datetime DEFAULT NULL COMMENT 'next allowed retry time',
  `attachment_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'notification attachment path',
  `attachment_format` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'attachment format',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_notification_source` (`project_id`,`source_record_key`),
  KEY `idx_em_notification_event` (`event_id`),
  KEY `idx_em_notification_project` (`project_id`,`created_at`),
  KEY `idx_em_notification_status` (`status`,`created_at`),
  KEY `idx_em_notification_pending` (`status`,`next_retry_time`,`retry_count`,`created_at`),
  KEY `idx_em_notification_transition` (`transition_id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Notification tasks generated by events';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_obs_acceleration_feature`
--

DROP TABLE IF EXISTS `em_obs_acceleration_feature`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_obs_acceleration_feature` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint NOT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `window_start` datetime(3) NOT NULL,
  `window_end` datetime(3) NOT NULL,
  `metric_value` decimal(20,10) NOT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_batch_id` bigint DEFAULT NULL,
  `feature_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_version` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'v1',
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_accel_feature_once` (`source_batch_id`,`metric_code`,`feature_version`),
  KEY `idx_em_accel_feature_project_metric_time` (`project_id`,`metric_code`,`window_start`),
  KEY `idx_em_accel_feature_instrument_time` (`instrument_id`,`window_start`)
) ENGINE=InnoDB AUTO_INCREMENT=2956 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Derived high-frequency features such as PGA/RMS/peak vector';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_obs_displacement`
--

DROP TABLE IF EXISTS `em_obs_displacement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_obs_displacement` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineering_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observed_at` datetime(3) NOT NULL,
  `raw_value` decimal(20,8) DEFAULT NULL,
  `raw_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_value` decimal(20,8) DEFAULT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_value` decimal(20,8) DEFAULT NULL,
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'v1',
  `conversion_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `conversion_remark` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_obs_lf_source` (`project_id`,`source_record_key`),
  KEY `idx_em_obs_lf_project_metric_time` (`project_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_station_metric_time` (`station_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_instrument_time` (`instrument_id`,`observed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=310904 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Displacement / inclinometer / tilt observations';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_obs_earth_pressure`
--

DROP TABLE IF EXISTS `em_obs_earth_pressure`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_obs_earth_pressure` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineering_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observed_at` datetime(3) NOT NULL,
  `raw_value` decimal(20,8) DEFAULT NULL,
  `raw_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_value` decimal(20,8) DEFAULT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_value` decimal(20,8) DEFAULT NULL,
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'v1',
  `conversion_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `conversion_remark` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_obs_lf_source` (`project_id`,`source_record_key`),
  KEY `idx_em_obs_lf_project_metric_time` (`project_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_station_metric_time` (`station_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_instrument_time` (`instrument_id`,`observed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=65301 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Earth pressure cell observations';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_obs_pressure_water_level`
--

DROP TABLE IF EXISTS `em_obs_pressure_water_level`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_obs_pressure_water_level` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineering_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observed_at` datetime(3) NOT NULL,
  `raw_value` decimal(20,8) DEFAULT NULL,
  `raw_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_value` decimal(20,8) DEFAULT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_value` decimal(20,8) DEFAULT NULL,
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'v1',
  `conversion_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `conversion_remark` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_obs_lf_source` (`project_id`,`source_record_key`),
  KEY `idx_em_obs_lf_project_metric_time` (`project_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_station_metric_time` (`station_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_instrument_time` (`instrument_id`,`observed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=31550 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Pressure water level observations';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_obs_static_level`
--

DROP TABLE IF EXISTS `em_obs_static_level`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_obs_static_level` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineering_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observed_at` datetime(3) NOT NULL,
  `raw_value` decimal(20,8) DEFAULT NULL,
  `raw_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_value` decimal(20,8) DEFAULT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_value` decimal(20,8) DEFAULT NULL,
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'v1',
  `conversion_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `conversion_remark` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_obs_lf_source` (`project_id`,`source_record_key`),
  KEY `idx_em_obs_lf_project_metric_time` (`project_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_station_metric_time` (`station_id`,`metric_code`,`observed_at`),
  KEY `idx_em_obs_lf_instrument_time` (`instrument_id`,`observed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=60767 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Static level / settlement observations';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_observation_table_registry`
--

DROP TABLE IF EXISTS `em_observation_table_registry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_observation_table_registry` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `registry_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint DEFAULT NULL,
  `instrument_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_group` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `storage_backend` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'mysql' COMMENT 'mysql/timescaledb/influxdb/tdengine/file',
  `storage_mode` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'type_table/sensor_table/project_table/tsdb_measurement',
  `logical_series_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `physical_table_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `schema_version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1',
  `sample_frequency_hz` decimal(12,4) DEFAULT NULL,
  `time_precision` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'millisecond',
  `is_queryable` tinyint NOT NULL DEFAULT '1',
  `is_event_source` tinyint NOT NULL DEFAULT '1',
  `partition_strategy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `retention_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `downsample_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `access_policy_json` json DEFAULT NULL,
  `field_mapping_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_registry_code` (`registry_code`),
  KEY `idx_em_registry_project` (`project_id`),
  KEY `idx_em_registry_instrument` (`instrument_id`),
  KEY `idx_em_registry_backend_mode` (`storage_backend`,`storage_mode`),
  KEY `idx_em_registry_queryable` (`is_queryable`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Whitelist and routing metadata for observation tables or TSDB measurements';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_prediction_batch`
--

DROP TABLE IF EXISTS `em_prediction_batch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_batch` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `batch_code` varchar(96) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `base_time` datetime(3) NOT NULL,
  `time_step_minutes` int NOT NULL DEFAULT '3',
  `horizon_minutes` int NOT NULL DEFAULT '120',
  `rolling_steps` int NOT NULL DEFAULT '40',
  `model_count` int NOT NULL DEFAULT '0',
  `feature_count` int NOT NULL DEFAULT '0',
  `pipeline_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pit_pre_v1',
  `feature_mapping_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pit_pre_v1',
  `input_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `output_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'running',
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime(3) DEFAULT NULL,
  `finished_at` datetime(3) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_prediction_batch_code` (`batch_code`),
  KEY `idx_em_prediction_batch_project_time` (`project_id`,`base_time`),
  KEY `idx_em_prediction_batch_status` (`project_id`,`status`,`base_time`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core prediction batch for synchronized multi-model rolling forecasts';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary view structure for view `em_prediction_display`
--

DROP TABLE IF EXISTS `em_prediction_display`;
/*!50001 DROP VIEW IF EXISTS `em_prediction_display`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `em_prediction_display` AS SELECT 
 1 AS `id`,
 1 AS `project_id`,
 1 AS `batch_id`,
 1 AS `batch_code`,
 1 AS `run_id`,
 1 AS `model_id`,
 1 AS `model_code`,
 1 AS `model_version`,
 1 AS `target_type`,
 1 AS `feature_code`,
 1 AS `feature_label`,
 1 AS `station_id`,
 1 AS `station_name`,
 1 AS `instrument_id`,
 1 AS `instrument_code`,
 1 AS `metric_code`,
 1 AS `step`,
 1 AS `horizon_minutes`,
 1 AS `base_time`,
 1 AS `future_time`,
 1 AS `predicted_value`,
 1 AS `predicted_unit`,
 1 AS `lower_bound`,
 1 AS `upper_bound`,
 1 AS `confidence`,
 1 AS `quality_flag`,
 1 AS `source_record_key`,
 1 AS `created_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `em_prediction_feature_mapping`
--

DROP TABLE IF EXISTS `em_prediction_feature_mapping`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_feature_mapping` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `model_id` bigint DEFAULT NULL,
  `feature_code` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_label` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `training_feature_code` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_group` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'model_input',
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `source_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_registry_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_field` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'metric_value',
  `source_value_column` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'metric_value',
  `input_value_mode` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RAW',
  `schema_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pit_pre_v1',
  `feature_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `output_conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `output_conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `window_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `window_size_seconds` int DEFAULT NULL,
  `feature_order` int NOT NULL DEFAULT '0',
  `required` tinyint NOT NULL DEFAULT '1',
  `prediction_target` tinyint NOT NULL DEFAULT '0',
  `transform_json` json DEFAULT NULL,
  `metadata_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_prediction_feature_schema` (`project_id`,`schema_version`,`feature_code`),
  UNIQUE KEY `uk_em_prediction_feature` (`project_id`,`model_id`,`feature_code`),
  KEY `idx_em_prediction_feature_model` (`model_id`,`feature_order`),
  KEY `idx_em_prediction_feature_metric` (`project_id`,`source_metric_code`,`enabled`),
  KEY `idx_em_prediction_feature_target` (`project_id`,`target_type`,`enabled`,`feature_order`),
  KEY `idx_em_prediction_feature_object` (`station_id`,`instrument_id`,`source_metric_code`)
) ENGINE=InnoDB AUTO_INCREMENT=1119 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Registry-to-model feature mapping for reproducible PIT_PRE model inputs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_prediction_execution_gate`
--

DROP TABLE IF EXISTS `em_prediction_execution_gate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_execution_gate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `batch_id` bigint NOT NULL,
  `project_id` bigint NOT NULL,
  `batch_code` varchar(96) COLLATE utf8mb4_unicode_ci NOT NULL,
  `execution_mode` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'OPERATIONAL, REPLAY, or REPRODUCTION',
  `reference_time` datetime(3) NOT NULL,
  `contract_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contract_fingerprint` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_model_count` int NOT NULL,
  `actual_model_count` int NOT NULL,
  `successful_model_count` int NOT NULL,
  `expected_feature_count` int NOT NULL,
  `actual_feature_count` int NOT NULL,
  `expected_steps` int NOT NULL,
  `expected_point_count` int NOT NULL,
  `actual_point_count` int NOT NULL,
  `missing_point_count` int NOT NULL,
  `invalid_timestamp_count` int NOT NULL DEFAULT '0',
  `quality_issue_count` int NOT NULL DEFAULT '0',
  `base_time_age_minutes` bigint DEFAULT NULL,
  `max_age_minutes` int DEFAULT NULL,
  `model_set_valid` tinyint NOT NULL DEFAULT '0',
  `feature_set_valid` tinyint NOT NULL DEFAULT '0',
  `timeline_valid` tinyint NOT NULL DEFAULT '0',
  `quality_valid` tinyint NOT NULL DEFAULT '0',
  `artifact_hash_valid` tinyint NOT NULL DEFAULT '0',
  `freshness_valid` tinyint NOT NULL DEFAULT '0',
  `execution_eligible` tinyint NOT NULL DEFAULT '0',
  `issues_json` json NOT NULL,
  `missing_models_json` json NOT NULL,
  `unexpected_models_json` json NOT NULL,
  `missing_features_json` json NOT NULL,
  `unexpected_features_json` json NOT NULL,
  `missing_timeline_points_json` json NOT NULL,
  `target_summary_json` json NOT NULL,
  `gate_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `evaluated_at` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_prediction_gate_identity` (`batch_id`,`execution_mode`,`gate_hash`),
  KEY `idx_em_prediction_gate_project_time` (`project_id`,`evaluated_at`),
  KEY `idx_em_prediction_gate_eligibility` (`project_id`,`execution_mode`,`execution_eligible`,`evaluated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Immutable prediction execution eligibility decision derived from database model contracts';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_prediction_model`
--

DROP TABLE IF EXISTS `em_prediction_model`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_model` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint DEFAULT NULL,
  `model_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'rolling_forecast',
  `target_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_metrics_json` json DEFAULT NULL,
  `artifact_uri` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `artifact_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preprocessor_uri` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preprocessor_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inference_script_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `best_params_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runtime_manifest_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `environment_digest` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `artifact_bundle_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1',
  `runtime_config_json` json DEFAULT NULL,
  `required_history_rows` int DEFAULT NULL,
  `input_schema_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pit_pre_contract_v1',
  `expected_steps` int NOT NULL DEFAULT '40',
  `time_step_minutes` int NOT NULL DEFAULT '3',
  `max_operational_age_minutes` int NOT NULL DEFAULT '15',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_prediction_model` (`project_id`,`model_code`,`model_version`),
  KEY `idx_em_prediction_model_project` (`project_id`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core prediction model registry';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_prediction_result`
--

DROP TABLE IF EXISTS `em_prediction_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_result` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` bigint DEFAULT NULL,
  `batch_id` bigint DEFAULT NULL,
  `model_id` bigint DEFAULT NULL,
  `target_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_code` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feature_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step` int DEFAULT NULL,
  `horizon_minutes` int DEFAULT NULL,
  `base_time` datetime(3) DEFAULT NULL,
  `future_time` datetime(3) DEFAULT NULL,
  `project_id` bigint NOT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `predicted_at` datetime(3) DEFAULT NULL,
  `prediction_time` datetime(3) NOT NULL,
  `raw_predicted_value` decimal(20,8) DEFAULT NULL,
  `raw_predicted_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `predicted_value` decimal(20,8) NOT NULL,
  `predicted_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `engineering_metric_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `engineering_value` decimal(20,8) DEFAULT NULL,
  `engineering_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `engineering_lower_bound` decimal(20,8) DEFAULT NULL,
  `engineering_upper_bound` decimal(20,8) DEFAULT NULL,
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `conversion_remark` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lower_bound` decimal(20,8) DEFAULT NULL,
  `upper_bound` decimal(20,8) DEFAULT NULL,
  `confidence` decimal(8,6) DEFAULT NULL,
  `quality_flag` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_prediction_source` (`project_id`,`source_record_key`),
  KEY `idx_em_prediction_result_run` (`run_id`,`prediction_time`),
  KEY `idx_em_prediction_result_project_metric_time` (`project_id`,`metric_code`,`prediction_time`),
  KEY `idx_em_prediction_result_station_time` (`station_id`,`prediction_time`),
  KEY `idx_em_prediction_result_batch_feature` (`batch_id`,`target_type`,`feature_code`,`step`),
  KEY `idx_em_prediction_result_latest_feature` (`project_id`,`target_type`,`feature_code`,`base_time`,`step`)
) ENGINE=InnoDB AUTO_INCREMENT=19621 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core prediction time-series results with forecast horizon and model provenance';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_prediction_run`
--

DROP TABLE IF EXISTS `em_prediction_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_prediction_run` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `batch_id` bigint DEFAULT NULL,
  `model_id` bigint DEFAULT NULL,
  `model_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model_version` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `artifact_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preprocessor_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inference_script_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `best_params_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runtime_manifest_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `environment_digest` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `artifact_bundle_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_schema_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `required_history_rows` int DEFAULT NULL,
  `station_id` bigint DEFAULT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_window_start` datetime(3) DEFAULT NULL,
  `input_window_end` datetime(3) DEFAULT NULL,
  `horizon_seconds` int DEFAULT NULL,
  `horizon_minutes` int DEFAULT NULL,
  `rolling_steps` int DEFAULT NULL,
  `input_snapshot_json` json DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'success',
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runtime_seconds` decimal(12,4) DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_prediction_run_project_time` (`project_id`,`created_at`),
  KEY `idx_em_prediction_run_model` (`model_id`,`created_at`),
  KEY `idx_em_prediction_run_station_metric` (`station_id`,`metric_code`,`created_at`),
  KEY `idx_em_prediction_run_batch` (`batch_id`,`model_id`),
  KEY `idx_em_prediction_run_target` (`project_id`,`target_type`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core prediction model run under a synchronized forecast batch';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_project`
--

DROP TABLE IF EXISTS `em_project`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_project` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `infrastructure_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'excavation/bridge/tunnel/slope/dam/building/generic',
  `scenario_label` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location_text` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` decimal(12,8) DEFAULT NULL,
  `latitude` decimal(12,8) DEFAULT NULL,
  `coordinate_system` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'local_layout',
  `coordinate_source` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT 'manual',
  `coordinate_quality` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'unverified',
  `map_provider` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spatial_context_json` json DEFAULT NULL COMMENT 'boundary, layout image, GIS metadata, BIM link, site map config',
  `description` text COLLATE utf8mb4_unicode_ci,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_project_code` (`project_code`),
  KEY `idx_em_project_type_status` (`infrastructure_type`,`status`),
  KEY `idx_em_project_geo` (`longitude`,`latitude`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Engineering project atlas and scenario context';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_report_instance`
--

DROP TABLE IF EXISTS `em_report_instance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_report_instance` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `event_id` bigint DEFAULT NULL,
  `template_id` bigint DEFAULT NULL,
  `report_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event',
  `report_title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content_html` longtext COLLATE utf8mb4_unicode_ci,
  `content_text` longtext COLLATE utf8mb4_unicode_ci,
  `docx_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pdf_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `report_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `report_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'generated',
  `generated_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `generated_at` datetime DEFAULT NULL,
  `source_record_key` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metadata_json` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_report_source` (`project_id`,`source_record_key`),
  KEY `idx_em_report_project` (`project_id`,`generated_at`),
  KEY `idx_em_report_event` (`event_id`),
  KEY `idx_em_report_status` (`status`,`generated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Generated reports';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_report_template`
--

DROP TABLE IF EXISTS `em_report_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_report_template` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint DEFAULT NULL,
  `template_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `template_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `report_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'daily/weekly/event/replay/custom',
  `title_template` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `body_template` longtext COLLATE utf8mb4_unicode_ci,
  `template_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `template_schema_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_report_template` (`project_id`,`template_code`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Report templates';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_scenario_profile`
--

DROP TABLE IF EXISTS `em_scenario_profile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_scenario_profile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `scenario_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scenario_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `infrastructure_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `metric_schema_json` json DEFAULT NULL,
  `rule_schema_json` json DEFAULT NULL,
  `ui_schema_json` json DEFAULT NULL,
  `enabled` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_scenario_code` (`scenario_code`),
  KEY `idx_em_scenario_type` (`infrastructure_type`,`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Scenario configuration layer; excavation/bridge/tunnel are configurations, not core branches';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_station`
--

DROP TABLE IF EXISTS `em_station`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_station` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `station_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `station_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'settlement/displacement/vibration/strain/earth_pressure/water_level/custom',
  `position_desc` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` decimal(12,8) DEFAULT NULL,
  `latitude` decimal(12,8) DEFAULT NULL,
  `x` decimal(18,6) DEFAULT NULL,
  `y` decimal(18,6) DEFAULT NULL,
  `z` decimal(18,6) DEFAULT NULL,
  `layout_x` decimal(18,6) DEFAULT NULL,
  `layout_y` decimal(18,6) DEFAULT NULL,
  `elevation` decimal(18,6) DEFAULT NULL,
  `installation_time` datetime DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_station_project_code` (`project_id`,`station_code`),
  KEY `idx_em_station_project` (`project_id`),
  KEY `idx_em_station_type` (`project_id`,`station_type`),
  KEY `idx_em_station_layout` (`project_id`,`layout_x`,`layout_y`)
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sensor attachment and installation-position records; not the field monitoring-point count';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_station_metric`
--

DROP TABLE IF EXISTS `em_station_metric`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_station_metric` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `station_id` bigint NOT NULL,
  `instrument_id` bigint DEFAULT NULL,
  `metric_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `raw_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metric_unit` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conversion_operator_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `baseline_value` decimal(20,8) DEFAULT NULL,
  `baseline_time` datetime(3) DEFAULT NULL,
  `warning_enabled` tinyint NOT NULL DEFAULT '1',
  `display_order` int DEFAULT '0',
  `enabled` tinyint NOT NULL DEFAULT '1',
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_station_metric` (`station_id`,`instrument_id`,`metric_code`),
  KEY `idx_em_sm_project` (`project_id`),
  KEY `idx_em_sm_metric` (`project_id`,`metric_code`),
  KEY `idx_em_sm_instrument` (`instrument_id`)
) ENGINE=InnoDB AUTO_INCREMENT=491 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Station-instrument-metric binding';
/*!40101 SET character_set_client = @saved_cs_client */;





--
-- Table structure for table `em_workflow_run`
--

DROP TABLE IF EXISTS `em_workflow_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_workflow_run` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `dataset_id` bigint DEFAULT NULL,
  `workflow_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `workflow_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'validation',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'running',
  `input_params_json` json DEFAULT NULL,
  `output_summary_json` json DEFAULT NULL,
  `expected_output_json` json DEFAULT NULL,
  `actual_output_json` json DEFAULT NULL,
  `result_hash` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `created_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_em_workflow_project` (`project_id`,`started_at`),
  KEY `idx_em_workflow_dataset` (`dataset_id`),
  KEY `idx_em_workflow_hash` (`result_hash`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Reproducible workflow runs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `em_workflow_run_step`
--

DROP TABLE IF EXISTS `em_workflow_run_step`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `em_workflow_run_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `workflow_run_id` bigint NOT NULL,
  `step_order` int NOT NULL,
  `step_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `step_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `input_snapshot_json` json DEFAULT NULL,
  `output_snapshot_json` json DEFAULT NULL,
  `message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_em_workflow_step` (`workflow_run_id`,`step_code`),
  KEY `idx_em_workflow_step_run` (`workflow_run_id`,`step_order`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Steps of reproducible workflow runs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Final view structure for view `em_prediction_display`
--

DROP VIEW IF EXISTS `em_prediction_display`;
CREATE VIEW `em_prediction_display` AS
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
       COALESCE(r.engineering_value, r.raw_predicted_value, r.predicted_value) AS predicted_value,
       COALESCE(r.engineering_unit, r.raw_predicted_unit, r.predicted_unit) AS predicted_unit,
       r.raw_predicted_value,
       r.raw_predicted_unit,
       r.engineering_value,
       r.engineering_unit,
       COALESCE(r.engineering_lower_bound, r.lower_bound) AS lower_bound,
       COALESCE(r.engineering_upper_bound, r.upper_bound) AS upper_bound,
       r.lower_bound AS raw_lower_bound,
       r.upper_bound AS raw_upper_bound,
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

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-12 16:16:09
