package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class EventRule {
    private Long id;
    private Long projectId;
    private String ruleCode;
    private String ruleName;
    private String metricCode;
    private String sourceInstrumentType;
    private String inputSource;
    private String predictionModelCode;
    private String predictionTargetType;
    private String predictionFeatureCode;
    private Integer forecastHorizonMinutes;
    private Integer minimumConsecutiveSteps;
    private String seriesQualityFilter;
    private String stationScope;
    private String stationIdsJson;
    private String instrumentIdsJson;
    private String ruleMode;
    private String eventType;
    private String eventLevel;
    private String timeWindow;
    private String aggregationMethod;
    private String operator;
    private BigDecimal thresholdValue;
    private BigDecimal thresholdValueUpper;
    private String thresholdUnit;
    private String baselineStrategy;
    private String qualityPolicy;
    private String missingDataPolicy;
    private String resultPolicy;
    private Integer continuousCount;
    private Integer cooldownMinutes;
    private Integer cooldownSeconds;
    private String currentVersion;
    private String ruleSnapshotJson;
    private Long actionPolicyId;
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





