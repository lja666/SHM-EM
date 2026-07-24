package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.application.service.MetricSeriesProvider;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class PredictionSeriesProvider implements MetricSeriesProvider {
    private final PredictionService predictionService;

    public PredictionSeriesProvider(PredictionService predictionService) {
        this.predictionService = predictionService;
    }

    @Override
    public String sourceType() {
        return "PREDICTION";
    }

    @Override
    public List<MetricSeriesPoint> load(EventRule rule, RuleEvaluationRequest request) {
        PredictionQuery query = new PredictionQuery();
        query.setProjectId(request.getProjectId() == null ? rule.getProjectId() : request.getProjectId());
        query.setBatchId(request.getPredictionBatchId());
        query.setBatchCode(request.getPredictionBatchCode());
        query.setModelCode(request.getPredictionModelCode() == null ? rule.getPredictionModelCode() : request.getPredictionModelCode());
        query.setTargetType(request.getPredictionTargetType() == null ? rule.getPredictionTargetType() : request.getPredictionTargetType());
        query.setFeatureCode(request.getPredictionFeatureCode() == null ? rule.getPredictionFeatureCode() : request.getPredictionFeatureCode());
        query.setMetricCode(rule.getMetricCode());
        query.setStationIds(request.getStationIds());
        query.setInstrumentIds(request.getInstrumentIds());
        query.setStartTime(request.getStartTime());
        query.setEndTime(request.getEndTime());
        query.setMaxHorizonMinutes(request.getForecastHorizonMinutes() == null
                ? rule.getForecastHorizonMinutes() : request.getForecastHorizonMinutes());
        query.setQualityFilter(request.getSeriesQualityFilter() == null
                ? rule.getSeriesQualityFilter() : request.getSeriesQualityFilter());
        query.setLimit(50000);
        query.setValueMode("ENGINEERING");
        return predictionService.predictionSeries(query);
    }
}
