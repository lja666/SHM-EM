package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.ResponseResourceService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/em")
public class EventResponseController {
    private final ResponseResourceService service;

    public EventResponseController(ResponseResourceService service) {
        this.service = service;
    }

    @GetMapping("/notification-tasks")
    public ApiResponse<List<Map<String, Object>>> notificationTasks(@RequestParam(required = false) Long projectId) {
        return ApiResponse.ok(service.notificationTasks(projectId));
    }

    @GetMapping("/notification-subscribers")
    public ApiResponse<List<Map<String, Object>>> notificationSubscribers(@RequestParam(required = false) Long projectId,
                                                                          @RequestParam(required = false) String channelType,
                                                                          @RequestParam(required = false) Integer enabled) {
        return ApiResponse.ok(service.notificationSubscribers(projectId, channelType, enabled));
    }

    @GetMapping("/notification-state-transitions")
    public ApiResponse<List<Map<String, Object>>> notificationTransitions(@RequestParam(required = false) Long projectId,
                                                                          @RequestParam(required = false) String transitionType,
                                                                          @RequestParam(required = false) String deliveryStatus,
                                                                          @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.notificationTransitions(projectId, transitionType, deliveryStatus, limit));
    }

    @GetMapping("/notification-delivery-logs")
    public ApiResponse<List<Map<String, Object>>> notificationDeliveryLogs(@RequestParam(required = false) Long projectId,
                                                                           @RequestParam(required = false) Long taskId,
                                                                           @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.notificationDeliveryLogs(projectId, taskId, limit));
    }

    @GetMapping("/event-response-workflows")
    public ApiResponse<List<Map<String, Object>>> workflows(@RequestParam(required = false) Long projectId) {
        return ApiResponse.ok(service.responseWorkflows(projectId));
    }

}
