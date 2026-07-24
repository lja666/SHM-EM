package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.AuditLog;

import java.util.List;

public interface AuditLogService {
    List<AuditLog> list(Long projectId, String actionType, Integer limit);
}
