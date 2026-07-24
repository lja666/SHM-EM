package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.ProjectContextService;
import mybatis.iem.em.modules.engineering.application.service.ProjectFutureStateService;
import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.domain.model.ProjectFutureState;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.application.service.ProjectService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.time.LocalDateTime;
import org.springframework.format.annotation.DateTimeFormat;

@RestController
@RequestMapping("/api/em/projects")
public class ProjectController {
    private final ProjectService service;
    private final ProjectContextService contextService;
    private final ProjectFutureStateService futureStateService;

    public ProjectController(ProjectService service,
                             ProjectContextService contextService,
                             ProjectFutureStateService futureStateService) {
        this.service = service;
        this.contextService = contextService;
        this.futureStateService = futureStateService;
    }

    @GetMapping("/overview")
    public ApiResponse<Map<String, Object>> overview() {
        return ApiResponse.ok(contextService.overview());
    }

    @GetMapping
    public ApiResponse<List<Project>> list(@RequestParam(required = false) Long projectId,
                                             @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.list(projectId, limit));
    }

    @GetMapping("/{id}")
    public ApiResponse<Project> get(@PathVariable Long id) {
        return ApiResponse.ok(service.get(id));
    }

    @GetMapping("/{id}/context")
    public ApiResponse<Map<String, Object>> context(@PathVariable Long id) {
        return ApiResponse.ok(contextService.context(id));
    }

    @GetMapping("/{id}/object-tree")
    public ApiResponse<Map<String, Object>> objectTree(@PathVariable Long id) {
        return ApiResponse.ok(contextService.objectTree(id));
    }

    @GetMapping("/{id}/future-state")
    public ApiResponse<ProjectFutureState> futureState(
            @PathVariable Long id,
            @RequestParam(required = false) Long batchId,
            @RequestParam(required = false) Integer horizonMinutes,
            @RequestParam(required = false, defaultValue = "OPERATIONAL") PredictionExecutionMode executionMode,
            @RequestParam(required = false)
            @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime referenceTime) {
        return ApiResponse.ok(futureStateService.get(id, batchId, horizonMinutes, executionMode, referenceTime));
    }
}





