package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.service.ResponseResourceService;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventResponseWorkflowMapper;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@Service
public class ResponseResourceServiceImpl implements ResponseResourceService {
    private final EventResponseWorkflowMapper mapper;
    private final EventNotificationChainService notificationChainService;
    private final NotificationTaskService notificationTaskService;

    public ResponseResourceServiceImpl(EventResponseWorkflowMapper mapper,
                                       EventNotificationChainService notificationChainService,
                                       NotificationTaskService notificationTaskService) {
        this.mapper = mapper;
        this.notificationChainService = notificationChainService;
        this.notificationTaskService = notificationTaskService;
    }

    @Override
    public List<Map<String, Object>> notificationTasks(Long projectId) {
        List<Map<String, Object>> rows = notificationTaskService.list(null, projectId, 200);
        return rows == null ? Collections.emptyList() : rows;
    }

    @Override
    public List<Map<String, Object>> notificationSubscribers(Long projectId, String channelType, Integer enabled) {
        return notificationChainService.listSubscribers(projectId, channelType, enabled);
    }

    @Override
    public List<Map<String, Object>> notificationTransitions(Long projectId, String transitionType, String deliveryStatus, Integer limit) {
        return notificationChainService.listTransitions(projectId, transitionType, deliveryStatus, limit);
    }

    @Override
    public List<Map<String, Object>> notificationDeliveryLogs(Long projectId, Long taskId, Integer limit) {
        return notificationTaskService.deliveryLogs(projectId, taskId, limit);
    }

    @Override
    public List<Map<String, Object>> responseWorkflows(Long projectId) {
        List<Map<String, Object>> rows = mapper.selectResponseWorkflows(projectId);
        return rows == null ? Collections.emptyList() : rows;
    }

}
