package mybatis.iem.em;

import mybatis.iem.em.modules.engineering.application.service.impl.MetricRuleEventEngine;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class MetricRuleEventEngineTest {
    private final MetricRuleEventEngine engine = new MetricRuleEventEngine();

    @Test
    public void evaluatesRateOfChangeRules() {
        EventRule rule = baseRule();
        rule.setRuleMode("rate_of_change");
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("3.0"));

        List<Event> events = engine.evaluate(rule, Arrays.asList(
                observation("settlement", "10.0", null, 0),
                observation("settlement", "13.5", null, 10)
        ), false);

        assertEquals(1, events.size());
        assertEquals(new BigDecimal("3.5"), events.get(0).getTriggerValue());
        assertTrue(events.get(0).getTriggerReason().contains("rate_of_change"));
    }

    @Test
    public void evaluatesPercentOfBaselineRules() {
        EventRule rule = baseRule();
        rule.setRuleMode("percent_of_baseline");
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("80"));

        List<Event> events = engine.evaluate(rule, Arrays.asList(
                observation("settlement", "8.5", "10.0", 0)
        ), false);

        assertEquals(1, events.size());
        assertEquals(new BigDecimal("85.000000"), events.get(0).getTriggerValue());
        assertTrue(events.get(0).getTriggerReason().contains("percent_of_baseline"));
    }

    @Test
    public void requiresConfiguredConsecutiveMatches() {
        EventRule rule = baseRule();
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("10"));
        rule.setContinuousCount(3);

        List<Event> events = engine.evaluate(rule, Arrays.asList(
                observation("settlement", "11", null, 0),
                observation("settlement", "12", null, 10),
                observation("settlement", "9", null, 20),
                observation("settlement", "13", null, 30)
        ), false);

        assertTrue(events.isEmpty());

        events = engine.evaluate(rule, Arrays.asList(
                observation("settlement", "11", null, 0),
                observation("settlement", "12", null, 10),
                observation("settlement", "13", null, 20)
        ), false);

        assertEquals(1, events.size());
        assertTrue(events.get(0).getTriggerReason().contains("consecutive"));
    }

    @Test
    public void evaluatesEachMonitoringObjectIndependently() {
        EventRule rule = baseRule();
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("10"));

        List<Event> events = engine.evaluate(rule, Arrays.asList(
                observation("settlement", "11", null, 0),
                observation(4L, 5L, "settlement", "12", null, 10)
        ), true);

        assertEquals(2, events.size());
        assertEquals(2L, events.get(0).getStationId());
        assertEquals(4L, events.get(1).getStationId());
    }

    @Test
    public void createsStableEventCodeForSameRuleAndInputWindow() {
        EventRule rule = baseRule();
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("10"));
        List<MetricSeriesPoint> observations = Arrays.asList(
                observation("settlement", "11", null, 0),
                observation("settlement", "12", null, 10)
        );

        List<Event> first = engine.evaluate(rule, observations, true);
        List<Event> second = engine.evaluate(rule, observations, true);

        assertEquals(1, first.size());
        assertEquals(first.get(0).getEventCode(), second.get(0).getEventCode());
        assertTrue(first.get(0).getCalculationSnapshotJson().contains("inputDigest"));
    }

    @Test
    public void createsForecastEventProvenanceFromPredictionSeries() {
        EventRule rule = baseRule();
        rule.setOperator(">=");
        rule.setThresholdValue(new BigDecimal("10"));
        rule.setContinuousCount(2);

        MetricSeriesPoint first = prediction("11", 1);
        MetricSeriesPoint second = prediction("13", 2);
        List<Event> events = engine.evaluate(rule, Arrays.asList(first, second), true);

        assertEquals(1, events.size());
        Event event = events.get(0);
        assertEquals("FORECAST", event.getSourceType());
        assertEquals(4L, event.getPredictionBatchId());
        assertEquals(24L, event.getPredictionRunId());
        assertEquals(3, event.getLeadTimeMinutes());
        assertEquals(new BigDecimal("13"), event.getPeakPredictedValue());
        assertTrue(event.getEventCode().startsWith("FEVT-"));
    }

    private EventRule baseRule() {
        EventRule rule = new EventRule();
        rule.setId(1L);
        rule.setProjectId(1L);
        rule.setRuleCode("TEST_RULE");
        rule.setMetricCode("settlement");
        rule.setEventType("threshold");
        rule.setEventLevel("yellow");
        rule.setThresholdUnit("mm");
        return rule;
    }

    private MetricSeriesPoint observation(String metricCode, String value, String baseline, int minute) {
        return observation(2L, 3L, metricCode, value, baseline, minute);
    }

    private MetricSeriesPoint observation(Long stationId, Long instrumentId, String metricCode, String value, String baseline, int minute) {
        MetricSeriesPoint observation = new MetricSeriesPoint();
        observation.setProjectId(1L);
        observation.setStationId(stationId);
        observation.setInstrumentId(instrumentId);
        observation.setMetricCode(metricCode);
        observation.setValue(new BigDecimal(value));
        observation.setBaselineValue(baseline == null ? null : new BigDecimal(baseline));
        observation.setUnit("mm");
        observation.setTimestamp(LocalDateTime.of(2026, 6, 14, 10, 0).plusMinutes(minute));
        observation.setSourceType("OBSERVATION");
        observation.setSourceRegistryCode("SHM_EM_PUBLIC_SAMPLE_STATIC_LEVEL");
        observation.setSourceRecordKey("observation:test:" + minute);
        return observation;
    }

    private MetricSeriesPoint prediction(String value, int step) {
        MetricSeriesPoint point = observation("settlement", value, null, step * 3);
        point.setSourceType("PREDICTION");
        point.setSourceRegistryCode(null);
        point.setSourceRecordKey("ROLLING_120M:test:" + step);
        point.setSourceBatchId(4L);
        point.setSourceBatchCode("ROLLING_120M");
        point.setSourceRunId(24L);
        point.setSourceModelId(8L);
        point.setSourceModelCode("settlement");
        point.setSourceModelVersion("pit_pre_v1");
        point.setFeatureCode("dtu1_point1_settlement_value");
        point.setOriginTime(LocalDateTime.of(2026, 6, 14, 10, 0));
        point.setHorizonMinutes(step * 3);
        point.setResultHash("result-hash");
        return point;
    }
}
