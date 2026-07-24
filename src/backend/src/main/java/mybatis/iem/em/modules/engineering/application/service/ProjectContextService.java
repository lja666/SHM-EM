package mybatis.iem.em.modules.engineering.application.service;

import java.util.Map;

public interface ProjectContextService {
    Map<String, Object> overview();

    Map<String, Object> context(Long projectId);

    Map<String, Object> objectTree(Long projectId);
}
