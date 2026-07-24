package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.application.service.ProjectFutureStateService;
import mybatis.iem.em.modules.engineering.application.service.ProjectService;
import mybatis.iem.em.modules.engineering.domain.model.FutureRiskThreshold;
import mybatis.iem.em.modules.engineering.domain.model.FutureStatePolicy;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.domain.model.ProjectFutureState;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectFutureStateMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class ProjectFutureStateServiceImpl implements ProjectFutureStateService {
    private final ProjectService projectService;
    private final PredictionService predictionService;
    private final PredictionExecutionGateService executionGateService;
    private final ProjectFutureStateMapper mapper;
    private final CanonicalHashService canonicalHashService;
    private final ObjectMapper objectMapper;

    public ProjectFutureStateServiceImpl(ProjectService projectService,
                                         PredictionService predictionService,
                                         PredictionExecutionGateService executionGateService,
                                         ProjectFutureStateMapper mapper,
                                         CanonicalHashService canonicalHashService,
                                         ObjectMapper objectMapper) {
        this.projectService = projectService;
        this.predictionService = predictionService;
        this.executionGateService = executionGateService;
        this.mapper = mapper;
        this.canonicalHashService = canonicalHashService;
        this.objectMapper = objectMapper;
    }

    @Override
    public ProjectFutureState get(Long projectId,
                                  Long batchId,
                                  Integer horizonMinutes,
                                  PredictionExecutionMode executionMode,
                                  LocalDateTime referenceTime) {
        Project project = projectService.get(projectId);
        if (project == null) throw new BusinessException("Project not found: " + projectId);
        FutureStatePolicy policy = mapper.selectActivePolicy(projectId);
        if (policy == null || isBlank(policy.getPolicyCode()) || isBlank(policy.getPolicyVersion())
                || isBlank(policy.getPolicyHash())) {
            throw new BusinessException("No active future-state aggregation policy is configured for project " + projectId);
        }
        PolicySettings policySettings = policySettings(policy);
        PredictionQuery batchQuery = new PredictionQuery();
        batchQuery.setProjectId(projectId);
        batchQuery.setBatchId(batchId);
        batchQuery.setStatus("success");
        PredictionBatch batch = predictionService.resolveBatch(batchQuery);
        if (!projectId.equals(batch.getProjectId())) {
            throw new BusinessException("Prediction batch does not belong to project " + projectId);
        }
        if (!"success".equalsIgnoreCase(batch.getStatus())) {
            throw new BusinessException("Project future state requires a successful prediction batch");
        }
        int effectiveHorizon = normalizeHorizon(horizonMinutes, batch.getHorizonMinutes());
        PredictionExecutionMode effectiveMode = executionMode == null
                ? PredictionExecutionMode.OPERATIONAL : executionMode;
        PredictionExecutionGate gate = executionGateService.inspect(batch.getId(), effectiveMode, referenceTime);

        PredictionQuery seriesQuery = new PredictionQuery();
        seriesQuery.setProjectId(projectId);
        seriesQuery.setBatchId(batch.getId());
        seriesQuery.setMaxHorizonMinutes(effectiveHorizon);
        seriesQuery.setIncludeObserved(false);
        seriesQuery.setValueMode("ENGINEERING");
        seriesQuery.setLimit(50000);
        List<MetricSeriesPoint> points = predictionService.predictionSeries(seriesQuery).stream()
                .filter(point -> point.getValue() != null)
                .filter(point -> "success".equalsIgnoreCase(point.getConversionStatus()))
                .sorted(Comparator.comparing(MetricSeriesPoint::getTimestamp, Comparator.nullsLast(Comparator.naturalOrder()))
                        .thenComparing(MetricSeriesPoint::getFeatureCode, Comparator.nullsLast(String::compareTo)))
                .collect(Collectors.toList());
        if (points.isEmpty()) {
            throw new BusinessException("No engineering prediction series is available for batch " + batch.getId());
        }

        List<FutureRiskThreshold> thresholds = "enabledEventRuleLevels".equals(policySettings.thresholdSource)
                ? safe(mapper.selectRiskThresholds(projectId)) : Collections.<FutureRiskThreshold>emptyList();
        Map<String, List<FutureRiskThreshold>> thresholdsByMetric = thresholds.stream()
                .filter(item -> !isBlank(item.getMetricCode()))
                .collect(Collectors.groupingBy(item -> item.getMetricCode().toLowerCase(), LinkedHashMap::new, Collectors.toList()));
        List<AssessedPoint> assessed = assess(points, thresholdsByMetric, policySettings);
        Map<Long, String> stationNames = stationNames(safeMaps(mapper.selectStationNames(projectId)));
        ObservedRisk observed = observedRisk(safeMaps(mapper.selectOpenObservedRiskCounts(projectId)));

        ProjectFutureState result = new ProjectFutureState();
        result.setProjectId(projectId);
        result.setBatchId(batch.getId());
        result.setBatchCode(batch.getBatchCode());
        result.setBaseTime(batch.getBaseTime());
        result.setHorizonMinutes(effectiveHorizon);
        result.setExecutionMode(effectiveMode.name());
        result.setGateId(gate.getId());
        result.setExecutionEligible(gate.getExecutionEligible());
        result.setExecutionBlockers(new ArrayList<String>(gate.getIssues()));
        result.setExecutionGate(gate);
        result.setAggregationPolicyCode(policy.getPolicyCode());
        result.setAggregationPolicyVersion(policy.getPolicyVersion());
        result.setAggregationPolicyHash(policy.getPolicyHash());
        result.setObservedRiskLevel(observed.level.code);
        result.setOpenObservedEventCount(observed.count);

        RiskLevel forecast = forecastRisk(assessed, policySettings);
        result.setForecastRiskLevel(forecast.code);
        result.setOverallRiskLevel(overallRisk(observed.level, forecast, policySettings).code);
        result.setEarliestExceedanceTime(assessed.stream()
                .filter(item -> item.risk.rank > 0)
                .map(item -> item.point.getTimestamp())
                .filter(item -> item != null)
                .min(LocalDateTime::compareTo).orElse(null));

        Set<String> assessedFeatures = assessed.stream().filter(item -> item.assessed)
                .map(item -> featureKey(item.point, policySettings)).collect(Collectors.toCollection(LinkedHashSet::new));
        Set<String> allFeatures = points.stream().map(item -> featureKey(item, policySettings))
                .collect(Collectors.toCollection(LinkedHashSet::new));
        result.setAssessedFeatureCount(assessedFeatures.size());
        result.setUnassessedFeatureCount(Math.max(0, allFeatures.size() - assessedFeatures.size()));
        result.setTargets(targets(assessed, policySettings));
        result.setStations(stations(assessed, stationNames, policySettings));
        result.setTimeline(timeline(assessed, policySettings));
        result.setStateHash(stateHash(result));
        return result;
    }

    private List<AssessedPoint> assess(List<MetricSeriesPoint> points,
                                       Map<String, List<FutureRiskThreshold>> thresholdsByMetric,
                                       PolicySettings policy) {
        Map<String, List<MetricSeriesPoint>> byFeature = points.stream()
                .collect(Collectors.groupingBy(item -> featureKey(item, policy), LinkedHashMap::new, Collectors.toList()));
        List<AssessedPoint> result = new ArrayList<AssessedPoint>();
        for (List<MetricSeriesPoint> featurePoints : byFeature.values()) {
            featurePoints.sort(Comparator.comparing(MetricSeriesPoint::getStep, Comparator.nullsLast(Integer::compareTo)));
            Map<String, Integer> streaks = new HashMap<String, Integer>();
            for (MetricSeriesPoint point : featurePoints) {
                List<FutureRiskThreshold> candidates = thresholdsByMetric.getOrDefault(
                        text(point.getMetricCode()).toLowerCase(), Collections.<FutureRiskThreshold>emptyList());
                AssessedPoint assessed = new AssessedPoint(point, candidates.isEmpty());
                for (FutureRiskThreshold threshold : candidates) {
                    if (!unitsMatch(point.getUnit(), threshold.getThresholdUnit(), policy)) continue;
                    String key = threshold.getRuleId() + ":" + threshold.getLevelCode();
                    int streak = matches(point.getValue(), threshold) ? streaks.getOrDefault(key, 0) + 1 : 0;
                    streaks.put(key, streak);
                    assessed.assessed = true;
                    int required = threshold.getMinimumConsecutiveSteps() == null
                            ? 1 : Math.max(1, threshold.getMinimumConsecutiveSteps());
                    RiskLevel risk = RiskLevel.of(threshold.getLevelCode(), threshold.getLevelRank());
                    if (streak >= required && risk.rank > assessed.risk.rank) {
                        assessed.risk = risk;
                        assessed.threshold = threshold;
                    }
                }
                result.add(assessed);
            }
        }
        return result;
    }

    private List<ProjectFutureState.TargetState> targets(List<AssessedPoint> points, PolicySettings policy) {
        Map<String, List<AssessedPoint>> groups = points.stream().collect(Collectors.groupingBy(
                item -> text(item.point.getTargetType()), LinkedHashMap::new, Collectors.toList()));
        List<ProjectFutureState.TargetState> result = new ArrayList<ProjectFutureState.TargetState>();
        for (Map.Entry<String, List<AssessedPoint>> entry : groups.entrySet()) {
            List<AssessedPoint> rows = entry.getValue();
            ProjectFutureState.TargetState item = new ProjectFutureState.TargetState();
            item.setTargetType(entry.getKey());
            Set<String> features = rows.stream().map(row -> featureKey(row.point, policy)).collect(Collectors.toSet());
            Set<String> assessedFeatures = rows.stream().filter(row -> row.assessed).map(row -> featureKey(row.point, policy)).collect(Collectors.toSet());
            Set<String> warnings = rows.stream().filter(row -> row.risk.rank >= 10).map(row -> featureKey(row.point, policy)).collect(Collectors.toSet());
            Set<String> alarms = rows.stream().filter(row -> row.risk.rank >= 30).map(row -> featureKey(row.point, policy)).collect(Collectors.toSet());
            item.setFeatureCount(features.size());
            item.setAssessedFeatureCount(assessedFeatures.size());
            item.setWarningCount(warnings.size());
            item.setAlarmCount(alarms.size());
            item.setRiskLevel(rows.stream().map(row -> row.risk).max(Comparator.comparingInt(level -> level.rank)).orElse(RiskLevel.UNASSESSED).code);
            item.setMinPredictedValue(rows.stream().map(row -> row.point.getValue()).filter(value -> value != null)
                    .min(BigDecimal::compareTo).orElse(null));
            item.setMaxPredictedValue(rows.stream().map(row -> row.point.getValue()).filter(value -> value != null)
                    .max(BigDecimal::compareTo).orElse(null));
            AssessedPoint governing = rows.stream().filter(row -> row.point.getValue() != null)
                    .max(Comparator.comparingInt((AssessedPoint row) -> row.risk.rank)
                            .thenComparing(this::thresholdDistance)).orElse(null);
            item.setGoverningValue(governing == null ? null : governing.point.getValue());
            item.setGoverningThreshold(governing == null || governing.threshold == null
                    ? null : governing.threshold.getThresholdValue());
            item.setThresholdDistance(governing == null ? null : thresholdDistance(governing));
            item.setPeakValue(item.getGoverningValue());
            item.setUnit(governing == null ? null : governing.point.getUnit());
            item.setFirstExceedanceTime(rows.stream().filter(row -> row.risk.rank > 0)
                    .map(row -> row.point.getTimestamp()).filter(value -> value != null)
                    .min(LocalDateTime::compareTo).orElse(null));
            result.add(item);
        }
        result.sort(Comparator.comparing(ProjectFutureState.TargetState::getTargetType));
        return result;
    }

    private List<ProjectFutureState.StationState> stations(List<AssessedPoint> points,
                                                           Map<Long, String> names,
                                                           PolicySettings policy) {
        Map<Long, List<AssessedPoint>> groups = points.stream()
                .filter(item -> item.point.getStationId() != null)
                .collect(Collectors.groupingBy(item -> item.point.getStationId(), LinkedHashMap::new, Collectors.toList()));
        List<ProjectFutureState.StationState> result = new ArrayList<ProjectFutureState.StationState>();
        for (Map.Entry<Long, List<AssessedPoint>> entry : groups.entrySet()) {
            Map<String, AssessedPoint> contributors = new LinkedHashMap<String, AssessedPoint>();
            for (AssessedPoint row : entry.getValue()) {
                if (row.risk.rank <= 0) continue;
                String key = featureKey(row.point, policy);
                AssessedPoint current = contributors.get(key);
                if (current == null || row.risk.rank > current.risk.rank
                        || (row.risk.rank == current.risk.rank && earlier(row.point.getTimestamp(), current.point.getTimestamp()))) {
                    contributors.put(key, row);
                }
            }
            ProjectFutureState.StationState item = new ProjectFutureState.StationState();
            item.setStationId(entry.getKey());
            item.setStationName(names.getOrDefault(entry.getKey(), "Point " + entry.getKey()));
            item.setRiskLevel(entry.getValue().stream().map(row -> row.risk)
                    .max(Comparator.comparingInt(level -> level.rank)).orElse(RiskLevel.UNASSESSED).code);
            item.setContributors(contributors.values().stream().map(this::contributor)
                    .sorted(Comparator.comparing(ProjectFutureState.Contributor::getRiskRank).reversed()
                            .thenComparing(ProjectFutureState.Contributor::getFirstExceedanceTime, Comparator.nullsLast(LocalDateTime::compareTo)))
                    .collect(Collectors.toList()));
            result.add(item);
        }
        result.sort(Comparator.comparing(ProjectFutureState.StationState::getStationId));
        return result;
    }

    private ProjectFutureState.Contributor contributor(AssessedPoint row) {
        ProjectFutureState.Contributor item = new ProjectFutureState.Contributor();
        item.setFeatureCode(row.point.getFeatureCode());
        item.setFeatureLabel(row.point.getFeatureLabel());
        item.setTargetType(row.point.getTargetType());
        item.setMetricCode(row.point.getMetricCode());
        item.setPredictedValue(row.point.getValue());
        item.setUnit(row.point.getUnit());
        item.setRiskLevel(row.risk.code);
        item.setRiskRank(row.risk.rank);
        item.setFirstExceedanceTime(row.point.getTimestamp());
        if (row.threshold != null) {
            item.setThresholdValue(row.threshold.getThresholdValue());
            item.setOperator(row.threshold.getOperator());
            item.setRuleCode(row.threshold.getRuleCode());
        }
        return item;
    }

    private List<ProjectFutureState.TimelineState> timeline(List<AssessedPoint> points, PolicySettings policy) {
        Map<Integer, List<AssessedPoint>> groups = points.stream().filter(item -> item.point.getStep() != null)
                .collect(Collectors.groupingBy(item -> item.point.getStep(), LinkedHashMap::new, Collectors.toList()));
        List<ProjectFutureState.TimelineState> result = new ArrayList<ProjectFutureState.TimelineState>();
        for (Map.Entry<Integer, List<AssessedPoint>> entry : groups.entrySet()) {
            ProjectFutureState.TimelineState item = new ProjectFutureState.TimelineState();
            item.setStep(entry.getKey());
            MetricSeriesPoint first = entry.getValue().get(0).point;
            item.setHorizonMinutes(first.getHorizonMinutes());
            item.setFutureTime(first.getTimestamp());
            item.setRiskLevel(entry.getValue().stream().map(row -> row.risk)
                    .max(Comparator.comparingInt(level -> level.rank)).orElse(RiskLevel.UNASSESSED).code);
            item.setExceedingFeatureCount((int) entry.getValue().stream().filter(row -> row.risk.rank > 0)
                    .map(row -> featureKey(row.point, policy)).distinct().count());
            result.add(item);
        }
        result.sort(Comparator.comparing(ProjectFutureState.TimelineState::getStep));
        return result;
    }

    private boolean matches(BigDecimal value, FutureRiskThreshold threshold) {
        if (value == null || threshold.getThresholdValue() == null) return false;
        String operator = text(threshold.getOperator()).toLowerCase();
        int comparison = value.compareTo(threshold.getThresholdValue());
        if (">".equals(operator) || "gt".equals(operator)) return comparison > 0;
        if (">=".equals(operator) || "gte".equals(operator)) return comparison >= 0;
        if ("<".equals(operator) || "lt".equals(operator)) return comparison < 0;
        if ("<=".equals(operator) || "lte".equals(operator)) return comparison <= 0;
        if ("abs_gt".equals(operator)) return value.abs().compareTo(threshold.getThresholdValue().abs()) > 0;
        if ("abs_gte".equals(operator)) return value.abs().compareTo(threshold.getThresholdValue().abs()) >= 0;
        if ("between".equals(operator) && threshold.getThresholdValueUpper() != null) {
            return comparison >= 0 && value.compareTo(threshold.getThresholdValueUpper()) <= 0;
        }
        return false;
    }

    private ObservedRisk observedRisk(List<Map<String, Object>> rows) {
        RiskLevel level = RiskLevel.NORMAL;
        int count = 0;
        for (Map<String, Object> row : rows) {
            RiskLevel candidate = RiskLevel.of(String.valueOf(row.get("riskLevel")), null);
            level = max(level, candidate);
            Object value = row.get("eventCount");
            count += value instanceof Number ? ((Number) value).intValue() : 0;
        }
        return new ObservedRisk(level, count);
    }

    private Map<Long, String> stationNames(List<Map<String, Object>> rows) {
        Map<Long, String> result = new LinkedHashMap<Long, String>();
        for (Map<String, Object> row : rows) {
            Object id = row.get("stationId");
            if (id instanceof Number) result.put(((Number) id).longValue(), String.valueOf(row.get("stationName")));
        }
        return result;
    }

    private PolicySettings policySettings(FutureStatePolicy policy) {
        if (isBlank(policy.getPolicyJson())) {
            throw new BusinessException("Future-state policy JSON is missing for " + policy.getPolicyCode());
        }
        Map<String, String> values;
        try {
            values = objectMapper.readValue(policy.getPolicyJson(), new TypeReference<Map<String, String>>() {});
        } catch (Exception ex) {
            throw new BusinessException("Future-state policy JSON is invalid for " + policy.getPolicyCode());
        }
        List<String> required = Arrays.asList(
                "unitPolicy", "overallRisk", "featureGroup", "forecastRisk", "thresholdSource");
        if (values.size() != required.size() || !values.keySet().containsAll(required)) {
            throw new BusinessException("Future-state policy must contain exactly: " + String.join(", ", required));
        }
        String calculatedHash = canonicalHashService.sha256Canonical(values);
        if (!calculatedHash.equalsIgnoreCase(policy.getPolicyHash())) {
            throw new BusinessException("Future-state policy hash mismatch for " + policy.getPolicyCode());
        }
        PolicySettings settings = new PolicySettings(
                required(values, "unitPolicy"),
                required(values, "overallRisk"),
                required(values, "featureGroup"),
                required(values, "forecastRisk"),
                required(values, "thresholdSource"));
        requireSupported("unitPolicy", settings.unitPolicy, "exactMatch", "normalizedExactMatch");
        requireSupported("overallRisk", settings.overallRisk,
                "maxObservedAndForecast", "observedOnly", "forecastOnly");
        requireSupported("featureGroup", settings.featureGroup,
                "targetType+featureCode", "metricCode+featureCode");
        requireSupported("forecastRisk", settings.forecastRisk, "maxRiskRank");
        requireSupported("thresholdSource", settings.thresholdSource, "enabledEventRuleLevels");
        return settings;
    }

    private String required(Map<String, String> values, String key) {
        String value = values.get(key);
        if (isBlank(value)) throw new BusinessException("Future-state policy value is missing: " + key);
        return value.trim();
    }

    private void requireSupported(String key, String value, String... supported) {
        if (!Arrays.asList(supported).contains(value)) {
            throw new BusinessException("Unsupported future-state policy value " + key + "=" + value);
        }
    }

    private RiskLevel forecastRisk(List<AssessedPoint> assessed, PolicySettings policy) {
        if (!"maxRiskRank".equals(policy.forecastRisk)) return RiskLevel.UNASSESSED;
        return assessed.stream().map(item -> item.risk)
                .max(Comparator.comparingInt(item -> item.rank)).orElse(RiskLevel.UNASSESSED);
    }

    private RiskLevel overallRisk(RiskLevel observed, RiskLevel forecast, PolicySettings policy) {
        if ("observedOnly".equals(policy.overallRisk)) return observed;
        if ("forecastOnly".equals(policy.overallRisk)) return forecast;
        return max(observed, forecast);
    }

    private String stateHash(ProjectFutureState state) {
        Map<String, Object> material = new LinkedHashMap<String, Object>();
        material.put("batchId", state.getBatchId());
        material.put("horizonMinutes", state.getHorizonMinutes());
        material.put("policyHash", state.getAggregationPolicyHash());
        List<Map<String, Object>> targets = new ArrayList<Map<String, Object>>();
        for (ProjectFutureState.TargetState target : state.getTargets()) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("targetType", target.getTargetType());
            row.put("featureCount", target.getFeatureCount());
            row.put("assessedFeatureCount", target.getAssessedFeatureCount());
            row.put("warningCount", target.getWarningCount());
            row.put("alarmCount", target.getAlarmCount());
            row.put("riskLevel", target.getRiskLevel());
            row.put("minPredictedValue", target.getMinPredictedValue());
            row.put("maxPredictedValue", target.getMaxPredictedValue());
            row.put("governingValue", target.getGoverningValue());
            row.put("governingThreshold", target.getGoverningThreshold());
            row.put("thresholdDistance", target.getThresholdDistance());
            row.put("unit", target.getUnit());
            row.put("firstExceedanceTime", time(target.getFirstExceedanceTime()));
            targets.add(row);
        }
        List<Map<String, Object>> stations = new ArrayList<Map<String, Object>>();
        for (ProjectFutureState.StationState station : state.getStations()) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("stationId", station.getStationId());
            row.put("stationName", station.getStationName());
            row.put("riskLevel", station.getRiskLevel());
            List<Map<String, Object>> contributors = new ArrayList<Map<String, Object>>();
            for (ProjectFutureState.Contributor contributor : station.getContributors()) {
                Map<String, Object> item = new LinkedHashMap<String, Object>();
                item.put("featureCode", contributor.getFeatureCode());
                item.put("targetType", contributor.getTargetType());
                item.put("metricCode", contributor.getMetricCode());
                item.put("predictedValue", contributor.getPredictedValue());
                item.put("unit", contributor.getUnit());
                item.put("thresholdValue", contributor.getThresholdValue());
                item.put("operator", contributor.getOperator());
                item.put("riskLevel", contributor.getRiskLevel());
                item.put("riskRank", contributor.getRiskRank());
                item.put("firstExceedanceTime", time(contributor.getFirstExceedanceTime()));
                item.put("ruleCode", contributor.getRuleCode());
                contributors.add(item);
            }
            row.put("contributors", contributors);
            stations.add(row);
        }
        List<Map<String, Object>> timeline = new ArrayList<Map<String, Object>>();
        for (ProjectFutureState.TimelineState item : state.getTimeline()) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("step", item.getStep());
            row.put("horizonMinutes", item.getHorizonMinutes());
            row.put("futureTime", time(item.getFutureTime()));
            row.put("riskLevel", item.getRiskLevel());
            row.put("exceedingFeatureCount", item.getExceedingFeatureCount());
            timeline.add(row);
        }
        material.put("targets", targets);
        material.put("stations", stations);
        material.put("timeline", timeline);
        return canonicalHashService.sha256Canonical(material);
    }

    private String time(LocalDateTime value) {
        return value == null ? null : value.toString();
    }

    private int normalizeHorizon(Integer requested, Integer available) {
        int max = available == null || available <= 0 ? 120 : available;
        if (requested == null || requested <= 0) return max;
        return Math.min(requested, max);
    }

    private boolean unitsMatch(String actual, String expected, PolicySettings policy) {
        if (isBlank(expected)) return true;
        if (isBlank(actual)) return false;
        return "exactMatch".equals(policy.unitPolicy)
                ? actual.trim().equals(expected.trim())
                : actual.trim().equalsIgnoreCase(expected.trim());
    }

    private String featureKey(MetricSeriesPoint point, PolicySettings policy) {
        String group = "metricCode+featureCode".equals(policy.featureGroup)
                ? text(point.getMetricCode()) : text(point.getTargetType());
        return group + ":" + text(point.getFeatureCode());
    }

    private BigDecimal thresholdDistance(AssessedPoint row) {
        if (row == null || row.point.getValue() == null || row.threshold == null
                || row.threshold.getThresholdValue() == null) {
            return BigDecimal.ZERO;
        }
        BigDecimal value = row.point.getValue();
        BigDecimal threshold = row.threshold.getThresholdValue();
        String operator = text(row.threshold.getOperator()).toLowerCase();
        if ("<".equals(operator) || "lt".equals(operator)
                || "<=".equals(operator) || "lte".equals(operator)) {
            return threshold.subtract(value);
        }
        if ("abs_gt".equals(operator) || "abs_gte".equals(operator)) {
            return value.abs().subtract(threshold.abs());
        }
        if ("between".equals(operator) && row.threshold.getThresholdValueUpper() != null) {
            BigDecimal lowerDistance = value.subtract(threshold).abs();
            BigDecimal upperDistance = value.subtract(row.threshold.getThresholdValueUpper()).abs();
            return lowerDistance.min(upperDistance).negate();
        }
        return value.subtract(threshold);
    }

    private boolean earlier(LocalDateTime first, LocalDateTime second) {
        return first != null && (second == null || first.isBefore(second));
    }

    private RiskLevel max(RiskLevel first, RiskLevel second) {
        return first.rank >= second.rank ? first : second;
    }

    private String text(String value) {
        return value == null ? "" : value.trim();
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private <T> List<T> safe(List<T> values) {
        return values == null ? Collections.<T>emptyList() : values;
    }

    private List<Map<String, Object>> safeMaps(List<Map<String, Object>> values) {
        return values == null ? Collections.<Map<String, Object>>emptyList() : values;
    }

    private static final class AssessedPoint {
        private final MetricSeriesPoint point;
        private boolean assessed;
        private RiskLevel risk = RiskLevel.UNASSESSED;
        private FutureRiskThreshold threshold;

        private AssessedPoint(MetricSeriesPoint point, boolean noThreshold) {
            this.point = point;
            this.assessed = !noThreshold;
            this.risk = noThreshold ? RiskLevel.UNASSESSED : RiskLevel.NORMAL;
        }
    }

    private static final class ObservedRisk {
        private final RiskLevel level;
        private final int count;

        private ObservedRisk(RiskLevel level, int count) {
            this.level = level;
            this.count = count;
        }
    }

    private static final class PolicySettings {
        private final String unitPolicy;
        private final String overallRisk;
        private final String featureGroup;
        private final String forecastRisk;
        private final String thresholdSource;

        private PolicySettings(String unitPolicy,
                               String overallRisk,
                               String featureGroup,
                               String forecastRisk,
                               String thresholdSource) {
            this.unitPolicy = unitPolicy;
            this.overallRisk = overallRisk;
            this.featureGroup = featureGroup;
            this.forecastRisk = forecastRisk;
            this.thresholdSource = thresholdSource;
        }
    }

    private enum RiskLevel {
        UNASSESSED("unassessed", -1), NORMAL("normal", 0), YELLOW("yellow", 10),
        ORANGE("orange", 20), RED("red", 30);

        private final String code;
        private final int rank;

        RiskLevel(String code, int rank) {
            this.code = code;
            this.rank = rank;
        }

        private static RiskLevel of(String code, Integer rank) {
            String value = code == null ? "" : code.trim().toLowerCase();
            for (RiskLevel level : values()) if (level.code.equals(value)) return level;
            if (rank != null) {
                if (rank >= 30) return RED;
                if (rank >= 20) return ORANGE;
                if (rank >= 10) return YELLOW;
                if (rank >= 0) return NORMAL;
            }
            return UNASSESSED;
        }
    }
}
