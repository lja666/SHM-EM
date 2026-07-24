package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.AuditLogService;
import mybatis.iem.em.modules.engineering.domain.model.AuditLog;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/em/audit-logs")
public class AuditLogController {
    private final AuditLogService service;

    public AuditLogController(AuditLogService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<AuditLog>> list(@RequestParam(required = false) Long projectId,
                                            @RequestParam(required = false) String actionType,
                                            @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.list(projectId, actionType, limit));
    }
}
