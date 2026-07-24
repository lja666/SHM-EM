package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Data
public class PredictionCompleteness {
    private Long gateId;
    private Long batchId;
    private String batchCode;
    private Integer expectedModels;
    private Integer actualModels;
    private Integer successfulModels;
    private Integer expectedSteps;
    private Integer featureCount;
    private Integer expectedPointCount;
    private Integer actualPointCount;
    private Integer missingPointCount;
    private BigDecimal completenessPercent;
    private Boolean complete;
    private String batchStatus;
    private Integer invalidTimestampCount;
    private Integer qualityIssueCount;
    private Boolean executionEligible;
    private String executionMode;
    private Boolean modelSetValid;
    private Boolean featureSetValid;
    private Boolean timelineValid;
    private Boolean qualityValid;
    private Boolean artifactHashValid;
    private Boolean freshnessValid;
    private List<String> issues = new ArrayList<String>();
    private List<TargetCompleteness> targets = new ArrayList<TargetCompleteness>();

    @Data
    public static class TargetCompleteness {
        private String targetType;
        private Integer featureCount;
        private Integer expectedPointCount;
        private Integer actualPointCount;
        private Integer missingPointCount;
        private BigDecimal completenessPercent;
        private Boolean complete;
        private Integer coveredSteps;
        private Integer qualityIssueCount;
        private List<String> missingPoints = new ArrayList<String>();
    }
}
