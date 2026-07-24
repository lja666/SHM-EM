package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class ProjectFutureState {
    private Long projectId;
    private Long batchId;
    private String batchCode;
    private LocalDateTime baseTime;
    private Integer horizonMinutes;
    private String executionMode;
    private Long gateId;
    private Boolean executionEligible;
    private List<String> executionBlockers = new ArrayList<String>();
    private String aggregationPolicyVersion;
    private String aggregationPolicyCode;
    private String aggregationPolicyHash;
    private String stateHash;
    private String observedRiskLevel;
    private Integer openObservedEventCount;
    private String forecastRiskLevel;
    private String overallRiskLevel;
    private LocalDateTime earliestExceedanceTime;
    private Integer assessedFeatureCount;
    private Integer unassessedFeatureCount;
    private PredictionExecutionGate executionGate;
    private List<TargetState> targets = new ArrayList<TargetState>();
    private List<StationState> stations = new ArrayList<StationState>();
    private List<TimelineState> timeline = new ArrayList<TimelineState>();

    @Data
    public static class TargetState {
        private String targetType;
        private Integer featureCount;
        private Integer assessedFeatureCount;
        private Integer warningCount;
        private Integer alarmCount;
        private String riskLevel;
        private BigDecimal minPredictedValue;
        private BigDecimal maxPredictedValue;
        private BigDecimal governingValue;
        private BigDecimal governingThreshold;
        private BigDecimal thresholdDistance;
        private BigDecimal peakValue;
        private String unit;
        private LocalDateTime firstExceedanceTime;
    }

    @Data
    public static class StationState {
        private Long stationId;
        private String stationName;
        private String riskLevel;
        private List<Contributor> contributors = new ArrayList<Contributor>();
    }

    @Data
    public static class Contributor {
        private String featureCode;
        private String featureLabel;
        private String targetType;
        private String metricCode;
        private BigDecimal predictedValue;
        private String unit;
        private BigDecimal thresholdValue;
        private String operator;
        private String riskLevel;
        private Integer riskRank;
        private LocalDateTime firstExceedanceTime;
        private String ruleCode;
    }

    @Data
    public static class TimelineState {
        private Integer step;
        private Integer horizonMinutes;
        private LocalDateTime futureTime;
        private String riskLevel;
        private Integer exceedingFeatureCount;
    }
}
