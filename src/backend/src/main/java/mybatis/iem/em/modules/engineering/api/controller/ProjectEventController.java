package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.EventService;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/em/projects/{projectId}/events")
public class ProjectEventController {
    private final EventService service;

    public ProjectEventController(EventService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<Event>> list(@PathVariable Long projectId,
                                         @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.list(projectId, limit));
    }

    @GetMapping("/device-warnings")
    public ApiResponse<List<Map<String, Object>>> deviceWarnings(@PathVariable Long projectId,
                                                                 @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.deviceWarnings(projectId, limit));
    }
}
