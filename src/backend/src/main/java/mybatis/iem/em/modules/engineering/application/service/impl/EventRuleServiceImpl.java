package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventRuleMapper;
import mybatis.iem.em.modules.engineering.application.service.EventRuleService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EventRuleServiceImpl implements EventRuleService {
    private final EventRuleMapper mapper;

    public EventRuleServiceImpl(EventRuleMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public List<EventRule> list(Long projectId, Integer limit) {
        return mapper.selectList(projectId, normalizeLimit(limit));
    }

    @Override
    public EventRule get(Long id) {
        return get(null, id);
    }

    @Override
    public EventRule get(Long projectId, Long id) {
        return projectId == null ? mapper.selectById(id) : mapper.selectByIdAndProject(id, projectId);
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 200;
        }
        return Math.min(limit, 1000);
    }
}





