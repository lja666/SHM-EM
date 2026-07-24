package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PredictionFeatureMapping {
    private Long id;
    private Long projectId;
    private Long modelId;
    private String featureCode;
    private String featureName;
    private String featureLabel;
    private String trainingFeatureCode;
    private String featureGroup;
    private String targetType;
    private String featureRole;
    private Long stationId;
    private Long instrumentId;
    private String sourceMetricCode;
    private String sourceRegistryCode;
    private String sourceField;
    private String sourceValueColumn;
    private String inputValueMode;
    private String schemaVersion;
    private String featureOperatorCode;
    private String outputConversionOperatorCode;
    private String outputConversionVersion;
    private String windowType;
    private Integer windowSizeSeconds;
    private Integer featureOrder;
    private Integer required;
    private Integer predictionTarget;
    private String transformJson;
    private String metadataJson;
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
