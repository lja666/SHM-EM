package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class Event {
    private Long id;
    private String eventCode;
    private Long projectId;
    private Long stationId;
    private Long instrumentId;
    private String metricCode;
    private Long ruleId;
    private Long evaluationRunId;
    private String eventType;
    private String eventLevel;
    private String eventStatus;
    private String sourceType;
    private String runType;
    private LocalDateTime detectedAt;
    private LocalDateTime windowStart;
    private LocalDateTime windowEnd;
    private BigDecimal triggerValue;
    private BigDecimal thresholdValue;
    private String unit;
    private String triggerReason;
    private String sourceRegistryCode;
    private String calculationSnapshotJson;
    private String acknowledgedBy;
    private LocalDateTime acknowledgedAt;
    private String resolvedBy;
    private LocalDateTime resolvedAt;
    private String closedBy;
    private LocalDateTime closedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Long predictionBatchId;
    private Long predictionRunId;
    private Long predictionModelId;
    private LocalDateTime predictionBaseTime;
    private LocalDateTime firstExceedanceTime;
    private Integer leadTimeMinutes;
    private BigDecimal peakPredictedValue;
    private Integer consecutiveExceedanceSteps;
    private String forecastSnapshotJson;
    private String predictionResultHash;
}





