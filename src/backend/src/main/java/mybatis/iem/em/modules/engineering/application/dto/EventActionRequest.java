package mybatis.iem.em.modules.engineering.application.dto;

import lombok.Data;

@Data
public class EventActionRequest {
    private Long operatorId;
    private String operatorName;
    private String operatorRole;
    private String reason;
    private String assignee;
    private String targetLevel;
    private String requestId;
    private String dataVersion;
}
