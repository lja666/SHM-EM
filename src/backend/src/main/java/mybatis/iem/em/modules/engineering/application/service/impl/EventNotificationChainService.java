package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.json.JSONArray;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class EventNotificationChainService {
    private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String STATE_SCHEMA_VERSION = "state-current";
    private static final String DECISION_MODEL_VERSION = "state-transition-current";

    private final JdbcTemplate jdbcTemplate;
    private final NotificationTaskService taskService;
    private final EventNotificationDecisionPolicy decisionPolicy = new EventNotificationDecisionPolicy();

    @Value("${shm-em.notification.enabled:true}")
    private boolean enabled;
    @Value("${shm-em.notification.task-create-enabled:true}")
    private boolean taskCreateEnabled;
    @Value("${shm-em.notification.same-level-cooldown-minutes:60}")
    private int sameLevelCooldownMinutes;
    @Value("${shm-em.notification.persistent-reminder-minutes:720}")
    private int persistentReminderMinutes;
    @Value("${shm-em.notification.red-reminder-minutes:180}")
    private int redReminderMinutes;
    @Value("${shm-em.notification.significant-change-percent:50}")
    private BigDecimal significantChangePercent;
    @Value("${shm-em.notification.significant-change-absolute:0}")
    private BigDecimal significantChangeAbsolute;

    public EventNotificationChainService(JdbcTemplate jdbcTemplate,
                                         NotificationTaskService taskService) {
        this.jdbcTemplate = jdbcTemplate;
        this.taskService = taskService;
    }

    public NotificationPlan processEvent(Event event) {
        NotificationPlan plan = new NotificationPlan();
        if (!enabled || event == null || event.getProjectId() == null || event.getId() == null) {
            plan.decision = "disabled_or_invalid";
            return plan;
        }
        EventStateInput input = fromEvent(event);
        return processInput(input);
    }

    public NotificationPlan processNormalObservation(EventRule rule, List<MetricSeriesPoint> observations) {
        NotificationPlan plan = new NotificationPlan();
        if (!enabled || rule == null) {
            plan.decision = "disabled_or_invalid";
            return plan;
        }
        MetricSeriesPoint latest = latestObservation(rule, observations);
        Long projectId = latest == null || latest.getProjectId() == null ? rule.getProjectId() : latest.getProjectId();
        if (latest == null || projectId == null) {
            plan.decision = "disabled_or_invalid";
            plan.reason = "no observation available for normal-state notification";
            return plan;
        }
        EventStateInput input = new EventStateInput();
        input.projectId = projectId;
        input.eventId = null;
        input.eventCode = "NORMAL-" + nullText(rule.getId()) + "-" + format(latest.getTimestamp()).replace(" ", "-").replace(":", "");
        input.sourceType = "RULE_EVENT";
        input.stationId = latest.getStationId();
        input.instrumentId = latest.getInstrumentId();
        input.metricCode = defaultIfBlank(rule.getMetricCode(), defaultIfBlank(latest.getMetricCode(), ""));
        input.ruleId = rule.getId();
        input.currentLevel = "NORMAL";
        input.currentValue = latest.getValue();
        input.windowStart = latest.getTimestamp();
        input.windowEnd = latest.getTimestamp();
        input.reason = "Rule execution no longer triggers the threshold; event state recovered to NORMAL";
        input.eventType = rule.getEventType();
        input.unit = defaultIfBlank(latest.getUnit(), rule.getThresholdUnit());
        input.monitorKey = monitorKey(input);
        return processInput(input);
    }

    private NotificationPlan processInput(EventStateInput input) {
        NotificationPlan plan = new NotificationPlan();
        Map<String, Object> state = findState(input.monitorKey);
        if (state == null && decisionPolicy.levelRank(input.currentLevel) == 0) {
            plan.decision = "NO_ACTIVE_STATE";
            plan.reason = "No existing abnormal state; recovery notification is not required";
            return plan;
        }
        String previousLevel = state == null ? "NORMAL" : decisionPolicy.normalizeLevel(string(state.get("current_level")));
        BigDecimal previousValue = state == null ? null : toBigDecimal(state.get("current_value"));

        EventNotificationDecisionPolicy.Input policyInput = new EventNotificationDecisionPolicy.Input();
        policyInput.hasState = state != null;
        policyInput.previousLevel = previousLevel;
        policyInput.currentLevel = input.currentLevel;
        policyInput.currentValue = input.currentValue;
        policyInput.lastNotificationAt = toLocalDateTime(state == null ? null : state.get("last_notification_at"));
        policyInput.lastNotificationValue = toBigDecimal(state == null ? null : state.get("last_notification_value"));
        policyInput.sameLevelCooldownMinutes = sameLevelCooldownMinutes;
        policyInput.persistentReminderMinutes = persistentReminderMinutes;
        policyInput.redReminderMinutes = redReminderMinutes;
        policyInput.significantChangePercent = significantChangePercent;
        policyInput.significantChangeAbsolute = significantChangeAbsolute;

        EventNotificationDecisionPolicy.Decision decision = decisionPolicy.decide(policyInput);
        DecisionTrace trace = buildTrace(input, previousLevel, previousValue, decision);
        plan.decision = decision.transitionType;
        plan.reason = decision.reason;
        recordCandidate(input, previousLevel, previousValue, decision, trace);
        upsertState(input, decision, trace);
        if (!decision.createTransition) return plan;

        Long transitionId = insertTransition(input, previousLevel, previousValue, decision, trace);
        plan.transitionId = transitionId;
        if (transitionId == null || !taskCreateEnabled) return plan;

        String recipients = resolveRecipients(input, previousLevel, decision.transitionType);
        if (!hasText(recipients)) {
            markTransitionNoRecipient(transitionId);
            plan.deliveryStatus = "no_recipient";
            return plan;
        }
        Long channelId = selectPreferredChannel(input.projectId);
        String sourceKey = "event_notification_task:" + input.projectId + ":" + transitionId;
        NotificationTaskService.TaskDraft draft = new NotificationTaskService.TaskDraft();
        draft.projectId = input.projectId;
        draft.eventId = input.eventId;
        draft.channelId = channelId;
        draft.transitionId = transitionId;
        draft.notificationType = notificationType(input, decision.transitionType);
        draft.subject = buildSubject(input, previousLevel, decision.transitionType);
        draft.contentHtml = buildHtml(input, previousLevel, previousValue, decision);
        draft.toEmails = recipients;
        draft.message = "created by SHM-EM event notification chain";
        draft.sourceRecordKey = sourceKey;
        draft.provenanceJson = trace.evidenceJson;
        Long taskId = taskService.createTask(draft);
        jdbcTemplate.update("UPDATE em_event_state_transition SET notification_task_id=?, delivery_status='pending', "
                + "recipient_emails=?, subject=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                taskId, recipients, draft.subject, transitionId);
        plan.taskId = taskId;
        plan.deliveryStatus = "pending";
        return plan;
    }

    public List<Map<String, Object>> listTransitions(Long projectId, String transitionType, String deliveryStatus, Integer limit) {
        StringBuilder sql = new StringBuilder("SELECT id, source_record_key AS sourceRecordKey, monitor_key AS monitorKey, "
                + "project_id AS projectId, source_type AS sourceType, event_id AS eventId, event_code AS eventCode, "
                + "station_id AS stationId, instrument_id AS instrumentId, metric_code AS metricCode, rule_id AS ruleId, "
                + "previous_level AS previousLevel, current_level AS currentLevel, previous_value AS previousValue, "
                + "current_value AS currentValue, previous_rank AS previousRank, current_rank AS currentRank, "
                + "transition_type AS transitionType, decision_model_version AS decisionModelVersion, action_required AS actionRequired, "
                + "input_digest AS inputDigest, previous_state_digest AS previousStateDigest, current_state_digest AS currentStateDigest, "
                + "evidence_json AS evidenceJson, window_start AS windowStart, "
                + "window_end AS windowEnd, subject, recipient_emails AS recipientEmails, notification_task_id AS notificationTaskId, "
                + "delivery_status AS deliveryStatus, reason, created_at AS createdAt, updated_at AS updatedAt "
                + "FROM em_event_state_transition WHERE 1=1 ");
        List<Object> args = new ArrayList<Object>();
        if (projectId != null) {
            sql.append("AND project_id=? ");
            args.add(projectId);
        }
        if (hasText(transitionType)) {
            sql.append("AND transition_type=? ");
            args.add(transitionType.trim());
        }
        if (hasText(deliveryStatus)) {
            sql.append("AND delivery_status=? ");
            args.add(deliveryStatus.trim());
        }
        sql.append("ORDER BY created_at DESC, id DESC LIMIT ?");
        args.add(normalizeLimit(limit));
        return jdbcTemplate.queryForList(sql.toString(), args.toArray());
    }

    public List<Map<String, Object>> listSubscribers(Long projectId, String channelType, Integer enabledOnly) {
        StringBuilder sql = new StringBuilder("SELECT id, project_id AS projectId, subscriber_code AS subscriberCode, "
                + "subscriber_name AS subscriberName, contact_email AS contactEmail, contact_phone AS contactPhone, "
                + "channel_type AS channelType, min_event_level AS minEventLevel, infrastructure_scope AS infrastructureScope, "
                + "station_scope_json AS stationScopeJson, instrument_scope_json AS instrumentScopeJson, metric_scope_json AS metricScopeJson, "
                + "rule_scope_json AS ruleScopeJson, quiet_time_json AS quietTimeJson, enabled, remark, created_at AS createdAt, updated_at AS updatedAt "
                + "FROM em_notification_subscriber WHERE 1=1 ");
        List<Object> args = new ArrayList<Object>();
        if (projectId != null) {
            sql.append("AND project_id=? ");
            args.add(projectId);
        }
        if (hasText(channelType)) {
            sql.append("AND channel_type=? ");
            args.add(channelType.trim());
        }
        if (enabledOnly != null) {
            sql.append("AND enabled=? ");
            args.add(enabledOnly);
        }
        sql.append("ORDER BY project_id ASC, enabled DESC, subscriber_code ASC, id DESC");
        return jdbcTemplate.queryForList(sql.toString(), args.toArray());
    }

    private EventStateInput fromEvent(Event event) {
        EventStateInput input = new EventStateInput();
        input.projectId = event.getProjectId();
        input.eventId = event.getId();
        input.eventCode = event.getEventCode();
        input.sourceType = "RULE_EVENT";
        input.stationId = event.getStationId();
        input.instrumentId = event.getInstrumentId();
        input.metricCode = defaultIfBlank(event.getMetricCode(), "");
        input.ruleId = event.getRuleId();
        input.currentLevel = decisionPolicy.normalizeLevel(event.getEventLevel());
        input.currentValue = event.getTriggerValue();
        input.windowStart = event.getWindowStart();
        input.windowEnd = event.getWindowEnd();
        input.reason = event.getTriggerReason();
        input.eventType = event.getEventType();
        input.unit = event.getUnit();
        input.monitorKey = monitorKey(input);
        return input;
    }

    private String resolveRecipients(EventStateInput input, String previousLevel, String transitionType) {
        int matchRank = ("RECOVERY".equals(transitionType) || "LEVEL_DOWN".equals(transitionType))
                ? Math.max(decisionPolicy.levelRank(previousLevel), decisionPolicy.levelRank(input.currentLevel))
                : decisionPolicy.levelRank(input.currentLevel);
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT * FROM em_notification_subscriber WHERE project_id=? AND enabled=1 AND channel_type='email' ORDER BY id ASC",
                input.projectId);
        Set<String> recipients = new LinkedHashSet<String>();
        for (Map<String, Object> row : rows) {
            if (matchRank < decisionPolicy.levelRank(string(row.get("min_event_level")))) continue;
            if (!scopeMatches(string(row.get("station_scope_json")), input.stationId, null)) continue;
            if (!scopeMatches(string(row.get("instrument_scope_json")), input.instrumentId, null)) continue;
            if (!scopeMatches(string(row.get("metric_scope_json")), null, input.metricCode)) continue;
            if (!scopeMatches(string(row.get("rule_scope_json")), input.ruleId, null)) continue;
            String[] emails = NotificationAddressUtils.parseValidArray(string(row.get("contact_email")));
            for (String email : emails) recipients.add(email);
        }
        return join(recipients);
    }

    private Long selectPreferredChannel(Long projectId) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id FROM em_notification_channel WHERE project_id=? AND enabled=1 "
                        + "AND channel_type='email' ORDER BY id ASC LIMIT 1",
                projectId);
        return rows.isEmpty() ? null : toLong(rows.get(0).get("id"));
    }

    private Map<String, Object> findState(String monitorKey) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList("SELECT * FROM em_event_notification_state WHERE monitor_key=? LIMIT 1", monitorKey);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private void recordCandidate(EventStateInput input, String previousLevel, BigDecimal previousValue,
                                 EventNotificationDecisionPolicy.Decision decision, DecisionTrace trace) {
        String digest = sha256(input.monitorKey + "|" + input.eventId + "|" + format(input.windowEnd) + "|" + previousLevel + "|" + input.currentLevel
                + "|" + previousValue + "|" + input.currentValue + "|" + decision.transitionType + "|" + input.reason
                + "|" + trace.inputDigest);
        String sourceKey = "event_notification_candidate:" + input.projectId + ":" + digest;
        jdbcTemplate.update("INSERT IGNORE INTO em_event_state_candidate_log(source_record_key, monitor_key, project_id, source_type, "
                        + "event_id, event_code, metric_code, previous_level, current_level, previous_value, current_value, "
                        + "previous_rank, current_rank, transition_type, decision, decision_model_version, action_required, "
                        + "reason, input_digest, state_digest, content_digest, evidence_json, created_at) "
                        + "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                sourceKey, input.monitorKey, input.projectId, input.sourceType, input.eventId, input.eventCode, input.metricCode,
                previousLevel, input.currentLevel, previousValue, input.currentValue, trace.previousRank, trace.currentRank,
                decision.transitionType, decision.createTransition ? "TRANSITION_CREATED" : "SUPPRESSED",
                DECISION_MODEL_VERSION, decision.createTransition ? 1 : 0, truncate(decision.reason, 1000),
                trace.inputDigest, trace.currentStateDigest, digest, trace.evidenceJson);
    }

    private void upsertState(EventStateInput input, EventNotificationDecisionPolicy.Decision decision, DecisionTrace trace) {
        jdbcTemplate.update("INSERT INTO em_event_notification_state(monitor_key, project_id, source_type, station_id, instrument_id, "
                        + "metric_code, rule_id, state_schema_version, decision_model_version, current_level, current_rank, current_value, "
                        + "current_event_id, current_event_code, last_transition_type, last_transition_at, last_input_digest, last_state_digest, state_vector_json) "
                        + "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END,?,?,?) "
                        + "ON DUPLICATE KEY UPDATE state_schema_version=VALUES(state_schema_version), decision_model_version=VALUES(decision_model_version), "
                        + "current_level=VALUES(current_level), current_rank=VALUES(current_rank), current_value=VALUES(current_value), "
                        + "current_event_id=VALUES(current_event_id), current_event_code=VALUES(current_event_code), "
                        + "last_input_digest=VALUES(last_input_digest), last_state_digest=VALUES(last_state_digest), state_vector_json=VALUES(state_vector_json), "
                        + "last_transition_type=CASE WHEN ? THEN VALUES(last_transition_type) ELSE last_transition_type END, "
                        + "last_transition_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_transition_at END, updated_at=CURRENT_TIMESTAMP",
                input.monitorKey, input.projectId, input.sourceType, input.stationId, input.instrumentId, input.metricCode, input.ruleId,
                STATE_SCHEMA_VERSION, DECISION_MODEL_VERSION, input.currentLevel, trace.currentRank, input.currentValue,
                input.eventId, input.eventCode, decision.transitionType, decision.createTransition, trace.inputDigest, trace.currentStateDigest,
                trace.stateVectorJson,
                decision.createTransition, decision.createTransition);
    }

    private Long insertTransition(EventStateInput input, String previousLevel, BigDecimal previousValue,
                                  EventNotificationDecisionPolicy.Decision decision, DecisionTrace trace) {
        String sourceKey = transitionSourceKey(input, decision);
        Long existing = findTransitionId(input.projectId, sourceKey);
        if (existing != null) return existing;
        KeyHolder holder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO em_event_state_transition(source_record_key, monitor_key, project_id, source_type, event_id, event_code, "
                            + "station_id, instrument_id, metric_code, rule_id, previous_level, current_level, previous_value, current_value, "
                            + "previous_rank, current_rank, transition_type, decision_model_version, action_required, input_digest, "
                            + "previous_state_digest, current_state_digest, evidence_json, window_start, window_end, subject, delivery_status, reason, created_at, updated_at) "
                            + "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, sourceKey);
            ps.setString(2, input.monitorKey);
            ps.setObject(3, input.projectId);
            ps.setString(4, input.sourceType);
            ps.setObject(5, input.eventId);
            ps.setString(6, input.eventCode);
            ps.setObject(7, input.stationId);
            ps.setObject(8, input.instrumentId);
            ps.setString(9, input.metricCode);
            ps.setObject(10, input.ruleId);
            ps.setString(11, previousLevel);
            ps.setString(12, input.currentLevel);
            ps.setObject(13, previousValue);
            ps.setObject(14, input.currentValue);
            ps.setObject(15, trace.previousRank);
            ps.setObject(16, trace.currentRank);
            ps.setString(17, decision.transitionType);
            ps.setString(18, DECISION_MODEL_VERSION);
            ps.setInt(19, decision.createTransition ? 1 : 0);
            ps.setString(20, trace.inputDigest);
            ps.setString(21, trace.previousStateDigest);
            ps.setString(22, trace.currentStateDigest);
            ps.setString(23, trace.evidenceJson);
            ps.setTimestamp(24, timestamp(input.windowStart));
            ps.setTimestamp(25, timestamp(input.windowEnd));
            ps.setString(26, buildSubject(input, previousLevel, decision.transitionType));
            ps.setString(27, "created");
            ps.setString(28, truncate(decision.reason, 1000));
            return ps;
        }, holder);
        Number key = holder.getKey();
        return key == null ? findTransitionId(input.projectId, sourceKey) : key.longValue();
    }

    private Long findTransitionId(Long projectId, String sourceKey) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id FROM em_event_state_transition WHERE project_id=? AND source_record_key=? LIMIT 1", projectId, sourceKey);
        return rows.isEmpty() ? null : toLong(rows.get(0).get("id"));
    }

    private String transitionSourceKey(EventStateInput input, EventNotificationDecisionPolicy.Decision decision) {
        String anchor = input.eventId == null
                ? "state:" + sha256(input.monitorKey + "|" + format(input.windowEnd) + "|" + input.currentLevel).substring(0, 24)
                : "event:" + input.eventId;
        return "event_state_transition:" + input.projectId + ":" + anchor + ":" + decision.transitionType + ":" + input.currentLevel;
    }

    private MetricSeriesPoint latestObservation(EventRule rule, List<MetricSeriesPoint> observations) {
        if (observations == null || observations.isEmpty()) return null;
        MetricSeriesPoint latest = null;
        String metricCode = rule == null ? null : rule.getMetricCode();
        for (MetricSeriesPoint observation : observations) {
            if (observation == null || observation.getValue() == null) continue;
            if (hasText(metricCode) && hasText(observation.getMetricCode()) && !metricCode.equals(observation.getMetricCode())) continue;
            if (latest == null) {
                latest = observation;
                continue;
            }
            if (latest.getTimestamp() == null || (observation.getTimestamp() != null && observation.getTimestamp().isAfter(latest.getTimestamp()))) {
                latest = observation;
            }
        }
        return latest;
    }

    private DecisionTrace buildTrace(EventStateInput input, String previousLevel, BigDecimal previousValue,
                                     EventNotificationDecisionPolicy.Decision decision) {
        DecisionTrace trace = new DecisionTrace();
        trace.previousRank = decisionPolicy.levelRank(previousLevel);
        trace.currentRank = decisionPolicy.levelRank(input.currentLevel);
        trace.inputDigest = sha256(input.monitorKey + "|" + input.eventId + "|" + input.ruleId + "|"
                + input.metricCode + "|" + format(input.windowStart) + "|" + format(input.windowEnd) + "|"
                + input.currentLevel + "|" + decimalText(input.currentValue));
        trace.previousStateDigest = sha256(input.monitorKey + "|" + previousLevel + "|" + decimalText(previousValue));
        trace.currentStateDigest = sha256(input.monitorKey + "|" + input.currentLevel + "|" + decimalText(input.currentValue));

        JSONObject evidence = new JSONObject();
        evidence.put("schemaVersion", STATE_SCHEMA_VERSION);
        evidence.put("decisionModelVersion", DECISION_MODEL_VERSION);
        evidence.put("monitorKey", input.monitorKey);
        evidence.put("projectId", input.projectId);
        evidence.put("eventId", input.eventId);
        evidence.put("eventCode", input.eventCode);
        evidence.put("sourceType", input.sourceType);
        evidence.put("stationId", input.stationId);
        evidence.put("instrumentId", input.instrumentId);
        evidence.put("metricCode", input.metricCode);
        evidence.put("ruleId", input.ruleId);
        evidence.put("previousLevel", previousLevel);
        evidence.put("currentLevel", input.currentLevel);
        evidence.put("previousRank", trace.previousRank);
        evidence.put("currentRank", trace.currentRank);
        evidence.put("previousValue", decimalText(previousValue));
        evidence.put("currentValue", decimalText(input.currentValue));
        evidence.put("transitionType", decision.transitionType);
        evidence.put("actionRequired", decision.createTransition);
        evidence.put("reason", decision.reason);
        evidence.put("windowStart", format(input.windowStart));
        evidence.put("windowEnd", format(input.windowEnd));
        evidence.put("inputDigest", trace.inputDigest);
        evidence.put("previousStateDigest", trace.previousStateDigest);
        evidence.put("currentStateDigest", trace.currentStateDigest);
        trace.evidenceJson = evidence.toString();

        JSONObject stateVector = new JSONObject();
        stateVector.put("schemaVersion", STATE_SCHEMA_VERSION);
        stateVector.put("decisionModelVersion", DECISION_MODEL_VERSION);
        stateVector.put("monitorKey", input.monitorKey);
        stateVector.put("level", input.currentLevel);
        stateVector.put("rank", trace.currentRank);
        stateVector.put("value", decimalText(input.currentValue));
        stateVector.put("eventId", input.eventId);
        stateVector.put("eventCode", input.eventCode);
        stateVector.put("inputDigest", trace.inputDigest);
        stateVector.put("stateDigest", trace.currentStateDigest);
        trace.stateVectorJson = stateVector.toString();
        return trace;
    }

    private void markTransitionNoRecipient(Long transitionId) {
        jdbcTemplate.update("UPDATE em_event_state_transition SET delivery_status='no_recipient', reason='No matching event notification subscriber', "
                + "updated_at=CURRENT_TIMESTAMP WHERE id=?", transitionId);
    }

    private String buildSubject(EventStateInput input, String previousLevel, String transitionType) {
        String label = defaultIfBlank(input.metricCode, defaultIfBlank(input.eventType, "event"));
        if ("RECOVERY".equals(transitionType)) {
            return "[SHM-EM] Project event recovered: " + label;
        }
        if ("LEVEL_UP".equals(transitionType)) {
            return "[SHM-EM] Project event escalated to " + input.currentLevel + ": " + label;
        }
        if ("LEVEL_DOWN".equals(transitionType)) {
            return "[SHM-EM] Project event downgraded to " + input.currentLevel + ": " + label;
        }
        if ("PERSISTENT_REMINDER".equals(transitionType)) {
            return "[SHM-EM] " + input.currentLevel + " event persistent reminder: " + label;
        }
        if ("SIGNIFICANT_WORSENING".equals(transitionType)) {
            return "[SHM-EM] " + input.currentLevel + " event worsening reminder: " + label;
        }
        return "[SHM-EM] " + input.currentLevel + " project monitoring event: " + label;
    }

    private String buildHtml(EventStateInput input, String previousLevel, BigDecimal previousValue,
                             EventNotificationDecisionPolicy.Decision decision) {
        StringBuilder html = new StringBuilder();
        html.append("<div style=\"font-family:Arial,sans-serif;font-size:14px;line-height:1.7;color:#222;\">");
        html.append("<h2>SHM-EM Project Monitoring Event Notification</h2>");
        html.append("<p>The system detected a project monitoring event state change and linked it to the event response and evidence chain.</p>");
        html.append("<table border=\"1\" cellpadding=\"6\" cellspacing=\"0\" style=\"border-collapse:collapse;min-width:760px;\">");
        row(html, "Event code", input.eventCode);
        row(html, "State change", decision.transitionType);
        row(html, "Previous level", previousLevel);
        row(html, "Current level", input.currentLevel);
        row(html, "Previous risk value", previousValue == null ? "" : previousValue.toPlainString());
        row(html, "Current risk value", input.currentValue == null ? "" : input.currentValue.toPlainString() + defaultIfBlank(input.unit, ""));
        row(html, "Point ID", input.stationId == null ? "" : String.valueOf(input.stationId));
        row(html, "Instrument ID", input.instrumentId == null ? "" : String.valueOf(input.instrumentId));
        row(html, "Metric", input.metricCode);
        row(html, "Window", format(input.windowStart) + " to " + format(input.windowEnd));
        row(html, "Trigger reason", firstNonBlank(input.reason, decision.reason));
        html.append("</table>");
        html.append("<h3>Recommended action</h3>");
        if ("RED".equals(input.currentLevel)) {
            html.append("<p>A Red event is active. Organize immediate site verification and add handling records and evidence in the SHM-EM response workspace.</p>");
        } else if ("ORANGE".equals(input.currentLevel)) {
            html.append("<p>An Orange event is active. Strengthen site inspection and data review, and monitor subsequent trends.</p>");
        } else if ("YELLOW".equals(input.currentLevel)) {
            html.append("<p>A Yellow event is active. Continue observation and confirm instrument acquisition status.</p>");
        } else {
            html.append("<p>This is mainly a recovery or state-improvement notice. Confirm risk closure against site handling records.</p>");
        }
        html.append("<p style=\"color:#666;margin-top:18px;\">This email was automatically sent by the SHM-EM project monitoring event response platform. Do not reply directly.</p>");
        html.append("</div>");
        return html.toString();
    }

    private String notificationType(EventStateInput input, String transitionType) {
        return "RECOVERY".equals(transitionType) || "LEVEL_DOWN".equals(transitionType)
                ? "event_state_notice"
                : "event_alert";
    }

    private String monitorKey(EventStateInput input) {
        return input.projectId + "|" + input.sourceType + "|station:" + nullText(input.stationId)
                + "|instrument:" + nullText(input.instrumentId) + "|metric:" + nullText(input.metricCode)
                + "|rule:" + nullText(input.ruleId);
    }

    private boolean scopeMatches(String scopeJson, Long numericCandidate, String textCandidate) {
        if (!hasText(scopeJson)) return true;
        String scope = scopeJson.trim();
        if ("ALL".equalsIgnoreCase(scope)) return true;
        String numeric = numericCandidate == null ? null : String.valueOf(numericCandidate);
        if (matchesScopeValue(scope, numeric) || matchesScopeValue(scope, textCandidate)) return true;
        try {
            Object parsed = scope.startsWith("[") ? new JSONArray(scope) : new JSONObject(scope);
            return parsed.toString().contains("\"ALL\"")
                    || matchesScopeValue(parsed.toString(), numeric)
                    || matchesScopeValue(parsed.toString(), textCandidate);
        } catch (Exception ignored) {
            return false;
        }
    }

    private boolean matchesScopeValue(String scope, String candidate) {
        if (!hasText(scope) || !hasText(candidate)) return false;
        String value = candidate.trim();
        return scope.equalsIgnoreCase(value) || scope.contains("\"" + value + "\"") || scope.contains(value);
    }

    private String jsonOrNull(Object value) {
        if (value == null) return null;
        if (value instanceof JSONArray || value instanceof JSONObject) return value.toString();
        if (value instanceof Iterable) {
            JSONArray arr = new JSONArray();
            for (Object item : (Iterable<?>) value) arr.put(item);
            return arr.toString();
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) return null;
        if (text.startsWith("[") || text.startsWith("{")) return text;
        JSONArray arr = new JSONArray();
        arr.put(text);
        return arr.toString();
    }

    private Object first(Map<String, Object> data, String first, String second) {
        Object value = data.get(first);
        return value == null ? data.get(second) : value;
    }

    private void row(StringBuilder html, String name, String value) {
        html.append("<tr><th align=\"left\" style=\"background:#f6f7f9;\">")
                .append(escape(name)).append("</th><td>").append(escape(value)).append("</td></tr>");
    }

    private String join(Set<String> values) {
        if (values == null || values.isEmpty()) return null;
        StringBuilder builder = new StringBuilder();
        for (String value : values) {
            if (!hasText(value)) continue;
            if (builder.length() > 0) builder.append(',');
            builder.append(value.trim());
        }
        return builder.length() == 0 ? null : builder.toString();
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : bytes) {
                String hex = Integer.toHexString(b & 0xff);
                if (hex.length() == 1) builder.append('0');
                builder.append(hex);
            }
            return builder.toString();
        } catch (Exception ex) {
            return Integer.toHexString(value == null ? 0 : value.hashCode());
        }
    }

    private Timestamp timestamp(LocalDateTime time) {
        return time == null ? null : Timestamp.valueOf(time);
    }

    private LocalDateTime toLocalDateTime(Object raw) {
        if (raw instanceof Timestamp) return ((Timestamp) raw).toLocalDateTime();
        if (raw instanceof LocalDateTime) return (LocalDateTime) raw;
        return null;
    }

    private BigDecimal toBigDecimal(Object raw) {
        if (raw instanceof BigDecimal) return (BigDecimal) raw;
        if (raw instanceof Number) return BigDecimal.valueOf(((Number) raw).doubleValue());
        try {
            return raw == null ? null : new BigDecimal(String.valueOf(raw));
        } catch (Exception ex) {
            return null;
        }
    }

    private Long toLong(Object raw) {
        if (raw instanceof Number) return ((Number) raw).longValue();
        try {
            return raw == null ? null : Long.valueOf(String.valueOf(raw));
        } catch (Exception ex) {
            return null;
        }
    }

    private Integer number(Object raw, int fallback) {
        if (raw instanceof Number) return ((Number) raw).intValue();
        try {
            return raw == null ? fallback : Integer.valueOf(String.valueOf(raw));
        } catch (Exception ex) {
            return fallback;
        }
    }

    private String string(Object raw) {
        return raw == null ? null : String.valueOf(raw);
    }

    private String firstNonBlank(String... values) {
        if (values == null) return "";
        for (String value : values) {
            if (hasText(value)) return value.trim();
        }
        return "";
    }

    private String defaultIfBlank(String value, String fallback) {
        return hasText(value) ? value.trim() : fallback;
    }

    private String nullText(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String decimalText(BigDecimal value) {
        return value == null ? null : value.stripTrailingZeros().toPlainString();
    }

    private String truncate(String value, int max) {
        if (value == null || value.length() <= max) return value;
        return value.substring(0, max);
    }

    private String format(LocalDateTime time) {
        return time == null ? "" : time.format(DTF);
    }

    private String escape(String value) {
        if (value == null) return "";
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private int normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) return 100;
        return Math.min(limit, 500);
    }

    public static class NotificationPlan {
        public Long transitionId;
        public Long taskId;
        public String decision;
        public String deliveryStatus;
        public String reason;
    }

    private static class DecisionTrace {
        Integer previousRank;
        Integer currentRank;
        String inputDigest;
        String previousStateDigest;
        String currentStateDigest;
        String evidenceJson;
        String stateVectorJson;
    }

    private static class EventStateInput {
        Long projectId;
        Long eventId;
        String eventCode;
        String sourceType;
        Long stationId;
        Long instrumentId;
        String metricCode;
        Long ruleId;
        String currentLevel;
        BigDecimal currentValue;
        LocalDateTime windowStart;
        LocalDateTime windowEnd;
        String reason;
        String eventType;
        String unit;
        String monitorKey;
    }
}
