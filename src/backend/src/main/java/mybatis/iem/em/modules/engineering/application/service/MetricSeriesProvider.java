package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;

import java.util.List;

public interface MetricSeriesProvider {
    String sourceType();

    default boolean supports(String inputSource) {
        return sourceType().equalsIgnoreCase(inputSource);
    }

    List<MetricSeriesPoint> load(EventRule rule, RuleEvaluationRequest request);
}
