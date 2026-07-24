package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class StationMetric {
    private Long id;
    private Long projectId;
    private Long stationId;
    private Long instrumentId;
    private String metricCode;
    private String displayName;
    private String rawUnit;
    private String metricUnit;
    private String conversionOperatorCode;
    private BigDecimal baselineValue;
    private LocalDateTime baselineTime;
    private Integer warningEnabled;
    private Integer displayOrder;
    private String metadataJson;
    private String parameterJson;
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





