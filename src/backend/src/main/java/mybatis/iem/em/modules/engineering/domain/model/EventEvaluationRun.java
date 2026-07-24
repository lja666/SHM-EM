package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class EventEvaluationRun {
    private Long id;
    private Long projectId;
    private Long ruleId;
    private String runMode;
    private String ruleVersion;
    private String conversionVersion;
    private String inputRegistryCode;
    private LocalDateTime timeStart;
    private LocalDateTime timeEnd;
    private String inputParamsJson;
    private Integer eventCount;
    private String resultSummaryJson;
    private String resultHash;
    private String status;
    private String message;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private String createdBy;
}





