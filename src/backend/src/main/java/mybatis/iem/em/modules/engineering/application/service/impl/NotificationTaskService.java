package mybatis.iem.em.modules.engineering.application.service.impl;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import javax.mail.internet.MimeMessage;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class NotificationTaskService {
    private static final Logger log = LoggerFactory.getLogger(NotificationTaskService.class);

    private final JdbcTemplate jdbcTemplate;
    private final JavaMailSender mailSender;

    @Value("${shm-em.notification.mail-send-enabled:false}")
    private boolean mailSendEnabled;
    @Value("${shm-em.notification.mail-recipient-mode:TO}")
    private String recipientMode;
    @Value("${shm-em.notification.mail-bcc-anchor-to:}")
    private String bccAnchorTo;
    @Value("${shm-em.notification.mail-from-name:SHM-EM Project Monitoring Event Response Platform}")
    private String fromName;
    @Value("${spring.mail.username:}")
    private String mailUsername;
    @Value("${shm-em.notification.max-stuck-sending-minutes:10}")
    private int maxStuckSendingMinutes;
    @Value("${shm-em.notification.retry-delay-seconds:60,300,900}")
    private String retryDelaySeconds;

    public NotificationTaskService(JdbcTemplate jdbcTemplate,
                                   @Autowired(required = false) JavaMailSender mailSender) {
        this.jdbcTemplate = jdbcTemplate;
        this.mailSender = mailSender;
    }

    public Long createTask(TaskDraft draft) {
        if (draft == null) throw new IllegalArgumentException("notification task draft is required");
        if (draft.projectId == null) throw new IllegalArgumentException("projectId is required");
        if (!hasText(draft.sourceRecordKey)) throw new IllegalArgumentException("sourceRecordKey is required");
        String toEmails = NotificationAddressUtils.normalizeToCommaText(draft.toEmails);
        if (!hasText(toEmails)) throw new IllegalArgumentException("recipient email is required");
        draft.toEmails = toEmails;
        Long existing = findTaskIdBySource(draft.projectId, draft.sourceRecordKey);
        if (existing != null) return existing;

        KeyHolder holder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO em_notification_task(event_id, project_id, channel_id, transition_id, notification_type, action_backend, subject, content, "
                            + "target_json, status, retry_count, max_retry, message, source_record_key, next_retry_time, "
                            + "attachment_path, attachment_format, provenance_json, created_at, updated_at) "
                            + "VALUES(?,?,?,?,?,?,?,?,?,'pending',0,?,?,?,CURRENT_TIMESTAMP,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setObject(1, draft.eventId);
            ps.setObject(2, draft.projectId);
            ps.setObject(3, draft.channelId);
            ps.setObject(4, draft.transitionId);
            ps.setString(5, hasText(draft.notificationType) ? draft.notificationType : "event_alert");
            ps.setString(6, hasText(draft.actionBackend) ? draft.actionBackend : "email");
            ps.setString(7, draft.subject);
            ps.setString(8, draft.contentHtml);
            ps.setString(9, targetJson(draft));
            ps.setInt(10, draft.maxRetry == null ? 3 : draft.maxRetry);
            ps.setString(11, draft.message);
            ps.setString(12, draft.sourceRecordKey);
            ps.setString(13, draft.attachmentPath);
            ps.setString(14, draft.attachmentFormat);
            ps.setString(15, draft.provenanceJson);
            return ps;
        }, holder);
        Number key = holder.getKey();
        return key == null ? findTaskIdBySource(draft.projectId, draft.sourceRecordKey) : key.longValue();
    }

    public List<Map<String, Object>> list(String status, Long projectId, Integer limit) {
        StringBuilder sql = new StringBuilder("SELECT t.id, t.event_id AS eventId, t.project_id AS projectId, "
                + "t.channel_id AS channelId, t.transition_id AS transitionId, c.channel_code AS channelCode, c.channel_name AS channelName, "
                + "c.channel_type AS channelType, t.notification_type AS notificationType, t.action_backend AS actionBackend, t.subject, t.content, "
                + "t.target_json AS targetJson, t.status, t.retry_count AS retryCount, t.max_retry AS maxRetry, "
                + "t.message, t.sent_at AS sentAt, t.source_record_key AS sourceRecordKey, t.sending_time AS sendingTime, "
                + "t.last_attempt_time AS lastAttemptTime, t.next_retry_time AS nextRetryTime, t.created_at AS createdAt, "
                + "t.provenance_json AS provenanceJson, t.updated_at AS updatedAt FROM em_notification_task t "
                + "LEFT JOIN em_notification_channel c ON c.id=t.channel_id WHERE 1=1 ");
        List<Object> args = new ArrayList<Object>();
        if (projectId != null) {
            sql.append("AND t.project_id=? ");
            args.add(projectId);
        }
        if (hasText(status)) {
            sql.append("AND LOWER(t.status)=LOWER(?) ");
            args.add(status.trim());
        }
        sql.append("ORDER BY COALESCE(t.sent_at, t.created_at) DESC, t.id DESC LIMIT ?");
        args.add(normalizeLimit(limit, 100));
        return jdbcTemplate.queryForList(sql.toString(), args.toArray());
    }

    public List<Map<String, Object>> listByEvent(Long projectId, Long eventId, Integer limit) {
        if (projectId == null || eventId == null) return new ArrayList<Map<String, Object>>();
        String sql = "SELECT t.id, t.event_id AS eventId, t.project_id AS projectId, "
                + "t.channel_id AS channelId, t.transition_id AS transitionId, c.channel_code AS channelCode, c.channel_name AS channelName, "
                + "c.channel_type AS channelType, t.notification_type AS notificationType, t.action_backend AS actionBackend, t.subject, t.content, "
                + "t.target_json AS targetJson, t.status, t.retry_count AS retryCount, t.max_retry AS maxRetry, "
                + "t.message, t.sent_at AS sentAt, t.source_record_key AS sourceRecordKey, t.sending_time AS sendingTime, "
                + "t.last_attempt_time AS lastAttemptTime, t.next_retry_time AS nextRetryTime, t.created_at AS createdAt, "
                + "t.provenance_json AS provenanceJson, t.updated_at AS updatedAt FROM em_notification_task t "
                + "LEFT JOIN em_notification_channel c ON c.id=t.channel_id "
                + "WHERE t.project_id=? AND t.event_id=? "
                + "ORDER BY COALESCE(t.sent_at, t.created_at) DESC, t.id DESC LIMIT ?";
        return jdbcTemplate.queryForList(sql, projectId, eventId, normalizeLimit(limit, 100));
    }

    public List<Map<String, Object>> deliveryLogs(Long projectId, Long taskId, Integer limit) {
        StringBuilder sql = new StringBuilder("SELECT id, task_id AS taskId, project_id AS projectId, subscriber_id AS subscriberId, "
                + "channel_id AS channelId, transition_id AS transitionId, recipient, delivery_type AS deliveryType, subject, status, attempt_no AS attemptNo, "
                + "provider_message_id AS providerMessageId, error_code AS errorCode, error_message AS errorMessage, "
                + "sent_at AS sentAt, acknowledged_at AS acknowledgedAt, source_record_key AS sourceRecordKey, "
                + "metadata_json AS metadataJson, created_at AS createdAt FROM em_notification_delivery_log WHERE 1=1 ");
        List<Object> args = new ArrayList<Object>();
        if (projectId != null) {
            sql.append("AND project_id=? ");
            args.add(projectId);
        }
        if (taskId != null) {
            sql.append("AND task_id=? ");
            args.add(taskId);
        }
        sql.append("ORDER BY created_at DESC, id DESC LIMIT ?");
        args.add(normalizeLimit(limit, 200));
        return jdbcTemplate.queryForList(sql.toString(), args.toArray());
    }

    public Map<String, Object> runPending(Integer limit) {
        recoverStuckSending();
        List<Map<String, Object>> tasks = findPending(normalizeLimit(limit, 20));
        int success = 0;
        int failed = 0;
        int skipped = 0;
        for (Map<String, Object> task : tasks) {
            SendResult result = sendOne(task);
            if (result.success) success++;
            else if (result.skipped) skipped++;
            else failed++;
        }
        Map<String, Object> body = new HashMap<String, Object>();
        body.put("picked", tasks.size());
        body.put("success", success);
        body.put("failed", failed);
        body.put("skipped", skipped);
        return body;
    }

    public int recoverStuckSending() {
        int minutes = maxStuckSendingMinutes <= 0 ? 10 : maxStuckSendingMinutes;
        return jdbcTemplate.update("UPDATE em_notification_task SET status='pending', next_retry_time=CURRENT_TIMESTAMP, "
                + "message='The task stayed in sending for too long; the system reset it to pending for retry', updated_at=CURRENT_TIMESTAMP "
                + "WHERE LOWER(status)='sending' AND COALESCE(sending_time, created_at) < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL ? MINUTE)",
                minutes);
    }

    private SendResult sendOne(Map<String, Object> task) {
        Long id = toLong(task.get("id"));
        if (id == null) return SendResult.skipped("task id is empty");
        int locked = jdbcTemplate.update("UPDATE em_notification_task SET status='sending', sending_time=CURRENT_TIMESTAMP, "
                + "last_attempt_time=CURRENT_TIMESTAMP, message=NULL, updated_at=CURRENT_TIMESTAMP "
                + "WHERE id=? AND LOWER(status)='pending'", id);
        if (locked <= 0) return SendResult.skipped("task is not pending");

        String toEmails = extractToEmails(task);
        String[] recipients = NotificationAddressUtils.parseValidArray(toEmails);
        if (recipients.length == 0) return failTask(task, "recipient email is empty");
        try {
            if (!mailSendEnabled) throw new IllegalStateException("SHM-EM mail sender is disabled");
            if (mailSender == null) throw new IllegalStateException("JavaMailSender is not configured");
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            setFromIfPossible(helper);
            setRecipients(helper, recipients);
            helper.setSubject(defaultIfBlank(string(task.get("subject")), "SHM-EM Project Monitoring Event Notification"));
            helper.setText(defaultIfBlank(string(task.get("content")), ""), true);
            addAttachmentIfNeeded(helper, task);
            mailSender.send(message);
            markSuccess(task, recipients, "mail sent");
            return SendResult.success("mail sent");
        } catch (Exception ex) {
            return failTask(task, ex.getMessage() == null ? ex.toString() : ex.getMessage());
        }
    }

    private SendResult failTask(Map<String, Object> task, String message) {
        Long id = toLong(task.get("id"));
        int retryCount = number(task.get("retryCount"), 0);
        int maxRetry = number(task.get("maxRetry"), 3);
        if (retryCount + 1 >= maxRetry) {
            jdbcTemplate.update("UPDATE em_notification_task SET status='failed', retry_count=retry_count+1, "
                    + "last_attempt_time=CURRENT_TIMESTAMP, sent_at=CURRENT_TIMESTAMP, message=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    truncate(message, 512), id);
            updateTransitionStatus(id, "failed", message);
        } else {
            jdbcTemplate.update("UPDATE em_notification_task SET status='pending', retry_count=retry_count+1, "
                    + "last_attempt_time=CURRENT_TIMESTAMP, next_retry_time=DATE_ADD(CURRENT_TIMESTAMP, INTERVAL ? SECOND), "
                    + "message=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    retryDelaySeconds(retryCount + 1), truncate(message, 512), id);
            updateTransitionStatus(id, "pending", message);
        }
        insertDeliveryLogs(task, extractToEmails(task), "failed", message);
        log.warn("SHM-EM notification task {} failed: {}", id, message);
        return SendResult.failed(message);
    }

    private void markSuccess(Map<String, Object> task, String[] recipients, String message) {
        Long id = toLong(task.get("id"));
        jdbcTemplate.update("UPDATE em_notification_task SET status='success', sent_at=CURRENT_TIMESTAMP, "
                + "last_attempt_time=CURRENT_TIMESTAMP, next_retry_time=NULL, message=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                truncate(message, 512), id);
        insertDeliveryLogs(task, join(recipients), "success", null);
        updateTransitionStatus(id, "success", null);
        jdbcTemplate.update("UPDATE em_event_notification_state s "
                + "JOIN em_event_state_transition tr ON tr.monitor_key=s.monitor_key "
                + "SET s.last_notification_at=CURRENT_TIMESTAMP, s.last_notification_level=tr.current_level, "
                + "s.last_notification_value=tr.current_value, s.updated_at=CURRENT_TIMESTAMP "
                + "WHERE tr.notification_task_id=?", id);
    }

    private void updateTransitionStatus(Long taskId, String status, String message) {
        jdbcTemplate.update("UPDATE em_event_state_transition SET delivery_status=?, "
                + "reason=CASE WHEN ? IS NULL OR ?='' THEN reason ELSE ? END, updated_at=CURRENT_TIMESTAMP "
                + "WHERE notification_task_id=?", status, message, message, truncate(message, 1000), taskId);
    }

    private void insertDeliveryLogs(Map<String, Object> task, String toEmails, String status, String error) {
        String[] recipients = NotificationAddressUtils.parseValidArray(toEmails);
        if (recipients.length == 0) recipients = new String[] { "" };
        Long taskId = toLong(task.get("id"));
        Long projectId = toLong(task.get("projectId"));
        Long channelId = toLong(task.get("channelId"));
        Long transitionId = toLong(task.get("transitionId"));
        int attemptNo = number(task.get("retryCount"), 0) + 1;
        for (String recipient : recipients) {
            String sourceKey = "notification_task:" + taskId + ":attempt:" + attemptNo + ":" + Integer.toHexString(recipient.hashCode());
            jdbcTemplate.update("INSERT INTO em_notification_delivery_log(task_id, project_id, channel_id, transition_id, recipient, delivery_type, "
                            + "subject, status, attempt_no, error_message, sent_at, source_record_key, metadata_json, created_at) "
                            + "VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?,CURRENT_TIMESTAMP) "
                            + "ON DUPLICATE KEY UPDATE status=VALUES(status), error_message=VALUES(error_message), sent_at=VALUES(sent_at)",
                    taskId, projectId, channelId, transitionId, recipient, defaultIfBlank(string(task.get("channelType")), "email"),
                    string(task.get("subject")), status, attemptNo, truncate(error, 512), sourceKey,
                    "{\"taskStatus\":\"" + escapeJson(status) + "\"}");
        }
    }

    private List<Map<String, Object>> findPending(int limit) {
        return jdbcTemplate.queryForList("SELECT t.id, t.event_id AS eventId, t.project_id AS projectId, t.channel_id AS channelId, "
                + "t.transition_id AS transitionId, c.channel_type AS channelType, t.notification_type AS notificationType, t.action_backend AS actionBackend, t.subject, t.content, "
                + "t.target_json AS targetJson, t.status, t.retry_count AS retryCount, t.max_retry AS maxRetry, "
                + "t.attachment_path AS attachmentPath, t.attachment_format AS attachmentFormat, t.source_record_key AS sourceRecordKey "
                + "FROM em_notification_task t LEFT JOIN em_notification_channel c ON c.id=t.channel_id "
                + "WHERE LOWER(t.status)='pending' AND t.retry_count < t.max_retry "
                + "AND (t.next_retry_time IS NULL OR t.next_retry_time <= CURRENT_TIMESTAMP) "
                + "ORDER BY t.created_at ASC, t.id ASC LIMIT ?", limit);
    }

    private Map<String, Object> findById(Long id) {
        if (id == null) return null;
        List<Map<String, Object>> rows = jdbcTemplate.queryForList("SELECT t.id, t.event_id AS eventId, t.project_id AS projectId, "
                + "t.channel_id AS channelId, t.transition_id AS transitionId, c.channel_type AS channelType, t.notification_type AS notificationType, t.action_backend AS actionBackend, "
                + "t.subject, t.content, t.target_json AS targetJson, t.status, t.retry_count AS retryCount, t.max_retry AS maxRetry, "
                + "t.attachment_path AS attachmentPath, t.attachment_format AS attachmentFormat, t.source_record_key AS sourceRecordKey "
                + "FROM em_notification_task t LEFT JOIN em_notification_channel c ON c.id=t.channel_id WHERE t.id=? LIMIT 1", id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Long findTaskIdBySource(Long projectId, String sourceRecordKey) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id FROM em_notification_task WHERE project_id=? AND source_record_key=? LIMIT 1",
                projectId, sourceRecordKey);
        return rows.isEmpty() ? null : toLong(rows.get(0).get("id"));
    }

    private String targetJson(TaskDraft draft) {
        JSONObject json = new JSONObject();
        json.put("toEmails", draft.toEmails);
        json.put("recipientCount", NotificationAddressUtils.parseValidArray(draft.toEmails).length);
        json.put("source", "event_notification_chain");
        if (draft.transitionId != null) json.put("transitionId", draft.transitionId);
        if (hasText(draft.provenanceJson)) json.put("provenanceDigest", sha256(draft.provenanceJson));
        return json.toString();
    }

    private String extractToEmails(Map<String, Object> task) {
        String targetJson = string(task.get("targetJson"));
        if (hasText(targetJson)) {
            try {
                JSONObject json = new JSONObject(targetJson);
                String value = json.optString("toEmails", null);
                if (hasText(value)) return value;
            } catch (Exception ignored) {
            }
        }
        return string(task.get("toEmails"));
    }

    private void setFromIfPossible(MimeMessageHelper helper) {
        try {
            if (hasText(mailUsername)) {
                helper.setFrom(mailUsername.trim(), hasText(fromName) ? fromName.trim() : "SHM-EM Project Monitoring Event Response Platform");
            }
        } catch (Exception ignored) {
        }
    }

    private void setRecipients(MimeMessageHelper helper, String[] recipients) throws Exception {
        String mode = recipientMode == null ? "TO" : recipientMode.trim().toUpperCase(Locale.ROOT);
        if ("BCC".equals(mode)) {
            String anchor = firstNonBlank(bccAnchorTo, mailUsername, recipients.length == 0 ? null : recipients[0]);
            helper.setTo(anchor);
            helper.setBcc(recipients);
        } else {
            helper.setTo(recipients);
        }
    }

    private void addAttachmentIfNeeded(MimeMessageHelper helper, Map<String, Object> task) throws Exception {
        String path = string(task.get("attachmentPath"));
        if (!hasText(path)) return;
        File file = new File(path.trim());
        if (!file.exists() || !file.isFile()) throw new IllegalArgumentException("attachment not found: " + path);
        if (!file.canRead()) throw new IllegalArgumentException("attachment is not readable: " + path);
        helper.addAttachment(file.getName(), file);
    }

    private int retryDelaySeconds(int failedAttempts) {
        int[] defaults = new int[] {60, 300, 900};
        List<Integer> parsed = new ArrayList<Integer>();
        if (hasText(retryDelaySeconds)) {
            String[] values = retryDelaySeconds.split(",");
            for (String value : values) {
                try {
                    int seconds = Integer.parseInt(value.trim());
                    if (seconds > 0) parsed.add(seconds);
                } catch (Exception ignored) {
                }
            }
        }
        int index = Math.max(0, failedAttempts - 1);
        if (parsed.isEmpty()) return defaults[Math.min(index, defaults.length - 1)];
        return parsed.get(Math.min(index, parsed.size() - 1));
    }

    private int normalizeLimit(Integer limit, int fallback) {
        if (limit == null || limit <= 0) return fallback;
        return Math.min(limit, 500);
    }

    private int number(Object value, int fallback) {
        if (value instanceof Number) return ((Number) value).intValue();
        try {
            return value == null ? fallback : Integer.parseInt(String.valueOf(value));
        } catch (Exception ex) {
            return fallback;
        }
    }

    private Long toLong(Object value) {
        if (value instanceof Number) return ((Number) value).longValue();
        try {
            return value == null ? null : Long.valueOf(String.valueOf(value));
        } catch (Exception ex) {
            return null;
        }
    }

    private String join(String[] values) {
        StringBuilder builder = new StringBuilder();
        for (String value : values) {
            if (!hasText(value)) continue;
            if (builder.length() > 0) builder.append(',');
            builder.append(value.trim());
        }
        return builder.toString();
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

    private String truncate(String value, int max) {
        if (value == null || value.length() <= max) return value;
        return value.substring(0, max);
    }

    private String string(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private String escapeJson(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
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

    public static class TaskDraft {
        public Long eventId;
        public Long projectId;
        public Long channelId;
        public Long transitionId;
        public String notificationType;
        public String actionBackend;
        public String subject;
        public String contentHtml;
        public String toEmails;
        public String message;
        public String sourceRecordKey;
        public Integer maxRetry;
        public String attachmentPath;
        public String attachmentFormat;
        public String provenanceJson;
    }

    private static class SendResult {
        private final boolean success;
        private final boolean skipped;
        private final String message;

        private SendResult(boolean success, boolean skipped, String message) {
            this.success = success;
            this.skipped = skipped;
            this.message = message;
        }

        private static SendResult success(String message) {
            return new SendResult(true, false, message);
        }

        private static SendResult failed(String message) {
            return new SendResult(false, false, message);
        }

        private static SendResult skipped(String message) {
            return new SendResult(false, true, message);
        }
    }
}
