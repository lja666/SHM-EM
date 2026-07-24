package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventResponseWorkflowMapper;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class EventResponseOrchestratorTest {

    @Test
    public void completesWorkflowWithGeneratedReportWhenNotificationsAreSuppressed() {
        EventResponseWorkflowMapper mapper = mock(EventResponseWorkflowMapper.class);
        EventNotificationChainService notificationService = mock(EventNotificationChainService.class);
        NotificationTaskService taskService = mock(NotificationTaskService.class);
        EventResponseOrchestrator orchestrator = new EventResponseOrchestrator(mapper, notificationService, taskService);

        Event event = new Event();
        event.setId(23L);
        event.setProjectId(1L);
        EventNotificationChainService.NotificationPlan plan = new EventNotificationChainService.NotificationPlan();
        plan.decision = "SUPPRESSED";

        when(mapper.selectWorkflowId(23L)).thenReturn(27L);
        when(notificationService.processEvent(event)).thenReturn(plan);
        when(mapper.selectReportInstanceId(23L, 1L)).thenReturn(2L);
        when(mapper.selectResponseSteps(27L)).thenReturn(Collections.emptyList());
        when(mapper.selectReportInstancesByEvent(1L, 23L)).thenReturn(Collections.emptyList());
        when(mapper.selectEvidenceResourcesByEvent(1L, 23L)).thenReturn(Collections.emptyList());
        when(mapper.selectActionLogsByEvent(1L, 23L)).thenReturn(Collections.emptyList());
        when(taskService.listByEvent(1L, 23L, 100)).thenReturn(Collections.emptyList());

        orchestrator.orchestrate(event);

        verify(mapper).insertReportInstance(23L, 1L);
        verify(mapper).insertStep(eq(27L), eq(2), eq("NOTIFICATION"), eq("Notification task"),
                eq("suppressed"), eq("notification"), eq(null));
        verify(mapper).insertStep(eq(27L), eq(3), eq("REPORT_GENERATION"), eq("Report generation"),
                eq("completed"), eq("report"), eq(2L));
        verify(mapper).completeWorkflow(27L, null, 2L);
    }
}
