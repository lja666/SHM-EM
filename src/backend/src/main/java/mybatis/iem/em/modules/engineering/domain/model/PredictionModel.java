package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PredictionModel {
    private Long id;
    private Long projectId;
    private String modelCode;
    private String modelName;
    private String modelType;
    private String targetType;
    private String targetMetricCode;
    private String inputMetricsJson;
    private String artifactUri;
    private String artifactHash;
    private String preprocessorUri;
    private String preprocessorHash;
    private String inferenceScriptHash;
    private String bestParamsHash;
    private String runtimeManifestHash;
    private String environmentDigest;
    private String artifactBundleHash;
    private String modelVersion;
    private String runtimeConfigJson;
    private Integer requiredHistoryRows;
    private String inputSchemaHash;
    private String contractVersion;
    private Integer expectedSteps;
    private Integer timeStepMinutes;
    private Integer maxOperationalAgeMinutes;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
