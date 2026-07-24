package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.dto.EventActionRequest;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.application.service.EventService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/api/em/events")
public class EventController {
    private final EventService service;

    public EventController(EventService service) {
        this.service = service;
    }

    @GetMapping("/{id}")
    public ApiResponse<Event> get(@PathVariable Long id) {
        return ApiResponse.ok(service.get(id));
    }

    @PostMapping("/{id}/acknowledge")
    public ApiResponse<Event> acknowledge(@PathVariable Long id,
                                          @RequestBody(required = false) EventActionRequest body,
                                          HttpServletRequest request) {
        return ApiResponse.ok(service.acknowledge(id, body, clientIp(request)));
    }

    @PostMapping("/{id}/assign")
    public ApiResponse<Event> assign(@PathVariable Long id,
                                     @RequestBody(required = false) EventActionRequest body,
                                     HttpServletRequest request) {
        return ApiResponse.ok(service.assign(id, body, clientIp(request)));
    }

    @PostMapping("/{id}/change-level")
    public ApiResponse<Event> changeLevel(@PathVariable Long id,
                                          @RequestBody(required = false) EventActionRequest body,
                                          HttpServletRequest request) {
        return ApiResponse.ok(service.changeLevel(id, body, clientIp(request)));
    }

    @PostMapping("/{id}/resolve")
    public ApiResponse<Event> resolve(@PathVariable Long id,
                                      @RequestBody(required = false) EventActionRequest body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(service.resolve(id, body, clientIp(request)));
    }

    @PostMapping("/{id}/close")
    public ApiResponse<Event> close(@PathVariable Long id,
                                    @RequestBody(required = false) EventActionRequest body,
                                    HttpServletRequest request) {
        return ApiResponse.ok(service.close(id, body, clientIp(request)));
    }

    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.trim().isEmpty()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}





