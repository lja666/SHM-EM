package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class AuditLog {
    private Long id;
    private Long projectId;
    private Long actorId;
    private String actorName;
    private String actionType;
    private String objectType;
    private Long objectId;
    private String objectCode;
    private String beforeJson;
    private String afterJson;
    private String requestId;
    private String ipAddress;
    private LocalDateTime createdAt;
}
