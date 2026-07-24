package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.EventRule;

import java.util.List;

public interface EventRuleService {
    List<EventRule> list(Long projectId, Integer limit);

    EventRule get(Long id);

    EventRule get(Long projectId, Long id);
}





