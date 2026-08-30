package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PredictionBatch {
    private Long id;
    private String batchCode;
    private Long projectId;
    private LocalDateTime baseTime;
    private Integer timeStepMinutes;
    private Integer horizonMinutes;
    private Integer rollingSteps;
    private Integer modelCount;
    private Integer featureCount;
    private String pipelineVersion;
    private String featureMappingVersion;
    private String inputHash;
    private String outputHash;
    private String persistedOutputHash;
    private String persistedOutputHashVersion;
    private String status;
    private String message;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
