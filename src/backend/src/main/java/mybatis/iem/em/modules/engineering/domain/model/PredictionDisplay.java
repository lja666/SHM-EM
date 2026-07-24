package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class PredictionDisplay {
    private Long id;
    private Long projectId;
    private Long batchId;
    private String batchCode;
    private Long runId;
    private Long modelId;
    private String modelCode;
    private String modelVersion;
    private String targetType;
    private String featureCode;
    private String featureLabel;
    private Long stationId;
    private String stationName;
    private Long instrumentId;
    private String instrumentCode;
    private String metricCode;
    private String engineeringMetricCode;
    private Integer step;
    private Integer horizonMinutes;
    private LocalDateTime baseTime;
    private LocalDateTime futureTime;
    private BigDecimal predictedValue;
    private String predictedUnit;
    private BigDecimal rawPredictedValue;
    private String rawPredictedUnit;
    private BigDecimal engineeringValue;
    private String engineeringUnit;
    private BigDecimal rawLowerBound;
    private BigDecimal rawUpperBound;
    private String conversionOperatorCode;
    private String conversionVersion;
    private String conversionStatus;
    private String conversionRemark;
    private BigDecimal lowerBound;
    private BigDecimal upperBound;
    private BigDecimal confidence;
    private String qualityFlag;
    private String sourceRecordKey;
    private String runResultHash;
    private String batchOutputHash;
    private LocalDateTime createdAt;
}
