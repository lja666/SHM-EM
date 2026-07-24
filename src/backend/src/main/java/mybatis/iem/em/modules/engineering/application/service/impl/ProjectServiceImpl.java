package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectMapper;
import mybatis.iem.em.modules.engineering.application.service.ProjectService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ProjectServiceImpl implements ProjectService {
    private final ProjectMapper mapper;

    public ProjectServiceImpl(ProjectMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public List<Project> list(Long projectId, Integer limit) {
        return mapper.selectList(projectId, normalizeLimit(limit));
    }

    @Override
    public Project get(Long id) {
        return mapper.selectById(id);
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 200;
        }
        return Math.min(limit, 1000);
    }
}





