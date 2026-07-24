package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.EventActionRequest;
import mybatis.iem.em.modules.engineering.application.service.EventService;
import mybatis.iem.em.modules.engineering.domain.model.AuditLog;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.AuditLogMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventMapper;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

@Service
public class EventServiceImpl implements EventService {
    private final EventMapper mapper;
    private final AuditLogMapper auditLogMapper;
    private final ObjectMapper objectMapper;

    public EventServiceImpl(EventMapper mapper,
                            AuditLogMapper auditLogMapper,
                            ObjectMapper objectMapper) {
        this.mapper = mapper;
        this.auditLogMapper = auditLogMapper;
        this.objectMapper = objectMapper;
    }

    @Override
    public List<Event> list(Long projectId, Integer limit) {
        return mapper.selectList(projectId, normalizeLimit(limit));
    }

    @Override
    public List<Map<String, Object>> deviceWarnings(Long projectId, Integer limit) {
        return mapper.selectDeviceWarnings(projectId, normalizeLimit(limit));
    }

    @Override
    public Event get(Long id) {
        return mapper.selectById(id);
    }

    @Override
    public Event acknowledge(Long id, EventActionRequest request, String ipAddress) {
        return transitionStatus(id, "acknowledged", "EVENT_ACKNOWLEDGE", request, ipAddress, false);
    }

    @Override
    public Event assign(Long id, EventActionRequest request, String ipAddress) {
        EventActionRequest action = normalizeRequest(request);
        String requestId = requestId(action);
        if (isDuplicate(requestId)) {
            return requireEvent(id);
        }
        Event before = requireEvent(id);
        ensureNotClosed(before, "closed events cannot be assigned");
        if (!StringUtils.hasText(action.getAssignee())) {
            throw new BusinessException("assignee is required");
        }
        Map<String, Object> after = eventSnapshot(before);
        after.put("assignee", action.getAssignee().trim());
        after.put("operatorRole", action.getOperatorRole());
        after.put("reason", action.getReason());
        audit(before, "EVENT_ASSIGN", action, ipAddress, requestId, eventSnapshot(before), after);
        return before;
    }

    @Override
    public Event changeLevel(Long id, EventActionRequest request, String ipAddress) {
        EventActionRequest action = normalizeRequest(request);
        String requestId = requestId(action);
        if (isDuplicate(requestId)) {
            return requireEvent(id);
        }
        Event before = requireEvent(id);
        ensureNotClosed(before, "closed events cannot change level");
        String targetLevel = normalizeLevel(action.getTargetLevel());
        if (!StringUtils.hasText(targetLevel)) {
            throw new BusinessException("targetLevel is required");
        }
        if (!StringUtils.hasText(action.getReason())) {
            throw new BusinessException("reason is required when changing event level");
        }
        if (targetLevel.equals(normalizeLevel(before.getEventLevel()))) {
            return before;
        }
        mapper.updateLevel(id, targetLevel);
        Event after = requireEvent(id);
        audit(before, "EVENT_CHANGE_LEVEL", action, ipAddress, requestId, eventSnapshot(before), eventSnapshot(after));
        return after;
    }

    @Override
    public Event resolve(Long id, EventActionRequest request, String ipAddress) {
        return transitionStatus(id, "resolved", "EVENT_RESOLVE", request, ipAddress, true);
    }

    @Override
    public Event close(Long id, EventActionRequest request, String ipAddress) {
        return transitionStatus(id, "closed", "EVENT_CLOSE", request, ipAddress, true);
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 200;
        }
        return Math.min(limit, 1000);
    }

    private Event transitionStatus(Long id,
                                   String targetStatus,
                                   String actionType,
                                   EventActionRequest request,
                                   String ipAddress,
                                   boolean reasonRequired) {
        EventActionRequest action = normalizeRequest(request);
        String requestId = requestId(action);
        if (isDuplicate(requestId)) {
            return requireEvent(id);
        }
        Event before = requireEvent(id);
        String currentStatus = normalizeStatus(before.getEventStatus());
        if ("closed".equals(currentStatus)) {
            throw new BusinessException("closed events cannot be changed");
        }
        if (reasonRequired && !StringUtils.hasText(action.getReason())) {
            throw new BusinessException("reason is required");
        }
        if ("closed".equals(targetStatus) && !"resolved".equals(currentStatus)) {
            throw new BusinessException("only resolved events can be closed");
        }
        if (targetStatus.equals(currentStatus)) {
            return before;
        }
        mapper.updateStatus(id, targetStatus, operatorName(action));
        Event after = requireEvent(id);
        audit(before, actionType, action, ipAddress, requestId, eventSnapshot(before), eventSnapshot(after));
        return after;
    }

    private Event requireEvent(Long id) {
        Event event = mapper.selectById(id);
        if (event == null) {
            throw new BusinessException(404, "event is not found: " + id);
        }
        return event;
    }

    private void ensureNotClosed(Event event, String message) {
        if ("closed".equals(normalizeStatus(event.getEventStatus()))) {
            throw new BusinessException(message);
        }
    }

    private EventActionRequest normalizeRequest(EventActionRequest request) {
        return request == null ? new EventActionRequest() : request;
    }

    private String requestId(EventActionRequest request) {
        if (StringUtils.hasText(request.getRequestId())) {
            return request.getRequestId().trim();
        }
        return "event-action-" + UUID.randomUUID().toString();
    }

    private boolean isDuplicate(String requestId) {
        return StringUtils.hasText(requestId) && auditLogMapper.countByRequestId(requestId) > 0;
    }

    private void audit(Event event,
                       String actionType,
                       EventActionRequest request,
                       String ipAddress,
                       String requestId,
                       Map<String, Object> before,
                       Map<String, Object> after) {
        AuditLog auditLog = new AuditLog();
        auditLog.setProjectId(event.getProjectId());
        auditLog.setActorId(operatorId(request));
        auditLog.setActorName(operatorName(request));
        auditLog.setActionType(actionType);
        auditLog.setObjectType("monitoring_event");
        auditLog.setObjectId(event.getId());
        auditLog.setObjectCode(event.getEventCode());
        auditLog.setBeforeJson(toJson(before));
        auditLog.setAfterJson(toJson(after));
        auditLog.setRequestId(requestId);
        auditLog.setIpAddress(ipAddress);
        auditLogMapper.insert(auditLog);
    }

    private Map<String, Object> eventSnapshot(Event event) {
        Map<String, Object> item = new LinkedHashMap<String, Object>();
        item.put("eventId", event.getId());
        item.put("eventCode", event.getEventCode());
        item.put("projectId", event.getProjectId());
        item.put("eventStatus", event.getEventStatus());
        item.put("eventLevel", event.getEventLevel());
        item.put("updatedAt", event.getUpdatedAt() == null ? null : DateTimeFormatter.ISO_LOCAL_DATE_TIME.format(event.getUpdatedAt()));
        return item;
    }

    private String toJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new BusinessException(500, "Unable to serialize audit payload.");
        }
    }

    private Long operatorId(EventActionRequest request) {
        return request.getOperatorId();
    }

    private String operatorName(EventActionRequest request) {
        if (StringUtils.hasText(request.getOperatorName())) {
            return request.getOperatorName().trim();
        }
        return "system";
    }

    private String normalizeStatus(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private String normalizeLevel(String value) {
        if (!StringUtils.hasText(value)) {
            return "";
        }
        String level = value.trim().toLowerCase(Locale.ROOT);
        if (!"blue".equals(level) && !"yellow".equals(level) && !"orange".equals(level) && !"red".equals(level) && !"normal".equals(level)) {
            throw new BusinessException("unsupported event level: " + value);
        }
        return level;
    }
}





