package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
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
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class ProjectFutureStateServiceImplTest {
    @Test
    public void aggregatesConsecutiveForecastRiskAndKeepsObservedRiskSeparate() {
        ProjectService projectService = mock(ProjectService.class);
        PredictionService predictionService = mock(PredictionService.class);
        PredictionExecutionGateService gateService = mock(PredictionExecutionGateService.class);
        ProjectFutureStateMapper mapper = mock(ProjectFutureStateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();
        CanonicalHashService hashService = new CanonicalHashService(objectMapper);
        ProjectFutureStateServiceImpl service = new ProjectFutureStateServiceImpl(
                projectService, predictionService, gateService, mapper, hashService, objectMapper);

        Project project = new Project();
        project.setId(1L);
        when(projectService.get(1L)).thenReturn(project);
        FutureStatePolicy policy = new FutureStatePolicy();
        policy.setPolicyCode("PROJECT_MAX_OBSERVED_FORECAST");
        policy.setPolicyVersion("1.0.0");
        policy.setPolicyJson("{\"unitPolicy\":\"normalizedExactMatch\",\"overallRisk\":\"maxObservedAndForecast\","
                + "\"featureGroup\":\"targetType+featureCode\",\"forecastRisk\":\"maxRiskRank\","
                + "\"thresholdSource\":\"enabledEventRuleLevels\"}");
        try {
            policy.setPolicyHash(hashService.sha256Canonical(objectMapper.readValue(policy.getPolicyJson(), Map.class)));
        } catch (Exception ex) {
            throw new AssertionError(ex);
        }
        when(mapper.selectActivePolicy(1L)).thenReturn(policy);

        LocalDateTime base = LocalDateTime.of(2026, 6, 24, 10, 0);
        PredictionBatch batch = new PredictionBatch();
        batch.setId(6L);
        batch.setProjectId(1L);
        batch.setBatchCode("BATCH-6");
        batch.setBaseTime(base);
        batch.setHorizonMinutes(120);
        batch.setStatus("success");
        when(predictionService.resolveBatch(any(PredictionQuery.class))).thenReturn(batch);

        PredictionExecutionGate gate = new PredictionExecutionGate();
        gate.setId(9L);
        gate.setExecutionEligible(true);
        when(gateService.inspect(6L, PredictionExecutionMode.REPLAY, base)).thenReturn(gate);

        List<MetricSeriesPoint> points = new ArrayList<MetricSeriesPoint>();
        points.add(point("feature-a", "Pressure", "earth_pressure_p", 1, 5, base));
        points.add(point("feature-a", "Pressure", "earth_pressure_p", 2, 12, base));
        points.add(point("feature-a", "Pressure", "earth_pressure_p", 3, 15, base));
        points.add(point("feature-b", "water", "groundwater_elevation_m", 1, 8, base));
        when(predictionService.predictionSeries(any(PredictionQuery.class))).thenReturn(points);

        FutureRiskThreshold threshold = new FutureRiskThreshold();
        threshold.setRuleId(1L);
        threshold.setRuleCode("PRESSURE-WARNING");
        threshold.setMetricCode("earth_pressure_p");
        threshold.setLevelCode("yellow");
        threshold.setLevelRank(10);
        threshold.setOperator(">");
        threshold.setThresholdValue(BigDecimal.TEN);
        threshold.setThresholdUnit("MPa");
        threshold.setMinimumConsecutiveSteps(2);
        when(mapper.selectRiskThresholds(1L)).thenReturn(Collections.singletonList(threshold));
        when(mapper.selectStationNames(1L)).thenReturn(Collections.singletonList(row("stationId", 3L, "stationName", "Point 3")));
        when(mapper.selectOpenObservedRiskCounts(1L)).thenReturn(Collections.singletonList(row("riskLevel", "orange", "eventCount", 2L)));

        ProjectFutureState state = service.get(1L, 6L, 120, PredictionExecutionMode.REPLAY, base);

        assertEquals("yellow", state.getForecastRiskLevel());
        assertEquals("orange", state.getObservedRiskLevel());
        assertEquals("orange", state.getOverallRiskLevel());
        assertEquals(1, state.getAssessedFeatureCount());
        assertEquals(1, state.getUnassessedFeatureCount());
        assertEquals(base.plusMinutes(9), state.getEarliestExceedanceTime());
        assertEquals("normal", state.getTimeline().get(1).getRiskLevel());
        assertEquals("yellow", state.getTimeline().get(2).getRiskLevel());
        assertTrue(state.getExecutionEligible());
        assertEquals("PROJECT_MAX_OBSERVED_FORECAST", state.getAggregationPolicyCode());
        assertNotNull(state.getStateHash());
        assertEquals(64, state.getStateHash().length());
    }

    @Test
    public void rejectsPolicyHashDriftBeforeAggregation() {
        ProjectService projectService = mock(ProjectService.class);
        PredictionService predictionService = mock(PredictionService.class);
        PredictionExecutionGateService gateService = mock(PredictionExecutionGateService.class);
        ProjectFutureStateMapper mapper = mock(ProjectFutureStateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();
        ProjectFutureStateServiceImpl service = new ProjectFutureStateServiceImpl(
                projectService, predictionService, gateService, mapper,
                new CanonicalHashService(objectMapper), objectMapper);
        Project project = new Project();
        project.setId(1L);
        when(projectService.get(1L)).thenReturn(project);
        FutureStatePolicy policy = new FutureStatePolicy();
        policy.setPolicyCode("DRIFTED");
        policy.setPolicyVersion("1.0.0");
        policy.setPolicyJson("{\"unitPolicy\":\"exactMatch\"}");
        policy.setPolicyHash("0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f");
        when(mapper.selectActivePolicy(1L)).thenReturn(policy);

        assertThrows(BusinessException.class,
                () -> service.get(1L, null, 120, PredictionExecutionMode.REPLAY, null));
    }

    @Test
    public void leavesFeatureUnassessedWhenNoApplicableRuleExists() {
        LocalDateTime base = LocalDateTime.of(2026, 6, 24, 10, 0);
        Fixture fixture = fixture(Collections.singletonList(
                point(1L, "feature-water", "water", "groundwater_elevation_m", 1, 8, "m", base)),
                Collections.<FutureRiskThreshold>emptyList(), base);

        ProjectFutureState state = fixture.service.get(1L, 6L, 120, PredictionExecutionMode.REPLAY, base);

        assertEquals("unassessed", state.getForecastRiskLevel());
        assertEquals("normal", state.getOverallRiskLevel());
        assertEquals(0, state.getAssessedFeatureCount());
        assertEquals(1, state.getUnassessedFeatureCount());
        assertEquals("unassessed", state.getTargets().get(0).getRiskLevel());
    }

    @Test
    public void distinguishesStrictAndInclusiveExactThresholds() {
        LocalDateTime base = LocalDateTime.of(2026, 6, 24, 10, 0);
        MetricSeriesPoint exact = point(1L, "feature-pressure", "Pressure", "earth_pressure_p",
                1, 10, "MPa", base);
        FutureRiskThreshold strict = threshold(1L, "STRICT", "earth_pressure_p", "yellow", 10,
                ">", 10, "MPa", 1);
        FutureRiskThreshold inclusive = threshold(2L, "INCLUSIVE", "earth_pressure_p", "yellow", 10,
                ">=", 10, "MPa", 1);

        ProjectFutureState strictState = fixture(Collections.singletonList(exact),
                Collections.singletonList(strict), base).service.get(
                1L, 6L, 120, PredictionExecutionMode.REPLAY, base);
        ProjectFutureState inclusiveState = fixture(Collections.singletonList(exact),
                Collections.singletonList(inclusive), base).service.get(
                1L, 6L, 120, PredictionExecutionMode.REPLAY, base);

        assertEquals("normal", strictState.getForecastRiskLevel());
        assertEquals("yellow", inclusiveState.getForecastRiskLevel());
        assertEquals(base.plusMinutes(3), inclusiveState.getEarliestExceedanceTime());
    }

    @Test
    public void aggregatesMultipleTargetsAndStationsByHighestSeverityAndEarliestTime() {
        LocalDateTime base = LocalDateTime.of(2026, 6, 24, 10, 0);
        List<MetricSeriesPoint> points = new ArrayList<MetricSeriesPoint>();
        points.add(point(1L, "pressure-a", "Pressure", "earth_pressure_p", 1, 11, "MPa", base));
        points.add(point(2L, "settlement-b", "settlement", "ground_settlement", 1, 25, "mm", base));
        points.add(point(1L, "pressure-a", "Pressure", "earth_pressure_p", 2, 12, "MPa", base));
        List<FutureRiskThreshold> thresholds = new ArrayList<FutureRiskThreshold>();
        thresholds.add(threshold(1L, "PRESSURE-YELLOW", "earth_pressure_p", "yellow", 10,
                ">", 10, "MPa", 1));
        thresholds.add(threshold(2L, "SETTLEMENT-RED", "ground_settlement", "red", 30,
                ">", 20, "mm", 1));
        Fixture fixture = fixture(points, thresholds, base);
        when(fixture.mapper.selectStationNames(1L)).thenReturn(java.util.Arrays.asList(
                row("stationId", 1L, "stationName", "Point 1"),
                row("stationId", 2L, "stationName", "Point 2")));

        ProjectFutureState state = fixture.service.get(1L, 6L, 120, PredictionExecutionMode.REPLAY, base);

        assertEquals("red", state.getForecastRiskLevel());
        assertEquals("red", state.getOverallRiskLevel());
        assertEquals(base.plusMinutes(3), state.getEarliestExceedanceTime());
        assertEquals(2, state.getTargets().size());
        assertEquals(2, state.getStations().size());
        assertEquals("yellow", state.getStations().get(0).getRiskLevel());
        assertEquals("red", state.getStations().get(1).getRiskLevel());
        assertFalse(state.getStations().get(1).getContributors().isEmpty());
    }

    @Test
    public void producesDeterministicStateHashForEquivalentInput() {
        LocalDateTime base = LocalDateTime.of(2026, 6, 24, 10, 0);
        List<MetricSeriesPoint> points = java.util.Arrays.asList(
                point(2L, "feature-b", "Pressure", "earth_pressure_p", 2, 12, "MPa", base),
                point(1L, "feature-a", "Pressure", "earth_pressure_p", 1, 11, "MPa", base));
        FutureRiskThreshold threshold = threshold(1L, "PRESSURE-YELLOW", "earth_pressure_p",
                "yellow", 10, ">", 10, "MPa", 1);
        Fixture fixture = fixture(points, Collections.singletonList(threshold), base);

        ProjectFutureState first = fixture.service.get(1L, 6L, 120, PredictionExecutionMode.REPLAY, base);
        ProjectFutureState second = fixture.service.get(1L, 6L, 120, PredictionExecutionMode.REPLAY, base);

        assertEquals(first.getStateHash(), second.getStateHash());
        assertEquals(64, first.getStateHash().length());
    }

    private MetricSeriesPoint point(String feature,
                                    String model,
                                    String metric,
                                    int step,
                                    double value,
                                    LocalDateTime base) {
        MetricSeriesPoint point = new MetricSeriesPoint();
        point.setProjectId(1L);
        point.setStationId(3L);
        point.setInstrumentId(30L);
        point.setFeatureCode(feature);
        point.setFeatureLabel(feature);
        point.setSourceModelCode(model);
        point.setTargetType(model);
        point.setMetricCode(metric);
        point.setStep(step);
        point.setHorizonMinutes(step * 3);
        point.setTimestamp(base.plusMinutes(step * 3L));
        point.setValue(BigDecimal.valueOf(value));
        point.setUnit("earth_pressure_p".equals(metric) ? "MPa" : "m");
        point.setConversionStatus("success");
        return point;
    }

    private MetricSeriesPoint point(Long stationId,
                                    String feature,
                                    String target,
                                    String metric,
                                    int step,
                                    double value,
                                    String unit,
                                    LocalDateTime base) {
        MetricSeriesPoint point = new MetricSeriesPoint();
        point.setProjectId(1L);
        point.setStationId(stationId);
        point.setInstrumentId(stationId * 10L);
        point.setFeatureCode(feature);
        point.setFeatureLabel(feature);
        point.setSourceModelCode(target);
        point.setTargetType(target);
        point.setMetricCode(metric);
        point.setStep(step);
        point.setHorizonMinutes(step * 3);
        point.setTimestamp(base.plusMinutes(step * 3L));
        point.setValue(BigDecimal.valueOf(value));
        point.setUnit(unit);
        point.setConversionStatus("success");
        return point;
    }

    private FutureRiskThreshold threshold(Long ruleId,
                                          String ruleCode,
                                          String metricCode,
                                          String levelCode,
                                          int levelRank,
                                          String operator,
                                          double value,
                                          String unit,
                                          int consecutiveSteps) {
        FutureRiskThreshold threshold = new FutureRiskThreshold();
        threshold.setRuleId(ruleId);
        threshold.setRuleCode(ruleCode);
        threshold.setMetricCode(metricCode);
        threshold.setLevelCode(levelCode);
        threshold.setLevelRank(levelRank);
        threshold.setOperator(operator);
        threshold.setThresholdValue(BigDecimal.valueOf(value));
        threshold.setThresholdUnit(unit);
        threshold.setMinimumConsecutiveSteps(consecutiveSteps);
        return threshold;
    }

    private Fixture fixture(List<MetricSeriesPoint> points,
                            List<FutureRiskThreshold> thresholds,
                            LocalDateTime base) {
        ProjectService projectService = mock(ProjectService.class);
        PredictionService predictionService = mock(PredictionService.class);
        PredictionExecutionGateService gateService = mock(PredictionExecutionGateService.class);
        ProjectFutureStateMapper mapper = mock(ProjectFutureStateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();
        CanonicalHashService hashService = new CanonicalHashService(objectMapper);
        ProjectFutureStateServiceImpl service = new ProjectFutureStateServiceImpl(
                projectService, predictionService, gateService, mapper, hashService, objectMapper);

        Project project = new Project();
        project.setId(1L);
        when(projectService.get(1L)).thenReturn(project);
        FutureStatePolicy policy = new FutureStatePolicy();
        policy.setPolicyCode("PROJECT_MAX_OBSERVED_FORECAST");
        policy.setPolicyVersion("1.0.0");
        policy.setPolicyJson("{\"unitPolicy\":\"normalizedExactMatch\",\"overallRisk\":\"maxObservedAndForecast\","
                + "\"featureGroup\":\"targetType+featureCode\",\"forecastRisk\":\"maxRiskRank\","
                + "\"thresholdSource\":\"enabledEventRuleLevels\"}");
        try {
            policy.setPolicyHash(hashService.sha256Canonical(objectMapper.readValue(policy.getPolicyJson(), Map.class)));
        } catch (Exception ex) {
            throw new AssertionError(ex);
        }
        when(mapper.selectActivePolicy(1L)).thenReturn(policy);

        PredictionBatch batch = new PredictionBatch();
        batch.setId(6L);
        batch.setProjectId(1L);
        batch.setBatchCode("BATCH-6");
        batch.setBaseTime(base);
        batch.setHorizonMinutes(120);
        batch.setStatus("success");
        when(predictionService.resolveBatch(any(PredictionQuery.class))).thenReturn(batch);
        when(predictionService.predictionSeries(any(PredictionQuery.class))).thenReturn(points);

        PredictionExecutionGate gate = new PredictionExecutionGate();
        gate.setId(9L);
        gate.setExecutionEligible(true);
        when(gateService.inspect(6L, PredictionExecutionMode.REPLAY, base)).thenReturn(gate);
        when(mapper.selectRiskThresholds(1L)).thenReturn(thresholds);
        when(mapper.selectStationNames(1L)).thenReturn(Collections.<Map<String, Object>>emptyList());
        when(mapper.selectOpenObservedRiskCounts(1L)).thenReturn(
                Collections.singletonList(row("riskLevel", "normal", "eventCount", 0L)));
        return new Fixture(service, mapper);
    }

    private static final class Fixture {
        private final ProjectFutureStateServiceImpl service;
        private final ProjectFutureStateMapper mapper;

        private Fixture(ProjectFutureStateServiceImpl service, ProjectFutureStateMapper mapper) {
            this.service = service;
            this.mapper = mapper;
        }
    }

    private Map<String, Object> row(String key1, Object value1, String key2, Object value2) {
        Map<String, Object> row = new LinkedHashMap<String, Object>();
        row.put(key1, value1);
        row.put(key2, value2);
        return row;
    }
}
