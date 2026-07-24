package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatchDetail;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.EventPredictionTrace;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.format.annotation.DateTimeFormat;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/em/predictions")
public class PredictionController {
    private final PredictionService service;
    private final PredictionExecutionGateService executionGateService;

    public PredictionController(PredictionService service, PredictionExecutionGateService executionGateService) {
        this.service = service;
        this.executionGateService = executionGateService;
    }

    @GetMapping("/batches")
    public ApiResponse<List<PredictionBatch>> batches(@ModelAttribute PredictionQuery query) {
        return ApiResponse.ok(service.batches(query));
    }

    @GetMapping("/models")
    public ApiResponse<List<PredictionModel>> models(@ModelAttribute PredictionQuery query) {
        return ApiResponse.ok(service.models(query));
    }

    @GetMapping("/features")
    public ApiResponse<List<PredictionFeatureMapping>> features(@ModelAttribute PredictionQuery query) {
        return ApiResponse.ok(service.features(query));
    }

    @GetMapping("/latest")
    public ApiResponse<List<PredictionDisplay>> latest(@ModelAttribute PredictionQuery query) {
        return ApiResponse.ok(service.latest(query));
    }

    @GetMapping("/batches/{batchId}")
    public ApiResponse<PredictionBatchDetail> batchDetail(@PathVariable Long batchId) {
        return ApiResponse.ok(service.batchDetail(batchId));
    }

    @GetMapping("/batches/{batchId}/runs")
    public ApiResponse<List<PredictionRun>> runs(@PathVariable Long batchId) {
        return ApiResponse.ok(service.runs(batchId));
    }

    @GetMapping("/batches/{batchId}/execution-gate")
    public ApiResponse<PredictionExecutionGate> executionGate(
            @PathVariable Long batchId,
            @RequestParam(defaultValue = "OPERATIONAL") String mode,
            @RequestParam(required = false)
            @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime referenceTime) {
        return ApiResponse.ok(executionGateService.inspect(
                batchId,
                PredictionExecutionMode.from(mode, PredictionExecutionMode.OPERATIONAL),
                referenceTime));
    }

    @GetMapping("/batches/{batchId}/execution-gate/latest")
    public ApiResponse<PredictionExecutionGate> latestExecutionGate(
            @PathVariable Long batchId,
            @RequestParam(defaultValue = "OPERATIONAL") String mode) {
        return ApiResponse.ok(executionGateService.latest(
                batchId,
                PredictionExecutionMode.from(mode, PredictionExecutionMode.OPERATIONAL)));
    }

    @PostMapping("/batches/{batchId}/execution-gate/evaluate")
    public ApiResponse<PredictionExecutionGate> evaluateExecutionGate(
            @PathVariable Long batchId,
            @RequestParam(defaultValue = "OPERATIONAL") String mode,
            @RequestParam(required = false)
            @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime referenceTime) {
        return ApiResponse.ok(executionGateService.evaluate(
                batchId,
                PredictionExecutionMode.from(mode, PredictionExecutionMode.OPERATIONAL),
                referenceTime));
    }

    @GetMapping("/series")
    public ApiResponse<List<MetricSeriesPoint>> series(@ModelAttribute PredictionQuery query) {
        return ApiResponse.ok(service.series(query));
    }

    @GetMapping("/events/{eventId}/trace")
    public ApiResponse<EventPredictionTrace> eventTrace(@PathVariable Long eventId) {
        return ApiResponse.ok(service.eventTrace(eventId));
    }
}
