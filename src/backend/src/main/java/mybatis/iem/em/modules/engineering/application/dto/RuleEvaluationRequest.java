package mybatis.iem.em.modules.engineering.application.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class RuleEvaluationRequest {
    private Long ruleId;
    private Long projectId;
    private List<Long> stationIds;
    private List<Long> instrumentIds;
    private String instrumentType;
    private String metricCode;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;

    private String runMode = "evaluate";
    private Boolean customRule;
    private String eventLevel;
    private String operator;
    private BigDecimal thresholdValue;
    private List<ThresholdLevel> thresholds;
    private String thresholdUnit;
    private String inputSource;
    private Long predictionBatchId;
    private String predictionBatchCode;
    private String predictionModelCode;
    private String predictionTargetType;
    private String predictionFeatureCode;
    private Integer forecastHorizonMinutes;
    private Integer minimumConsecutiveSteps;
    private String seriesQualityFilter;
    private String predictionExecutionMode;

    @Data
    public static class ThresholdLevel {
        private String level;
        private BigDecimal thresholdValue;
    }
}
