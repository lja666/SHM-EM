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

    private Map<String, Object> row(String key1, Object value1, String key2, Object value2) {
        Map<String, Object> row = new LinkedHashMap<String, Object>();
        row.put(key1, value1);
        row.put(key2, value2);
        return row;
    }
}
