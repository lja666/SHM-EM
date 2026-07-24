package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.service.AuditLogService;
import mybatis.iem.em.modules.engineering.domain.model.AuditLog;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.AuditLogMapper;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AuditLogServiceImpl implements AuditLogService {
    private final AuditLogMapper mapper;

    public AuditLogServiceImpl(AuditLogMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public List<AuditLog> list(Long projectId, String actionType, Integer limit) {
        return mapper.selectList(projectId, actionType, normalizeLimit(limit));
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 100;
        }
        return Math.min(limit, 1000);
    }
}
