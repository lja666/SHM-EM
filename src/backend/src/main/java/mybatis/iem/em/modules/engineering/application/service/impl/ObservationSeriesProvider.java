package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import mybatis.iem.em.modules.engineering.application.service.MetricSeriesProvider;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class ObservationSeriesProvider implements MetricSeriesProvider {
    private final LowFrequencyObservationService observationService;

    public ObservationSeriesProvider(LowFrequencyObservationService observationService) {
        this.observationService = observationService;
    }

    @Override
    public String sourceType() {
        return "OBSERVATION";
    }

    @Override
    public List<MetricSeriesPoint> load(EventRule rule, RuleEvaluationRequest request) {
        ObservationQuery query = new ObservationQuery();
        query.setProjectId(request.getProjectId() == null ? rule.getProjectId() : request.getProjectId());
        query.setMetricCode(rule.getMetricCode());
        query.setStationIds(request.getStationIds());
        query.setInstrumentIds(request.getInstrumentIds());
        query.setInstrumentType(request.getInstrumentType());
        query.setStartTime(request.getStartTime());
        query.setEndTime(request.getEndTime());
        query.setLimit(2000);
        List<MetricSeriesPoint> rows = new ArrayList<MetricSeriesPoint>();
        for (LowFrequencyObservation item : observationService.list(query)) {
            MetricSeriesPoint point = new MetricSeriesPoint();
            point.setProjectId(item.getProjectId());
            point.setStationId(item.getStationId());
            point.setInstrumentId(item.getInstrumentId());
            point.setMetricCode(item.getEngineeringMetricCode() == null ? item.getMetricCode() : item.getEngineeringMetricCode());
            point.setEngineeringMetricCode(item.getEngineeringMetricCode());
            point.setTimestamp(item.getObservedAt());
            point.setValue(item.getMetricValue());
            point.setUnit(item.getMetricUnit());
            point.setRawValue(item.getRawValue());
            point.setRawUnit(item.getRawUnit());
            point.setEngineeringValue(item.getEngineeringValue());
            point.setEngineeringUnit(item.getEngineeringUnit());
            point.setValueMode("ENGINEERING");
            point.setBaselineValue(item.getBaselineValue());
            point.setQualityFlag(item.getQualityFlag());
            point.setConversionOperatorCode(item.getConversionOperatorCode());
            point.setConversionVersion(item.getConversionVersion());
            point.setConversionStatus(item.getConversionStatus());
            point.setConversionRemark(item.getConversionRemark());
            point.setSourceType(sourceType());
            point.setSourceRegistryCode(item.getSourceRegistryCode());
            point.setSourceRecordKey(item.getSourceRecordKey());
            rows.add(point);
        }
        return rows;
    }
}
