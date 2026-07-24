package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class EventPredictionTrace {
    private Long id;
    private Long eventId;
    private String eventCode;
    private String eventSource;
    private Long predictionBatchId;
    private String batchCode;
    private LocalDateTime baseTime;
    private Integer horizonMinutes;
    private String batchStatus;
    private String pipelineVersion;
    private String featureMappingVersion;
    private String inputHash;
    private String outputHash;
    private Long predictionRunId;
    private Long predictionGateId;
    private Long modelId;
    private String modelCode;
    private String modelVersion;
    private String targetType;
    private LocalDateTime inputWindowStart;
    private LocalDateTime inputWindowEnd;
    private String artifactHash;
    private String inputSchemaHash;
    private String runResultHash;
    private LocalDateTime firstExceedanceTime;
    private Integer leadTimeMinutes;
    private BigDecimal peakPredictedValue;
    private Integer consecutiveExceedanceSteps;
    private String forecastSnapshotJson;
    private String resultHash;
    private String gateExecutionMode;
    private Boolean gateExecutionEligible;
    private String gateHash;
    private String gateIssuesJson;
    private LocalDateTime gateEvaluatedAt;
    private LocalDateTime createdAt;
}
