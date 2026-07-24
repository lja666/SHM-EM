package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.common.BusinessException;
import org.json.JSONObject;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class MetricRuleEventEngine {
    public List<Event> evaluate(EventRule rule, List<MetricSeriesPoint> observations, boolean formal) {
        List<MetricSeriesPoint> usable = filter(rule, observations);
        if (usable.isEmpty()) {
            return new ArrayList<Event>();
        }
        List<Event> events = new ArrayList<Event>();
        for (List<MetricSeriesPoint> group : groupByMonitoringObject(usable).values()) {
            EvaluationResult evaluation = evaluateRule(rule, group);
            if (!evaluation.matched) {
                continue;
            }
            events.add(buildEvent(rule, group, evaluation, formal));
        }
        return events;
    }

    private Event buildEvent(EventRule rule, List<MetricSeriesPoint> observations, EvaluationResult evaluation, boolean formal) {
        MetricSeriesPoint trigger = evaluation.trigger;
        boolean prediction = "PREDICTION".equalsIgnoreCase(trigger.getSourceType());
        Event event = new Event();
        event.setEventCode(stableEventCode(rule, observations, evaluation, formal));
        event.setProjectId(trigger.getProjectId());
        event.setStationId(trigger.getStationId());
        event.setInstrumentId(trigger.getInstrumentId());
        event.setMetricCode(rule.getMetricCode());
        event.setRuleId(rule.getId());
        event.setEventType(rule.getEventType());
        event.setEventLevel(rule.getEventLevel());
        event.setEventStatus(formal ? "open" : "simulated");
        event.setSourceType(prediction ? "FORECAST" : "OBSERVATION");
        event.setDetectedAt(prediction ? LocalDateTime.now() : (trigger.getTimestamp() == null ? LocalDateTime.now() : trigger.getTimestamp()));
        event.setWindowStart(observations.get(0).getTimestamp());
        event.setWindowEnd(observations.get(observations.size() - 1).getTimestamp());
        event.setTriggerValue(evaluation.triggerValue);
        event.setThresholdValue(rule.getThresholdValue());
        event.setUnit(trigger.getUnit() == null ? rule.getThresholdUnit() : trigger.getUnit());
        event.setTriggerReason(evaluation.reason);
        event.setSourceRegistryCode(trigger.getSourceRegistryCode());
        String snapshot = snapshotJson(rule, observations, evaluation);
        event.setCalculationSnapshotJson(snapshot);
        if (prediction) {
            event.setPredictionBatchId(trigger.getSourceBatchId());
            event.setPredictionRunId(trigger.getSourceRunId());
            event.setPredictionModelId(trigger.getSourceModelId());
            event.setPredictionBaseTime(trigger.getOriginTime());
            event.setFirstExceedanceTime(trigger.getTimestamp());
            event.setLeadTimeMinutes(leadTimeMinutes(trigger));
            event.setPeakPredictedValue(peakValue(rule, observations));
            event.setConsecutiveExceedanceSteps(evaluation.consecutiveCount);
            event.setForecastSnapshotJson(snapshot);
            event.setPredictionResultHash(trigger.getResultHash());
        }
        return event;
    }

    public List<Map<String, Object>> snapshots(EventRule rule, List<MetricSeriesPoint> observations) {
        List<MetricSeriesPoint> usable = filter(rule, observations);
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        if (usable.isEmpty()) {
            return rows;
        }
        for (List<MetricSeriesPoint> group : groupByMonitoringObject(usable).values()) {
            EvaluationResult evaluation = evaluateRule(rule, group);
            MetricSeriesPoint trigger = evaluation.trigger;
            Map<String, Object> item = new HashMap<String, Object>();
            item.put("projectId", trigger.getProjectId());
            item.put("stationId", trigger.getStationId());
            item.put("instrumentId", trigger.getInstrumentId());
            item.put("metricCode", rule.getMetricCode());
            item.put("ruleMode", ruleMode(rule));
            item.put("aggregationMethod", aggregation(rule));
            item.put("timestamp", trigger.getTimestamp());
            item.put("sourceType", trigger.getSourceType());
            item.put("batchId", trigger.getSourceBatchId());
            item.put("runId", trigger.getSourceRunId());
            item.put("modelCode", trigger.getSourceModelCode());
            item.put("modelVersion", trigger.getSourceModelVersion());
            item.put("featureCode", trigger.getFeatureCode());
            item.put("baseTime", trigger.getOriginTime());
            item.put("horizonMinutes", trigger.getHorizonMinutes());
            item.put("value", evaluation.triggerValue);
            item.put("rawValue", trigger.getRawValue());
            item.put("rawUnit", trigger.getRawUnit());
            item.put("engineeringValue", trigger.getEngineeringValue());
            item.put("engineeringUnit", trigger.getEngineeringUnit());
            item.put("engineeringMetricCode", trigger.getEngineeringMetricCode());
            item.put("valueMode", trigger.getValueMode());
            item.put("conversionOperatorCode", trigger.getConversionOperatorCode());
            item.put("conversionVersion", trigger.getConversionVersion());
            item.put("conversionStatus", trigger.getConversionStatus());
            item.put("threshold", rule.getThresholdValue());
            item.put("thresholdUpper", rule.getThresholdValueUpper());
            item.put("windowStart", group.get(0).getTimestamp());
            item.put("windowEnd", group.get(group.size() - 1).getTimestamp());
            item.put("sampleCount", group.size());
            item.put("matched", evaluation.matched);
            item.put("reason", evaluation.reason);
            item.put("inputDigest", inputDigest(rule, group, evaluation));
            item.put("createdAt", LocalDateTime.now());
            rows.add(item);
        }
        return rows;
    }

    private List<MetricSeriesPoint> filter(EventRule rule, List<MetricSeriesPoint> observations) {
        List<MetricSeriesPoint> rows = new ArrayList<MetricSeriesPoint>();
        if (observations == null) {
            return rows;
        }
        for (MetricSeriesPoint observation : observations) {
            if (observation.getValue() == null) {
                continue;
            }
            if (observation.getConversionStatus() != null
                    && !"success".equalsIgnoreCase(observation.getConversionStatus())) {
                continue;
            }
            if (rule.getMetricCode() != null && !rule.getMetricCode().equals(observation.getMetricCode())) {
                continue;
            }
            requireCompatibleUnit(rule, observation);
            rows.add(observation);
        }
        rows.sort(Comparator.comparing(MetricSeriesPoint::getTimestamp, Comparator.nullsLast(Comparator.naturalOrder())));
        return rows;
    }

    private void requireCompatibleUnit(EventRule rule, MetricSeriesPoint point) {
        String thresholdUnit = normalizeUnit(rule.getThresholdUnit());
        String engineeringUnit = normalizeUnit(point.getUnit());
        if (!thresholdUnit.isEmpty() && !engineeringUnit.isEmpty() && !thresholdUnit.equals(engineeringUnit)) {
            throw new BusinessException("Rule threshold unit " + rule.getThresholdUnit()
                    + " does not match engineering value unit " + point.getUnit()
                    + " for metric " + point.getMetricCode());
        }
    }

    private String normalizeUnit(String unit) {
        if (unit == null) return "";
        return unit.trim().toLowerCase().replace(" ", "").replace("°c", "c");
    }

    private Map<String, List<MetricSeriesPoint>> groupByMonitoringObject(List<MetricSeriesPoint> observations) {
        Map<String, List<MetricSeriesPoint>> groups = new LinkedHashMap<String, List<MetricSeriesPoint>>();
        for (MetricSeriesPoint observation : observations) {
            String key = observation.getProjectId() + "|" + observation.getStationId() + "|"
                    + observation.getInstrumentId() + "|" + observation.getMetricCode();
            List<MetricSeriesPoint> group = groups.get(key);
            if (group == null) {
                group = new ArrayList<MetricSeriesPoint>();
                groups.put(key, group);
            }
            group.add(observation);
        }
        return groups;
    }

    private MetricSeriesPoint pickTrigger(EventRule rule, List<MetricSeriesPoint> observations) {
        String method = aggregation(rule);
        if ("max".equals(method) || "pga".equals(method)) {
            return observations.stream().max(Comparator.comparing(MetricSeriesPoint::getValue)).orElse(observations.get(observations.size() - 1));
        }
        if ("min".equals(method)) {
            return observations.stream().min(Comparator.comparing(MetricSeriesPoint::getValue)).orElse(observations.get(observations.size() - 1));
        }
        if ("mean".equals(method) || "avg".equals(method)) {
            BigDecimal sum = BigDecimal.ZERO;
            for (MetricSeriesPoint item : observations) {
                sum = sum.add(item.getValue());
            }
            BigDecimal mean = sum.divide(BigDecimal.valueOf(observations.size()), 6, RoundingMode.HALF_UP);
            MetricSeriesPoint last = observations.get(observations.size() - 1);
            MetricSeriesPoint synthetic = new MetricSeriesPoint();
            synthetic.setProjectId(last.getProjectId());
            synthetic.setStationId(last.getStationId());
            synthetic.setInstrumentId(last.getInstrumentId());
            synthetic.setMetricCode(last.getMetricCode());
            synthetic.setTimestamp(last.getTimestamp());
            synthetic.setUnit(last.getUnit());
            synthetic.setValue(mean);
            synthetic.setRawValue(last.getRawValue());
            synthetic.setRawUnit(last.getRawUnit());
            synthetic.setEngineeringValue(mean);
            synthetic.setEngineeringUnit(last.getEngineeringUnit());
            synthetic.setEngineeringMetricCode(last.getEngineeringMetricCode());
            synthetic.setValueMode("ENGINEERING");
            synthetic.setConversionOperatorCode(last.getConversionOperatorCode());
            synthetic.setConversionVersion(last.getConversionVersion());
            synthetic.setConversionStatus(last.getConversionStatus());
            synthetic.setConversionRemark(last.getConversionRemark());
            synthetic.setSourceType(last.getSourceType());
            synthetic.setSourceRegistryCode(last.getSourceRegistryCode());
            synthetic.setSourceRecordKey(last.getSourceRecordKey());
            synthetic.setSourceBatchId(last.getSourceBatchId());
            synthetic.setSourceBatchCode(last.getSourceBatchCode());
            synthetic.setSourceRunId(last.getSourceRunId());
            synthetic.setSourceModelId(last.getSourceModelId());
            synthetic.setSourceModelCode(last.getSourceModelCode());
            synthetic.setSourceModelVersion(last.getSourceModelVersion());
            synthetic.setFeatureCode(last.getFeatureCode());
            synthetic.setFeatureLabel(last.getFeatureLabel());
            synthetic.setOriginTime(last.getOriginTime());
            synthetic.setResultHash(last.getResultHash());
            return synthetic;
        }
        return observations.get(observations.size() - 1);
    }

    private EvaluationResult evaluateRule(EventRule rule, List<MetricSeriesPoint> observations) {
        String mode = ruleMode(rule);
        if ("rate_of_change".equals(mode) || "rate".equals(aggregation(rule))) {
            return evaluateRateOfChange(rule, observations);
        }
        if ("percent_of_baseline".equals(mode) || "percent_of_design_value".equals(mode)
                || "percent_of_baseline".equals(baselineStrategy(rule))) {
            return evaluatePercentOfBaseline(rule, observations);
        }
        if (rule.getContinuousCount() != null && rule.getContinuousCount() > 1) {
            return evaluateContinuous(rule, observations);
        }
        MetricSeriesPoint trigger = pickTrigger(rule, observations);
        BigDecimal value = trigger == null ? null : trigger.getValue();
        boolean matched = value != null && matches(rule, value);
        return new EvaluationResult(matched, trigger, value, "metric " + rule.getMetricCode()
                + " " + normalizeOperator(rule.getOperator()) + " " + rule.getThresholdValue(), matched ? 1 : 0);
    }

    private EvaluationResult evaluateRateOfChange(EventRule rule, List<MetricSeriesPoint> observations) {
        if (observations.size() < 2) {
            return EvaluationResult.notMatched(observations.get(observations.size() - 1), "rate_of_change requires at least 2 samples");
        }
        MetricSeriesPoint first = observations.get(0);
        MetricSeriesPoint last = observations.get(observations.size() - 1);
        if (first.getValue() == null || last.getValue() == null) {
            return EvaluationResult.notMatched(last, "rate_of_change has null metric value");
        }
        BigDecimal delta = last.getValue().subtract(first.getValue());
        boolean matched = matches(rule, delta);
        return new EvaluationResult(matched, last, delta, "metric " + rule.getMetricCode()
                + " rate_of_change " + normalizeOperator(rule.getOperator()) + " " + rule.getThresholdValue()
                + " (delta=" + delta + ")", matched ? 1 : 0);
    }

    private EvaluationResult evaluatePercentOfBaseline(EventRule rule, List<MetricSeriesPoint> observations) {
        MetricSeriesPoint trigger = pickTrigger(rule, observations);
        if (trigger == null || trigger.getValue() == null || trigger.getBaselineValue() == null
                || BigDecimal.ZERO.compareTo(trigger.getBaselineValue()) == 0) {
            return EvaluationResult.notMatched(trigger, "percent_of_baseline requires non-zero baseline");
        }
        BigDecimal percent = trigger.getValue()
                .divide(trigger.getBaselineValue(), 6, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100));
        boolean matched = matches(rule, percent);
        return new EvaluationResult(matched, trigger, percent, "metric " + rule.getMetricCode()
                + " percent_of_baseline " + normalizeOperator(rule.getOperator()) + " " + rule.getThresholdValue()
                + " (percent=" + percent + ")", matched ? 1 : 0);
    }

    private EvaluationResult evaluateContinuous(EventRule rule, List<MetricSeriesPoint> observations) {
        int required = Math.max(1, rule.getContinuousCount());
        int count = 0;
        MetricSeriesPoint firstMatch = null;
        MetricSeriesPoint latest = observations.get(observations.size() - 1);
        for (MetricSeriesPoint current : observations) {
            if (current.getValue() != null && matches(rule, current.getValue())) {
                if (count == 0) firstMatch = current;
                count++;
                if (count >= required) {
                    return new EvaluationResult(true, firstMatch, firstMatch.getValue(), "metric " + rule.getMetricCode()
                            + " matched " + required + " consecutive samples "
                            + normalizeOperator(rule.getOperator()) + " " + rule.getThresholdValue(), count);
                }
            } else {
                count = 0;
                firstMatch = null;
            }
        }
        return new EvaluationResult(false, latest, latest.getValue(), "metric " + rule.getMetricCode()
                + " matched " + count + "/" + required + " consecutive samples", count);
    }

    private Integer leadTimeMinutes(MetricSeriesPoint trigger) {
        if (trigger.getOriginTime() == null || trigger.getTimestamp() == null) {
            return trigger.getHorizonMinutes();
        }
        long minutes = Duration.between(trigger.getOriginTime(), trigger.getTimestamp()).toMinutes();
        if (minutes > Integer.MAX_VALUE) return Integer.MAX_VALUE;
        if (minutes < Integer.MIN_VALUE) return Integer.MIN_VALUE;
        return (int) minutes;
    }

    private BigDecimal peakValue(EventRule rule, List<MetricSeriesPoint> observations) {
        if (observations == null || observations.isEmpty()) return null;
        String operator = normalizeOperator(rule.getOperator());
        if ("<".equals(operator) || "<=".equals(operator)) {
            return observations.stream().map(MetricSeriesPoint::getValue).filter(value -> value != null)
                    .min(BigDecimal::compareTo).orElse(null);
        }
        if ("abs_gt".equals(operator)) {
            return observations.stream().map(MetricSeriesPoint::getValue).filter(value -> value != null)
                    .max((left, right) -> left.abs().compareTo(right.abs())).orElse(null);
        }
        return observations.stream().map(MetricSeriesPoint::getValue).filter(value -> value != null)
                .max(BigDecimal::compareTo).orElse(null);
    }

    private boolean matches(EventRule rule, BigDecimal value) {
        BigDecimal threshold = rule.getThresholdValue() == null ? BigDecimal.ZERO : rule.getThresholdValue();
        String operator = normalizeOperator(rule.getOperator());
        if (">".equals(operator)) {
            return value.compareTo(threshold) > 0;
        }
        if (">=".equals(operator)) {
            return value.compareTo(threshold) >= 0;
        }
        if ("<".equals(operator)) {
            return value.compareTo(threshold) < 0;
        }
        if ("<=".equals(operator)) {
            return value.compareTo(threshold) <= 0;
        }
        if ("between".equals(operator)) {
            return rule.getThresholdValueUpper() != null
                    && value.compareTo(threshold) >= 0
                    && value.compareTo(rule.getThresholdValueUpper()) <= 0;
        }
        if ("abs_gt".equals(operator)) {
            return value.abs().compareTo(threshold) > 0;
        }
        return value.compareTo(threshold) == 0;
    }

    private String normalizeOperator(String operator) {
        return operator == null || operator.trim().isEmpty() ? ">=" : operator.trim().toLowerCase();
    }

    private String aggregation(EventRule rule) {
        return rule.getAggregationMethod() == null || rule.getAggregationMethod().trim().isEmpty()
                ? "last"
                : rule.getAggregationMethod().trim().toLowerCase();
    }

    private String ruleMode(EventRule rule) {
        return rule.getRuleMode() == null || rule.getRuleMode().trim().isEmpty()
                ? "threshold"
                : rule.getRuleMode().trim().toLowerCase();
    }

    private String baselineStrategy(EventRule rule) {
        return rule.getBaselineStrategy() == null || rule.getBaselineStrategy().trim().isEmpty()
                ? ""
                : rule.getBaselineStrategy().trim().toLowerCase();
    }

    private String snapshotJson(EventRule rule, List<MetricSeriesPoint> observations, EvaluationResult evaluation) {
        MetricSeriesPoint trigger = evaluation.trigger;
        JSONObject json = new JSONObject();
        json.put("ruleCode", rule.getRuleCode());
        json.put("ruleVersion", rule.getCurrentVersion());
        json.put("ruleMode", ruleMode(rule));
        json.put("aggregationMethod", aggregation(rule));
        json.put("projectId", trigger == null ? null : trigger.getProjectId());
        json.put("stationId", trigger == null ? null : trigger.getStationId());
        json.put("instrumentId", trigger == null ? null : trigger.getInstrumentId());
        json.put("metricCode", rule.getMetricCode());
        json.put("sourceType", trigger == null ? null : trigger.getSourceType());
        json.put("batchId", trigger == null ? null : trigger.getSourceBatchId());
        json.put("batchCode", trigger == null ? null : trigger.getSourceBatchCode());
        json.put("runId", trigger == null ? null : trigger.getSourceRunId());
        json.put("modelCode", trigger == null ? null : trigger.getSourceModelCode());
        json.put("modelVersion", trigger == null ? null : trigger.getSourceModelVersion());
        json.put("featureCode", trigger == null ? null : trigger.getFeatureCode());
        json.put("baseTime", trigger == null ? null : trigger.getOriginTime());
        json.put("futureTime", trigger == null ? null : trigger.getTimestamp());
        json.put("horizonMinutes", trigger == null ? null : trigger.getHorizonMinutes());
        json.put("windowStart", observations.isEmpty() ? null : observations.get(0).getTimestamp());
        json.put("windowEnd", observations.isEmpty() ? null : observations.get(observations.size() - 1).getTimestamp());
        json.put("sampleCount", observations.size());
        json.put("triggerValue", evaluation.triggerValue);
        json.put("rawValue", trigger == null ? null : trigger.getRawValue());
        json.put("rawUnit", trigger == null ? null : trigger.getRawUnit());
        json.put("engineeringValue", trigger == null ? null : trigger.getEngineeringValue());
        json.put("engineeringUnit", trigger == null ? null : trigger.getEngineeringUnit());
        json.put("engineeringMetricCode", trigger == null ? null : trigger.getEngineeringMetricCode());
        json.put("valueMode", trigger == null ? null : trigger.getValueMode());
        json.put("conversionOperatorCode", trigger == null ? null : trigger.getConversionOperatorCode());
        json.put("conversionVersion", trigger == null ? null : trigger.getConversionVersion());
        json.put("conversionStatus", trigger == null ? null : trigger.getConversionStatus());
        json.put("conversionRemark", trigger == null ? null : trigger.getConversionRemark());
        json.put("thresholdValue", rule.getThresholdValue());
        json.put("thresholdValueUpper", rule.getThresholdValueUpper());
        json.put("matched", evaluation.matched);
        json.put("reason", evaluation.reason);
        json.put("consecutiveSteps", evaluation.consecutiveCount);
        json.put("inputDigest", inputDigest(rule, observations, evaluation));
        return json.toString();
    }

    private String stableEventCode(EventRule rule, List<MetricSeriesPoint> observations, EvaluationResult evaluation, boolean formal) {
        boolean prediction = evaluation.trigger != null && "PREDICTION".equalsIgnoreCase(evaluation.trigger.getSourceType());
        String prefix = prediction ? (formal ? "FEVT" : "SIM-FEVT") : (formal ? "EVT" : "SIM-EVT");
        String rulePart = rule.getId() == null ? "RULE" : String.valueOf(rule.getId());
        return prefix + "-" + rulePart + "-" + inputDigest(rule, observations, evaluation).substring(0, 20);
    }

    private String inputDigest(EventRule rule, List<MetricSeriesPoint> observations, EvaluationResult evaluation) {
        MetricSeriesPoint first = observations.isEmpty() ? null : observations.get(0);
        MetricSeriesPoint last = observations.isEmpty() ? null : observations.get(observations.size() - 1);
        MetricSeriesPoint trigger = evaluation.trigger;
        String material = value(rule.getId()) + "|" + value(rule.getCurrentVersion()) + "|" + value(rule.getRuleCode())
                + "|" + ruleMode(rule) + "|" + aggregation(rule) + "|" + normalizeOperator(rule.getOperator())
                + "|" + decimal(rule.getThresholdValue()) + "|" + decimal(rule.getThresholdValueUpper())
                + "|" + value(trigger == null ? null : trigger.getProjectId())
                + "|" + value(trigger == null ? null : trigger.getStationId())
                + "|" + value(trigger == null ? null : trigger.getInstrumentId())
                + "|" + value(trigger == null ? null : trigger.getSourceType())
                + "|" + value(trigger == null ? null : trigger.getSourceBatchId())
                + "|" + value(trigger == null ? null : trigger.getSourceRunId())
                + "|" + value(trigger == null ? null : trigger.getFeatureCode())
                + "|" + value(rule.getMetricCode())
                + "|" + value(trigger == null ? null : trigger.getConversionVersion())
                + "|" + decimal(trigger == null ? null : trigger.getRawValue())
                + "|" + decimal(trigger == null ? null : trigger.getEngineeringValue())
                + "|" + value(first == null ? null : first.getTimestamp())
                + "|" + value(last == null ? null : last.getTimestamp())
                + "|" + observations.size()
                + "|" + decimal(evaluation.triggerValue);
        return sha256(material);
    }

    private String decimal(BigDecimal value) {
        return value == null ? "" : value.stripTrailingZeros().toPlainString();
    }

    private String value(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String sha256(String material) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(material.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : bytes) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private static class EvaluationResult {
        private final boolean matched;
        private final MetricSeriesPoint trigger;
        private final BigDecimal triggerValue;
        private final String reason;
        private final int consecutiveCount;

        private EvaluationResult(boolean matched, MetricSeriesPoint trigger, BigDecimal triggerValue, String reason, int consecutiveCount) {
            this.matched = matched;
            this.trigger = trigger;
            this.triggerValue = triggerValue;
            this.reason = reason;
            this.consecutiveCount = consecutiveCount;
        }

        private static EvaluationResult notMatched(MetricSeriesPoint trigger, String reason) {
            return new EvaluationResult(false, trigger, trigger == null ? null : trigger.getValue(), reason, 0);
        }
    }
}
