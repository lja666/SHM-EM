package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MetricRuleEventEngineEngineeringTest {
    private final MetricRuleEventEngine engine = new MetricRuleEventEngine();

    @Test
    void rejectsThresholdUnitThatDoesNotMatchEngineeringUnit() {
        EventRule rule = rule("ground_settlement", "cm", "5");
        MetricSeriesPoint point = point("ground_settlement", "mm", "9.41");
        assertThrows(BusinessException.class, () -> engine.evaluate(rule, Collections.singletonList(point), false));
    }

    @Test
    void eventSnapshotCarriesRawEngineeringAndVersionedFormula() {
        EventRule rule = rule("ground_settlement", "mm", "5");
        MetricSeriesPoint point = point("ground_settlement", "mm", "9.41");
        List<Event> events = engine.evaluate(rule, Collections.singletonList(point), false);
        assertEquals(1, events.size());
        String snapshot = events.get(0).getCalculationSnapshotJson();
        assertTrue(snapshot.contains("\"rawValue\":54.13"));
        assertTrue(snapshot.contains("\"engineeringValue\":9.41"));
        assertTrue(snapshot.contains("static-level-v2-positive-20260713"));
    }

    private EventRule rule(String metricCode, String unit, String threshold) {
        EventRule rule = new EventRule();
        rule.setId(1L);
        rule.setRuleCode("TEST_RULE");
        rule.setCurrentVersion("test-v1");
        rule.setMetricCode(metricCode);
        rule.setThresholdUnit(unit);
        rule.setThresholdValue(new BigDecimal(threshold));
        rule.setOperator(">");
        rule.setRuleMode("threshold");
        rule.setAggregationMethod("last");
        rule.setEventType("warning");
        rule.setEventLevel("yellow");
        return rule;
    }

    private MetricSeriesPoint point(String metricCode, String unit, String value) {
        MetricSeriesPoint point = new MetricSeriesPoint();
        point.setProjectId(1L);
        point.setStationId(1L);
        point.setInstrumentId(1L);
        point.setMetricCode(metricCode);
        point.setTimestamp(LocalDateTime.of(2026, 6, 24, 10, 0));
        point.setValue(new BigDecimal(value));
        point.setUnit(unit);
        point.setRawValue(new BigDecimal("54.13"));
        point.setRawUnit("mm");
        point.setEngineeringValue(new BigDecimal(value));
        point.setEngineeringUnit(unit);
        point.setEngineeringMetricCode(metricCode);
        point.setValueMode("ENGINEERING");
        point.setConversionOperatorCode("static_level_reference_compensation");
        point.setConversionVersion("static-level-v2-positive-20260713");
        point.setConversionStatus("success");
        point.setSourceType("OBSERVATION");
        return point;
    }
}
