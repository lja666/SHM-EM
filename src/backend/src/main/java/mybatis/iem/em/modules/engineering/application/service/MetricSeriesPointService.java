package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MetricSeriesPointService {
    private final List<MetricSeriesProvider> providers;

    public MetricSeriesPointService(List<MetricSeriesProvider> providers) {
        this.providers = providers;
    }

    public List<MetricSeriesPoint> load(EventRule rule, RuleEvaluationRequest request) {
        String inputSource = normalizeSource(request.getInputSource(), rule.getInputSource());
        for (MetricSeriesProvider provider : providers) {
            if (provider.supports(inputSource)) {
                return provider.load(rule, request);
            }
        }
        throw new BusinessException("Unsupported rule input source: " + inputSource);
    }

    public String resolveInputSource(EventRule rule, RuleEvaluationRequest request) {
        return normalizeSource(request.getInputSource(), rule.getInputSource());
    }

    private String normalizeSource(String requested, String configured) {
        String value = requested == null || requested.trim().isEmpty() ? configured : requested;
        if (value == null || value.trim().isEmpty()) {
            return "OBSERVATION";
        }
        String normalized = value.trim().toUpperCase();
        return "FORECAST".equals(normalized) ? "PREDICTION" : normalized;
    }
}
