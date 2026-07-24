package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.Evidence;

import java.util.List;

public interface EvidenceService {
    List<Evidence> list(Long projectId, Integer limit);
}
