package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class PredictionRun {
    private Long id;
    private Long projectId;
    private Long batchId;
    private Long modelId;
    private String modelCode;
    private String modelVersion;
    private String targetType;
    private String artifactHash;
    private String preprocessorHash;
    private String inferenceScriptHash;
    private String bestParamsHash;
    private String runtimeManifestHash;
    private String environmentDigest;
    private String artifactBundleHash;
    private String inputSchemaHash;
    private Integer requiredHistoryRows;
    private Long stationId;
    private Long instrumentId;
    private String metricCode;
    private LocalDateTime inputWindowStart;
    private LocalDateTime inputWindowEnd;
    private Integer horizonSeconds;
    private Integer horizonMinutes;
    private Integer rollingSteps;
    private String inputSnapshotJson;
    private String status;
    private String message;
    private String resultHash;
    private BigDecimal runtimeSeconds;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private LocalDateTime createdAt;
}
