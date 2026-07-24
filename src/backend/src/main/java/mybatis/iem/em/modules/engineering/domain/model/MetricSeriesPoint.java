package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class MetricSeriesPoint {
    private Long projectId;
    private Long stationId;
    private Long instrumentId;
    private String metricCode;
    private String engineeringMetricCode;
    private LocalDateTime timestamp;
    private BigDecimal value;
    private String unit;
    private BigDecimal rawValue;
    private String rawUnit;
    private BigDecimal engineeringValue;
    private String engineeringUnit;
    private String valueMode;
    private BigDecimal baselineValue;
    private String qualityFlag;
    private String conversionOperatorCode;
    private String conversionVersion;
    private String conversionStatus;
    private String conversionRemark;
    private String sourceType;
    private String sourceRegistryCode;
    private String sourceRecordKey;
    private Long sourceBatchId;
    private String sourceBatchCode;
    private Long sourceRunId;
    private Long sourceModelId;
    private String sourceModelCode;
    private String sourceModelVersion;
    private String targetType;
    private String featureCode;
    private String featureLabel;
    private Integer step;
    private Integer horizonMinutes;
    private LocalDateTime originTime;
    private BigDecimal lowerBound;
    private BigDecimal upperBound;
    private BigDecimal confidence;
    private String resultHash;
}
