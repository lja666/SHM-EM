package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.Project;

import java.util.List;

public interface ProjectService {
    List<Project> list(Long projectId, Integer limit);

    Project get(Long id);
}





