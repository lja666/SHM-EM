package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventResponseWorkflowMapper;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class EventResponseOrchestrator {
    private final EventResponseWorkflowMapper mapper;
    private final EventNotificationChainService notificationChainService;
    private final NotificationTaskService notificationTaskService;

    public EventResponseOrchestrator(EventResponseWorkflowMapper mapper,
                                     EventNotificationChainService notificationChainService,
                                     NotificationTaskService notificationTaskService) {
        this.mapper = mapper;
        this.notificationChainService = notificationChainService;
        this.notificationTaskService = notificationTaskService;
    }

    public Map<String, Object> orchestrate(Event event) {
        if (event == null || event.getId() == null) {
            throw new IllegalArgumentException("A persisted event is required for response orchestration");
        }
        Long projectId = event.getProjectId() == null ? 1L : event.getProjectId();
        EventNotificationChainService.NotificationPlan notificationPlan = persistWorkflow(event, projectId);
        return realResponse(event, projectId, notificationPlan);
    }

    private Map<String, Object> realResponse(Event event, Long projectId,
                                             EventNotificationChainService.NotificationPlan notificationPlan) {
        Long eventId = event.getId();
        Map<String, Object> workflow = mapper.selectResponseWorkflowByEvent(projectId, eventId);
        Long workflowId = workflow == null ? null : longValue(workflow.get("id"));
        Map<String, Object> result = new HashMap<String, Object>();
        result.put("responseWorkflow", workflow == null ? Collections.emptyMap() : workflow);
        result.put("responseSteps", workflowId == null ? Collections.emptyList() : mapper.selectResponseSteps(workflowId));
        result.put("notificationTasks", notificationTaskService.listByEvent(projectId, eventId, 100));
        result.put("reports", mapper.selectReportInstancesByEvent(projectId, eventId));
        result.put("evidenceResources", mapper.selectEvidenceResourcesByEvent(projectId, eventId));
        result.put("actionLogs", mapper.selectActionLogsByEvent(projectId, eventId));
        if (notificationPlan != null) {
            result.put("notificationPlan", notificationPlanMap(notificationPlan));
        }
        result.put("operationalCore", "notification, report, evidence archive");
        result.put("dataMode", "real");
        result.put("responseDataSource", "database");
        return result;
    }

    private Map<String, Object> notificationPlanMap(EventNotificationChainService.NotificationPlan plan) {
        Map<String, Object> row = new HashMap<String, Object>();
        row.put("transitionId", plan.transitionId);
        row.put("taskId", plan.taskId);
        row.put("decision", plan.decision);
        row.put("deliveryStatus", plan.deliveryStatus);
        row.put("reason", plan.reason);
        return row;
    }

    private EventNotificationChainService.NotificationPlan persistWorkflow(Event event, Long projectId) {
        Long eventId = event == null ? null : event.getId();
        if (eventId == null) {
            return null;
        }
        EventNotificationChainService.NotificationPlan notificationPlan = null;
        mapper.insertWorkflow(eventId, projectId);
        Long workflowId = mapper.selectWorkflowId(eventId);
        notificationPlan = notificationChainService.processEvent(event);
        mapper.insertReportInstance(eventId, projectId);
        Long reportId = mapper.selectReportInstanceId(eventId, projectId);
        if (workflowId != null) {
            mapper.insertStep(workflowId, 1, "RULE_TRIGGER", "Rule trigger", "completed", "event", eventId);
            mapper.insertStep(workflowId, 2, "NOTIFICATION", "Notification task",
                    notificationPlan.taskId == null ? "suppressed" : "completed", "notification", notificationPlan.taskId);
            mapper.insertStep(workflowId, 3, "REPORT_GENERATION", "Report generation",
                    reportId == null ? "failed" : "completed", "report", reportId);
            mapper.insertStep(workflowId, 4, "EVIDENCE_ARCHIVE", "Evidence archive", "completed", "evidence", null);
            mapper.completeWorkflow(workflowId, notificationPlan.taskId, reportId);
        }
        return notificationPlan;
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number) return ((Number) value).longValue();
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }
}
