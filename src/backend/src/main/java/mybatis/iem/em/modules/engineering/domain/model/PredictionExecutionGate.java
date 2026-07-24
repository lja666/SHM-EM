package mybatis.iem.em.modules.engineering.domain.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class PredictionExecutionGate {
    private Long id;
    private Long batchId;
    private Long projectId;
    private String batchCode;
    private String executionMode;
    private LocalDateTime referenceTime;
    private String contractVersion;
    private String contractFingerprint;
    private Integer expectedModelCount;
    private Integer actualModelCount;
    private Integer successfulModelCount;
    private Integer expectedFeatureCount;
    private Integer actualFeatureCount;
    private Integer expectedSteps;
    private Integer expectedPointCount;
    private Integer actualPointCount;
    private Integer missingPointCount;
    private Integer invalidTimestampCount;
    private Integer qualityIssueCount;
    private Long baseTimeAgeMinutes;
    private Integer maxAgeMinutes;
    private Boolean modelSetValid;
    private Boolean featureSetValid;
    private Boolean timelineValid;
    private Boolean qualityValid;
    private Boolean artifactHashValid;
    private Boolean freshnessValid;
    private Boolean executionEligible;
    private String gateHash;
    private LocalDateTime evaluatedAt;
    private List<String> issues = new ArrayList<String>();
    private List<String> missingModels = new ArrayList<String>();
    private List<String> unexpectedModels = new ArrayList<String>();
    private List<String> missingFeatures = new ArrayList<String>();
    private List<String> unexpectedFeatures = new ArrayList<String>();
    private List<String> missingTimelinePoints = new ArrayList<String>();
    private List<PredictionCompleteness.TargetCompleteness> targets = new ArrayList<PredictionCompleteness.TargetCompleteness>();

    @JsonIgnore
    private String issuesJson;
    @JsonIgnore
    private String missingModelsJson;
    @JsonIgnore
    private String unexpectedModelsJson;
    @JsonIgnore
    private String missingFeaturesJson;
    @JsonIgnore
    private String unexpectedFeaturesJson;
    @JsonIgnore
    private String missingTimelinePointsJson;
    @JsonIgnore
    private String targetSummaryJson;
}
