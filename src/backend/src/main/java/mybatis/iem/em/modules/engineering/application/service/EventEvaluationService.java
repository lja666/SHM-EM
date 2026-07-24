package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;

import java.util.Map;

public interface EventEvaluationService {
    Map<String, Object> evaluate(RuleEvaluationRequest request);

    Map<String, Object> execute(RuleEvaluationRequest request);
}
