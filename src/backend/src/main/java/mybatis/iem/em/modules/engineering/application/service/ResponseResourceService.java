package mybatis.iem.em.modules.engineering.application.service;

import java.util.List;
import java.util.Map;

public interface ResponseResourceService {
    List<Map<String, Object>> notificationTasks(Long projectId);

    List<Map<String, Object>> notificationSubscribers(Long projectId, String channelType, Integer enabled);

    List<Map<String, Object>> notificationTransitions(Long projectId, String transitionType, String deliveryStatus, Integer limit);

    List<Map<String, Object>> notificationDeliveryLogs(Long projectId, Long taskId, Integer limit);

    List<Map<String, Object>> responseWorkflows(Long projectId);

}
