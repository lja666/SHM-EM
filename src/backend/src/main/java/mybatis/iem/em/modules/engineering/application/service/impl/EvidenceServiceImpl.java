package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.service.EvidenceService;
import mybatis.iem.em.modules.engineering.domain.model.Evidence;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EvidenceMapper;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
public class EvidenceServiceImpl implements EvidenceService {
    private final EvidenceMapper mapper;

    public EvidenceServiceImpl(EvidenceMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public List<Evidence> list(Long projectId, Integer limit) {
        List<Evidence> rows = mapper.selectEvidence(projectId, normalizeLimit(limit));
        return rows == null ? Collections.emptyList() : rows;
    }

    private int normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 100;
        }
        return Math.min(limit, 1000);
    }
}
