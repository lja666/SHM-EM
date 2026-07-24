package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class FutureRiskThreshold {
    private Long ruleId;
    private String ruleCode;
    private String metricCode;
    private String levelCode;
    private Integer levelRank;
    private String operator;
    private BigDecimal thresholdValue;
    private BigDecimal thresholdValueUpper;
    private String thresholdUnit;
    private Integer minimumConsecutiveSteps;
}
