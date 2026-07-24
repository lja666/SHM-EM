package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.AuditLog;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface AuditLogMapper {
    List<AuditLog> selectList(@Param("projectId") Long projectId,
                              @Param("actionType") String actionType,
                              @Param("limit") Integer limit);

    int insert(AuditLog auditLog);

    int countByRequestId(@Param("requestId") String requestId);
}
