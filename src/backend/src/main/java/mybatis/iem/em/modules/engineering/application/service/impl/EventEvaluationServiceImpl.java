package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.application.service.EventEvaluationService;
import mybatis.iem.em.modules.engineering.application.service.EventRuleService;
import mybatis.iem.em.modules.engineering.application.service.MetricSeriesPointService;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.domain.model.EventEvaluationRun;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.EventPredictionTrace;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventEvaluationRunMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventPredictionTraceMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class EventEvaluationServiceImpl implements EventEvaluationService {
    private final EventRuleService ruleService;
    private final MetricSeriesPointService seriesPointService;
    private final EventEvaluationRunMapper runMapper;
    private final EventMapper eventMapper;
    private final MetricRuleEventEngine engine;
    private final EventResponseOrchestrator orchestrator;
    private final EventNotificationChainService notificationChainService;
    private final CanonicalHashService canonicalHashService;
    private final EventPredictionTraceMapper predictionTraceMapper;
    private final PredictionService predictionService;
    private final PredictionExecutionGateService predictionExecutionGateService;
    private final ReproductionExecutionPolicy reproductionExecutionPolicy;

    public EventEvaluationServiceImpl(EventRuleService ruleService,
                                      MetricSeriesPointService seriesPointService,
                                      EventEvaluationRunMapper runMapper,
                                      EventMapper eventMapper,
                                      MetricRuleEventEngine engine,
                                      EventResponseOrchestrator orchestrator,
                                      EventNotificationChainService notificationChainService,
                                      CanonicalHashService canonicalHashService,
                                      EventPredictionTraceMapper predictionTraceMapper,
                                      PredictionService predictionService,
                                      PredictionExecutionGateService predictionExecutionGateService,
                                      ReproductionExecutionPolicy reproductionExecutionPolicy) {
        this.ruleService = ruleService;
        this.seriesPointService = seriesPointService;
        this.runMapper = runMapper;
        this.eventMapper = eventMapper;
        this.engine = engine;
        this.orchestrator = orchestrator;
        this.notificationChainService = notificationChainService;
        this.canonicalHashService = canonicalHashService;
        this.predictionTraceMapper = predictionTraceMapper;
        this.predictionService = predictionService;
        this.predictionExecutionGateService = predictionExecutionGateService;
        this.reproductionExecutionPolicy = reproductionExecutionPolicy;
    }

    @Override
    public Map<String, Object> evaluate(RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = request == null ? new RuleEvaluationRequest() : request;
        List<EventRule> rules = resolveRules(effectiveRequest);
        EventRule rule = rules.get(0);
        List<MetricSeriesPoint> points = seriesPointService.load(rule, effectiveRequest);
        PredictionExecutionGate predictionGate = predictionGate(rule, effectiveRequest, PredictionExecutionMode.REPLAY, false);
        List<Event> events = evaluateBySeverity(rules, points, false);
        EventEvaluationRun run = createRun(rule, effectiveRequest, events.size(), points);
        Map<String, Object> result = new HashMap<String, Object>();
        result.put("runId", run.getId());
        result.put("ruleId", rule.getId());
        result.put("eventCount", events.size());
        result.put("resultHash", run.getResultHash());
        result.put("ruleVersion", run.getRuleVersion());
        result.put("conversionVersion", run.getConversionVersion());
        result.put("events", events);
        result.put("snapshots", engine.snapshots(rule, points));
        result.put("inputSource", seriesPointService.resolveInputSource(rule, effectiveRequest));
        addPredictionGate(result, predictionGate);
        result.put("message", "rule evaluation completed");
        return result;
    }

    @Override
    @Transactional
    public Map<String, Object> execute(RuleEvaluationRequest request) {
        RuleEvaluationRequest effectiveRequest = request == null ? new RuleEvaluationRequest() : request;
        List<EventRule> rules = resolveRules(effectiveRequest);
        EventRule rule = rules.get(0);
        List<MetricSeriesPoint> points = seriesPointService.load(rule, effectiveRequest);
        PredictionExecutionMode executionMode = formalExecutionMode(rule, effectiveRequest);
        PredictionBatch reproductionBatch = null;
        if (executionMode == PredictionExecutionMode.REPRODUCTION) {
            reproductionBatch = predictionService.resolveBatch(predictionQuery(rule, effectiveRequest));
            reproductionExecutionPolicy.assertAllowed(reproductionBatch);
        }
        PredictionExecutionGate predictionGate = requirePredictionExecutionEligible(rule, effectiveRequest, executionMode);
        List<Event> events = evaluateBySeverity(rules, points, true);
        EventEvaluationRun run = createRun(rule, effectiveRequest, events.size(), points);
        for (Event event : events) {
            event.setEvaluationRunId(run.getId());
            event.setRunType(executionMode == PredictionExecutionMode.REPRODUCTION
                    ? "reproduction" : "operational");
            if (reproductionBatch != null) event.setDetectedAt(reproductionBatch.getBaseTime());
            persistEvent(event);
            persistPredictionTrace(event, predictionGate);
        }
        List<Map<String, Object>> responses = new ArrayList<Map<String, Object>>();
        for (Event event : events) {
            responses.add(orchestrator.orchestrate(event));
        }
        EventNotificationChainService.NotificationPlan normalNotificationPlan = null;
        if (events.isEmpty() && "OBSERVATION".equals(seriesPointService.resolveInputSource(rule, effectiveRequest))) {
            normalNotificationPlan = notificationChainService.processNormalObservation(rule, points);
        }
        Map<String, Object> result = new HashMap<String, Object>();
        Map<String, Object> evaluation = new HashMap<String, Object>();
        evaluation.put("runId", run.getId());
        evaluation.put("ruleId", rule.getId());
        evaluation.put("eventCount", events.size());
        evaluation.put("resultHash", run.getResultHash());
        evaluation.put("ruleVersion", run.getRuleVersion());
        evaluation.put("conversionVersion", run.getConversionVersion());
        evaluation.put("events", events);
        evaluation.put("snapshots", engine.snapshots(rule, points));
        evaluation.put("inputSource", seriesPointService.resolveInputSource(rule, effectiveRequest));
        addPredictionGate(evaluation, predictionGate);
        result.put("evaluation", evaluation);
        Event event = events.isEmpty() ? null : events.get(0);
        result.put("event", event);
        result.put("responses", responses);
        result.put("runType", executionMode == PredictionExecutionMode.REPRODUCTION
                ? "reproduction" : "operational");
        if (normalNotificationPlan != null) {
            result.put("notificationPlan", notificationPlanMap(normalNotificationPlan));
        }
        if (!responses.isEmpty()) {
            result.putAll(responses.get(0));
        }
        result.put("message", "rule execution completed");
        return result;
    }

    private Map<String, Object> notificationPlanMap(EventNotificationChainService.NotificationPlan plan) {
        Map<String, Object> row = new HashMap<String, Object>();
        row.put("transitionId", plan.transitionId);
        row.put("taskId", plan.taskId);
        row.put("decision", plan.decision);
        row.put("deliveryStatus", plan.deliveryStatus);
        row.put("reason", plan.reason);
        return row;
    }

    private List<Event> evaluateBySeverity(List<EventRule> rules, List<MetricSeriesPoint> points, boolean persistMode) {
        for (EventRule rule : rules) {
            List<Event> events = engine.evaluate(rule, points, persistMode);
            if (!events.isEmpty()) {
                return events;
            }
        }
        return new ArrayList<Event>();
    }

    private List<EventRule> resolveRules(RuleEvaluationRequest request) {
        EventRule baseRule = ruleService.get(request.getRuleId() == null ? 1L : request.getRuleId());
        applyRequestScope(baseRule, request);
        List<EventRule> rules = new ArrayList<EventRule>();
        if (Boolean.TRUE.equals(request.getCustomRule()) && request.getThresholds() != null && !request.getThresholds().isEmpty()) {
            request.getThresholds().stream()
                    .filter(item -> item.getThresholdValue() != null)
                    .sorted(Comparator.comparingInt(item -> severityRank(item.getLevel())))
                    .forEach(item -> {
                        EventRule rule = copyRule(baseRule);
                        rule.setRuleCode("CUSTOM_" + item.getLevel() + "_" + (request.getMetricCode() == null ? "RULE" : request.getMetricCode()));
                        rule.setRuleName("Custom multi-level threshold rule");
                        rule.setEventLevel(item.getLevel());
                        rule.setOperator(request.getOperator());
                        rule.setThresholdValue(item.getThresholdValue());
                        rule.setThresholdUnit(request.getThresholdUnit());
                        rule.setAggregationMethod("last");
                        rules.add(rule);
                    });
        }
        if (rules.isEmpty()) {
            EventRule rule = copyRule(baseRule);
            if (Boolean.TRUE.equals(request.getCustomRule())) {
                rule.setRuleCode("CUSTOM_" + (request.getMetricCode() == null ? "RULE" : request.getMetricCode()));
                rule.setRuleName("Custom threshold rule");
                rule.setEventLevel(request.getEventLevel());
                rule.setOperator(request.getOperator());
                rule.setThresholdValue(request.getThresholdValue());
                rule.setThresholdUnit(request.getThresholdUnit());
                rule.setAggregationMethod("last");
            }
            rules.add(rule);
        }
        return rules;
    }

    private void applyRequestScope(EventRule rule, RuleEvaluationRequest request) {
        if (request.getMetricCode() != null && !request.getMetricCode().trim().isEmpty()) {
            rule.setMetricCode(request.getMetricCode().trim());
        }
        if (request.getInstrumentType() != null && !request.getInstrumentType().trim().isEmpty()) {
            rule.setSourceInstrumentType(request.getInstrumentType().trim());
        }
        if (request.getInputSource() != null && !request.getInputSource().trim().isEmpty()) {
            rule.setInputSource(request.getInputSource().trim().toUpperCase());
        }
        if (request.getPredictionModelCode() != null && !request.getPredictionModelCode().trim().isEmpty()) {
            rule.setPredictionModelCode(request.getPredictionModelCode().trim());
        }
        if (request.getPredictionTargetType() != null && !request.getPredictionTargetType().trim().isEmpty()) {
            rule.setPredictionTargetType(request.getPredictionTargetType().trim());
        }
        if (request.getPredictionFeatureCode() != null && !request.getPredictionFeatureCode().trim().isEmpty()) {
            rule.setPredictionFeatureCode(request.getPredictionFeatureCode().trim());
        }
        if (request.getForecastHorizonMinutes() != null && request.getForecastHorizonMinutes() > 0) {
            rule.setForecastHorizonMinutes(request.getForecastHorizonMinutes());
        }
        if (request.getMinimumConsecutiveSteps() != null && request.getMinimumConsecutiveSteps() > 0) {
            rule.setMinimumConsecutiveSteps(request.getMinimumConsecutiveSteps());
            rule.setContinuousCount(request.getMinimumConsecutiveSteps());
        }
        if (request.getSeriesQualityFilter() != null && !request.getSeriesQualityFilter().trim().isEmpty()) {
            rule.setSeriesQualityFilter(request.getSeriesQualityFilter().trim());
        }
    }

    private EventRule copyRule(EventRule source) {
        EventRule rule = new EventRule();
        rule.setId(source.getId());
        rule.setProjectId(source.getProjectId());
        rule.setRuleCode(source.getRuleCode());
        rule.setRuleName(source.getRuleName());
        rule.setMetricCode(source.getMetricCode());
        rule.setSourceInstrumentType(source.getSourceInstrumentType());
        rule.setInputSource(source.getInputSource());
        rule.setPredictionModelCode(source.getPredictionModelCode());
        rule.setPredictionTargetType(source.getPredictionTargetType());
        rule.setPredictionFeatureCode(source.getPredictionFeatureCode());
        rule.setForecastHorizonMinutes(source.getForecastHorizonMinutes());
        rule.setMinimumConsecutiveSteps(source.getMinimumConsecutiveSteps());
        rule.setSeriesQualityFilter(source.getSeriesQualityFilter());
        rule.setStationScope(source.getStationScope());
        rule.setStationIdsJson(source.getStationIdsJson());
        rule.setInstrumentIdsJson(source.getInstrumentIdsJson());
        rule.setRuleMode(source.getRuleMode());
        rule.setEventType(source.getEventType());
        rule.setEventLevel(source.getEventLevel());
        rule.setTimeWindow(source.getTimeWindow());
        rule.setAggregationMethod(source.getAggregationMethod());
        rule.setOperator(source.getOperator());
        rule.setThresholdValue(source.getThresholdValue());
        rule.setThresholdValueUpper(source.getThresholdValueUpper());
        rule.setThresholdUnit(source.getThresholdUnit());
        rule.setBaselineStrategy(source.getBaselineStrategy());
        rule.setQualityPolicy(source.getQualityPolicy());
        rule.setMissingDataPolicy(source.getMissingDataPolicy());
        rule.setResultPolicy(source.getResultPolicy());
        rule.setContinuousCount(source.getContinuousCount());
        rule.setCooldownMinutes(source.getCooldownMinutes());
        rule.setCooldownSeconds(source.getCooldownSeconds());
        rule.setCurrentVersion(source.getCurrentVersion());
        rule.setRuleSnapshotJson(source.getRuleSnapshotJson());
        rule.setActionPolicyId(source.getActionPolicyId());
        rule.setEnabled(source.getEnabled());
        rule.setCreatedAt(source.getCreatedAt());
        rule.setUpdatedAt(source.getUpdatedAt());
        return rule;
    }

    private int severityRank(String level) {
        if ("red".equalsIgnoreCase(level)) {
            return 1;
        }
        if ("orange".equalsIgnoreCase(level)) {
            return 2;
        }
        if ("yellow".equalsIgnoreCase(level)) {
            return 3;
        }
        return 9;
    }

    private EventEvaluationRun createRun(EventRule rule, RuleEvaluationRequest request, int eventCount,
                                         List<MetricSeriesPoint> points) {
        LocalDateTime end = request.getEndTime() == null ? LocalDateTime.now() : request.getEndTime();
        LocalDateTime start = request.getStartTime() == null ? end.minusDays(1) : request.getStartTime();
        EventEvaluationRun run = new EventEvaluationRun();
        run.setProjectId(request.getProjectId() == null ? rule.getProjectId() : request.getProjectId());
        run.setRuleId(rule.getId());
        run.setRunMode(request.getRunMode() == null ? "dry_run" : request.getRunMode());
        run.setRuleVersion(rule.getCurrentVersion() == null ? "baseline" : rule.getCurrentVersion());
        run.setConversionVersion(conversionVersion(points));
        String inputSource = seriesPointService.resolveInputSource(rule, request);
        run.setInputRegistryCode("PREDICTION".equals(inputSource)
                ? "prediction:" + text(rule.getPredictionFeatureCode(), rule.getMetricCode())
                : (rule.getSourceInstrumentType() == null ? null : rule.getSourceInstrumentType() + ":" + rule.getMetricCode()));
        run.setTimeStart(start);
        run.setTimeEnd(end);
        run.setInputParamsJson(canonicalHashService.canonicalJson(inputParams(rule, request)));
        run.setEventCount(eventCount);
        run.setResultSummaryJson(canonicalHashService.canonicalJson(resultSummary(run, eventCount)));
        run.setResultHash(canonicalHashService.sha256Canonical(hashMaterial(run)));
        run.setStatus("success");
        run.setMessage("Metric-Rule-Event engine completed");
        run.setStartedAt(LocalDateTime.now());
        run.setFinishedAt(LocalDateTime.now());
        runMapper.insert(run);
        return run;
    }

    private String conversionVersion(List<MetricSeriesPoint> points) {
        java.util.Set<String> versions = new java.util.TreeSet<String>();
        if (points != null) {
            for (MetricSeriesPoint point : points) {
                if (point.getConversionVersion() != null && !point.getConversionVersion().trim().isEmpty()) {
                    versions.add(point.getConversionVersion().trim());
                }
            }
        }
        if (versions.isEmpty()) return "unversioned";
        if (versions.size() == 1) return versions.iterator().next();
        return "mixed-" + canonicalHashService.sha256Canonical(versions).substring(0, 24);
    }

    private Map<String, Object> inputParams(EventRule rule, RuleEvaluationRequest request) {
        Map<String, Object> params = new LinkedHashMap<String, Object>();
        params.put("projectId", request.getProjectId() == null ? rule.getProjectId() : request.getProjectId());
        params.put("ruleId", rule.getId());
        params.put("runMode", request.getRunMode() == null ? "dry_run" : request.getRunMode());
        params.put("stationIds", request.getStationIds());
        params.put("instrumentIds", request.getInstrumentIds());
        params.put("instrumentType", request.getInstrumentType());
        params.put("metricCode", request.getMetricCode());
        params.put("requestedStartTime", request.getStartTime() == null ? null : request.getStartTime().toString());
        params.put("requestedEndTime", request.getEndTime() == null ? null : request.getEndTime().toString());
        params.put("customRule", request.getCustomRule());
        params.put("eventLevel", request.getEventLevel());
        params.put("operator", request.getOperator());
        params.put("thresholdValue", request.getThresholdValue());
        params.put("thresholds", request.getThresholds());
        params.put("thresholdUnit", request.getThresholdUnit());
        params.put("inputSource", seriesPointService.resolveInputSource(rule, request));
        params.put("predictionBatchId", request.getPredictionBatchId());
        params.put("predictionBatchCode", request.getPredictionBatchCode());
        params.put("predictionModelCode", request.getPredictionModelCode());
        params.put("predictionTargetType", request.getPredictionTargetType());
        params.put("predictionFeatureCode", request.getPredictionFeatureCode());
        params.put("forecastHorizonMinutes", request.getForecastHorizonMinutes());
        params.put("minimumConsecutiveSteps", request.getMinimumConsecutiveSteps());
        params.put("seriesQualityFilter", request.getSeriesQualityFilter());
        return params;
    }

    private Map<String, Object> resultSummary(EventEvaluationRun run, int eventCount) {
        Map<String, Object> summary = new LinkedHashMap<String, Object>();
        summary.put("eventCount", eventCount);
        summary.put("ruleVersion", run.getRuleVersion());
        summary.put("conversionVersion", run.getConversionVersion());
        summary.put("inputRegistryCode", run.getInputRegistryCode());
        return summary;
    }

    private Map<String, Object> hashMaterial(EventEvaluationRun run) {
        Map<String, Object> material = new LinkedHashMap<String, Object>();
        material.put("projectId", run.getProjectId());
        material.put("ruleId", run.getRuleId());
        material.put("ruleVersion", run.getRuleVersion());
        material.put("conversionVersion", run.getConversionVersion());
        material.put("inputRegistryCode", run.getInputRegistryCode());
        material.put("inputParams", run.getInputParamsJson());
        material.put("eventCount", run.getEventCount());
        material.put("resultSummary", run.getResultSummaryJson());
        return material;
    }

    private void persistEvent(Event event) {
        eventMapper.insert(event);
        Event persisted = eventMapper.selectByCode(event.getProjectId(), event.getEventCode());
        if (persisted == null || persisted.getId() == null) {
            throw new IllegalStateException("Persisted event cannot be resolved: " + event.getEventCode());
        }
        event.setId(persisted.getId());
    }

    private void persistPredictionTrace(Event event, PredictionExecutionGate gate) {
        if (event == null || event.getId() == null || !"FORECAST".equalsIgnoreCase(event.getSourceType())) {
            return;
        }
        EventPredictionTrace trace = new EventPredictionTrace();
        trace.setEventId(event.getId());
        trace.setPredictionBatchId(event.getPredictionBatchId());
        trace.setPredictionRunId(event.getPredictionRunId());
        trace.setPredictionGateId(gate == null ? null : gate.getId());
        trace.setModelId(event.getPredictionModelId());
        trace.setFirstExceedanceTime(event.getFirstExceedanceTime());
        trace.setLeadTimeMinutes(event.getLeadTimeMinutes());
        trace.setPeakPredictedValue(event.getPeakPredictedValue());
        trace.setConsecutiveExceedanceSteps(event.getConsecutiveExceedanceSteps());
        trace.setForecastSnapshotJson(event.getForecastSnapshotJson());
        trace.setResultHash(event.getPredictionResultHash());
        predictionTraceMapper.insert(trace);
    }

    private String text(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }

    private void addPredictionGate(Map<String, Object> result, PredictionExecutionGate gate) {
        if (gate == null) {
            result.put("executionEligible", true);
            return;
        }
        result.put("predictionGate", gate);
        result.put("executionEligible", gate.getExecutionEligible());
        result.put("executionBlockers", gate.getIssues());
    }

    private PredictionExecutionMode formalExecutionMode(EventRule rule, RuleEvaluationRequest request) {
        if (!"PREDICTION".equals(seriesPointService.resolveInputSource(rule, request))) {
            return PredictionExecutionMode.OPERATIONAL;
        }
        PredictionExecutionMode mode = PredictionExecutionMode.from(
                request.getPredictionExecutionMode(), PredictionExecutionMode.OPERATIONAL);
        if (mode == PredictionExecutionMode.REPLAY) {
            throw new BusinessException("REPLAY is evaluation-only and cannot create formal events");
        }
        return mode;
    }

    private PredictionExecutionGate requirePredictionExecutionEligible(EventRule rule,
                                                                        RuleEvaluationRequest request,
                                                                        PredictionExecutionMode mode) {
        if (!"PREDICTION".equals(seriesPointService.resolveInputSource(rule, request))) {
            return null;
        }
        PredictionExecutionGate gate = predictionGate(rule, request, mode, true);
        if (!Boolean.TRUE.equals(gate.getExecutionEligible())) {
            throw new BusinessException("Prediction batch is not eligible for formal event execution: "
                    + String.join(", ", gate.getIssues()));
        }
        return gate;
    }

    private PredictionExecutionGate predictionGate(EventRule rule,
                                                    RuleEvaluationRequest request,
                                                    PredictionExecutionMode defaultMode,
                                                    boolean record) {
        if (!"PREDICTION".equals(seriesPointService.resolveInputSource(rule, request))) {
            return null;
        }
        PredictionBatch batch = predictionService.resolveBatch(predictionQuery(rule, request));
        PredictionExecutionMode mode = PredictionExecutionMode.from(request.getPredictionExecutionMode(), defaultMode);
        LocalDateTime referenceTime = mode == PredictionExecutionMode.REPLAY
                ? request.getEndTime()
                : (mode == PredictionExecutionMode.REPRODUCTION ? batch.getBaseTime() : null);
        return record
                ? predictionExecutionGateService.evaluate(batch.getId(), mode, referenceTime)
                : predictionExecutionGateService.inspect(batch.getId(), mode, referenceTime);
    }

    private PredictionQuery predictionQuery(EventRule rule, RuleEvaluationRequest request) {
        PredictionQuery query = new PredictionQuery();
        query.setProjectId(request.getProjectId() == null ? rule.getProjectId() : request.getProjectId());
        query.setBatchId(request.getPredictionBatchId());
        query.setBatchCode(request.getPredictionBatchCode());
        query.setModelCode(text(request.getPredictionModelCode(), rule.getPredictionModelCode()));
        query.setTargetType(text(request.getPredictionTargetType(), rule.getPredictionTargetType()));
        query.setFeatureCode(text(request.getPredictionFeatureCode(), rule.getPredictionFeatureCode()));
        return query;
    }
}
