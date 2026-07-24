package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.application.service.EventEvaluationService;
import mybatis.iem.em.modules.engineering.application.service.EventRuleService;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/em/projects/{projectId}/rules")
public class ProjectRuleController {
    private final EventRuleService ruleService;
    private final EventEvaluationService evaluationService;

    public ProjectRuleController(EventRuleService ruleService, EventEvaluationService evaluationService) {
        this.ruleService = ruleService;
        this.evaluationService = evaluationService;
    }

    @GetMapping
    public ApiResponse<List<EventRule>> list(@PathVariable Long projectId,
                                             @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(ruleService.list(projectId, limit));
    }

    @GetMapping("/{ruleId}")
    public ApiResponse<EventRule> get(@PathVariable Long projectId, @PathVariable Long ruleId) {
        EventRule rule = ruleService.get(projectId, ruleId);
        return ApiResponse.ok(rule);
    }

    @PostMapping("/evaluate")
    public ApiResponse<Map<String, Object>> evaluateCustom(@PathVariable Long projectId,
                                                           @RequestBody(required = false) RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = bind(projectId, null, request);
        effectiveRequest.setRunMode("evaluate");
        return ApiResponse.ok(evaluationService.evaluate(effectiveRequest));
    }

    @PostMapping("/execute")
    public ApiResponse<Map<String, Object>> executeCustom(@PathVariable Long projectId,
                                                          @RequestBody(required = false) RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = bind(projectId, null, request);
        effectiveRequest.setRunMode("execute");
        return ApiResponse.ok(evaluationService.execute(effectiveRequest));
    }

    @PostMapping("/{ruleId}/evaluate")
    public ApiResponse<Map<String, Object>> evaluate(@PathVariable Long projectId,
                                                     @PathVariable Long ruleId,
                                                     @RequestBody(required = false) RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = bind(projectId, ruleId, request);
        effectiveRequest.setRunMode("evaluate");
        return ApiResponse.ok(evaluationService.evaluate(effectiveRequest));
    }

    @PostMapping("/{ruleId}/execute")
    public ApiResponse<Map<String, Object>> execute(@PathVariable Long projectId,
                                                    @PathVariable Long ruleId,
                                                    @RequestBody(required = false) RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = bind(projectId, ruleId, request);
        effectiveRequest.setRunMode("execute");
        return ApiResponse.ok(evaluationService.execute(effectiveRequest));
    }

    private RuleEvaluationRequest bind(Long projectId, Long ruleId, RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = request == null ? new RuleEvaluationRequest() : request;
        effectiveRequest.setProjectId(projectId);
        if (ruleId != null) {
            effectiveRequest.setRuleId(ruleId);
        }
        return effectiveRequest;
    }
}
