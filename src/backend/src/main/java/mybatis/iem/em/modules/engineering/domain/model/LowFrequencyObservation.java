package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class LowFrequencyObservation {
    private Long id;
    private Long projectId;
    private Long stationId;
    private Long instrumentId;
    private String metricCode;
    private String engineeringMetricCode;
    private LocalDateTime observedAt;
    private BigDecimal rawValue;
    private String rawUnit;
    private BigDecimal metricValue;
    private String metricUnit;
    private BigDecimal engineeringValue;
    private String engineeringUnit;
    private BigDecimal baselineValue;
    private String qualityFlag;
    private String conversionOperatorCode;
    private String conversionVersion;
    private String conversionStatus;
    private String conversionRemark;
    private String sourceRegistryCode;
    private String sourceRecordKey;
    private LocalDateTime createdAt;
}





